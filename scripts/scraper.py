"""
PromoIndo Scraper — Full Threads scraping via Playwright (Stealth Mode).
Techniques: stealth browser, randomized delays, scroll loading, retry, anti-detection.
"""
import json
import os
import re
import random
import asyncio
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "public", "data")

ACCOUNTS = [
    # Bank besar
    "promosbca", "bankmandiri", "bankbri_id", "bankbni", "bankmega.id",
    # Bank digital & baru
    "jaborofficial", "blu.bybcadigital", "bankjago.id",
    "seaborid", "superbank_id", "bankneocommerce",
    "linebank_id", "motionbanking", "digiaborid",
    # E-wallet & Payment
    "gopayindonesia", "ovoofficial", "shopeepay_id", "dana.id",
    "linkaja", "isaborid", "astrapay.id",
    # Marketplace
    "grabid", "tokopedia", "shopee_id",
    "lazada_id", "bliblipromo", "taborofficial",
    # Food delivery
    "grabfoodid", "gofoodindonesia",
    # Travel & Lifestyle
    "taborofficial", "tiaborcom", "pegipegi",
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
                "kopi", "jco", "j.co", "sushi", "hokben", "mixue", "chatime"],
    "belanja": ["diskon", "sale", "fashion", "belanja", "shopee",
                "tokopedia", "lazada", "blibli", "zalora", "uniqlo",
                "gadget", "elektronik", "ibox"],
    "hiburan": ["bioskop", "cinema", "cgv", "xxi", "konser",
                "spotify", "netflix", "nonton", "tix", "film"],
    "hotel": ["hotel", "traveloka", "tiket.com", "agoda", "booking",
              "villa", "resort", "wisata", "pesawat", "flight"],
    "transport": ["grab", "gojek", "gocar", "goride", "grabcar",
                  "transport", "kereta", "bbm", "bensin", "bandara"],
    "kesehatan": ["apotek", "halodoc", "alodokter", "obat", "vitamin",
                  "kesehatan", "klinik"],
    "keuangan": ["cashback", "cicilan", "bunga", "kredit", "debit",
                 "kartu", "paylater", "tagihan", "pln", "transfer"],
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
    m = re.search(r'(?:kode|code|voucher|kupon)[:\s]*([A-Z0-9]{4,15})', text, re.IGNORECASE)
    return m.group(1).upper() if m else None


def extract_valid_until(text):
    m = re.search(
        r'(?:s/?d|sampai|hingga|until|berlaku|expired?|periode)[:\s]*(\d{1,2}[\s/\-]\w+[\s/\-]\d{2,4})',
        text, re.IGNORECASE)
    return m.group(1) if m else None


def is_promo_post(text):
    t = text.lower()
    return any(kw in t for kw in PROMO_KEYWORDS)


def parse_date_id(s):
    if not s:
        return None
    months = {"januari":1,"februari":2,"maret":3,"april":4,"mei":5,"juni":6,
              "juli":7,"agustus":8,"september":9,"oktober":10,"november":11,"desember":12}
    m = re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})', s.strip())
    if m:
        mon = months.get(m.group(2).lower())
        if mon:
            from datetime import date
            return date(int(m.group(3)), mon, int(m.group(1)))
    m2 = re.match(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', s.strip())
    if m2:
        from datetime import date
        return date(int(m2.group(3)), int(m2.group(2)), int(m2.group(1)))
    return None


# ─── Stealth browser config ─────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
]


async def stealth_page(context):
    """Create a stealth page with anti-detection measures."""
    page = await context.new_page()

    # Override navigator.webdriver to false
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['id-ID', 'id', 'en-US', 'en'] });
        window.chrome = { runtime: {} };
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters);
    """)
    return page


async def scrape_account(page, username, retry=2):
    """Scrape posts from a Threads account with retries."""
    posts = []
    url = f"https://www.threads.net/@{username}"

    for attempt in range(retry):
        try:
            # Random delay to appear human
            await page.wait_for_timeout(random.randint(1000, 3000))

            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            if response and response.status == 200:
                # Wait for content to render
                await page.wait_for_timeout(random.randint(3000, 5000))

                # Scroll down multiple times to trigger lazy loading
                for scroll in range(4):
                    await page.evaluate(f"window.scrollBy(0, {random.randint(800, 1200)})")
                    await page.wait_for_timeout(random.randint(1000, 2000))

                # Try multiple extraction methods
                texts = set()

                # Method 1: Get all visible text blocks
                elements = await page.query_selector_all('div[dir="auto"]')
                for el in elements:
                    try:
                        text = await el.inner_text()
                        if text and len(text) > 30:
                            texts.add(text.strip()[:500])
                    except Exception:
                        continue

                # Method 2: Broader span selection
                if not texts:
                    spans = await page.query_selector_all('span[dir="auto"]')
                    for sp in spans:
                        try:
                            text = await sp.inner_text()
                            if text and len(text) > 30:
                                texts.add(text.strip()[:500])
                        except Exception:
                            continue

                # Method 3: Extract from page content/meta
                if not texts:
                    content = await page.content()
                    # Look for og:description or meta content
                    meta_texts = re.findall(
                        r'content="([^"]{30,500})"', content)
                    for mt in meta_texts:
                        if is_promo_post(mt):
                            texts.add(mt[:500])

                # Filter promo posts only
                for text in texts:
                    if is_promo_post(text):
                        posts.append({
                            "id": f"{username}_{hash(text) % 100000}",
                            "source": f"@{username}",
                            "source_url": url,
                            "text": text,
                            "category": classify(text),
                            "discount": extract_discount(text),
                            "code": extract_code(text),
                            "valid_until": extract_valid_until(text),
                            "scraped_at": datetime.now(timezone.utc).isoformat(),
                        })

                if posts:
                    break  # Success, no retry needed

            elif response and response.status in (302, 303, 429):
                print(f"    Redirect/rate-limit ({response.status}), retry...")
                await page.wait_for_timeout(random.randint(5000, 10000))
                continue

        except Exception as e:
            if attempt < retry - 1:
                print(f"    Attempt {attempt+1} failed: {e}, retrying...")
                await page.wait_for_timeout(random.randint(3000, 6000))
            else:
                print(f"  [!] Failed @{username} after {retry} attempts: {e}")

    return posts


async def main_async():
    from playwright.async_api import async_playwright

    os.makedirs(DATA_DIR, exist_ok=True)
    all_promos = []

    print(f"[*] Launching stealth Playwright browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
            ]
        )
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            locale="id-ID",
            timezone_id="Asia/Jakarta",
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
        )

        page = await stealth_page(context)

        print(f"[*] Scraping {len(ACCOUNTS)} Threads accounts...")
        for i, account in enumerate(ACCOUNTS):
            print(f"  [{i+1}/{len(ACCOUNTS)}] @{account}")
            posts = await scrape_account(page, account)
            if posts:
                print(f"    ✓ Found {len(posts)} promo(s)")
                all_promos.extend(posts)
            else:
                print(f"    - No promos found")

            # Human-like delay between accounts
            await page.wait_for_timeout(random.randint(2000, 5000))

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

    # Merge + deduplicate
    seen = set()
    unique = []
    for p in all_promos + existing:
        key = p.get("text", "")[:80]
        if key not in seen:
            seen.add(key)
            unique.append(p)

    # Sort newest first
    unique.sort(key=lambda x: x.get("scraped_at", ""), reverse=True)

    # Remove expired
    today = datetime.now(timezone.utc).date()
    active = []
    for p in unique:
        vu = p.get("valid_until")
        if vu:
            parsed = parse_date_id(vu)
            if parsed and parsed < today:
                continue
        active.append(p)
    unique = active[:500]

    # Write
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

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
