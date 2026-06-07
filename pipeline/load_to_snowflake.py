import logging
import os
import re
from pathlib import Path
import snowflake.connector
from dotenv import load_dotenv
from snowflake.connector import DictCursor
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# ==============================
# LOGGING
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename="pipeline.log"
)
logger = logging.getLogger(__name__)

# ==============================
# LOAD ENV VARIABLES
# ==============================
load_dotenv()
RAW_FOLDER = Path(__file__).parent.parent / "data" / "raw"
STAGE_NAME = "bne_rental_stage"

# ==============================
# VALIDATE ENV
# ==============================
def validate_env() -> None:
    required = [
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA",
        "SNOWFLAKE_ROLE",
    ]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")

# ==============================
# CONNECTION
# ==============================
def get_connection() -> snowflake.connector.SnowflakeConnection:
    with open(os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"), "rb") as f:
        private_key_bytes = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        ).private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
        private_key=private_key_bytes,
        session_parameters={"QUERY_TAG": "bne_project_loader"},
    )

# ==============================
# CLEAN TABLE NAME
# ==============================
def clean_table_name(file_name: str) -> str:
    """
    -uppercase table name from a parquet filename.
    -strips the extension, replaces non-alphanumeric chars with underscores,
    -trims leading/trailing underscores.
    """
    name = Path(file_name).stem                  # strip .parquet (handles multi-dot names)
    name = re.sub(r"[^a-zA-Z0-9]+", "_", name)  # replace unsafe chars
    name = name.strip("_")
    return name.upper()

# ==============================
# CREATE STAGE
# ==============================
def create_stage(conn: snowflake.connector.SnowflakeConnection) -> None:
    """Create the internal stage if it does not already exist. place to store object in snow"""
    with conn.cursor() as cur:
        cur.execute(f"CREATE STAGE IF NOT EXISTS {STAGE_NAME}")
    logger.info("Stage '%s' is ready.", STAGE_NAME)

# ==============================
# CREATE FILE FORMAT -- got error many times due to file format parquet 
# ==============================
def create_file_format(conn: snowflake.connector.SnowflakeConnection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE FILE FORMAT IF NOT EXISTS BRISBANE_RENTAL_DB.RAW.PARQUET_FORMAT
                TYPE = PARQUET
        """)
    logger.info("File format 'PARQUET_FORMAT' is ready.")
# ==============================
# CREATE TABLE
# ==============================
def create_table(conn: snowflake.connector.SnowflakeConnection, table_name: str, staged_file: str) -> None:
    # Step 1 — fetch schema from staged file
    with conn.cursor(DictCursor) as cur:
        cur.execute(f"""
            SELECT COLUMN_NAME, TYPE
            FROM TABLE(
                INFER_SCHEMA(
                    LOCATION => '@{STAGE_NAME}/{staged_file}',
                    FILE_FORMAT => 'BRISBANE_RENTAL_DB.RAW.PARQUET_FORMAT'
                )
            )
            ORDER BY ORDER_ID
        """)
        columns = cur.fetchall()

    if not columns:
        raise RuntimeError(f"INFER_SCHEMA returned no columns for '{staged_file}'.")

    # Step 2 — build column definitions from inferred schema
    col_defs = ", ".join(
        f"{row['COLUMN_NAME']} {row['TYPE']}"
        for row in columns
    )

    # Step 3 — create table with actual typed columns
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} ({col_defs})
        """)
    logger.info("Table '%s' is ready with %d column(s).", table_name, len(columns))

# ==============================
# UPLOAD FILE TO STAGE
# ==============================
def load_to_stage(conn: snowflake.connector.SnowflakeConnection,file_path: Path,) -> None:
    """
    a local Parquet --> Snowflake internal stage.
    """
    # Snowflake PUT requires forward slashes and an absolute path
    abs_path = file_path.resolve().as_posix()
    put_cmd = (
        f"PUT 'file://{abs_path}' @{STAGE_NAME} "
        f"AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
    )
    with conn.cursor(DictCursor) as cur:
        cur.execute(put_cmd)
        result = cur.fetchone()

    if not result:
        raise RuntimeError(f"PUT '{file_path.name}' returned no result.")

    status = result.get("status", "UNKNOWN")

    if status != "UPLOADED":
        raise RuntimeError(
            f"PUT '{file_path.name}' failed with status='{status}'."
        )
    logger.info("Uploaded '%s' to stage '%s'.", file_path.name, STAGE_NAME)

# ==============================
# remove STAGE FILES after being copied to table
# ==============================
def cleanup_staged_file(conn: snowflake.connector.SnowflakeConnection,file_name: str,) -> None:
    """
    Remove a specific file from the stage after a successful COPY INTO
    so the stage does not accumulate stale files
    """
    with conn.cursor() as cur:
        cur.execute(f"REMOVE @{STAGE_NAME}/{file_name}")
    logger.debug("Clean up staged file '%s'.", file_name)

# ==============================
# COPY parquet file from stage INTO TABLE
# ==============================
def copy_into_table(conn: snowflake.connector.SnowflakeConnection, table_name: str, file_name: str) -> int:
    staged_file = f"{file_name}"
    with conn.cursor(DictCursor) as cur:
        cur.execute(f"""
            COPY INTO {table_name}
            FROM @{STAGE_NAME}/{staged_file}
            FILE_FORMAT = (TYPE = PARQUET)
            MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
            FORCE = FALSE
            ON_ERROR = 'ABORT_STATEMENT'
        """)
        result = cur.fetchone()

    if not result:
        raise RuntimeError(f"COPY INTO '{table_name}' returned no result.")

    status = result.get("status", "UNKNOWN")
    rows_loaded = result.get("rows_loaded", 0)

    logger.info("COPY INTO '%s': status=%s, rows_loaded=%d.", table_name, status, rows_loaded)
    # ← THIS is what triggers the skip of cleanup_staged_file.  *********** check again 
    if status not in ("LOADED", "PARTIALLY_LOADED"):
        raise RuntimeError(
            f"COPY INTO '{table_name}' failed with status='{status}'. "
            f"File '{staged_file}' retained in stage for inspection."
        )
    return rows_loaded
# ==============================
# PROCESS SINGLE FILE
# ==============================
def process_file(conn: snowflake.connector.SnowflakeConnection, file_path: Path) -> None:
    """Full load pipeline"""
    table_name = clean_table_name(file_path.name)
    staged_file = f"{file_path.name}"
    
    logger.info("Processing '%s' → table '%s'.", file_path.name, table_name)

    load_to_stage(conn, file_path)                                        
    create_table(conn, table_name, staged_file)
    rows = copy_into_table(conn, table_name, file_path.name)
    cleanup_staged_file(conn, file_path.name)

    logger.info("Done: '%s' (%d rows loaded).", table_name, rows)

# ==============================
# MAIN LOADER
# ==============================
def load_all() -> None:
    """
    Discover all Parquet files in RAW_FOLDER and load each into Snowflake.
    Errors on individual files are logged but do not abort the remaining files.
    """
    validate_env()
    if not RAW_FOLDER.exists():
        raise FileNotFoundError(f"RAW_FOLDER does not exist: {RAW_FOLDER}")

    parquet_files = sorted(RAW_FOLDER.glob("*.parquet"))
    if not parquet_files:
        logger.warning("No .parquet files found in '%s'. Nothing to load.", RAW_FOLDER)
        return

    logger.info("Found %d parquet file(s) to load.", len(parquet_files))

    conn = get_connection()
    try:
        create_stage(conn)
        create_file_format(conn) 
        failed: list[str] = []
        for parquet_path in parquet_files:
            try:
                process_file(conn, parquet_path)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to load '%s': %s", parquet_path.name, exc, exc_info=True)
                failed.append(parquet_path.name)
        if failed:
            logger.warning(
                "⚠️ %d/%d file(s) failed to load: %s",
                len(failed), len(parquet_files), failed
            )
            raise RuntimeError(
                f"Load completed with {len(failed)} failure(s): {failed}"
            )

        logger.info("✅ All parquet files loaded successfully into Snowflake.")
    finally:
        conn.close()
# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    load_all()