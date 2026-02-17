# inference/inference.py

import json
import xgboost as xgb
import numpy as np
import os

MODEL_PATH = "/opt/ml/model/model.xgb"

def model_fn(model_dir):
    model = xgb.Booster()
    model.load_model(os.path.join(model_dir, "model.xgb"))
    return model

def input_fn(request_body, content_type):
    if content_type == "application/json":
        data = json.loads(request_body)
        return xgb.DMatrix(np.array(data))
    raise ValueError("Unsupported content type")

def predict_fn(input_data, model):
    preds = model.predict(input_data)
    return preds.tolist()

def output_fn(prediction, accept):
    return json.dumps({"prediction": prediction}), "application/json"
