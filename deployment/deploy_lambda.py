import boto3
import time

sm = boto3.client("sagemaker")

ENDPOINT_NAME = "bank-risk-endpoint"

def lambda_handler(event, context):

    model_package_arn = event["detail"]["ModelPackageArn"]

    response = sm.describe_model_package(ModelPackageName=model_package_arn)

    container = response["InferenceSpecification"]["Containers"][0]
    model_data = container["ModelDataUrl"]
    image = container["Image"]

    model_name = f"bank-model-{int(time.time())}"

    # Create Model
    sm.create_model(
        ModelName=model_name,
        ExecutionRoleArn=response["ExecutionRoleArn"],
        PrimaryContainer={
            "Image": image,
            "ModelDataUrl": model_data
        }
    )

    # Create Endpoint Config
    config_name = model_name + "-config"
    sm.create_endpoint_config(
        EndpointConfigName=config_name,
        ProductionVariants=[{
            "VariantName": "AllTraffic",
            "ModelName": model_name,
            "InstanceType": "ml.m5.large",
            "InitialInstanceCount": 1
        }]
    )

    # Create or Update Endpoint
    try:
        # If endpoint exists, tag it with previous endpoint config for rollback and update
        ep = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
        prev_config = ep.get("EndpointConfigName")
        if prev_config:
            # add a tag on the endpoint with previous endpoint config name
            try:
                ep_arn = ep.get("EndpointArn")
                sm.add_tags(ResourceArn=ep_arn, Tags=[{"Key": "previous_endpoint_config", "Value": prev_config}])
            except Exception:
                # non-fatal; continue
                pass

        sm.update_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=config_name)
    except:
        sm.create_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=config_name)

    return {"status": "deployment_started"}
