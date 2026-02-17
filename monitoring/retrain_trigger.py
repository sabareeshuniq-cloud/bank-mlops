# monitoring/retrain_trigger.py

import boto3

client = boto3.client("sagemaker")

PIPELINE_NAME = "BankChurnPipeline"

def trigger_retraining():
    response = client.start_pipeline_execution(
        PipelineName=PIPELINE_NAME
    )
    print("Retraining triggered:", response["PipelineExecutionArn"])

if __name__ == "__main__":
    trigger_retraining()
