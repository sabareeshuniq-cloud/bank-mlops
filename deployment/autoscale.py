# deployment/autoscale.py

import boto3

client = boto3.client("application-autoscaling")

resource_id = "endpoint/bank-churn-endpoint/variant/AllTraffic"

client.register_scalable_target(
    ServiceNamespace="sagemaker",
    ResourceId=resource_id,
    ScalableDimension="sagemaker:variant:DesiredInstanceCount",
    MinCapacity=1,
    MaxCapacity=4,
)

print("Autoscaling target registered")
