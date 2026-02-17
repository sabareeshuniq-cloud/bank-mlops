import pandas as pd
import numpy as np
import os

os.makedirs("data/raw", exist_ok=True)

np.random.seed(42)

n = 1000

df = pd.DataFrame({
    "age": np.random.randint(18, 70, n),
    "balance": np.random.randint(0, 100000, n),
    "tenure": np.random.randint(0, 10, n),
    "num_products": np.random.randint(1, 4, n),
    "is_active": np.random.randint(0, 2, n),
    "estimated_salary": np.random.randint(20000, 150000, n),
})

df["churn"] = (
    (df["balance"] < 20000) &
    (df["is_active"] == 0) &
    (df["num_products"] == 1)
).astype(int)

df.to_csv("data/raw/data.csv", index=False)

print("Dataset generated at data/raw/data.csv")
