import boto3
import json

runtime = boto3.client("sagemaker-runtime")

endpoint = "bank-churn-endpoint"

payload = [[45, 1, 2000, 0, 1, 1, 0, 50000]]

response = runtime.invoke_endpoint(
    EndpointName=endpoint,
    ContentType="application/json",
    Body=json.dumps(payload)
)

result = json.loads(response["Body"].read().decode())
print(result)
