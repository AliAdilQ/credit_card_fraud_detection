from django.contrib import admin
from django.utils.html import format_html
from .models import Transaction

admin.site.site_header = "Fraud Detection Administration"
admin.site.site_title = "Fraud Detection Admin"
admin.site.index_title = "System Management"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["short_id", "transaction_datetime", "amount", "status", "probability", "risk_level", "transaction_type", "is_demo"]
    list_filter = ["predicted_class", "risk_level", "transaction_type", "country", "is_demo"]
    search_fields = ["transaction_id"]
    ordering = ["-transaction_datetime"]
    date_hierarchy = "transaction_datetime"
    list_per_page = 25
    readonly_fields = ["transaction_id", "predicted_class", "fraud_probability", "risk_level", "model_version", "decision_threshold", "created_at", "updated_at", "is_demo"]
    fieldsets = [
        ("Transaction", {"fields": ["transaction_id", "transaction_datetime", "amount", "merchant_category", "transaction_type", "card_type", "country", "device_type"]}),
        ("Behavior", {"fields": ["previous_transactions_count", "average_transaction_amount", "transaction_frequency", "distance_from_home", "distance_from_last_transaction", "ratio_to_median_purchase_price", "used_chip", "used_pin_number", "online_order"]}),
        ("Model decision (read-only)", {"fields": ["predicted_class", "fraud_probability", "risk_level", "model_version", "decision_threshold", "is_demo", "created_at", "updated_at"]}),
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Metadata and its saved prediction must remain consistent.
        return False

    @admin.display(description="Prediction", ordering="predicted_class")
    def status(self, obj):
        color = "#b42318" if obj.predicted_class else "#087f6a"
        return format_html('<strong style="color:{}">{}</strong>', color, obj.prediction_label)

    @admin.display(description="Fraud probability", ordering="fraud_probability")
    def probability(self, obj):
        color = "#b42318" if obj.predicted_class else "#087f6a"
        return format_html('<strong style="color:{}">{}%</strong>', color, f"{obj.probability_percent:.1f}")
