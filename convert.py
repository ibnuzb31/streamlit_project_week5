import pandas as pd

df = pd.read_excel("sesuaikan_file.xlsx")
df.to_parquet("sesuaikan_file.parquet", index=False)
