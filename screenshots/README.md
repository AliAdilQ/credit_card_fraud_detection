# Actual application screenshots

These files are real captures of the running Django application, using local static assets and a seeded database. Desktop viewport: **1440 × 900**; full-page captures include content below the fold. Mobile viewport: **390 × 844**.

| File | Contents |
| --- | --- |
| `home.png` | Landing page, live KPI cards, features, and recent records |
| `dashboard.png` | Five Chart.js charts and database-backed analytics |
| `prediction-form.png` | Form populated with the unusual-activity preset |
| `prediction.png` | Saved result after actual form submission; estimated fraud score 95.1% |
| `transactions.png` | Search/filter interface and populated transaction history |
| `admin-panel.png` | Authenticated Django Admin transaction list |
| `mobile-home.png` | Home page with responsive cards and contained table scrolling |

The source database contains 240 seeded records and two real browser-submitted synthetic examples. The screenshots' counts and dates reflect that capture session; future seeded runs naturally have different dates and transaction IDs.

To regenerate, initialize the app following the root README, start the Django development server, and then run:

```bash
npm install
npx playwright install chromium
npm run screenshots
```

Optional environment variables: `DEMO_URL` (default `http://127.0.0.1:8000`), `DEMO_ADMIN_USERNAME`, `DEMO_ADMIN_PASSWORD`, and `CHROMIUM_EXECUTABLE` for an existing compatible Chromium executable. The script intentionally creates two synthetic prediction records each run. It checks both result paths, all five charts, CSV export, filters, real admin login, mobile overflow, and mobile menu behavior, and fails on browser errors or failed local assets.
