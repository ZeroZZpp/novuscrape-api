from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from enum import Enum


class OutputFormat(str, Enum):
    html = "html"
    text = "text"
    markdown = "markdown"


class ScrapeRequest(BaseModel):
    url: str = Field(..., description="The URL to scrape")
    output_format: OutputFormat = Field(
        default=OutputFormat.markdown,
        description="Output format: html, text, or markdown",
    )
    render_js: bool = Field(
        default=False,
        description="Whether to render JavaScript (slower but handles SPAs)",
    )
    wait_for: Optional[str] = Field(
        default=None,
        description="CSS selector to wait for before scraping (only with render_js=true)",
    )
    timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Timeout in seconds",
    )


class ExtractRequest(BaseModel):
    url: str = Field(..., description="The URL to extract data from")
    fields: dict[str, str] = Field(
        ...,
        description="Fields to extract. Keys are field names, values are descriptions of what to extract. Example: {'price': 'the product price', 'title': 'the product name'}",
    )
    render_js: bool = Field(default=False)
    timeout: int = Field(default=30, ge=5, le=120)


class LinksRequest(BaseModel):
    url: str = Field(..., description="The URL to extract links from")
    render_js: bool = Field(default=False)
    filter_pattern: Optional[str] = Field(
        default=None,
        description="Regex pattern to filter links",
    )
    timeout: int = Field(default=30, ge=5, le=120)


class ScreenshotRequest(BaseModel):
    url: str = Field(..., description="The URL to screenshot")
    full_page: bool = Field(default=False, description="Capture full scrollable page")
    width: int = Field(default=1280, ge=320, le=3840)
    height: int = Field(default=720, ge=240, le=2160)
    timeout: int = Field(default=30, ge=5, le=120)


class ScrapeResponse(BaseModel):
    url: str
    content: str
    format: OutputFormat
    title: Optional[str] = None
    status_code: int
    content_length: int


class ExtractResponse(BaseModel):
    url: str
    data: dict
    raw_text_length: int


class LinksResponse(BaseModel):
    url: str
    links: list[dict[str, Optional[str]]]
    total: int


class ScreenshotResponse(BaseModel):
    url: str
    image_base64: str
    width: int
    height: int
