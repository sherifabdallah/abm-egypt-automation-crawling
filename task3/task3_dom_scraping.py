"""
Task 3: DOM Scraping Assessment
- Scrape ALL images as base64 → allimages.json
- Scrape only VISIBLE images as base64 → visible_images_only.json
- Scrape only VISIBLE text instructions → visible_text.txt
"""

import asyncio
import base64
import json
import re
import httpx
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

# NOTE: Replace with the actual URL from the assessment PDF "Click Here" link.
# The PDF had a hyperlink that wasn't extracted as text — use the real URL here.
TARGET_URL = "https://cd.captchaaiplus.com/dom.html"


async def fetch_image_as_base64(client: httpx.AsyncClient, url: str) -> str | None:
    """Download an image URL and return its base64-encoded content."""
    try:
        resp = await client.get(url, timeout=15, follow_redirects=True)
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "image/png").split(";")[0].strip()
            b64 = base64.b64encode(resp.content).decode("utf-8")
            return f"data:{content_type};base64,{b64}"
    except Exception as e:
        print(f"  [Warning] Failed to fetch {url[:80]}: {e}")
    return None


async def run_task3(headless: bool = True):
    print(f"\n{'='*60}")
    print("Task 3: DOM Scraping")
    print(f"{'='*60}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        print(f"[Navigate] Opening {TARGET_URL} ...")
        await page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)

        # ─────────────────────────────────────────────────────────────────────
        # PART A: Collect ALL images (src, data-src, srcset, CSS backgrounds)
        # ─────────────────────────────────────────────────────────────────────
        print("[Scrape] Collecting ALL image URLs from the DOM...")
        all_image_data = await page.evaluate("""
            () => {
                const images = [];
                const seen = new Set();

                const addImg = (src, tag, location) => {
                    if (!src || src.startsWith('data:') || seen.has(src)) return;
                    seen.add(src);
                    images.push({ src, tag, location });
                };

                // <img> tags
                document.querySelectorAll('img').forEach(el => {
                    addImg(el.src, 'img', el.closest('[id]')?.id || '');
                    addImg(el.dataset.src, 'img[data-src]', '');
                    addImg(el.dataset.lazySrc, 'img[data-lazy-src]', '');
                    if (el.srcset) {
                        el.srcset.split(',').forEach(s => {
                            addImg(s.trim().split(' ')[0], 'img[srcset]', '');
                        });
                    }
                });

                // <picture><source> tags
                document.querySelectorAll('source').forEach(el => {
                    if (el.srcset) {
                        el.srcset.split(',').forEach(s => {
                            addImg(s.trim().split(' ')[0], 'source[srcset]', '');
                        });
                    }
                });

                // CSS background-image
                document.querySelectorAll('*').forEach(el => {
                    const style = window.getComputedStyle(el);
                    const bg = style.backgroundImage;
                    if (bg && bg !== 'none') {
                        const match = bg.match(/url\(['"]?([^'"()]+)['"]?\)/);
                        if (match) addImg(match[1], 'css-background', el.tagName);
                    }
                });

                return images;
            }
        """)
        print(f"[Scrape] Found {len(all_image_data)} total image URLs.")

        # ─────────────────────────────────────────────────────────────────────
        # PART B: Visible images only
        # ─────────────────────────────────────────────────────────────────────
        print("[Scrape] Identifying VISIBLE images...")
        visible_image_data = await page.evaluate("""
            () => {
                const images = [];
                const seen = new Set();

                const isVisible = (el) => {
                    if (!el) return false;
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return (
                        rect.width > 0 &&
                        rect.height > 0 &&
                        style.display !== 'none' &&
                        style.visibility !== 'hidden' &&
                        style.opacity !== '0' &&
                        rect.top < window.innerHeight &&
                        rect.bottom > 0
                    );
                };

                document.querySelectorAll('img').forEach(el => {
                    if (isVisible(el) && el.src && !seen.has(el.src)) {
                        seen.add(el.src);
                        const rect = el.getBoundingClientRect();
                        images.push({
                            src: el.src,
                            alt: el.alt || '',
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        });
                    }
                });

                return images;
            }
        """)
        print(f"[Scrape] Found {len(visible_image_data)} visible images.")

        # ─────────────────────────────────────────────────────────────────────
        # PART C: Visible text instructions
        # ─────────────────────────────────────────────────────────────────────
        print("[Scrape] Extracting visible text content...")
        visible_text_nodes = await page.evaluate("""
            () => {
                const texts = [];
                const isVisible = (el) => {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return (
                        style.display !== 'none' &&
                        style.visibility !== 'hidden' &&
                        parseFloat(style.opacity) > 0 &&
                        rect.width > 0 &&
                        rect.height > 0
                    );
                };

                // Walk all text-bearing elements
                const candidates = document.querySelectorAll(
                    'p, li, h1, h2, h3, h4, h5, h6, span, div, label, td, th'
                );
                const seen = new Set();
                candidates.forEach(el => {
                    if (!isVisible(el)) return;
                    // Only grab leaf-ish nodes (avoid duplicating parent text)
                    const directText = Array.from(el.childNodes)
                        .filter(n => n.nodeType === Node.TEXT_NODE)
                        .map(n => n.textContent.trim())
                        .join(' ')
                        .trim();
                    if (directText.length > 3 && !seen.has(directText)) {
                        seen.add(directText);
                        texts.push({
                            tag: el.tagName.toLowerCase(),
                            text: directText,
                        });
                    }
                });
                return texts;
            }
        """)
        print(f"[Scrape] Found {len(visible_text_nodes)} visible text nodes.")

        await context.close()
        await browser.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Download all images and encode as base64
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[Download] Fetching & encoding ALL images as base64...")
    all_images_json = []
    visible_images_json = []

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        verify=False,
    ) as client:
        # ALL images
        for i, img in enumerate(all_image_data, 1):
            src = img["src"]
            if src.startswith("data:"):
                b64_data = src  # already base64
            else:
                url = src if src.startswith("http") else urljoin(TARGET_URL, src)
                b64_data = await fetch_image_as_base64(client, url)
            all_images_json.append({
                "index": i,
                "src": src,
                "tag": img.get("tag", ""),
                "base64": b64_data or "FETCH_FAILED",
            })
            if i % 10 == 0:
                print(f"  ... processed {i}/{len(all_image_data)} images")

        # VISIBLE images
        visible_src_set = {img["src"] for img in visible_image_data}
        for entry in all_images_json:
            if entry["src"] in visible_src_set:
                # Find metadata
                meta = next((v for v in visible_image_data if v["src"] == entry["src"]), {})
                visible_images_json.append({
                    **entry,
                    "alt": meta.get("alt", ""),
                    "rendered_width": meta.get("width"),
                    "rendered_height": meta.get("height"),
                })

    # ─────────────────────────────────────────────────────────────────────────
    # Save outputs
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n[Save] Writing allimages.json ({len(all_images_json)} entries)...")
    with open("allimages.json", "w", encoding="utf-8") as f:
        json.dump(all_images_json, f, indent=2, ensure_ascii=False)

    print(f"[Save] Writing visible_images_only.json ({len(visible_images_json)} entries)...")
    with open("visible_images_only.json", "w", encoding="utf-8") as f:
        json.dump(visible_images_json, f, indent=2, ensure_ascii=False)

    print(f"[Save] Writing visible_text.txt ({len(visible_text_nodes)} lines)...")
    with open("visible_text.txt", "w", encoding="utf-8") as f:
        for node in visible_text_nodes:
            f.write(f"[{node['tag'].upper()}] {node['text']}\n")

    print("\n✅ Task 3 complete!")
    print(f"   allimages.json         — {len(all_images_json)} images (all)")
    print(f"   visible_images_only.json — {len(visible_images_json)} images (visible)")
    print(f"   visible_text.txt       — {len(visible_text_nodes)} text entries")


if __name__ == "__main__":
    asyncio.run(run_task3(headless=True))
