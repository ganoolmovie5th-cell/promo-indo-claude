# PromoIndo

Kumpulan promo, kode voucher, dan cashback Indonesia. Update otomatis setiap hari dari Threads.

## Stack

- Frontend: Static HTML/CSS/JS (deploy Vercel)
- Scraper: Python (GitHub Actions, daily cron)
- Data: JSON files in `public/data/`

## How it works

1. GitHub Actions runs `scripts/scraper.py` daily at 08:00 WIB
2. Scraper fetches promo posts from 21 Threads accounts
3. Data saved to `public/data/promos.json`
4. Vercel auto-deploys on push

## Local dev

```bash
python scripts/scraper.py  # Run scraper manually
```

Serve frontend:
```bash
cd public && python -m http.server 3000
```

## Deploy

Connected to Vercel. Auto-deploy on push to main.
