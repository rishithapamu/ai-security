import pandas as pd

df = pd.read_parquet("data/processed/combined.parquet")
df.to_csv("data/processed/combined.csv", index=False)
