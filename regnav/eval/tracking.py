"""MLflow setup: local SQLite store + artifact folder, both under ``./mlruns``.

(MLflow 3 put the plain file store into maintenance mode, so a SQLite file is used; it still
lives in ``./mlruns`` and needs no server. ``make mlflow-ui`` / docker compose serve the UI.)
"""

from __future__ import annotations

from pathlib import Path

from regnav.config import AppConfig


def tracking_uri(mlruns_dir: Path) -> str:
    mlruns_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(mlruns_dir / 'mlflow.db').resolve()}"


def setup_mlflow(cfg: AppConfig, experiment: str) -> None:
    import mlflow

    mlflow.set_tracking_uri(tracking_uri(cfg.paths.mlruns_dir))
    if mlflow.get_experiment_by_name(experiment) is None:
        artifacts = (cfg.paths.mlruns_dir / "artifacts").resolve()
        artifacts.mkdir(parents=True, exist_ok=True)
        mlflow.create_experiment(experiment, artifact_location=artifacts.as_uri())
    mlflow.set_experiment(experiment)
