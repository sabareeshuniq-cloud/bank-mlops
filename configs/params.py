import yaml
import os

ENV = os.environ.get("ENV", "dev")

with open(f"configs/{ENV}.yaml") as f:
    config = yaml.safe_load(f)

PROJECT = config["project"]
REGION = config["region"]
TRAIN_INSTANCE = config["training_instance"]
PROCESS_INSTANCE = config["processing_instance"]
ENDPOINT_INSTANCE = config["endpoint_instance"]
ACCURACY_THRESHOLD = config["min_accuracy"]
BUCKET_PREFIX = config["bucket_prefix"]
