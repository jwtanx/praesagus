# AI Pipeline Design

Status: Draft

Phases

1. Offline Feature Engineering: batch computation of time-series features stored in feature store and parquet snapshots for backtesting.
2. Experimentation: model training with tracked experiments (MLflow or SageMaker Experiments).
3. Model Registry: store model artifacts, metadata, evaluation metrics, and promotion tags.
4. Online Inference: low-latency scoring service that reads from feature store and writes signals.
5. Explainability: attach evidence pointers and feature attributions to each signal.

Model Types

- Heuristic scorers for velocity/acceleration.
- Time-series models for momentum detection.
- Classification/regression models for event prediction.
- Anomaly detection models for sudden shifts.

Data Lineage & Reproducibility

- Every model input references dataset IDs and feature timestamps.
- Provide a replay harness to backtest signal performance over historical data.

Deployment

- Containerized scoring services behind autoscaling groups; use canary promotions.
