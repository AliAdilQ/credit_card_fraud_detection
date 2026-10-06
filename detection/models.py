import uuid
from decimal import Decimal
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from .ml.schema import BOUNDS, CARDS, COUNTRIES, DEVICES, MERCHANTS, TYPES


def bounds(name):
    lower, upper = BOUNDS[name]
    return [MinValueValidator(lower), MaxValueValidator(upper)]


class Transaction(models.Model):
    """Synthetic transaction metadata only; never stores payment credentials."""

    class Risk(models.TextChoices):
        LOW = "low", "Low Risk"
        MEDIUM = "medium", "Medium Risk"
        HIGH = "high", "High Risk"

    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    transaction_datetime = models.DateTimeField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=bounds("amount"))
    merchant_category = models.CharField(max_length=30, choices=MERCHANTS)
    transaction_type = models.CharField(max_length=20, choices=TYPES)
    card_type = models.CharField(max_length=15, choices=CARDS)
    country = models.CharField(max_length=2, choices=COUNTRIES)
    device_type = models.CharField(max_length=15, choices=DEVICES)
    previous_transactions_count = models.PositiveIntegerField(validators=bounds("previous_transactions_count"))
    average_transaction_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=bounds("average_transaction_amount"))
    transaction_frequency = models.PositiveSmallIntegerField(validators=bounds("transaction_frequency"))
    distance_from_home = models.FloatField(validators=bounds("distance_from_home"))
    distance_from_last_transaction = models.FloatField(validators=bounds("distance_from_last_transaction"))
    ratio_to_median_purchase_price = models.FloatField(validators=bounds("ratio_to_median_purchase_price"))
    used_chip = models.BooleanField(default=True)
    used_pin_number = models.BooleanField(default=True)
    online_order = models.BooleanField(default=False)
    predicted_class = models.BooleanField(default=False, verbose_name="Flagged as potential fraud")
    fraud_probability = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    risk_level = models.CharField(max_length=10, choices=Risk.choices)
    model_version = models.CharField(max_length=50, default="unknown")
    decision_threshold = models.FloatField(default=0.5, validators=[MinValueValidator(0), MaxValueValidator(1)])
    is_demo = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-transaction_datetime", "-id"]
        indexes = [models.Index(fields=["transaction_datetime"]), models.Index(fields=["predicted_class", "risk_level"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="transaction_positive_amount"),
            models.CheckConstraint(condition=models.Q(fraud_probability__gte=0, fraud_probability__lte=1), name="probability_between_zero_and_one"),
        ]

    def __str__(self):
        return f"{self.short_id} · ${Decimal(str(self.amount)):,.2f} · {self.prediction_label}"

    @property
    def short_id(self):
        return f"TX-{str(self.transaction_id)[:8].upper()}"

    @property
    def probability_percent(self):
        return self.fraud_probability * 100

    @property
    def confidence_percent(self):
        return (self.fraud_probability if self.predicted_class else 1 - self.fraud_probability) * 100

    @property
    def prediction_label(self):
        return "Potential fraud" if self.predicted_class else "Legitimate"
