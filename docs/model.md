# Model methodology

The binary task is to distinguish synthetic legitimate transactions (0) from synthetic fraudulent transactions (1) using non-sensitive metadata. Predictions demonstrate a workflow; they are not a financial fraud decision system.

## Dataset and features

The default dataset has 4,000 records with roughly 4–5% fraud. Profile mixtures, overlapping behavior, and label noise make the task imbalanced and imperfect. See [feature definitions and generation](../data/README.md). A timestamp contributes UTC hour; dates and labels never enter the classifier. Numeric fields cover amount, past spending, counts, frequency, distances, and amount-to-median ratio. Categorical fields cover merchant category, transaction type, card type, country, and device; security flags are binary. The generator's prior-history count is a particularly strong synthetic signal and must not be generalized to real customers.

## Preprocessing and splits

With seed 42, stratified `train_test_split` makes 60% training (2,400 rows), 20% validation (800), and 20% held-out test (800). Numeric features use `StandardScaler`; categories use `OneHotEncoder(handle_unknown="ignore")`; binary flags pass through. An inference validator rejects unsupported categories and invalid ranges before preprocessing.

Each candidate is wrapped in `CalibratedClassifierCV(method="sigmoid", cv=3)`. Preprocessing is inside each pipeline, and fitted within each calibration training fold, which prevents scaling/encoding leakage. Balanced weights are used for Logistic Regression and Random Forest. Gradient Boosting uses its standard objective; all candidates use the same stratified partitions and selection procedure.

## Selection and evaluation

Compare Logistic Regression, Random Forest, and Gradient Boosting. For each, evaluate thresholds 0.05 through 0.80 on the validation partition. Choose the threshold with maximum F1, breaking ties by recall and then the lower threshold. Choose the model by validation F1, then recall, then ROC-AUC. This emphasizes minority-class performance without optimizing accuracy on mostly legitimate transactions.

Refit the winning calibrated estimator on training plus validation rows, retaining the validation-selected threshold. Evaluate this final estimator once on the untouched test set. Refitting may shift scores; threshold stability is a limitation of this small demonstration. No test result influences model or threshold selection.

Report accuracy, precision, recall, F1, ROC-AUC, average precision (PR summary), Brier score, and confusion matrices. The confusion matrix order is `[[true negatives, false positives], [false negatives, true positives]]`. [evaluation.json](../models/evaluation.json) contains the actual chosen model, metrics, validation comparison, versions, and dataset hash. [README](../README.md#model-evaluation) presents the measured results.

## Interpreting a prediction

`predict_proba` provides an estimated, sigmoid-calibrated fraud score. The binary prediction is score ≥ the selected threshold. Risk bands are low below 30%, medium from 30% through 70%, and high above 70%. They are descriptive bands, independent of the tuned classification threshold. A low-band transaction can therefore still be flagged.

The displayed class score is `p` for a flagged transaction and `1-p` for a legitimate prediction. It is not statistical certainty or a guarantee. Calibration on generated data does not establish real banking probabilities. Do not interpret these outputs as instructions to approve or decline a payment.

## Limitations and reproducibility

- Artificial behavioral relationships and low label counts limit generalization.
- False positives and missed fraud exist; accuracy alone conceals these costs.
- Countries are random context values, not a proxy for financial risk or nationality.
- The demo has no real customers, chronological backtesting, live bank integration, explanation engine, or drift monitoring.
- Train/test rows are IID synthetic records. Real deployments need customer-aware and time-aware splits and representative, lawfully obtained labels.
- Retrain after changing dependencies or features; Joblib files are not portable across every scikit-learn version.

Use `python manage.py train_model --regenerate` to reproduce default data and training. The dataset is deterministic; evaluation may vary slightly across library/platform versions. The timestamp of training is deliberately not deterministic.
