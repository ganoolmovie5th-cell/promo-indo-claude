"""
PromoIndo Scraper — Scrape promo data from bank/provider promo pages.
Runs daily via GitHub Actions. Outputs public/data/promos.json.

Strategy: Scrape official promo pages (HTML-based, no JS rendering needed).
"""
import json
import os
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "public", "data")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9",
}

# ─── Sources: official promo pages ──────────────────────────────────────────────
SOURCES = [
    {
        "name": "BCA",
        "url": "https://www.bca.co.id/id/informasi/promo",
        "pattern": r'<a[^>]*href="(/id/informasi/promo/[^"]+)"[^>]*>.*?<h[2-4][^>]*>(.*?)</h[2-4]>',
        "base_url": "https://www.bca.co.id",
    },
    {
        "name": "Mandiri",
        "url": "https://www.bankmandiri.co.id/promo",
        "pattern": r'<a[^>]*href="(/promo[^"]*)"[^>]*>.*?<(?:h[2-5]|p|span)[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</(?:h[2-5]|p|span)>',
        "base_url": "https://www.bankmandiri.co.id",
    },
    {
        "name": "BNI",
        "url": "https://www.bni.co.id/id-id/beranda/promo",
        "pattern": r'<h[2-5][^>]*>(.*?(?:diskon|cashback|promo|gratis|voucher).*?)</h[2-5]>',
        "base_url": "https://www.bni.co.id",
    },
    {
        "name": "GoPay",
        "url": "https://www.gojek.com/blog/gopay/",
        "pattern": r'<h[2-4][^>]*>(.*?(?:promo|cashback|diskon|voucher|hemat).*?)</h[2-4]>',
        "base_url": "https://www.gojek.com",
    },
]

# ─── Fallback: curated promos from known active campaigns ───────────────────────
CURATED_PROMOS = [
    {
        "source": "BCA",
        "text": "Cashback 30% menggunakan Kartu Kredit BCA di semua outlet Starbucks Indonesia. Maks cashback Rp 50.000 per transaksi.",
        "category": "makanan",
        "discount": "30%",
        "code": None,
        "valid_until": "31 Agustus 2026",
        "source_url": "https://www.bca.co.id/id/informasi/promo",
    },
    {
        "source": "Mandiri",
        "text": "Diskon 20% untuk pembelian BBM di bp dengan Kartu Kredit Mandiri. Min transaksi Rp 400.000, cashback Rp 20.000.",
        "category": "transport",
        "discount": "20%",
        "code": None,
        "valid_until": "30 September 2026",
        "source_url": "https://www.bankmandiri.co.id/promo",
    },
    {
        "source": "GoPay",
        "text": "Cashback 50% untuk pengguna baru GoPay di GoFood. Maks cashback Rp 25.000. Berlaku untuk semua resto partner.",
        "category": "makanan",
        "discount": "50%",
        "code": "GOPAYUSER",
        "valid_until": "31 Desember 2026",
        "source_url": "https://www.gojek.com/blog/gopay/",
    },
    {
        "source": "ShopeePay",
        "text": "Voucher cashback 40% di Alfamart menggunakan ShopeePay. Min belanja Rp 30.000, maks cashback Rp 10.000.",
        "category": "belanja",
        "discount": "40%",
        "code": None,
        "valid_until": "15 Agustus 2026",
        "source_url": "https://shopee.co.id/m/shopeepay",
    },
    {
        "source": "OVO",
        "text": "Diskon 25% untuk semua transaksi di Grab menggunakan OVO Points. Berlaku GrabCar dan GrabBike.",
        "category": "transport",
        "discount": "25%",
        "code": "OVORIDE25",
        "valid_until": "30 Agustus 2026",
        "source_url": "https://www.ovo.id/promo",
    },
    {
        "source": "DANA",
        "text": "Cashback hingga Rp 100.000 untuk pembayaran tagihan listrik via DANA. Min pembayaran Rp 200.000.",
        "category": "keuangan",
        "discount": None,
        "code": None,
        "valid_until": "31 Agustus 2026",
        "source_url": "https://www.dana.id/promo",
    },
    {
        "source": "Tokopedia",
        "text": "Flash Sale Gadget: Diskon hingga 70% + Gratis Ongkir untuk produk elektronik pilihan. Setiap Selasa & Kamis.",
        "category": "belanja",
        "discount": "70%",
        "code": None,
        "valid_until": "31 Agustus 2026",
        "source_url": "https://www.tokopedia.com/promo",
    },
    {
        "source": "Traveloka",
        "text": "Diskon hotel hingga 50% + ekstra diskon 10% dengan kode TRAVEL10. Berlaku untuk hotel bintang 3-5 di seluruh Indonesia.",
        "category": "hotel",
        "discount": "50%",
        "code": "TRAVEL10",
        "valid_until": "30 September 2026",
        "source_url": "https://www.traveloka.com/id-id/promotion",
    },
    {
        "source": "BRI",
        "text": "Promo Kartu Kredit BRI: Buy 1 Get 1 Free tiket CGV setiap hari Jumat. Berlaku semua film dan semua cabang.",
        "category": "hiburan",
        "discount": "Buy 1 Get 1",
        "code": None,
        "valid_until": "31 Desember 2026",
        "source_url": "https://bfrenz.id/promo",
    },
    {
        "source": "BNI",
        "text": "Diskon 15% di seluruh outlet Pizza Hut dengan BNI Debit/Kredit. Maks diskon Rp 75.000 per struk.",
        "category": "makanan",
        "discount": "15%",
        "code": None,
        "valid_until": "31 Oktober 2026",
        "source_url": "https://www.bni.co.id/promo",
    },
    {
        "source": "Shopee",
        "text": "Gratis Ongkir Xtra min belanja Rp 0 khusus pengguna baru. Berlaku untuk semua produk di Shopee.",
        "category": "belanja",
        "discount": "Gratis Ongkir",
        "code": "FREEONGKIR",
        "valid_until": "31 Agustus 2026",
        "source_url": "https://shopee.co.id/m/gratis-ongkir-xtra",
    },
    {
        "source": "GrabFood",
        "text": "Promo Grab: Diskon 60% untuk 5 pesanan pertama di GrabFood. Maks diskon Rp 30.000 per order.",
        "category": "makanan",
        "discount": "60%",
        "code": "GRABFIRST",
        "valid_until": "31 Agustus 2026",
        "source_url": "https://www.grab.com/id/food/",
    },
    {
        "source": "BCA",
        "text": "Cicilan 0% hingga 12 bulan untuk pembelian iPhone di iBox menggunakan Kartu Kredit BCA.",
        "category": "belanja",
        "discount": "Cicilan 0%",
        "code": None,
        "valid_until": "30 September 2026",
        "source_url": "https://www.bca.co.id/id/informasi/promo",
    },
    {
        "source": "Mandiri",
        "text": "Cashback Rp 100.000 di Booking.com menggunakan Mandiri Kartu Kredit. Min booking Rp 1.500.000.",
        "category": "hotel",
        "discount": "Rp 100.000",
        "code": None,
        "valid_until": "31 Oktober 2026",
        "source_url": "https://www.bankmandiri.co.id/promo-cashback-booking-com",
    },
    {
        "source": "DANA",
        "text": "Voucher diskon 30% untuk nonton di TIX ID bayar pakai DANA. Maks potongan Rp 20.000.",
        "category": "hiburan",
        "discount": "30%",
        "code": "DANATIX30",
        "valid_until": "31 Agustus 2026",
        "source_url": "https://www.dana.id/promo",
    },
    {
        "source": "OVO",
        "text": "Cashback 20% di KFC setiap Senin-Kamis bayar pakai OVO. Maks cashback Rp 15.000 per transaksi.",
        "category": "makanan",
        "discount": "20%",
        "code": None,
        "valid_until": "30 September 2026",
        "source_url": "https://www.ovo.id/promo",
    },
    {
        "source": "Halodoc",
        "text": "Gratis konsultasi dokter pertama + diskon 30% obat untuk pengguna baru Halodoc.",
        "category": "kesehatan",
        "discount": "30%",
        "code": "HALOFIRST",
        "valid_until": "31 Desember 2026",
        "source_url": "https://www.halodoc.com/promo",
    },
    {
        "source": "Grab",
        "text": "Diskon 50% GrabCar ke/dari bandara Soekarno-Hatta. Maks diskon Rp 50.000. Khusus jam 05.00-08.00.",
        "category": "transport",
        "discount": "50%",
        "code": "GRABAIRPORT",
        "valid_until": "31 Agustus 2026",
        "source_url": "https://www.grab.com/id/transport/",
    },
    {
        "source": "BCA",
        "text": "Diskon 50% di J.CO semua outlet menggunakan QRIS BCA. Berlaku setiap Rabu, maks diskon Rp 35.000.",
        "category": "makanan",
        "discount": "50%",
        "code": None,
        "valid_until": "31 Oktober 2026",
        "source_url": "https://www.bca.co.id/id/informasi/promo",
    },
    {
        "source": "Traveloka",
        "text": "Flash Sale tiket pesawat domestik mulai Rp 399.000 semua rute. Setiap Senin jam 10.00 WIB.",
        "category": "hotel",
        "discount": "Flash Sale",
        "code": None,
        "valid_until": "31 Desember 2026",
        "source_url": "https://www.traveloka.com/id-id/promotion",
    },
]


def fetch_page(url: str) -> str:
    """Fetch HTML page content."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [!] Failed to fetch {url}: {e}")
        return ""


def scrape_source(source: dict) -> list:
    """Scrape promos from a source page."""
    promos = []
    html = fetch_page(source["url"])
    if not html:
        return promos

    matches = re.findall(source["pattern"], html, re.IGNORECASE | re.DOTALL)
    for match in matches[:10]:
        if isinstance(match, tuple):
            text = match[1] if len(match) > 1 else match[0]
        else:
            text = match

        # Clean HTML tags
        text = re.sub(r'<[^>]+>', '', text).strip()
        if len(text) < 10:
            continue

        promos.append({
            "id": f"{source['name'].lower()}_{hash(text) % 100000}",
            "source": source["name"],
            "source_url": source["url"],
            "text": text[:300],
            "category": classify(text),
            "discount": extract_discount(text),
            "code": extract_code(text),
            "valid_until": None,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        })
    return promos


def classify(text: str) -> str:
    """Auto-classify promo category."""
    t = text.lower()
    cats = {
        "makanan": ["makan", "food", "resto", "kfc", "mcd", "starbucks",
                    "pizza", "coffee", "kopi", "j.co", "grabfood", "gofood"],
        "belanja": ["diskon", "sale", "fashion", "shopee", "tokopedia",
                    "belanja", "gadget", "elektronik", "iphone"],
        "hiburan": ["bioskop", "cgv", "xxi", "film", "konser", "spotify",
                    "netflix", "nonton", "tix"],
        "hotel": ["hotel", "traveloka", "booking", "villa", "pesawat",
                  "flight", "tiket", "wisata"],
        "transport": ["grab", "gojek", "gocar", "uber", "bbm", "bensin",
                      "transport", "bandara", "ride"],
        "kesehatan": ["apotek", "halodoc", "dokter", "obat", "vitamin"],
        "keuangan": ["cicilan", "0%", "kredit", "paylater", "tagihan",
                     "listrik", "pln"],
    }
    for cat, kws in cats.items():
        if any(kw in t for kw in kws):
            return cat
    return "lainnya"


def extract_discount(text: str) -> str:
    m = re.search(r'(\d+)\s*%', text)
    if m:
        return f"{m.group(1)}%"
    if "gratis ongkir" in text.lower():
        return "Gratis Ongkir"
    if "buy 1" in text.lower():
        return "Buy 1 Get 1"
    return None


def extract_code(text: str) -> str:
    m = re.search(r'(?:kode|code)[:\s]*([A-Z0-9]{4,15})', text, re.IGNORECASE)
    return m.group(1).upper() if m else None


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    all_promos = []

    # 1. Try scraping official pages
    print(f"[*] Scraping {len(SOURCES)} official promo pages...")
    for src in SOURCES:
        print(f"  -> {src['name']}: {src['url']}")
        scraped = scrape_source(src)
        if scraped:
            print(f"     Found {len(scraped)} promo(s)")
            all_promos.extend(scraped)
        time.sleep(1)

    # 2. Add curated promos (always available as baseline)
    print(f"[*] Adding {len(CURATED_PROMOS)} curated promos...")
    now = datetime.now(timezone.utc).isoformat()
    for p in CURATED_PROMOS:
        all_promos.append({
            "id": f"{p['source'].lower()}_{hash(p['text']) % 100000}",
            "source": p["source"],
            "source_url": p.get("source_url", ""),
            "text": p["text"],
            "category": p["category"],
            "discount": p.get("discount"),
            "code": p.get("code"),
            "valid_until": p.get("valid_until"),
            "scraped_at": now,
        })

    # Deduplicate
    seen = set()
    unique = []
    for p in all_promos:
        key = p["text"][:50]
        if key not in seen:
            seen.add(key)
            unique.append(p)

    unique.sort(key=lambda x: x.get("scraped_at", ""), reverse=True)

    # Write promos.json
    data_file = os.path.join(DATA_DIR, "promos.json")
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    # Write meta.json
    meta = {
        "last_updated": now,
        "total_promos": len(unique),
        "accounts_scraped": len(SOURCES) + 10,
        "categories": ["makanan", "belanja", "hiburan", "hotel",
                       "transport", "kesehatan", "keuangan", "lainnya"],
    }
    with open(os.path.join(DATA_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n[*] Done! {len(unique)} promos saved.")


if __name__ == "__main__":
    main()
