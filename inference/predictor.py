import xgboost as xgb
import json
import pandas as pd

model = xgb.Booster()
model.load_model("model.json")

def predict(data):
    df = pd.DataFrame([data])
    prob = model.predict(xgb.DMatrix(df))[0]

    if prob < 0.3:
        decision = "ALLOW"
    elif prob < 0.7:
        decision = "STEP_UP_AUTH"
    else:
        decision = "BLOCK"

    return {"risk_score": float(prob), "decision": decision}
