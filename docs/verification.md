# Verification record

Verified **6 October 2026** with Python 3.12.14, Django 5.2.17, Scikit-learn 1.7.2, Pandas 2.3.3, NumPy 2.3.5, and Joblib 1.5.3. Full installed Python dependency versions are in `requirements-lock.txt`.

| Check | Observed result |
| --- | --- |
| `python manage.py check` | No issues |
| `python manage.py migrate` | All migrations applied |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py train_model --regenerate` | 4,000 records, 173 synthetic fraud labels; three classifiers compared |
| Model selection | Gradient Boosting; validation F1 0.71875; threshold 0.36 |
| Held-out test | Accuracy 0.98125, precision 0.83333, recall 0.71429, F1 0.76923, ROC-AUC 0.89720 |
| Test confusion matrix | `[[760, 5], [10, 25]]` |
| `python manage.py seed_demo_data --reset` | 240 seeded records; 20 flagged by the trained model |
| `python manage.py create_demo_admin` | Local superuser created; authenticated admin login verified |
| `python manage.py test` | 27 tests passed |
| `python manage.py collectstatic --noinput` | Static assets, including Admin and vendored libraries, collected |
| Non-debug static collection / `check --deploy` | Manifest and compressed assets generated; Django deployment check reported no issues with temporary valid environment settings |
| Live desktop browser | Home, prediction form/result, dashboard, history, About, and Admin verified |
| Real prediction POST | Typical example 0.6% fraud score / legitimate; unusual example 95.1% / potential fraud; both saved and redirected |
| Chart.js | Five chart instances rendered; histogram totals matched database counts |
| History / CSV | Status and risk filtering and CSV response verified |
| Mobile browser | No document overflow on the five main pages at 390px; menu opens/closes |
| Browser errors | No page errors or failed local assets during verification |
| Screenshots | All five required screenshots plus prediction-form and mobile-home captures |

The final browser capture database has **242 total records**: 240 seeded plus two browser examples, with 21 model-flagged transactions. The SQLite file is local and ignored by Git; a fresh clone starts empty until setup commands are run.

Tests for missing/corrupt models, invalid metadata, CSRF, empty records, invalid filters, and custom 404 handling exercise failure behavior. Model contract tests use isolated temporary artifacts. The optional Playwright script is checked in so screenshots can be reproduced. CI configuration is provided but remote GitHub Actions has not been run by this local task.

These checks verify an educational local application, not a deployed financial system. No Git repository was initialized and no changes were pushed to GitHub.
