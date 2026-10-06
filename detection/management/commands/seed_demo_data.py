from datetime import timedelta
from decimal import Decimal
import uuid
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from detection.ml.model_service import ModelUnavailableError, predict_transactions
from detection.ml.utils import generate_dataset
from detection.models import Transaction


class Command(BaseCommand):
    help = "Seed 240 realistic model-scored records. Repeatable; --reset replaces only seeded records."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=240)
        parser.add_argument("--reset", action="store_true")

    def handle(self, *args, **options):
        count = options["count"]
        if not 20 <= count <= 5000:
            raise CommandError("Use --count between 20 and 5000.")
        # Enrich the demo stream with unusual behavior for useful chart examples.
        data = generate_dataset(max(count * 10, 4000), seed=2026)
        positive_count = max(2, round(count * 0.10))
        positive_pool = data[data.is_fraud == 1]
        sample = pd.concat([
            positive_pool.sample(positive_count, random_state=17, replace=positive_count > len(positive_pool)),
            data[data.is_fraud == 0].sample(count - positive_count, random_state=18),
        ]).sample(frac=1, random_state=21)
        records = sample.drop(columns="is_fraud").to_dict("records")
        now = timezone.now().replace(second=0, microsecond=0)
        for index, record in enumerate(records):
            record["transaction_datetime"] = now - timedelta(days=index % 30, hours=(index * 7) % 24, minutes=(index * 13) % 60)
        try:
            predictions = predict_transactions(records)
        except (ModelUnavailableError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        created = 0
        with transaction.atomic():
            if options["reset"]:
                Transaction.objects.filter(is_demo=True).delete()
            for index, (record, prediction) in enumerate(zip(records, predictions)):
                for field in ["amount", "average_transaction_amount"]:
                    record[field] = Decimal(str(record[field])).quantize(Decimal("0.01"))
                stable_id = uuid.uuid5(uuid.NAMESPACE_URL, f"credit-card-fraud-demo:{index}")
                _, is_created = Transaction.objects.get_or_create(transaction_id=stable_id, defaults={**record, **prediction, "is_demo": True})
                created += int(is_created)
        flagged = Transaction.objects.filter(is_demo=True, predicted_class=True).count()
        self.stdout.write(self.style.SUCCESS(f"Created {created} records. Demo total: {Transaction.objects.filter(is_demo=True).count()}, model-flagged: {flagged}."))
