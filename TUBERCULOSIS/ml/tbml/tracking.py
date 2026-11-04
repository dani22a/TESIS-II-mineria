"""Optional MLflow logging: every call is a no-op when mlflow is not installed or disabled."""
from __future__ import annotations

try:
    import mlflow
except ImportError:  # graceful: MLflow is optional
    mlflow = None


class Tracker:
    def __init__(self, enabled: bool = False, experiment: str = "tb-screening", uri: str | None = None):
        self.on = bool(enabled and mlflow is not None)
        if enabled and mlflow is None:
            print("[tracking] mlflow not installed; continuing without it (pip install mlflow)")
        if self.on:
            if uri:
                mlflow.set_tracking_uri(uri)
            mlflow.set_experiment(experiment)

    def run(self, name: str):
        return mlflow.start_run(run_name=name, nested=True) if self.on else _Null()

    def params(self, d: dict):
        if self.on:
            mlflow.log_params({k: str(v)[:250] for k, v in d.items()})

    def metrics(self, d: dict, step: int | None = None):
        if self.on:
            mlflow.log_metrics({k: float(v) for k, v in d.items() if v == v}, step=step)

    def artifact(self, path):
        if self.on:
            mlflow.log_artifact(str(path))


class _Null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False
