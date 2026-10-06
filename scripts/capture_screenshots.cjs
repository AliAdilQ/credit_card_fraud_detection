/* Optional: npm install && npx playwright install chromium, then start Django. */
const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const base = process.env.DEMO_URL || "http://127.0.0.1:8000";
const output = path.join(__dirname, "..", "screenshots");

(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_EXECUTABLE ? { executablePath: process.env.CHROMIUM_EXECUTABLE } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("response", response => { if (response.status() >= 400 && response.url().startsWith(base)) errors.push(`${response.status()} ${response.url()}`); });
  const open = async url => { const response = await page.goto(base + url); assert.equal(response.status(), 200, `Page ${url}`); await page.waitForLoadState("networkidle"); };
  const capture = async filename => { await page.screenshot({ path: path.join(output, filename), fullPage: true }); console.log(`Captured ${filename}`); };
  try {
    // Perform real CSRF-protected predictions before photographing the results.
    await open("/predict/");
    await page.locator('[data-preset="typical"]').click();
    await Promise.all([page.waitForURL("**/result/**"), page.locator('#analyze-button').click()]);
    await page.locator(".score-ring").waitFor();
    assert.match(await page.locator(".result-copy h2").innerText(), /Legitimate/);
    console.log("Verified typical prediction, persistence and result redirect.");
    await open("/predict/");
    await page.locator('[data-preset="unusual"]').click();
    await capture("prediction-form.png");
    await Promise.all([page.waitForURL("**/result/**"), page.locator('#analyze-button').click()]);
    await page.locator(".score-ring").waitFor();
    assert.match(await page.locator(".result-copy h2").innerText(), /Potential Fraud/);
    await capture("prediction.png");
    for (const [url, file] of [["/", "home.png"], ["/dashboard/", "dashboard.png"], ["/transactions/", "transactions.png"]]) {
      await open(url);
      if (url === "/dashboard/") {
        await page.waitForFunction(() => typeof Chart !== "undefined" && Object.keys(Chart.instances).length === 5);
        const counts = await page.locator("#chart-data").textContent();
        const data = JSON.parse(counts);
        assert.equal(data.status.reduce((a, b) => a + b, 0), data.probability.reduce((a, b) => a + b, 0));
      }
      await capture(file);
    }
    await open("/about/");
    assert.match(await page.title(), /About/);
    await open("/transactions/?status=fraud&risk=high");
    assert.ok(await page.locator("tbody .prediction-badge.flagged").count() > 0);
    assert.equal(await page.locator("tbody .prediction-badge.legitimate").count(), 0);
    const download = await page.request.get(base + "/transactions/export/?status=fraud");
    assert.equal(download.status(), 200);
    assert.match(await download.text(), /transaction_id,date,amount_usd/);
    await open("/admin/login/?next=/admin/detection/transaction/");
    await page.locator("#id_username").fill(process.env.DEMO_ADMIN_USERNAME || "admin");
    await page.locator("#id_password").fill(process.env.DEMO_ADMIN_PASSWORD || "DemoAdmin123!");
    await Promise.all([page.waitForURL("**/admin/detection/transaction/"), page.locator('input[type="submit"]').click()]);
    await page.waitForLoadState("networkidle");
    assert.ok(await page.locator("#result_list tbody tr").count() > 0);
    await capture("admin-panel.png");
    await page.setViewportSize({ width: 390, height: 844 });
    for (const url of ["/", "/predict/", "/dashboard/", "/transactions/", "/about/"]) {
      await open(url);
      const fits = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
      assert.ok(fits, `No document overflow at 390px: ${url}`);
    }
    await open("/");
    await page.locator("#menu-toggle").click();
    assert.equal(await page.locator("#menu-toggle").getAttribute("aria-expanded"), "true");
    await page.locator("#sidebar-overlay").click({ position: { x: 300, y: 100 } });
    assert.equal(await page.locator("#menu-toggle").getAttribute("aria-expanded"), "false");
    await capture("mobile-home.png");
    assert.deepEqual(errors, [], "No browser errors or failed local resources");
    console.log("PASS: predictions, navigation, five charts, history filters, CSV, admin login, mobile layout and menu; no browser errors.");
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
