"""
Promo Indo Scraper — Scrape promo posts from Threads accounts.
Runs daily via GitHub Actions. Outputs data/promos.json.
"""
import json
import os
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ─── Target Threads accounts (promo-focused) ───────────────────────────────────
ACCOUNTS = [
    # Bank
    "promosbca", "bankmandiri", "bankbri_id", "baboraofficial",
    "bankbni", "bankmega.id", "permaborofficial",
    # E-wallet & Payment
    "gopaborindonesia", "ovoofficial", "shopeepay_id", "dana.id",
    # Marketplace & Food
    "grabid", "gaborofficial", "tokopedia", "shopee_id",
    # Promo aggregators
    "promojakarta", "infopromo.jkt", "jakartapromo", "promodiskon",
    "voucherdeal.id", "promobank.id", "diskonaja",
]

CATEGORIES = {
    "makanan": ["makan", "food", "resto", "kuliner", "pizza", "burger", "kfc", "mcd", "starbucks", "grabfood", "gofood", "coffee", "kopi", "bakery", "sushi"],
    "belanja": ["diskon", "sale", "fashion", "belanja", "shopee", "tokopedia", "lazada", "blibli", "zalora", "uniqlo", "h&m"],
    "hiburan": ["bioskop", "cinema", "cgv", "xxi", "tiket", "konser", "event", "spotify", "netflix", "vidio", "disney"],
    "hotel": ["hotel", "traveloka", "tiket.com", "agoda", "booking", "villa", "resort", "penginapan", "wisata", "travel"],
    "transport": ["grab", "gojek", "gocar", "goride", "grabcar", "grabride", "transport", "kereta", "pesawat", "flight"],
    "kesehatan": ["apotek", "halodoc", "alodokter", "farmasi", "vitamin", "kesehatan", "klinik"],
    "keuangan": ["cashback", "cicilan", "0%", "bunga", "kredit", "debit", "kartu", "paylater", "pinjaman"],
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "data")


def classify_category(text: str) -> str:
    """Classify promo text into category."""
    lower = text.lower()
    scores = {}
    for cat, keywords in CATEGORIES.items():
        scores[cat] = sum(1 for kw in keywords if kw in lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "lainnya"


def extract_promo_info(text: str) -> dict:
    """Extract promo details from text."""
    info = {"discount": None, "code": None, "valid_until": None}

    # Discount percentage
    disc_match = re.search(r'(\d+)\s*%', text)
    if disc_match:
        info["discount"] = f"{disc_match.group(1)}%"

    # Voucher/promo code
    code_match = re.search(r'(?:kode|code|voucher|kupon)[:\s]*([A-Z0-9]{4,15})', text, re.IGNORECASE)
    if code_match:
        info["code"] = code_match.group(1).upper()

    # Valid until date
    date_match = re.search(r'(?:s/?d|sampai|hingga|until|berlaku)[:\s]*(\d{1,2}[\s/-]\w+[\s/-]\d{2,4})', text, re.IGNORECASE)
    if date_match:
        info["valid_until"] = date_match.group(1)

    return info


def fetch_threads_posts(username: str) -> list:
    """Fetch recent posts from a Threads user profile."""
    posts = []
    url = f"https://www.threads.net/@{username}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Extract JSON data from page source
        # Threads embeds post data in script tags
        json_matches = re.findall(r'"text":\s*"([^"]{20,500})"', html)

        for text_raw in json_matches[:10]:  # max 10 posts per account
            # Unescape unicode
            try:
                text = text_raw.encode().decode('unicode_escape')
            except Exception:
                text = text_raw

            # Filter: only promo-related content
            promo_keywords = ["promo", "diskon", "cashback", "voucher", "gratis", "free",
                            "hemat", "sale", "potongan", "kupon", "kode", "disc", "%off",
                            "buy 1", "beli 1", "flash sale", "special"]
            if not any(kw in text.lower() for kw in promo_keywords):
                continue

            info = extract_promo_info(text)
            category = classify_category(text)

            posts.append({
                "id": f"{username}_{hash(text) % 100000}",
                "source": f"@{username}",
                "source_url": f"https://www.threads.net/@{username}",
                "text": text[:500],
                "category": category,
                "discount": info["discount"],
                "code": info["code"],
                "valid_until": info["valid_until"],
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"  [!] Failed {username}: {e}")
    except Exception as e:
        print(f"  [!] Error {username}: {e}")

    return posts


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    all_promos = []

    # Load existing data to merge
    data_file = os.path.join(DATA_DIR, "promos.json")
    existing = []
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    print(f"[*] Scraping {len(ACCOUNTS)} Threads accounts...")
    for i, account in enumerate(ACCOUNTS):
        print(f"  [{i+1}/{len(ACCOUNTS)}] @{account}")
        posts = fetch_threads_posts(account)
        if posts:
            print(f"    Found {len(posts)} promo(s)")
            all_promos.extend(posts)
        time.sleep(2)  # rate limit

    # Deduplicate by text hash
    seen = set()
    unique = []
    for p in all_promos + existing:
        key = hash(p.get("text", ""))
        if key not in seen:
            seen.add(key)
            unique.append(p)

    # Sort by scraped_at (newest first)
    unique.sort(key=lambda x: x.get("scraped_at", ""), reverse=True)

    # Keep max 500 promos
    unique = unique[:500]

    # Write
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

    print(f"\n[*] Done! {len(unique)} promos saved to {data_file}")


if __name__ == "__main__":
    main()
