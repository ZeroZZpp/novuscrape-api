import re
import base64
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
import html2text

from .models import OutputFormat

_h2t = html2text.HTML2Text()
_h2t.ignore_links = False
_h2t.ignore_images = False
_h2t.body_width = 0

_HTTP_CLIENT: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            follow_redirects=True,
            timeout=60,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
    return _HTTP_CLIENT


async def fetch_html(url: str, timeout: int = 30) -> tuple[str, int]:
    client = await get_http_client()
    resp = await client.get(url, timeout=timeout)
    return resp.text, resp.status_code


async def fetch_with_js(
    url: str, timeout: int = 30, wait_for: str | None = None
) -> tuple[str, int]:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        resp = await page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
        if wait_for:
            await page.wait_for_selector(wait_for, timeout=timeout * 1000)
        html = await page.content()
        status = resp.status if resp else 200
        await browser.close()
        return html, status


async def screenshot_page(
    url: str,
    full_page: bool = False,
    width: int = 1280,
    height: int = 720,
    timeout: int = 30,
) -> tuple[bytes, int, int]:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": width, "height": height})
        await page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
        img_bytes = await page.screenshot(full_page=full_page, type="png")
        actual_w = width
        actual_h = height
        if full_page:
            size = await page.evaluate(
                "() => ({w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight})"
            )
            actual_w = size["w"]
            actual_h = size["h"]
        await browser.close()
        return img_bytes, actual_w, actual_h


def parse_html(html: str, output_format: OutputFormat, base_url: str = "") -> tuple[str, str | None]:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.string.strip() if soup.title and soup.title.string else None

    # Remove script and style tags
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    if output_format == OutputFormat.html:
        content = str(soup)
    elif output_format == OutputFormat.text:
        content = soup.get_text(separator="\n", strip=True)
    else:  # markdown
        content = _h2t.handle(str(soup))

    return content, title


def extract_links(html: str, base_url: str, pattern: str | None = None) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if href in seen:
            continue
        seen.add(href)
        text = a.get_text(strip=True) or None
        if pattern and not re.search(pattern, href):
            continue
        links.append({"url": href, "text": text})
    return links


def extract_fields_heuristic(html: str, fields: dict[str, str]) -> dict:
    """Simple heuristic extraction without AI — searches for field values in page text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    result = {}

    for field_name, description in fields.items():
        # Try to find the field by looking for the description or field name near content
        result[field_name] = _find_field_value(soup, text, field_name, description)

    return result


def _find_field_value(soup: BeautifulSoup, text: str, name: str, desc: str) -> str | None:
    """Try multiple strategies to find a field value."""
    # Strategy 1: Look for meta tags
    for meta in soup.find_all("meta"):
        meta_name = (meta.get("name") or meta.get("property") or "").lower()
        if name.lower() in meta_name or any(w in meta_name for w in desc.lower().split()):
            content = meta.get("content")
            if content:
                return content.strip()

    # Strategy 2: Look for elements with matching aria-label, id, class, or itemprop
    for attr in ["aria-label", "id", "class", "itemprop", "data-testid"]:
        for el in soup.find_all(attrs={attr: True}):
            attr_val = el.get(attr)
            if isinstance(attr_val, list):
                attr_val = " ".join(attr_val)
            if attr_val and (name.lower() in attr_val.lower() or any(w in attr_val.lower() for w in desc.lower().split() if len(w) > 3)):
                val = el.get_text(strip=True)
                if val and len(val) < 500:
                    return val

    # Strategy 3: Look for label/value pairs in text
    lines = text.split("\n")
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        if name.lower() in line_lower or any(w in line_lower for w in desc.lower().split() if len(w) > 3):
            # Return this line or next non-empty line
            cleaned = line.strip()
            if ":" in cleaned:
                val = cleaned.split(":", 1)[1].strip()
                if val:
                    return val
            if i + 1 < len(lines) and lines[i + 1].strip():
                return lines[i + 1].strip()
            if cleaned and len(cleaned) < 500:
                return cleaned

    return None
