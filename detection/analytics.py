"""Database-backed aggregates shared by the landing page and dashboard."""
import json
from django.conf import settings
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate


def summary(queryset):
    data = queryset.aggregate(total=Count("id"), fraud=Count("id", filter=Q(predicted_class=True)),
                              average=Avg("amount"), volume=Sum("amount"))
    data["legitimate"] = data["total"] - data["fraud"]
    data["fraud_percent"] = data["fraud"] / data["total"] * 100 if data["total"] else 0
    data["average"] = data["average"] or 0
    data["volume"] = data["volume"] or 0
    return data


def charts(queryset):
    total = summary(queryset)
    daily = list(queryset.order_by().annotate(day=TruncDate("transaction_datetime")).values("day").annotate(
        total=Count("id"), fraud=Count("id", filter=Q(predicted_class=True))).order_by("day"))
    types = list(queryset.order_by().values("transaction_type").annotate(
        total=Count("id"), fraud=Count("id", filter=Q(predicted_class=True))).order_by("transaction_type"))
    probability = queryset.aggregate(**{f"b{i}": Count("id", filter=Q(fraud_probability__gte=i / 5) &
                                     (Q(fraud_probability__lt=(i + 1) / 5) if i < 4 else Q(fraud_probability__lte=1))) for i in range(5)})
    ranges = [(0, 50), (50, 150), (150, 500), (500, 1000), (1000, None)]
    amounts = queryset.aggregate(**{f"b{i}": Count("id", filter=Q(amount__gte=low) &
                                  (Q(amount__lt=high) if high is not None else Q())) for i, (low, high) in enumerate(ranges)})
    return {"status": [total["legitimate"], total["fraud"]],
            "trend": {"labels": [r["day"].strftime("%d %b %Y") for r in daily], "total": [r["total"] for r in daily], "fraud": [r["fraud"] for r in daily]},
            "probability": list(probability.values()), "amounts": list(amounts.values()),
            "types": {"labels": [r["transaction_type"] for r in types], "total": [r["total"] for r in types], "fraud": [r["fraud"] for r in types]}}


def model_report():
    try:
        return json.loads(settings.MODEL_REPORT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
