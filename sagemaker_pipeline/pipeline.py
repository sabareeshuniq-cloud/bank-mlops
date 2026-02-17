# sagemaker_pipeline/pipeline.py

import sagemaker
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep, TrainingStep
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.properties import PropertyFile
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.estimator import Estimator
from sagemaker.model_metrics import MetricsSource, ModelMetrics
from sagemaker.workflow.model_step import ModelStep
from sagemaker.model import Model

from config import *

session = sagemaker.session.Session()

# =========================
# PARAMETERS
# =========================
input_data = ParameterString(
    name="InputDataUrl",
    default_value=f"s3://{BUCKET}/bank/data.csv"
)

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
    outputs=[]
)

# =========================
# TRAINING STEP
# =========================
estimator = Estimator(
    image_uri=sagemaker.image_uris.retrieve("xgboost", REGION, "1.5-1"),
    role=ROLE,
    instance_count=1,
    instance_type=TRAIN_INSTANCE,
    output_path=f"s3://{BUCKET}/bank/output",
    sagemaker_session=session
)

step_train = TrainingStep(
    name="TrainModel",
    estimator=estimator,
    inputs={}
)

# =========================
# EVALUATION STEP
# =========================
evaluation_report = PropertyFile(
    name="EvaluationReport",
    output_name="evaluation",
    path="evaluation.json",
)

step_eval = ProcessingStep(
    name="EvaluateModel",
    processor=processor,
    code="evaluation/evaluate.py",
    property_files=[evaluation_report]
)

# =========================
# CONDITION STEP
# =========================
cond = ConditionGreaterThanOrEqualTo(
    left=evaluation_report.json_path("accuracy"),
    right=ACCURACY_THRESHOLD
)

# =========================
# REGISTER MODEL
# =========================
model = Model(
    image_uri=estimator.training_image_uri(),
    model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
    role=ROLE,
    sagemaker_session=session
)

step_register = ModelStep(
    name="RegisterModel",
    step_args=model.register(
        content_types=["text/csv"],
        response_types=["text/csv"],
        model_package_group_name=MODEL_PACKAGE_GROUP_NAME
    )
)

step_cond = ConditionStep(
    name="AccuracyCondition",
    conditions=[cond],
    if_steps=[step_register],
    else_steps=[]
)

# =========================
# PIPELINE
# =========================
pipeline = Pipeline(
    name="BankChurnPipeline",
    parameters=[input_data],
    steps=[step_process, step_train, step_eval, step_cond]
)


from sagemaker.processing import ProcessingInput, ProcessingOutput

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
    ]
)


from sagemaker.inputs import TrainingInput

step_train = TrainingStep(
    name="TrainModel",
    estimator=estimator,
    inputs={
        "train": TrainingInput(
            s3_data=step_process.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri
        )
    }
)


step_eval = ProcessingStep(
    name="EvaluateModel",
    processor=processor,
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
    property_files=[evaluation_report]
)
