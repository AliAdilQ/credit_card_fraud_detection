from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from detection.ml.training import train


class Command(BaseCommand):
    help = "Compare three calibrated classifiers, select on validation F1, and report held-out test metrics."

    def add_arguments(self, parser):
        parser.add_argument("--regenerate", action="store_true", help="Regenerate the default 4,000-row dataset first.")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        path = settings.BASE_DIR / "data" / "sample_transactions.csv"
        if options["regenerate"] or not path.exists():
            call_command("generate_dataset", seed=options["seed"], stdout=self.stdout)
        self.stdout.write("Training Logistic Regression, Random Forest and Gradient Boosting…")
        try:
            report = train(path, settings.MODEL_PATH, settings.MODEL_REPORT_PATH, options["seed"])
        except (ValueError, OSError) as exc:
            raise CommandError(f"Training failed: {exc}") from exc
        for candidate in report["candidates"]:
            m = candidate["validation"]
            self.stdout.write(f"Validation {candidate['name']:22} F1={m['f1']:.3f} recall={m['recall']:.3f} precision={m['precision']:.3f} threshold={candidate['threshold']:.2f}")
        self.stdout.write(self.style.SUCCESS(f"Selected: {report['model_name']} | decision threshold {report['threshold']:.2f}"))
        for name, value in report["test"].items():
            self.stdout.write(f"Test {name}: {value:.4f}" if isinstance(value, float) else f"Test {name}: {value}")
        self.stdout.write(self.style.SUCCESS("Saved models/fraud_detection_model.pkl and models/evaluation.json."))
