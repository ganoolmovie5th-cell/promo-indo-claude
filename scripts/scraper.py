"""
PromoIndo Scraper — Full Threads scraping via Playwright.
Runs daily via GitHub Actions. Outputs public/data/promos.json.
"""
import json
import os
import re
import time
import asyncio
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "public", "data")

# ─── Threads accounts to scrape ─────────────────────────────────────────────────
ACCOUNTS = [
    # Bank promo
    "promosbca", "bankmandiri", "bankbri_id",
    "bankbni", "bankmega.id",
    # E-wallet & Payment
    "gopaborindonesia", "ovoofficial", "shopeepay_id", "dana.id",
    # Marketplace & Food
    "grabid", "tokopedia", "shopee_id",
    # Promo aggregators
    "promojakarta", "infopromo.jkt", "jakartapromo",
    "promodiskon", "voucherdeal.id", "promobank.id",
    "diskonaja", "infodiskon", "promopedia.id",
]

PROMO_KEYWORDS = [
    "promo", "diskon", "cashback", "voucher", "gratis", "free",
    "hemat", "sale", "potongan", "kupon", "kode", "disc", "off",
    "buy 1", "beli 1", "flash sale", "special", "cicilan", "0%",
]

CATEGORIES = {
    "makanan": ["makan", "food", "resto", "kuliner", "pizza", "burger",
                "kfc", "mcd", "starbucks", "grabfood", "gofood", "coffee",
                "kopi", "jco", "j.co", "sushi", "bakery", "chatime",
                "hokben", "yoshinoya", "richeese", "mixue", "boba"],
    "belanja": ["diskon", "sale", "fashion", "belanja", "shopee",
                "tokopedia", "lazada", "blibli", "zalora", "uniqlo",
                "h&m", "zara", "ibox", "gadget", "elektronik"],
    "hiburan": ["bioskop", "cinema", "cgv", "xxi", "tiket konser",
                "event", "spotify", "netflix", "vidio", "disney",
                "nonton", "tix id", "film"],
    "hotel": ["hotel", "traveloka", "tiket.com", "agoda", "booking",
              "villa", "resort", "penginapan", "wisata", "travel",
              "pesawat", "flight"],
    "transport": ["grab", "gojek", "gocar", "goride", "grabcar",
                  "grabride", "transport", "kereta", "bbm", "bensin",
                  "pertamina", "shell", "bp"],
    "kesehatan": ["apotek", "halodoc", "alodokter", "farmasi",
                  "vitamin", "kesehatan", "klinik", "obat"],
    "keuangan": ["cashback", "cicilan", "bunga", "kredit", "debit",
                 "kartu", "paylater", "pinjaman", "tagihan", "pln",
                 "bpjs", "transfer"],
}


def classify(text):
    t = text.lower()
    scores = {}
    for cat, kws in CATEGORIES.items():
        scores[cat] = sum(1 for kw in kws if kw in t)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "lainnya"


def extract_discount(text):
    m = re.search(r'(\d+)\s*%', text)
    if m:
        return f"{m.group(1)}%"
    if "gratis ongkir" in text.lower():
        return "Gratis Ongkir"
    if "buy 1" in text.lower() or "beli 1" in text.lower():
        return "Buy 1 Get 1"
    return None


def extract_code(text):
    m = re.search(
        r'(?:kode|code|voucher|kupon)[:\s]*([A-Z0-9]{4,15})',
        text, re.IGNORECASE
    )
    return m.group(1).upper() if m else None


def extract_valid_until(text):
    m = re.search(
        r'(?:s/?d|sampai|hingga|until|berlaku|expired?)[:\s]*'
        r'(\d{1,2}[\s/\-]\w+[\s/\-]\d{2,4})',
        text, re.IGNORECASE
    )
    return m.group(1) if m else None


def is_promo_post(text):
    t = text.lower()
    return any(kw in t for kw in PROMO_KEYWORDS)


async def scrape_threads_account(page, username):
    """Scrape posts from a single Threads account using Playwright."""
    posts = []
    url = f"https://www.threads.net/@{username}"

    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        # Wait for post content to render
        await page.wait_for_timeout(3000)

        # Scroll down to load more posts
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 1000)")
            await page.wait_for_timeout(1500)

        # Extract post texts from the page
        # Threads uses various selectors for post text
        selectors = [
            '[data-pressable-container="true"] span',
            'article span[dir="auto"]',
            'div[data-pressable-container] span[dir="auto"]',
            'span[class*="x1lliihq"]',
        ]

        texts = set()
        for sel in selectors:
            elements = await page.query_selector_all(sel)
            for el in elements:
                text = await el.inner_text()
                if text and len(text) > 30 and is_promo_post(text):
                    texts.add(text[:500])

        for text in texts:
            posts.append({
                "id": f"{username}_{hash(text) % 100000}",
                "source": f"@{username}",
                "source_url": f"https://www.threads.net/@{username}",
                "text": text,
                "category": classify(text),
                "discount": extract_discount(text),
                "code": extract_code(text),
                "valid_until": extract_valid_until(text),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })

    except Exception as e:
        print(f"  [!] Error @{username}: {e}")

    return posts


async def main_async():
    from playwright.async_api import async_playwright

    os.makedirs(DATA_DIR, exist_ok=True)
    all_promos = []

    print(f"[*] Launching Playwright browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/128.0.0.0 Safari/537.36",
            locale="id-ID",
        )
        page = await context.new_page()

        print(f"[*] Scraping {len(ACCOUNTS)} Threads accounts...")
        for i, account in enumerate(ACCOUNTS):
            print(f"  [{i+1}/{len(ACCOUNTS)}] @{account}")
            posts = await scrape_threads_account(page, account)
            if posts:
                print(f"    Found {len(posts)} promo(s)")
                all_promos.extend(posts)
            # Rate limit between accounts
            await page.wait_for_timeout(2000)

        await browser.close()

    # Load existing data to merge
    data_file = os.path.join(DATA_DIR, "promos.json")
    existing = []
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    # Merge new + existing, deduplicate
    seen = set()
    unique = []
    for p in all_promos + existing:
        key = p.get("text", "")[:80]
        if key not in seen:
            seen.add(key)
            unique.append(p)

    # Sort newest first, keep max 500
    unique.sort(key=lambda x: x.get("scraped_at", ""), reverse=True)
    unique = unique[:500]

    # Write data
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    # Write metadata
    meta = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_promos": len(unique),
        "accounts_scraped": len(ACCOUNTS),
        "categories": list(CATEGORIES.keys()) + ["lainnya"],
    }
    with open(os.path.join(DATA_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n[*] Done! {len(unique)} promos saved.")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
