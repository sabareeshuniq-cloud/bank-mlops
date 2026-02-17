# training/train.py

import pandas as pd
import xgboost as xgb
import os
import json

TRAIN_PATH = "/opt/ml/input/data/train/train.csv"
MODEL_DIR = "/opt/ml/model"

print("Loading training data...")
data = pd.read_csv(TRAIN_PATH, header=None)

y = data.iloc[:, 0]
X = data.iloc[:, 1:]

dtrain = xgb.DMatrix(X, label=y)

params = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "max_depth": 5,
    "eta": 0.2
}

print("Training model...")
model = xgb.train(params, dtrain, num_boost_round=100)

os.makedirs(MODEL_DIR, exist_ok=True)
model.save_model(f"{MODEL_DIR}/model.xgb")

print("Model saved!")
