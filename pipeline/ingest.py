import sys
import pandas as pd

df = pd.DataFrame({"day": [1, 2], "month": ["January","December"], "year": [2025, 2026]}) #source
df.to_parquet() #compress

print('hello pipeline cutie', sys.argv) 

age = int(sys.argv[1])
dollar = int(sys.argv[3])

print(f'one day you will be {age} ')
print(f'I have AUD {dollar} as I am rich')

## dealing with file
df = pd.DataFrame({"Fruit": ["banana", "pineapple", "orange", "kiwi", "nectarin"], 
                   "Amount": [14, 49, 32,46,11]})
print(df.head())

df.to_parquet(f"output_day_{sys.argv[1]}.parquet")