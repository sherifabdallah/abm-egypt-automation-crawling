# ABM Egypt - Python Developer Assessment (Automation & Crawling)

## Project Structure

```
abm_assessment/
├── task1/
│   └── task1_turnstile_bypass.py      # Cloudflare Turnstile bypass (10 attempts)
├── task2/
│   └── task2_network_intercept.py     # Network interception + token injection
├── task3/
│   └── task3_dom_scraping.py          # DOM scraping (all images, visible images, text)
├── task4/
│   ├── task4_architecture_diagram.py  # Generates the architecture diagram
│   ├── architecture_diagram.png       # Rendered diagram (PNG)
│   ├── architecture_diagram.svg       # Rendered diagram (SVG)
│   └── ARCHITECTURE.md                # Layer-by-layer explanation
├── requirements.txt
└── README.md
```

---

## Setup

```bash
# 1. Clone the repo
git clone <repo_url>
cd abm_assessment

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium
```

---

## Task 1 - Automation: Cloudflare Turnstile Bypass

**Goal:** Use Playwright (headless + headed) to automatically solve the Cloudflare Turnstile CAPTCHA on `https://cd.captchaaiplus.com/turnstile.html`, submit the form, and print the token. Run 10 attempts; achieve ≥ 60% success rate.

### Approach

- Playwright is launched with **stealth arguments** that suppress the `navigator.webdriver` flag and spoof browser fingerprints (plugins, languages, chrome object).
- Each attempt navigates to the target URL, fills in the form, waits for the Turnstile iframe to appear, and waits for the widget to auto-verify (non-interactive Turnstile mode).
- The hidden `cf-turnstile-response` input is read to capture the token after successful verification.
- Results (success/fail, token, duration) are written to `results_headless_True.json` and `results_headless_False.json`.

### Run

```bash
cd task1

# Both modes (headless=True then headless=False)
python task1_turnstile_bypass.py both

# Headless only
python task1_turnstile_bypass.py headless

# Headed (visible browser) only
python task1_turnstile_bypass.py headed
```

### Output
- `results_headless_True.json` - attempt details + tokens (headless mode)
- `results_headless_False.json` - attempt details + tokens (headed mode)
- `videos/` - screen recordings per attempt (headed mode)

---

## Task 2 - Network Interception & Token Injection

**Goal:** Open the Turnstile page, immediately block the Turnstile widget from loading, capture its configuration (sitekey, pageaction, cdata, pagedata), inject a valid token from Task 1, submit, and receive "Success! Verified".

### Approach

- Before navigation, `page.route("**/challenges.cloudflare.com/**", handler)` is registered to intercept all Cloudflare Turnstile requests and call `route.abort()`.
- The handler extracts query parameters (sitekey, pageaction, cdata, pagedata) from the blocked URLs.
- A fallback regex scan of the page HTML captures `data-sitekey` if not found in network calls.
- The captured token from Task 1 is injected directly into the `cf-turnstile-response` hidden input via `page.evaluate(...)`.
- The form is submitted and the success message is verified.

### Before Running

Open `task2_network_intercept.py` and replace `INJECTED_TOKEN` with a fresh token captured from Task 1 (tokens are single-use):

```python
INJECTED_TOKEN = "YOUR_VALID_TOKEN_FROM_TASK1_HERE"
```

### Run

```bash
cd task2
python task2_network_intercept.py
```

### Output
- `task2_results.json` - captured Turnstile details + injection result
- `videos/` - screen recording showing the widget never loads but form submits successfully

---

## Task 3 - DOM Scraping

**Goal:** Scrape (1) all images as base64, (2) only visible images as base64, and (3) visible text instructions from the target page.

### Approach

- Playwright loads the page and runs JavaScript evaluation to walk the DOM.
- **All images**: Collected from `<img src/srcset>`, `<source srcset>`, `data-src` lazy attributes, and CSS `background-image` computed styles.
- **Visible images only**: Filtered using `getBoundingClientRect()` + computed `display/visibility/opacity` checks in-viewport.
- **Visible text**: Walks `p, li, h1–h6, span, div, label, td, th` elements, filtering by the same visibility criteria, and extracts direct text nodes to avoid duplication.
- All image URLs are then fetched asynchronously with `httpx` and encoded as base64 data URIs.

### Run

```bash
cd task3
python task3_dom_scraping.py
```

### Output
- `allimages.json` - every image on the page (src, tag, base64)
- `visible_images_only.json` - only in-viewport visible images (src, tag, base64, rendered dimensions)
- `visible_text.txt` - visible human-readable text, one entry per line

---

## Task 4 - System Architecture Diagram

**Goal:** Design a comprehensive architecture for a distributed automation/crawling system.

See [`task4/ARCHITECTURE.md`](task4/ARCHITECTURE.md) for the full layer-by-layer explanation.

### Diagram highlights

| Layer | Technology |
|---|---|
| API Gateway | nginx / AWS ALB |
| Message Queue | RabbitMQ Cluster (mirrored) |
| Workers | Python Playwright/httpx - auto-scaled on Kubernetes |
| Database | PostgreSQL (primary + replica) + Redis + S3/MinIO |
| Monitoring | Prometheus, Grafana, Alertmanager, ELK, Jaeger |
| Failover | Patroni DB failover, RabbitMQ mirror promotion, DLQ + retry |

### Regenerate diagram

```bash
cd task4
python task4_architecture_diagram.py
# Outputs: architecture_diagram.png, architecture_diagram.svg
```

---

