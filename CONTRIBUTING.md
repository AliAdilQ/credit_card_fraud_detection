# Contributing

Thanks for helping improve this educational project.

1. Fork [AliAdilQ/credit_card_fraud_detection](https://github.com/AliAdilQ/credit_card_fraud_detection).
2. Clone your fork and follow the [README setup](README.md#installation).
3. Create a branch: `git switch -c feature/your-change`.
4. Keep web logic, ML logic, templates, and static assets in their existing directories. Add meaningful regression coverage for behavior changes. Use synthetic metadata only.
5. Run `python manage.py check` and `python manage.py test`. Check desktop and mobile layouts for visual changes.
6. Commit your changes with a clear message and push your branch to your fork.
7. Submit a pull request describing the problem, the resulting behavior, and validation. Include real screenshots for UI changes.

Never commit `.env`, local databases, credentials, payment information, virtual environments, or dependency caches. If changing the feature schema or dependency versions, retrain the artifact and update model documentation and metrics together. Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).
