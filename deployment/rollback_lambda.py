# deployment/rollback_lambda.py

import boto3

sm = boto3.client("sagemaker")

def lambda_handler(event, context):

    previous_config = event["previous_endpoint_config"]

    sm.update_endpoint(
        EndpointName="bank-churn-endpoint",
        EndpointConfigName=previous_config
    )

    return {"status": "rolled_back"}
