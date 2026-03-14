"""
Task 2: Network Interception
- Open the Turnstile page and immediately block/intercept the Turnstile from loading
- Capture the Turnstile configuration details (sitekey, pageaction, cdata, pagedata)
- Inject a valid token (obtained from Task 1) to bypass the CAPTCHA
- Submit and confirm "Success! Verified"
"""

import asyncio
import json
import re
from playwright.async_api import async_playwright, Route, Request

TARGET_URL = "https://cd.captchaaiplus.com/turnstile.html"

# ──────────────────────────────────────────────────────────────────────────────
# Replace this with a fresh token captured from Task 1.
# Tokens are single-use, so generate a new one before each run.
# Example (invalid placeholder):
INJECTED_TOKEN = "YOUR_VALID_TOKEN_FROM_TASK1_HERE"
# ──────────────────────────────────────────────────────────────────────────────

captured_details: dict = {
    "sitekey": None,
    "pageaction": None,
    "cdata": None,
    "pagedata": None,
    "blocked_requests": [],
}


async def intercept_turnstile(route: Route, request: Request):
    """
    Intercept all Cloudflare Turnstile network requests.
    - Log the request URL and extract parameters.
    - Abort the request so the widget never loads.
    """
    url = request.url
    captured_details["blocked_requests"].append(url)
    print(f"[Intercept] Blocked: {url[:120]}")

    # Extract query parameters from the Turnstile challenge URL
    # e.g. https://challenges.cloudflare.com/turnstile/v0/...?sitekey=...&...
    param_map = {}
    if "?" in url:
        query = url.split("?", 1)[1]
        for pair in query.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                param_map[k] = v

    for key in ("sitekey", "pageaction", "cdata", "pagedata"):
        if key in param_map and not captured_details[key]:
            captured_details[key] = param_map[key]
            print(f"[Intercept] Captured {key}: {param_map[key][:80]}")

    # Also try to parse from the URL path for api-based calls
    sitekey_match = re.search(r"/turnstile/v\d+/([A-Za-z0-9_\-]+)", url)
    if sitekey_match and not captured_details["sitekey"]:
        captured_details["sitekey"] = sitekey_match.group(1)

    # Abort the request — widget will not load
    await route.abort()


async def run_task2(headless: bool = False):
    print(f"\n{'='*60}")
    print("Task 2: Network Interception & Token Injection")
    print(f"{'='*60}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--window-size=1280,800",
            ],
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            record_video_dir="videos/",
        )

        # Stealth overrides
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        page = await context.new_page()

        # ── Step 1: Register route intercept BEFORE navigation ──────────────
        # Block all Cloudflare Turnstile resources
        await page.route("**/challenges.cloudflare.com/**", intercept_turnstile)
        await page.route("**/turnstile**", intercept_turnstile)
        print("[Setup] Route intercept registered for Cloudflare Turnstile.")

        # ── Step 2: Navigate to the target page ─────────────────────────────
        print(f"[Navigate] Opening {TARGET_URL} ...")
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # ── Step 3: Try to capture sitekey from page HTML/scripts ───────────
        html = await page.content()

        # Look for data-sitekey attribute on the turnstile widget div
        sitekey_match = re.search(
            r'data-sitekey=["\']([A-Za-z0-9_\-]+)["\']', html
        )
        if sitekey_match and not captured_details["sitekey"]:
            captured_details["sitekey"] = sitekey_match.group(1)

        # Look for pageaction
        action_match = re.search(r'data-action=["\']([^"\']+)["\']', html)
        if action_match:
            captured_details["pageaction"] = action_match.group(1)

        # Look for cdata
        cdata_match = re.search(r'data-cdata=["\']([^"\']+)["\']', html)
        if cdata_match:
            captured_details["cdata"] = cdata_match.group(1)

        print(f"\n[Captured Details]")
        print(f"  sitekey   : {captured_details['sitekey']}")
        print(f"  pageaction: {captured_details['pageaction']}")
        print(f"  cdata     : {captured_details['cdata']}")
        print(f"  pagedata  : {captured_details['pagedata']}")
        print(f"  Blocked {len(captured_details['blocked_requests'])} request(s)")

        # ── Step 4: Fill form fields ─────────────────────────────────────────
        try:
            await page.fill(
                'input[name="first-name"], input[id="first-name"], '
                'input[placeholder*="First"]',
                "Jane"
            )
            await page.fill(
                'input[name="last-name"], input[id="last-name"], '
                'input[placeholder*="Last"]',
                "Smith"
            )
        except Exception as e:
            print(f"[Form] Warning filling fields: {e}")

        # ── Step 5: Inject the token into the hidden input ──────────────────
        print(f"\n[Inject] Injecting token into cf-turnstile-response ...")
        injected = await page.evaluate(
            """(token) => {
                // Standard hidden input used by Turnstile
                const selectors = [
                    'input[name="cf-turnstile-response"]',
                    'textarea[name="cf-turnstile-response"]',
                    'input[name="turnstile-response"]',
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        el.value = token;
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
                // If hidden input doesn't exist yet, create it
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'cf-turnstile-response';
                input.value = token;
                const form = document.querySelector('form');
                if (form) {
                    form.appendChild(input);
                    return true;
                }
                document.body.appendChild(input);
                return true;
            }""",
            INJECTED_TOKEN,
        )
        print(f"[Inject] Token injection {'succeeded' if injected else 'failed'}.")
        await page.wait_for_timeout(1000)

        # ── Step 6: Submit the form ─────────────────────────────────────────
        print("[Submit] Clicking Submit button ...")
        await page.click(
            "button[type='submit'], input[type='submit'], button:text('Submit')"
        )
        await page.wait_for_timeout(4000)

        # ── Step 7: Check result ────────────────────────────────────────────
        page_text = await page.inner_text("body")
        success = any(
            phrase.lower() in page_text.lower()
            for phrase in ["Success! Turnstile verified", "Turnstile verified", "Success! Verified"]
        )

        if success:
            print("\n✅ SUCCESS — 'Turnstile verified' message detected!")
        else:
            print("\n❌ No success message found. Page text snippet:")
            print(page_text[:400])

        # ── Save captured details ───────────────────────────────────────────
        output = {
            "captured_turnstile_details": captured_details,
            "token_injected": INJECTED_TOKEN[:40] + "...",
            "submission_success": success,
        }
        with open("task2_results.json", "w") as f:
            json.dump(output, f, indent=2)
        print("\n[Output] Results saved to task2_results.json")

        await page.wait_for_timeout(2000)  # let video capture the result
        await context.close()
        await browser.close()

    return output


if __name__ == "__main__":
    asyncio.run(run_task2(headless=False))
