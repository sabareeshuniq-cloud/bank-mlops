import os
import boto3

sm = boto3.client("sagemaker")


def lambda_handler(event, context):
    """Rollback a SageMaker endpoint to the previous EndpointConfigName.

    Expects the endpoint name in event['endpoint'] or via ENV var ENDPOINT_NAME. The previous
    endpoint config name is read from the endpoint tags key 'previous_endpoint_config'.
    """
    endpoint = event.get("endpoint") or os.environ.get("ENDPOINT_NAME", "bank-risk-endpoint")

    try:
        ep = sm.describe_endpoint(EndpointName=endpoint)
    except sm.exceptions.ResourceNotFound:
        return {"status": "error", "message": f"Endpoint {endpoint} not found"}

    ep_arn = ep.get("EndpointArn")

    # get tags to find previous endpoint config
    try:
        tags_resp = sm.list_tags(ResourceArn=ep_arn)
        tags = {t["Key"]: t["Value"] for t in tags_resp.get("Tags", [])}
        prev_config = tags.get("previous_endpoint_config")
    except Exception:
        prev_config = None

    if not prev_config:
        return {"status": "no-op", "message": "No previous_endpoint_config tag found; cannot rollback"}

    # perform rollback by updating endpoint to previous config
    try:
        sm.update_endpoint(EndpointName=endpoint, EndpointConfigName=prev_config)
    except Exception as e:
        return {"status": "error", "message": str(e)}

    # Optionally remove the tag to avoid re-rolling back repeatedly
    try:
        sm.delete_tags(ResourceArn=ep_arn, TagKeys=["previous_endpoint_config"])
    except Exception:
        pass

    return {"status": "rolled_back", "endpoint": endpoint, "rolled_to": prev_config}


if __name__ == "__main__":
    print(lambda_handler({}, None))
