import yaml

def load_config(env="dev"):
    with open(f"configs/{env}.yaml") as f:
        return yaml.safe_load(f)
