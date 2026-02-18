Overview

This repo is a minimal MLOps scaffold that builds, evaluates, registers, deploys, and monitors a SageMaker model. Key stages: data generation -> preprocessing -> training -> evaluation -> conditional model registration & deployment -> monitoring & autoscaling -> retraining trigger.
Main pipeline orchestration lives in pipeline.py (see variable pipeline) and is started by run_pipeline.py.
Files and purpose (grouped)

Project metadata, setup, deps

.gitignore — files to ignore (venv, data artifacts, caches).
README.md — short project description.
requirements.txt — Python dependencies used in CI and local setup.
setup.sh — dev helper: creates virtualenv, installs deps, generates sample data and uploads it to S3.
Configuration

dev.yaml and prod.yaml — environment-specific config (instances, min_accuracy, bucket prefix).
params.py — loads the active config YAML and exposes variables like ACCURACY_THRESHOLD, TRAIN_INSTANCE, etc. Use this to make scripts environment-aware.
Data

generate_data.py — creates a synthetic bank dataset and writes data/raw/data.csv. Used by setup.sh to create sample input.
Preprocessing

preprocess.py — run inside a SageMaker Processing job. Reads the input CSV from /opt/ml/processing/input, encodes categorical columns, splits into train/test, and writes CSVs to /opt/ml/processing/train and /opt/ml/processing/test. These outputs feed the training and evaluation steps.
Training

train.py — training entrypoint that SageMaker TrainingStep uses. Reads training CSV from /opt/ml/input/data/train/train.csv, trains an XGBoost model and saves it to /opt/ml/model/model.xgb. This artifact is used for model registration and evaluation.
Evaluation

evaluate.py — run inside a ProcessingStep to load the trained model from /opt/ml/processing/model/model.xgb and test data from /opt/ml/processing/test/test.csv, compute accuracy, and write a JSON evaluation report to /opt/ml/processing/evaluation/evaluation.json. The pipeline reads the accuracy via the PropertyFile in pipeline.py.
Inference (serving)

inference.py — model serving entrypoint for the SageMaker model. Exposes serving hooks: model_fn, input_fn, predict_fn, output_fn. These load the XGBoost model and convert HTTP JSON requests to predictions.
predict.py — simple example client that calls the deployed endpoint via boto3 sagemaker-runtime and prints the response.
Pipeline orchestration (SageMaker)

config.py — alternative pipeline-level config that queries boto3/sagemaker for REGION, BUCKET, ROLE and default constants (PROJECT_NAME, ACCURACY_THRESHOLD). Note: this file is used directly by pipeline.py in the current repo.
pipeline.py — core: defines SageMaker Workflow with parameters and steps:
ProcessingStep to run preprocess.py
TrainingStep referencing train.py
ProcessingStep to evaluate using evaluate.py and a PropertyFile to extract accuracy
ConditionStep that checks accuracy >= threshold and (if true) creates a SageMaker Model (with inference entrypoint inference/inference.py), creates endpoint config and endpoint steps. The variable pipeline is the final Pipeline object.
Also configures data capture (model monitoring) in the EndpointConfigStep.
run_pipeline.py — small runner that calls pipeline.upsert() and pipeline.start() to create or update the pipeline and start an execution.
Deployment & autoscaling

deploy_lambda.py — Lambda handler to update the endpoint to a new endpoint config (simple deployment step that calls SageMaker UpdateEndpoint).
rollback_lambda.py — Lambda handler to roll back endpoint config to a previous config.
autoscale.py — registers a scalable target in Application Auto Scaling for the SageMaker endpoint.
create_autoscaling_and_alarm.py — attaches a target-tracking scaling policy and can create a CloudWatch alarm (here it creates only the scaling policy). These scripts are intended to be run once to enable automatic scaling.
Monitoring & retraining

baseline.py — runs DefaultModelMonitor.suggest_baseline on stored baseline data to produce statistics and constraints (used for drift detection).
monitor.py — creates a monitoring schedule (DefaultModelMonitor.create_monitoring_schedule) that runs hourly against the endpoint and stores reports in S3. It references the baseline statistics and constraints produced above.
retrain_trigger.py — simple script that calls start_pipeline_execution on the SageMaker Pipeline ARN/name (constant PIPELINE_NAME) to retrigger the pipeline (used when drift or other conditions require retraining).
Infrastructure artifacts

pipeline-role.json — minimal IAM policy for pipeline operations (S3, logs).
training-role.json — IAM policy used by training jobs (S3, EC2 describe).
endpoint-role.json — IAM for endpoint runtime (SageMaker and S3 get).
lambda-role.json — IAM policy for Lambdas that update/describe endpoints.
drift-alarm.json — CloudWatch alarm template for model-drift metric (constraint_violations).
model-approval-rule.json — EventBridge rule payload for reacting to model package approval events.
CI

mlops-ci.yml — GitHub Action that installs deps, configures AWS credentials, and runs run_pipeline.py on pushes to main (starts the pipeline in the configured AWS account).
How these pieces connect (example flow)

setup.sh (or CI) ensures dependencies and creates sample data at data/raw/data.csv (data/generate_data.py).
run_pipeline.py calls the pipeline defined in pipeline.py.
Pipeline Step: ProcessingStep runs preprocess.py -> writes train/test to Processing outputs.
Pipeline Step: TrainingStep runs train.py using train output -> saves model artifact.
Pipeline Step: Evaluate runs evaluate.py, writes evaluation.json containing accuracy.
Pipeline Step: ConditionStep compares accuracy against threshold (from configs) and on success:
registers a SageMaker Model that uses inference.py,
creates endpoint config (with DataCaptureConfig for monitoring),
deploys endpoint (creates endpoint).
After deployment, baseline.py and monitor.py create baseline and monitoring schedules to detect drift.
If drift or other trigger happens, retrain_trigger.py or an EventBridge rule can call the pipeline again to retrain.
autoscale.py and create_autoscaling_and_alarm.py set up autoscaling; Lambdas (deployment/deploy_lambda.py, deployment/rollback_lambda.py) provide simple programmatic endpoint reconfiguration.
