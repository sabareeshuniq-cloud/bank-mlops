import xgboost as xgb
import pandas as pd
import os

train = pd.read_parquet("/opt/ml/input/data/train")
X = train.drop("risk", axis=1)
y = train["risk"]

model = xgb.XGBClassifier(
    objective="binary:logistic",
    eval_metric="auc",
    reg_alpha=1,   # L1
    reg_lambda=1,  # L2
    max_depth=6,
    eta=0.1
)

model.fit(X,y)

model.save_model("/opt/ml/model/model.json")
