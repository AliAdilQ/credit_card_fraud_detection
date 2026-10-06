"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("menu-toggle");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebar-overlay");
  const closeMenu = () => { sidebar.classList.remove("open"); overlay.classList.remove("open"); toggle.setAttribute("aria-expanded", "false"); };
  toggle?.addEventListener("click", () => { const open = !sidebar.classList.contains("open"); sidebar.classList.toggle("open", open); overlay.classList.toggle("open", open); toggle.setAttribute("aria-expanded", String(open)); });
  overlay?.addEventListener("click", closeMenu);
  document.addEventListener("keydown", event => { if (event.key === "Escape") closeMenu(); });

  const presets = {
    typical: { amount: 48.90, merchant_category: "Groceries", transaction_type: "In-store", card_type: "Debit", country: "US", device_type: "Terminal", previous_transactions_count: 160, average_transaction_amount: 55, transaction_frequency: 1, distance_from_home: 3.2, distance_from_last_transaction: 1.5, ratio_to_median_purchase_price: 0.89, used_chip: true, used_pin_number: true, online_order: false },
    unusual: { amount: 1840, merchant_category: "Electronics", transaction_type: "Online", card_type: "Credit", country: "SG", device_type: "Desktop", previous_transactions_count: 24, average_transaction_amount: 85, transaction_frequency: 12, distance_from_home: 2200, distance_from_last_transaction: 870, ratio_to_median_purchase_price: 21.65, used_chip: false, used_pin_number: false, online_order: true }
  };
  document.querySelectorAll("[data-preset]").forEach(button => button.addEventListener("click", () => {
    const preset = presets[button.dataset.preset];
    for (const [name, value] of Object.entries(preset)) {
      const field = document.getElementById(`id_${name}`);
      if (field) { if (field.type === "checkbox") field.checked = value; else field.value = value; field.dispatchEvent(new Event("change")); }
    }
    // The Django field's current local time is preserved to respect TIME_ZONE.
    document.getElementById("id_amount")?.focus();
  }));
  document.getElementById("prediction-form")?.addEventListener("submit", () => {
    const button = document.getElementById("analyze-button");
    button.disabled = true;
    button.textContent = "Analyzing signals…";
  });
  window.addEventListener("pageshow", () => { const button = document.getElementById("analyze-button"); if (button) { button.disabled = false; button.textContent = "Analyze Transaction →"; } });
});
