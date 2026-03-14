"""
Task 1: Automation - Stealth Assessment
Bypass Cloudflare Turnstile using Python Playwright with stealth techniques.
Runs 10 attempts and reports success rate.
"""

import asyncio
import json
import time
from playwright.async_api import async_playwright

TARGET_URL = "https://cd.captchaaiplus.com/turnstile.html"
ATTEMPTS = 10
TIMEOUT_MS = 30000


async def attempt_turnstile(browser, attempt_num: int, headless: bool) -> dict:
    """
    Single attempt to solve the Cloudflare Turnstile captcha.
    Returns a dict with attempt result details.
    """
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="en-US",
        timezone_id="America/New_York",
        java_script_enabled=True,
        # Record video for each attempt
        record_video_dir="videos/" if not headless else None,
    )

    # Stealth: override navigator properties to avoid bot detection
    await context.add_init_script("""
        // Overwrite the `languages` property to use a custom getter
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        // Overwrite the `plugins` property to use a custom getter
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        // Pass webdriver check
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        // Add chrome object to window
        window.chrome = {
            runtime: {},
        };
        // Permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    """)

    page = await context.new_page()
    result = {
        "attempt": attempt_num,
        "success": False,
        "token": None,
        "error": None,
        "duration_s": 0,
    }
    start = time.time()

    try:
        print(f"\n[Attempt {attempt_num}] Navigating to {TARGET_URL} ...")
        await page.goto(TARGET_URL, wait_until="networkidle", timeout=TIMEOUT_MS)
        await page.wait_for_timeout(2000)

        # Fill in the form fields
        await page.fill('input[name="first-name"], input[placeholder*="First"], #first-name', "Jane")
        await page.fill('input[name="last-name"], input[placeholder*="Last"], #last-name', "Smith")
        await page.wait_for_timeout(1000)

        # Wait for Turnstile iframe to load
        print(f"[Attempt {attempt_num}] Waiting for Turnstile iframe...")
        await page.wait_for_selector("iframe[src*='challenges.cloudflare.com']", timeout=TIMEOUT_MS)
        await page.wait_for_timeout(3000)

        # Try to find and click the Turnstile checkbox inside the iframe
        frames = page.frames
        turnstile_frame = None
        for frame in frames:
            if "challenges.cloudflare.com" in frame.url:
                turnstile_frame = frame
                break

        if turnstile_frame:
            print(f"[Attempt {attempt_num}] Found Turnstile frame, attempting click...")
            try:
                checkbox = await turnstile_frame.wait_for_selector(
                    "input[type='checkbox'], .cf-turnstile-part--checkbox, [id*='checkbox']",
                    timeout=10000
                )
                if checkbox:
                    await checkbox.click()
                    await page.wait_for_timeout(3000)
            except Exception:
                # Some Turnstile variants auto-verify without a click
                print(f"[Attempt {attempt_num}] No checkbox found, waiting for auto-verify...")
                await page.wait_for_timeout(5000)
        else:
            print(f"[Attempt {attempt_num}] Waiting for auto-verification...")
            await page.wait_for_timeout(5000)

        # Check if verification succeeded (look for success indicator in iframe)
        verified = False
        for frame in page.frames:
            if "challenges.cloudflare.com" in frame.url:
                try:
                    success_el = await frame.query_selector(".cf-turnstile-part--success, [class*='success']")
                    if success_el:
                        verified = True
                        break
                except Exception:
                    pass

        # Extract the token from the hidden input
        token = await page.evaluate("""
            () => {
                const el = document.querySelector(
                    'input[name="cf-turnstile-response"], ' +
                    'input[name="turnstile-response"], ' +
                    'textarea[name="cf-turnstile-response"]'
                );
                return el ? el.value : null;
            }
        """)

        if token and len(token) > 10:
            verified = True
            result["token"] = token
            print(f"[Attempt {attempt_num}] ✅ Token captured: {token[:60]}...")
        elif not verified:
            print(f"[Attempt {attempt_num}] Verification status uncertain, checking page...")

        # Click submit
        print(f"[Attempt {attempt_num}] Clicking Submit...")
        await page.click("button[type='submit'], input[type='submit'], button:text('Submit')")
        await page.wait_for_timeout(3000)

        # Check for success message
        page_content = await page.content()
        success_texts = ["Success! Turnstile verified", "Success! Verified", "Turnstile verified"]
        for text in success_texts:
            if text.lower() in page_content.lower():
                result["success"] = True
                print(f"[Attempt {attempt_num}] ✅ SUCCESS - Got verified message!")
                break

        if not result["success"]:
            # Try checking visible text
            try:
                success_el = await page.wait_for_selector(
                    "text=Success, [class*='success-message'], #success",
                    timeout=5000
                )
                if success_el:
                    result["success"] = True
                    print(f"[Attempt {attempt_num}] ✅ SUCCESS via element check!")
            except Exception:
                print(f"[Attempt {attempt_num}] ❌ FAILED - No success message found.")

    except Exception as e:
        result["error"] = str(e)
        print(f"[Attempt {attempt_num}] ❌ ERROR: {e}")

    finally:
        result["duration_s"] = round(time.time() - start, 2)
        await page.close()
        await context.close()

    return result


async def run_task1(headless: bool = False):
    print(f"\n{'='*60}")
    print(f"Task 1: Turnstile Bypass — headless={headless}")
    print(f"Running {ATTEMPTS} attempts...")
    print(f"{'='*60}")

    results = []

    async with async_playwright() as p:
        # Launch with stealth args
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1280,800",
                "--start-maximized",
                "--disable-extensions",
                "--disable-plugins-discovery",
                "--disable-web-security",
            ],
        )

        for i in range(1, ATTEMPTS + 1):
            result = await attempt_turnstile(browser, i, headless)
            results.append(result)
            # Brief pause between attempts
            if i < ATTEMPTS:
                await asyncio.sleep(2)

        await browser.close()

    # Summary
    successes = sum(1 for r in results if r["success"])
    success_rate = (successes / ATTEMPTS) * 100
    tokens = [r["token"] for r in results if r["token"]]

    print(f"\n{'='*60}")
    print(f"RESULTS SUMMARY (headless={headless})")
    print(f"{'='*60}")
    print(f"Total Attempts : {ATTEMPTS}")
    print(f"Successes      : {successes}")
    print(f"Failures       : {ATTEMPTS - successes}")
    print(f"Success Rate   : {success_rate:.1f}%")
    if tokens:
        print(f"\nCaptured Tokens:")
        for t in tokens:
            print(f"  {t[:80]}...")
    print(f"{'='*60}\n")

    # Save results to JSON
    output = {
        "headless": headless,
        "total_attempts": ATTEMPTS,
        "successes": successes,
        "success_rate_pct": success_rate,
        "results": results,
        "tokens": tokens,
    }
    fname = f"results_headless_{headless}.json"
    with open(fname, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Results saved to {fname}")
    return output


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "both"

    if mode == "headless" or mode == "both":
        asyncio.run(run_task1(headless=True))

    if mode == "headed" or mode == "both":
        asyncio.run(run_task1(headless=False))
