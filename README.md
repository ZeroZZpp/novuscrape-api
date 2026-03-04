# NovuScrape API

Fast, reliable web scraping and data extraction API by Novusante.

## Endpoints

- `POST /scrape` — Scrape a URL, get content as HTML/text/markdown
- `POST /extract` — Extract structured data fields from a page
- `POST /links` — Extract all links from a page
- `POST /screenshot` — Take a screenshot of a page

## Quick Start

```bash
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload
```

## Docker

```bash
docker build -t novuscrape .
docker run -p 8000:8000 -e API_KEYS=your-key novuscrape
```

## Auth

Pass your API key via `X-Api-Key` header.
