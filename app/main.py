import base64
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from .auth import verify_api_key
from .models import (
    ScrapeRequest,
    ScrapeResponse,
    ExtractRequest,
    ExtractResponse,
    LinksRequest,
    LinksResponse,
    ScreenshotRequest,
    ScreenshotResponse,
)
from .scraper import (
    fetch_html,
    fetch_with_js,
    parse_html,
    extract_links,
    extract_fields_heuristic,
    screenshot_page,
)

load_dotenv()

RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="NovuScrape API",
    description="Fast, reliable web scraping and data extraction API by Novusante.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "NovuScrape API",
        "version": "1.0.0",
        "docs": "/docs",
        "by": "Novusante",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/scrape", response_model=ScrapeResponse)
@limiter.limit(RATE_LIMIT)
async def scrape(request: Request, body: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    if body.render_js:
        html, status = await fetch_with_js(body.url, body.timeout, body.wait_for)
    else:
        html, status = await fetch_html(body.url, body.timeout)

    content, title = parse_html(html, body.output_format, body.url)

    return ScrapeResponse(
        url=body.url,
        content=content,
        format=body.output_format,
        title=title,
        status_code=status,
        content_length=len(content),
    )


@app.post("/extract", response_model=ExtractResponse)
@limiter.limit(RATE_LIMIT)
async def extract(request: Request, body: ExtractRequest, api_key: str = Depends(verify_api_key)):
    if body.render_js:
        html, _ = await fetch_with_js(body.url, body.timeout)
    else:
        html, _ = await fetch_html(body.url, body.timeout)

    data = extract_fields_heuristic(html, body.fields)

    return ExtractResponse(
        url=body.url,
        data=data,
        raw_text_length=len(html),
    )


@app.post("/links", response_model=LinksResponse)
@limiter.limit(RATE_LIMIT)
async def links(request: Request, body: LinksRequest, api_key: str = Depends(verify_api_key)):
    if body.render_js:
        html, _ = await fetch_with_js(body.url, body.timeout)
    else:
        html, _ = await fetch_html(body.url, body.timeout)

    found_links = extract_links(html, body.url, body.filter_pattern)

    return LinksResponse(
        url=body.url,
        links=found_links,
        total=len(found_links),
    )


@app.post("/screenshot", response_model=ScreenshotResponse)
@limiter.limit(RATE_LIMIT)
async def screenshot(request: Request, body: ScreenshotRequest, api_key: str = Depends(verify_api_key)):
    img_bytes, w, h = await screenshot_page(
        body.url, body.full_page, body.width, body.height, body.timeout
    )

    return ScreenshotResponse(
        url=body.url,
        image_base64=base64.b64encode(img_bytes).decode(),
        width=w,
        height=h,
    )
