import pandas as pd
import numpy as np

np.random.seed(42)
n = 50000

df = pd.DataFrame({
    "txn_amount": np.random.gamma(2, 1500, n),
    "account_age_days": np.random.randint(10, 4000, n),
    "num_failed_logins": np.random.poisson(1.5, n),
    "device_change": np.random.binomial(1, 0.2, n),
    "ip_risk_score": np.random.uniform(0, 1, n),
    "txn_hour": np.random.randint(0,24,n)
})

df["risk"] = (
    (df.txn_amount > 20000) |
    (df.ip_risk_score > 0.8) |
    (df.device_change == 1) & (df.num_failed_logins > 2)
).astype(int)

df.to_csv("payments.csv", index=False)
