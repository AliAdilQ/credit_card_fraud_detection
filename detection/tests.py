"""Contract tests for validation, inference, persistence, analytics and setup."""
import csv
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import joblib
import numpy as np
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .analytics import charts, summary
from .forms import TransactionForm
from .ml.model_service import ModelUnavailableError, _load, classify_risk, predict_transaction
from .ml.preprocessing import feature_frame
from .ml.schema import FEATURES, SCHEMA_VERSION
from .ml.training import train
from .ml.utils import generate_dataset
from .models import Transaction


def metadata(**changes):
    values = {"transaction_datetime": timezone.now().replace(second=0, microsecond=0), "amount": "42.50",
              "merchant_category": "Groceries", "transaction_type": "In-store", "card_type": "Debit",
              "country": "US", "device_type": "Terminal", "previous_transactions_count": 155,
              "average_transaction_amount": "55.00", "transaction_frequency": 1,
              "distance_from_home": 2.2, "distance_from_last_transaction": 1.0,
              "ratio_to_median_purchase_price": 0.77, "used_chip": True, "used_pin_number": True, "online_order": False}
    return {**values, **changes}


class FixedClassifier:
    """Picklable inference fixture with an explicit probability contract."""
    def predict_proba(self, frame):
        return np.tile([0.2, 0.8], (len(frame), 1))


class WebTests(TestCase):
    def setUp(self):
        self.output = {"predicted_class": True, "fraud_probability": .8, "risk_level": "high", "model_version": "test-model", "decision_threshold": .4}
        self.row = Transaction.objects.create(**metadata(), **self.output)

    def test_home_has_database_statistics(self):
        response = self.client.get(reverse("detection:home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["total"], 1)
        self.assertContains(response, "Credit Card Fraud")

    def test_prediction_form_has_metadata_only(self):
        response = self.client.get(reverse("detection:predict"))
        self.assertContains(response, "Purchase amount (USD)")
        self.assertNotIn("card_number", response.context["form"].fields)
        self.assertNotIn("cvv", response.context["form"].fields)

    def test_valid_prediction_is_saved_and_redirected(self):
        with patch("detection.views.predict_transaction", return_value=self.output) as predict:
            response = self.client.post(reverse("detection:predict"), metadata())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Transaction.objects.count(), 2)
        predict.assert_called_once()
        result = self.client.get(response.url)
        self.assertContains(result, "Potential Fraud")
        self.assertContains(result, "80.0")

    def test_invalid_prediction_does_not_save(self):
        response = self.client.post(reverse("detection:predict"), metadata(amount="-1"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_missing_model_is_graceful_and_does_not_save(self):
        with patch("detection.views.predict_transaction", side_effect=ModelUnavailableError("Model unavailable")):
            response = self.client.post(reverse("detection:predict"), metadata())
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "Model unavailable", status_code=503)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_csrf_is_required(self):
        response = Client(enforce_csrf_checks=True).post(reverse("detection:predict"), metadata())
        self.assertEqual(response.status_code, 403)

    def test_dashboard_contains_real_chart_counts(self):
        response = self.client.get(reverse("detection:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["chart_data"]["status"], [0, 1])
        self.assertEqual(sum(response.context["chart_data"]["probability"]), 1)
        self.assertEqual(sum(response.context["chart_data"]["amounts"]), 1)

    def test_dashboard_date_filters(self):
        tomorrow = (timezone.now() + timezone.timedelta(days=1)).date().isoformat()
        response = self.client.get(reverse("detection:dashboard"), {"start": tomorrow})
        self.assertEqual(response.context["stats"]["total"], 0)

    def test_history_filters_search_and_export(self):
        response = self.client.get(reverse("detection:transactions"), {"q": self.row.short_id, "status": "fraud", "risk": "high", "min_probability": 70})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        export = self.client.get(reverse("detection:export"), {"status": "fraud"})
        rows = list(csv.reader(io.StringIO(export.content.decode())))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], str(self.row.transaction_id))
        self.assertEqual(self.client.get(reverse("detection:export"), {"min_probability": "nan"}).status_code, 400)

    def test_history_pagination_and_empty_state(self):
        response = self.client.get(reverse("detection:transactions"), {"status": "legitimate", "page": "invalid"})
        self.assertContains(response, "No transactions to show")
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_invalid_filters_are_reported(self):
        response = self.client.get(reverse("detection:transactions"), {"start": "2026-02-01", "end": "2026-01-01"})
        self.assertContains(response, "Invalid filters")
        self.assertEqual(response.context["stats"]["total"], 1)

    def test_model_properties(self):
        self.assertEqual(self.row.probability_percent, 80)
        self.assertEqual(self.row.confidence_percent, 80)
        self.assertIn("42.50", str(self.row))
        self.assertTrue(self.row.short_id.startswith("TX-"))

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
    def test_custom_404(self):
        response = self.client.get("/missing-page/")
        self.assertContains(response, "This page is out of view", status_code=404)

    def test_empty_database(self):
        Transaction.objects.all().delete()
        for name in ["home", "dashboard", "transactions", "about"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(f"detection:{name}")).status_code, 200)
        self.assertEqual(summary(Transaction.objects.all())["fraud_percent"], 0)

    def test_admin_login_and_read_only_transaction(self):
        user = get_user_model().objects.create_superuser("reviewer", "demo@example.com", "a-test-password-123")
        self.client.force_login(user)
        response = self.client.get(reverse("admin:detection_transaction_changelist"))
        self.assertContains(response, "Fraud Detection Administration")
        self.assertContains(response, "Potential fraud")
        response = self.client.get(reverse("admin:detection_transaction_change", args=[self.row.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="_save"')

    @override_settings(DEBUG=True)
    def test_demo_admin_command_is_idempotent(self):
        call_command("create_demo_admin", stdout=io.StringIO())
        user = get_user_model().objects.get(username="admin")
        self.assertTrue(user.check_password("DemoAdmin123!"))
        user.set_password("changed-password")
        user.save()
        call_command("create_demo_admin", stdout=io.StringIO())
        user.refresh_from_db()
        self.assertTrue(user.check_password("changed-password"))

    @override_settings(DEBUG=False)
    def test_demo_admin_command_refuses_production(self):
        with self.assertRaises(CommandError):
            call_command("create_demo_admin", stdout=io.StringIO())

    def test_seed_idempotence_and_reset_preserves_manual_records(self):
        with patch("detection.management.commands.seed_demo_data.predict_transactions", side_effect=lambda records: [self.output] * len(records)):
            call_command("seed_demo_data", count=20, stdout=io.StringIO())
            call_command("seed_demo_data", count=20, stdout=io.StringIO())
            self.assertEqual(Transaction.objects.filter(is_demo=True).count(), 20)
            call_command("seed_demo_data", count=25, reset=True, stdout=io.StringIO())
        self.assertEqual(Transaction.objects.filter(is_demo=True).count(), 25)
        self.assertTrue(Transaction.objects.filter(pk=self.row.pk).exists())


class FormTests(TestCase):
    def test_valid_metadata(self):
        form = TransactionForm(metadata())
        self.assertTrue(form.is_valid(), form.errors)

    def test_out_of_bounds_and_nonfinite_input(self):
        for name, value in [("amount", 0), ("distance_from_home", -1), ("transaction_frequency", 101),
                            ("ratio_to_median_purchase_price", 1001), ("distance_from_last_transaction", "nan"),
                            ("average_transaction_amount", "Infinity")]:
            with self.subTest(field=name):
                form = TransactionForm(metadata(**{name: value}))
                self.assertFalse(form.is_valid())
                self.assertIn(name, form.errors)

    def test_future_dates_and_inconsistent_online_order(self):
        form = TransactionForm(metadata(transaction_datetime=timezone.now() + timezone.timedelta(days=1), online_order=True))
        self.assertFalse(form.is_valid())
        self.assertIn("transaction_datetime", form.errors)
        self.assertIn("transaction_type", form.errors)


class MLTests(SimpleTestCase):
    def test_dataset_reproducibility_imbalance_and_schema(self):
        first, second = generate_dataset(), generate_dataset()
        self.assertTrue(first.equals(second))
        self.assertEqual(len(first), 4000)
        self.assertTrue(.03 <= first.is_fraud.mean() <= .06)
        self.assertEqual(list(feature_frame(first).columns), FEATURES)

    def test_preprocessing_rejects_invalid_metadata(self):
        for changes in [{"distance_from_home": float("inf")}, {"country": "XX"}, {"used_chip": .5}, {"transaction_frequency": 1.5}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                feature_frame([metadata(**changes)])

    def test_risk_boundaries(self):
        self.assertEqual([classify_risk(v) for v in [0, .299, .3, .7, .701, 1]], ["low", "low", "medium", "medium", "high", "high"])

    def test_real_joblib_service_contract_and_missing_file(self):
        with tempfile.TemporaryDirectory(prefix=".test-model-", dir=settings.BASE_DIR) as temp:
            path = Path(temp) / "model.pkl"
            joblib.dump({"schema_version": SCHEMA_VERSION, "features": FEATURES, "pipeline": FixedClassifier(), "threshold": .4, "model_version": "fixture"}, path)
            with override_settings(MODEL_PATH=path):
                result = predict_transaction(metadata())
                self.assertTrue(result["predicted_class"])
                self.assertEqual(result["risk_level"], "high")
                self.assertEqual(result["fraud_probability"], .8)
            with override_settings(MODEL_PATH=Path(temp) / "missing.pkl"), self.assertRaises(ModelUnavailableError):
                predict_transaction(metadata())
        _load.cache_clear()

    def test_corrupt_model_is_graceful(self):
        with tempfile.TemporaryDirectory(prefix=".test-model-", dir=settings.BASE_DIR) as temp:
            path = Path(temp) / "bad.pkl"
            path.write_bytes(b"not a model")
            with override_settings(MODEL_PATH=path), self.assertRaises(ModelUnavailableError):
                predict_transaction(metadata())
        _load.cache_clear()

    def test_training_artifact_report_and_splits(self):
        with tempfile.TemporaryDirectory(prefix=".test-model-", dir=settings.BASE_DIR) as temp:
            folder = Path(temp)
            generate_dataset(1000, seed=19).to_csv(folder / "data.csv", index=False)
            report = train(folder / "data.csv", folder / "model.pkl", folder / "report.json", seed=19)
            self.assertEqual(report["split"], {"train": 600, "validation": 200, "test": 200})
            self.assertEqual(len(report["candidates"]), 3)
            self.assertEqual(sum(sum(row) for row in report["test"]["confusion_matrix"]), 200)
            self.assertEqual(json.loads((folder / "report.json").read_text())["model_name"], report["model_name"])
            with override_settings(MODEL_PATH=folder / "model.pkl"):
                result = predict_transaction(metadata())
                self.assertTrue(0 <= result["fraud_probability"] <= 1)
        _load.cache_clear()
