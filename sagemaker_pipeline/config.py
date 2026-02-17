# sagemaker_pipeline/config.py
import boto3
import sagemaker

REGION = boto3.Session().region_name
BUCKET = sagemaker.Session().default_bucket()
ROLE = sagemaker.get_execution_role()

PROJECT_NAME = "bank-churn-mlops"

MODEL_PACKAGE_GROUP_NAME = "bank-churn-model-group"

TRAIN_INSTANCE = "ml.m5.large"
PROCESS_INSTANCE = "ml.m5.large"

ACCURACY_THRESHOLD = 0.75
