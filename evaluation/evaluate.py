from sklearn.metrics import precision_score, recall_score, roc_auc_score
import json

precision = precision_score(y_test, pred)
recall = recall_score(y_test, pred)
auc = roc_auc_score(y_test, prob)

metrics = {
    "precision": precision,
    "recall": recall,
    "auc": auc
}

with open("/opt/ml/processing/evaluation/evaluation.json","w") as f:
    json.dump(metrics,f)
