import pandas as pd

df = pd.read_excel("data_yield_2000_2021.xlsx")
df.to_parquet("data_yield_2000_2021.parquet", index=False)