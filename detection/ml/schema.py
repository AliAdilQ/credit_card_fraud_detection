"""One feature contract shared by the generator, forms and model pipeline."""
MERCHANTS = [(x, x) for x in ["Retail", "Groceries", "Dining", "Travel", "Electronics", "Entertainment", "Services"]]
TYPES = [(x, x) for x in ["In-store", "Online", "ATM", "Contactless"]]
CARDS = [(x, x) for x in ["Credit", "Debit", "Prepaid"]]
COUNTRIES = [(x, label) for x, label in [
    ("US", "United States"), ("GB", "United Kingdom"), ("ID", "Indonesia"),
    ("DE", "Germany"), ("SG", "Singapore"), ("AU", "Australia"), ("JP", "Japan"),
]]
DEVICES = [(x, x) for x in ["Mobile", "Desktop", "Terminal"]]
CATEGORICAL_FEATURES = ["merchant_category", "transaction_type", "card_type", "country", "device_type"]
NUMERIC_FEATURES = [
    "amount", "previous_transactions_count", "average_transaction_amount", "transaction_frequency",
    "distance_from_home", "distance_from_last_transaction", "ratio_to_median_purchase_price", "hour",
]
BOOLEAN_FEATURES = ["used_chip", "used_pin_number", "online_order"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES + BOOLEAN_FEATURES
BOUNDS = {"amount": (0.01, 100000), "previous_transactions_count": (0, 10000),
          "average_transaction_amount": (0.01, 100000), "transaction_frequency": (1, 100),
          "distance_from_home": (0, 20000), "distance_from_last_transaction": (0, 20000),
          "ratio_to_median_purchase_price": (0.01, 1000), "hour": (0, 23)}
CHOICES = dict(zip(CATEGORICAL_FEATURES, [MERCHANTS, TYPES, CARDS, COUNTRIES, DEVICES]))
SCHEMA_VERSION = 1
