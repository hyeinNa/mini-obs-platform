import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const SCREENSHOTS_DIR = new URL('../docs/screenshots/', import.meta.url).pathname;
mkdirSync(SCREENSHOTS_DIR, { recursive: true });

async function capture(page, url, filename, opts = {}) {
  try {
    console.log(`  Capturing ${filename}...`);
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    if (opts.wait) await page.waitForTimeout(opts.wait);
    if (opts.action) await opts.action(page);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/${filename}`, fullPage: opts.fullPage || false });
    console.log(`  ✓ ${filename}`);
  } catch (e) {
    console.log(`  ✗ ${filename}: ${e.message}`);
  }
}

async function main() {
  console.log('==> Launching browser...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, ignoreHTTPSErrors: true });
  const page = await context.newPage();

  // 1. Grafana (localhost:3000)
  console.log('\n==> Grafana Screenshots');
  // Login
  await page.goto('http://localhost:3000/login', { waitUntil: 'networkidle', timeout: 30000 });
  await page.fill('input[name="user"]', 'admin');
  await page.fill('input[name="password"]', 'admin');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);
  // Skip password change if prompted
  try { await page.click('a:has-text("Skip")', { timeout: 3000 }); } catch {}

  // Grafana home
  await capture(page, 'http://localhost:3000/', 'grafana-home.png', { wait: 2000 });

  // Grafana datasources
  await capture(page, 'http://localhost:3000/connections/datasources', 'grafana-datasources.png', { wait: 2000 });

  // RED Metrics dashboard (search by name)
  await capture(page, 'http://localhost:3000/dashboards', 'grafana-dashboards.png', { wait: 2000 });

  // Explore - Prometheus
  await capture(page, 'http://localhost:3000/explore', 'grafana-explore.png', { wait: 2000 });

  // 2. Prometheus Targets (localhost:9090)
  console.log('\n==> Prometheus Screenshots');
  await capture(page, 'http://localhost:9090/targets', 'prometheus-targets.png', { wait: 3000, fullPage: true });
  await capture(page, 'http://localhost:9090/graph?g0.expr=http_requests_total&g0.tab=0', 'prometheus-query.png', { wait: 3000 });

  // 3. Jaeger UI (localhost:16686)
  console.log('\n==> Jaeger Screenshots');
  await capture(page, 'http://localhost:16686/', 'jaeger-ui.png', { wait: 2000 });
  await capture(page, 'http://localhost:16686/search', 'jaeger-search.png', { wait: 2000 });

  // 4. ArgoCD UI (localhost:8090)
  console.log('\n==> ArgoCD Screenshots');
  await capture(page, 'https://localhost:8090/', 'argocd-login.png', { wait: 2000 });

  // 5. kubectl outputs as terminal screenshots
  console.log('\n==> Terminal screenshots will be captured separately');

  await browser.close();
  console.log('\n==> All screenshots captured!');
}

main().catch(e => { console.error(e); process.exit(1); });
