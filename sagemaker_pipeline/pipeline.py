# pipeline/pipeline.py

import boto3
import sagemaker

from sagemaker.session import Session
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.parameters import ParameterString, ParameterFloat, ParameterInteger
from sagemaker.workflow.steps import ProcessingStep, TrainingStep, CreateModelStep
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.functions import JsonGet

from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.model import Model
from sagemaker.model_metrics import MetricsSource, ModelMetrics
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.model_monitor import DataCaptureConfig

from config import *

# --------------------------
# Pipeline creator function
# --------------------------
def get_pipeline():

    session = Session()
    region = boto3.Session().region_name

    # =========================
    # PARAMETERS
    # =========================
    input_data = ParameterString(
        name="InputDataUrl",
        default_value=f"s3://{BUCKET}/bank/data.csv"
    )

    accuracy_threshold = ParameterFloat(
        name="AccuracyThreshold",
        default_value=ACCURACY_THRESHOLD
    )

    instance_count = ParameterInteger(name="InstanceCount", default_value=1)

    # =========================
    # PROCESSING STEP
    # =========================
    processor = SKLearnProcessor(
        framework_version="1.2-1",
        role=ROLE,
        instance_type=PROCESS_INSTANCE,
        instance_count=1,
        base_job_name="bank-process",
        sagemaker_session=session
    )

    step_process = ProcessingStep(
        name="ProcessData",
        processor=processor,
        code="processing/preprocess.py",
        inputs=[
            ProcessingInput(
                source=input_data,
                destination="/opt/ml/processing/input"
            )
        ],
        outputs=[
            ProcessingOutput(output_name="train", source="/opt/ml/processing/train"),
            ProcessingOutput(output_name="test", source="/opt/ml/processing/test"),
        ],
    )

    # =========================
    # TRAINING STEP
    # =========================
    estimator = Estimator(
        image_uri=sagemaker.image_uris.retrieve("xgboost", region, "1.7-1"),
        role=ROLE,
        instance_count=1,
        instance_type=TRAIN_INSTANCE,
        output_path=f"s3://{BUCKET}/bank/output",
        sagemaker_session=session
    )

    estimator.set_hyperparameters(
        objective="binary:logistic",
        eval_metric="auc",
        num_round=200
    )

    step_train = TrainingStep(
        name="TrainModel",
        estimator=estimator,
        inputs={
            "train": TrainingInput(
                s3_data=step_process.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri
            )
        },
    )

    # =========================
    # EVALUATION STEP
    # =========================
    evaluation_report = PropertyFile(
        name="EvaluationReport",
        output_name="evaluation",
        path="evaluation.json"
    )

    eval_processor = ScriptProcessor(
        image_uri=sagemaker.image_uris.retrieve("sklearn", region, "1.2-1"),
        command=["python3"],
        role=ROLE,
        instance_type=PROCESS_INSTANCE,
        instance_count=1,
        sagemaker_session=session
    )

    step_eval = ProcessingStep(
        name="EvaluateModel",
        processor=eval_processor,
        code="evaluation/evaluate.py",
        inputs=[
            ProcessingInput(
                source=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model"
            ),
            ProcessingInput(
                source=step_process.properties.ProcessingOutputConfig.Outputs["test"].S3Output.S3Uri,
                destination="/opt/ml/processing/test"
            )
        ],
        outputs=[
            ProcessingOutput(output_name="evaluation", source="/opt/ml/processing/evaluation")
        ],
        property_files=[evaluation_report],
    )

    # =========================
    # MODEL REGISTRATION
    # =========================
    model_metrics = ModelMetrics(
        model_statistics=MetricsSource(
            s3_uri=step_eval.properties.ProcessingOutputConfig.Outputs["evaluation"].S3Output.S3Uri,
            content_type="application/json",
        )
    )

    register_step = RegisterModel(
        name="RegisterBankModel",
        estimator=estimator,
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=["application/json"],
        response_types=["application/json"],
        inference_instances=["ml.m5.large"],
        transform_instances=["ml.m5.large"],
        model_package_group_name="BankChurnModelGroup",
        approval_status="PendingManualApproval",
        model_metrics=model_metrics,
    )

    # =========================
    # CONDITION STEP (Approval Gate)
    # =========================
    cond = ConditionGreaterThanOrEqualTo(
        left=JsonGet(
            step_name=step_eval.name,
            property_file=evaluation_report,
            json_path="accuracy"
        ),
        right=accuracy_threshold
    )

    step_cond = ConditionStep(
        name="AccuracyCondition",
        conditions=[cond],
        if_steps=[register_step],
        else_steps=[]
    )

    # =========================
    # PIPELINE
    # =========================
    pipeline = Pipeline(
        name="BankChurnPipeline",
        parameters=[input_data, accuracy_threshold, instance_count],
        steps=[step_process, step_train, step_eval, step_cond],
        sagemaker_session=session,
    )

    return pipeline
