# evaluation/evaluate.py

import json
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score
import os

MODEL_PATH = "/opt/ml/processing/model/model.xgb"
TEST_PATH = "/opt/ml/processing/test/test.csv"
OUTPUT_PATH = "/opt/ml/processing/evaluation"

os.makedirs(OUTPUT_PATH, exist_ok=True)

print("Loading model...")
model = xgb.Booster()
model.load_model(MODEL_PATH)

print("Loading test data...")
data = pd.read_csv(TEST_PATH, header=None)

y_true = data.iloc[:, 0]
X_test = data.iloc[:, 1:]

dtest = xgb.DMatrix(X_test)

preds = model.predict(dtest)
pred_labels = [1 if p > 0.5 else 0 for p in preds]

acc = accuracy_score(y_true, pred_labels)

print("Accuracy:", acc)

with open(f"{OUTPUT_PATH}/evaluation.json", "w") as f:
    json.dump({"accuracy": float(acc)}, f)
