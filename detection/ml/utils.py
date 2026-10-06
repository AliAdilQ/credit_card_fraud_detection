"""Reproducible synthetic transactions with overlapping behavioral profiles."""
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from .schema import CARDS, COUNTRIES, MERCHANTS


def generate_dataset(rows=4000, seed=42):
    """Sample a latent mixture, not a deterministic fraud rule.

    Some legitimate customers travel or spend heavily, while some fraudulent
    purchases resemble ordinary activity. Label noise represents hidden signals.
    """
    if not 500 <= rows <= 100000:
        raise ValueError("Generate between 500 and 100,000 rows.")
    rng = np.random.default_rng(seed)
    latent_fraud = rng.random(rows) < 0.042
    unusual_legitimate = (~latent_fraud) & (rng.random(rows) < 0.065)
    stealth_fraud = latent_fraud & (rng.random(rows) < 0.14)
    unusual = (latent_fraud & ~stealth_fraud) | unusual_legitimate
    average = np.clip(rng.lognormal(4.1, 0.65, rows), 8, 1500)
    ratio = np.clip(rng.lognormal(np.where(unusual, 1.55, -0.08), 0.62), 0.05, 90)
    amount = np.round(np.clip(average * ratio * rng.lognormal(0, 0.13, rows), 1, 50000), 2)
    distance_home = np.clip(rng.lognormal(np.where(unusual, 6.1, 2.0), 1.1), 0, 19000)
    distance_last = np.clip(rng.lognormal(np.where(unusual, 4.7, 0.9), 1.0), 0, 19000)
    frequency = np.clip(rng.poisson(np.where(latent_fraud, 5.8, np.where(unusual_legitimate, 2.8, 0.8))) + 1, 1, 100)
    online = rng.random(rows) < np.where(latent_fraud, 0.78, 0.32)
    types = np.where(online, "Online", rng.choice(["In-store", "ATM", "Contactless"], rows, p=[0.55, 0.12, 0.33]))
    chip = (~online) & (rng.random(rows) < np.where(latent_fraud, 0.36, 0.87))
    pin = (~online) & (rng.random(rows) < np.where(latent_fraud, 0.24, 0.73))
    hour_weights = np.array([1, 1, 1, 1, 1, 1, 2, 3, 4, 6, 7, 7, 8, 7, 7, 7, 7, 7, 6, 5, 4, 3, 2, 2])
    hours = rng.choice(np.arange(24), rows, p=hour_weights / hour_weights.sum())
    hours[latent_fraud] = rng.integers(0, 24, latent_fraud.sum())
    anchor = datetime(2026, 1, 1, tzinfo=timezone.utc)
    dates = [anchor + timedelta(days=int(d), hours=int(h), minutes=int(m)) for d, h, m in zip(rng.integers(0, 60, rows), hours, rng.integers(0, 60, rows))]
    labels = latent_fraud.copy()
    labels[rng.random(rows) < 0.004] ^= True
    return pd.DataFrame({
        "transaction_datetime": [d.isoformat() for d in dates], "amount": amount,
        "merchant_category": rng.choice([x[0] for x in MERCHANTS], rows, p=[0.24, 0.23, 0.17, 0.10, 0.11, 0.07, 0.08]),
        "transaction_type": types, "card_type": rng.choice([x[0] for x in CARDS], rows, p=[0.60, 0.34, 0.06]),
        "country": rng.choice([x[0] for x in COUNTRIES], rows),
        "device_type": np.where(online, rng.choice(["Mobile", "Desktop"], rows, p=[0.73, 0.27]), "Terminal"),
        "previous_transactions_count": np.clip(rng.lognormal(np.where(latent_fraud, 3.8, 4.9), 0.7).astype(int), 0, 10000),
        "average_transaction_amount": np.round(average, 2), "transaction_frequency": frequency,
        "distance_from_home": np.round(distance_home, 2), "distance_from_last_transaction": np.round(distance_last, 2),
        "ratio_to_median_purchase_price": np.round(ratio, 2),
        "used_chip": chip.astype(int), "used_pin_number": pin.astype(int), "online_order": online.astype(int),
        "is_fraud": labels.astype(int),
    })
