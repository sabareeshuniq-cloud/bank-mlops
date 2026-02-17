# sagemaker_pipeline/run_pipeline.py

from pipeline import pipeline

if __name__ == "__main__":
    pipeline.upsert(role_arn=pipeline.role)
    execution = pipeline.start()
    print("Pipeline started:", execution.arn)
