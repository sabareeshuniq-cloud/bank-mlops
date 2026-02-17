# processing/preprocess.py

import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

INPUT_PATH = "/opt/ml/processing/input"
TRAIN_PATH = "/opt/ml/processing/train"
TEST_PATH = "/opt/ml/processing/test"

os.makedirs(TRAIN_PATH, exist_ok=True)
os.makedirs(TEST_PATH, exist_ok=True)

print("Reading dataset...")
df = pd.read_csv(f"{INPUT_PATH}/data.csv")

# Drop customer id (not useful for training)
if "customer_id" in df.columns:
    df = df.drop(columns=["customer_id"])

# Encode categorical columns
for col in df.select_dtypes(include="object").columns:
    df[col] = LabelEncoder().fit_transform(df[col])

# Target column
target = "churn"

X = df.drop(columns=[target])
y = df[target]

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

train = pd.concat([y_train, X_train], axis=1)
test = pd.concat([y_test, X_test], axis=1)

train.to_csv(f"{TRAIN_PATH}/train.csv", index=False, header=False)
test.to_csv(f"{TEST_PATH}/test.csv", index=False, header=False)

print("Preprocessing complete")
