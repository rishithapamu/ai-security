import pandas as pd

df = pd.read_parquet(
    "/Users/rishithapamu/Desktop/internship_project/ai-sec-workbench/ai-sec-workbench/data/processed/advbench.parquet"
)
df.to_csv(
    "/Users/rishithapamu/Desktop/internship_project/ai-sec-workbench/ai-sec-workbench/data/processed/advbench.csv",
    index=False,
)
