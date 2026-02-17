# deployment/deploy_lambda.py

import boto3

sm = boto3.client("sagemaker")

def lambda_handler(event, context):

    model_name = event["model_name"]

    sm.update_endpoint(
        EndpointName="bank-churn-endpoint",
        EndpointConfigName=model_name
    )

    return {"status": "deployed"}
