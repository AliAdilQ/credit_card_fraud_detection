# Trained model artifacts

```bash
python manage.py train_model
```

- `fraud_detection_model.pkl`: compressed Joblib bundle containing the calibrated preprocessing/classifier pipeline, schema contract, tuned threshold, version identifier, and training metadata.
- `evaluation.json`: human-readable dataset hash, versions, split sizes, candidate validation metrics, selected model, held-out test metrics, and confusion matrices.

The bundled artifact is included for a quick demonstration. The documented setup retrains it on your installed library versions. Scikit-learn artifacts are version-sensitive; regenerate after dependency upgrades or changes to features or data. `requirements-lock.txt` records the verified Windows/Python 3.12 environment; `requirements.txt` provides Python 3.11+ compatible ranges.

The service loads lazily and caches by resolved path, modification time, and size. Retraining atomically replaces the artifact; subsequent requests pick up the new file. Each saved transaction retains its original score, version, and threshold, so historical results do not silently change.

**Trust boundary:** Joblib uses pickle. Only load an artifact trained locally by this project or supplied by someone you fully trust. Never use an arbitrary downloaded model. The application does not expose an artifact upload endpoint.
