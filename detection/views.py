import csv
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from .analytics import charts, model_report, summary
from .forms import TransactionFilterForm, TransactionForm
from .ml.model_service import ModelUnavailableError, predict_transaction
from .models import Transaction


@require_GET
def home(request):
    queryset = Transaction.objects.all()
    return render(request, "home.html", {"stats": summary(queryset), "recent": queryset[:5], "report": model_report()})


@require_http_methods(["GET", "POST"])
def predict(request):
    form = TransactionForm(request.POST or None)
    status = 200
    if request.method == "POST" and form.is_valid():
        try:
            prediction = predict_transaction(form.cleaned_data)
        except ModelUnavailableError as exc:
            form.add_error(None, str(exc))
            status = 503
        except ValueError:
            form.add_error(None, "Some metadata could not be analyzed. Please review the fields and try again.")
            status = 400
        else:
            instance = form.save(commit=False)
            for name, value in prediction.items():
                setattr(instance, name, value)
            instance.save()
            return redirect("detection:result", transaction_id=instance.transaction_id)
    return render(request, "predict.html", {"form": form}, status=status)


@require_GET
def result(request, transaction_id):
    instance = get_object_or_404(Transaction, transaction_id=transaction_id)
    return render(request, "prediction_result.html", {"transaction": instance, "threshold_percent": instance.decision_threshold * 100})


def filtered_transactions(request):
    form = TransactionFilterForm(request.GET)
    queryset = Transaction.objects.all()
    if form.is_valid():
        values = form.cleaned_data
        if values["q"]:
            search = values["q"].removeprefix("TX-").removeprefix("tx-")
            queryset = queryset.filter(transaction_id__icontains=search)
        if values["status"]:
            queryset = queryset.filter(predicted_class=values["status"] == "fraud")
        if values["risk"]:
            queryset = queryset.filter(risk_level=values["risk"])
        if values["type"]:
            queryset = queryset.filter(transaction_type=values["type"])
        if values["min_probability"] is not None:
            queryset = queryset.filter(fraud_probability__gte=values["min_probability"] / 100)
        if values["start"]:
            queryset = queryset.filter(transaction_datetime__date__gte=values["start"])
        if values["end"]:
            queryset = queryset.filter(transaction_datetime__date__lte=values["end"])
    return queryset, form


@require_GET
def dashboard(request):
    queryset, form = filtered_transactions(request)
    return render(request, "dashboard.html", {"stats": summary(queryset), "chart_data": charts(queryset),
                                               "recent": queryset[:5], "filter_form": form, "report": model_report()})


@require_GET
def transactions(request):
    queryset, form = filtered_transactions(request)
    page = Paginator(queryset, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "transactions.html", {"page_obj": page, "filter_form": form, "query_string": params.urlencode(), "stats": summary(queryset)})


@require_GET
def export_transactions(request):
    queryset, form = filtered_transactions(request)
    if not form.is_valid():
        return HttpResponse("Invalid filters. Please return to history and correct them.", status=400, content_type="text/plain")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="demo-transactions.csv"'
    writer = csv.writer(response)
    writer.writerow(["transaction_id", "date", "amount_usd", "type", "fraud_probability", "risk", "prediction", "model_version", "decision_threshold"])
    for row in queryset.iterator():
        writer.writerow([row.transaction_id, row.transaction_datetime.isoformat(), row.amount, row.transaction_type,
                         f"{row.fraud_probability:.6f}", row.get_risk_level_display(), row.prediction_label, row.model_version, row.decision_threshold])
    return response


@require_GET
def about(request):
    return render(request, "about.html", {"report": model_report()})


def not_found(request, exception=None):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)
