from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from detection.ml.utils import generate_dataset


class Command(BaseCommand):
    help = "Generate reproducible synthetic metadata (no real card or customer data)."

    def add_arguments(self, parser):
        parser.add_argument("--rows", type=int, default=4000)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        try:
            data = generate_dataset(options["rows"], options["seed"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        path = settings.BASE_DIR / "data" / "sample_transactions.csv"
        path.parent.mkdir(exist_ok=True)
        data.to_csv(path, index=False)
        self.stdout.write(self.style.SUCCESS(f"Generated {len(data):,} rows; fraud {data.is_fraud.mean():.2%}. Saved {path.name}. Retrain the model after changing data."))
