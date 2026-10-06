import math
from django import forms
from django.utils import timezone
from .models import Transaction


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["transaction_datetime", "amount", "merchant_category", "transaction_type", "card_type",
                  "country", "device_type", "previous_transactions_count", "average_transaction_amount",
                  "transaction_frequency", "distance_from_home", "distance_from_last_transaction",
                  "ratio_to_median_purchase_price", "used_chip", "used_pin_number", "online_order"]
        labels = {"transaction_datetime": "Transaction date & time", "amount": "Purchase amount (USD)",
                  "average_transaction_amount": "Usual purchase amount (USD)", "transaction_frequency": "Transactions in the past hour",
                  "distance_from_home": "Distance from home (km)", "distance_from_last_transaction": "Distance from last purchase (km)",
                  "ratio_to_median_purchase_price": "Amount / median purchase", "used_pin_number": "PIN authentication used",
                  "used_chip": "Chip authentication used", "online_order": "Online order",
                  "previous_transactions_count": "Previous transactions"}
        help_texts = {"ratio_to_median_purchase_price": "A ratio of 1 means a typical purchase; 5 means five times the median.",
                      "used_pin_number": "Only a yes/no signal. Never enter an actual PIN.",
                      "transaction_frequency": "Between 1 and 100, including this transaction."}
        widgets = {"transaction_datetime": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["transaction_datetime"].initial = timezone.localtime().replace(second=0, microsecond=0)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"
            if name in {"distance_from_home", "distance_from_last_transaction", "ratio_to_median_purchase_price"}:
                widget.attrs["step"] = "0.01"
            if field.help_text:
                widget.attrs["aria-describedby"] = f"help-{name}"
            if self.is_bound and name in self.errors:
                widget.attrs["class"] += " is-invalid"
                widget.attrs["aria-invalid"] = "true"
                widget.attrs["aria-describedby"] = f"error-{name}"

    def clean(self):
        cleaned = super().clean()
        for name in ["distance_from_home", "distance_from_last_transaction", "ratio_to_median_purchase_price"]:
            value = cleaned.get(name)
            if value is not None and not math.isfinite(value):
                self.add_error(name, "Enter a finite number.")
        date = cleaned.get("transaction_datetime")
        if date and date > timezone.now() + timezone.timedelta(minutes=5):
            self.add_error("transaction_datetime", "Use the current time or a past transaction date.")
        if cleaned.get("online_order") and cleaned.get("transaction_type") != "Online":
            self.add_error("transaction_type", "Choose Online for an online order.")
        return cleaned

    @property
    def sections(self):
        groups = [
            ("01", "Transaction details", "The purchase you want to analyze.", ["amount", "transaction_datetime", "merchant_category", "transaction_type", "card_type", "device_type"]),
            ("02", "Location & behavior", "Context helps the model spot unusual patterns.", ["country", "distance_from_home", "distance_from_last_transaction", "average_transaction_amount", "ratio_to_median_purchase_price", "previous_transactions_count", "transaction_frequency"]),
            ("03", "Security signals", "Authentication metadata only. No sensitive card data.", ["used_chip", "used_pin_number", "online_order"]),
        ]
        return [{"number": n, "title": title, "description": desc, "fields": [self[name] for name in fields]} for n, title, desc, fields in groups]


class TransactionFilterForm(forms.Form):
    q = forms.CharField(required=False, max_length=100, label="Search transaction ID", widget=forms.TextInput(attrs={"placeholder": "Search transaction ID…"}))
    status = forms.ChoiceField(required=False, choices=[("", "All predictions"), ("legitimate", "Legitimate"), ("fraud", "Potential fraud")])
    risk = forms.ChoiceField(required=False, choices=[("", "All risk levels")] + list(Transaction.Risk.choices))
    type = forms.ChoiceField(required=False, choices=[("", "All transaction types")] + list(Transaction._meta.get_field("transaction_type").choices))
    min_probability = forms.FloatField(required=False, min_value=0, max_value=100, label="Min. probability (%)", widget=forms.NumberInput(attrs={"placeholder": "0–100", "step": "1"}))
    start = forms.DateField(required=False, label="From", widget=forms.DateInput(attrs={"type": "date"}))
    end = forms.DateField(required=False, label="To", widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"

    def clean(self):
        values = super().clean()
        if values.get("start") and values.get("end") and values["start"] > values["end"]:
            raise forms.ValidationError("The start date must be on or before the end date.")
        probability = values.get("min_probability")
        if probability is not None and not math.isfinite(probability):
            self.add_error("min_probability", "Enter a finite percentage.")
        return values
