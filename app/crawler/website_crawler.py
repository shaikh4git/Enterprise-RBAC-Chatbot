# app/crawler/website_crawler.py
# This crawler uses requests and BeautifulSoup. It discovers internal links and sitemap URLs, 
# checks robots.txt, applies a delay between requests, and saves each page as a Markdown document.
# Note: This is an HTML crawler. It doesn't automatically download and extract PDF attachments such as the academic calendar. 
# We can add PDF extraction as a separate enhancement using your existing Docling installation.


import argparse
import hashlib
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import (
    urljoin,
    urlparse,
    urldefrag,
    urlunparse,
)
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://madinps.edu.in/"
DOMAIN = "madinps.edu.in"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "documents"
    / "Websites"
    / "madinps"
)

USER_AGENT = "MadinPSKnowledgeBot/1.0 (public website indexing)"

MAX_PAGES_DEFAULT = 500
REQUEST_DELAY_SECONDS = 1.5
REQUEST_TIMEOUT = 20

# Do not index pages that involve student-specific or private workflows.
EXCLUDED_PATHS = [
    "/result-portal",
    "/results",
    "/login",
    "/wp-admin",
    "/wp-login",
    "/student-portal",
]

# Avoid downloading assets as if they were HTML pages.
SKIPPED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".svg", ".ico", ".css", ".js",
    ".zip", ".mp4", ".mp3", ".woff", ".woff2",
    ".ttf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".pdf",
}


def normalize_url(url):
    """Normalize a URL and remove fragments and tracking parameters."""

    url, _ = urldefrag(url)
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return None

    if parsed.netloc.lower().removeprefix("www.") != DOMAIN:
        return None

    path = parsed.path or "/"

    # Ignore query parameters for canonical page discovery.
    normalized = urlunparse(
        (
            "https",
            DOMAIN,
            path,
            "",
            "",
            "",
        )
    )

    return normalized


def is_excluded(url):
    path = urlparse(url).path.lower()

    if any(path.startswith(item) for item in EXCLUDED_PATHS):
        return True

    suffix = Path(path).suffix.lower()

    return suffix in SKIPPED_EXTENSIONS


def load_robots(session):
    """Load and parse the website's robots.txt."""

    robots_url = urljoin(BASE_URL, "/robots.txt")

    response = session.get(
        robots_url,
        timeout=REQUEST_TIMEOUT,
    )

    # A 404 means no robots.txt file was published.
    if response.status_code == 404:
        print("robots.txt not found; no published robots rules.")
        parser = RobotFileParser()
        parser.parse([])
        return parser

    response.raise_for_status()

    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(response.text.splitlines())

    return parser


def get_sitemap_urls(session, robots):
    """Read sitemap locations declared in robots.txt."""

    sitemap_urls = []

    for line in robots.site_maps() or []:
        sitemap_urls.append(line)

    # Common fallback if robots.txt has no Sitemap entry.
    if not sitemap_urls:
        sitemap_urls.append(
            urljoin(BASE_URL, "/sitemap.xml")
        )

    discovered = set()
    queue = deque(sitemap_urls)

    while queue:
        sitemap_url = queue.popleft()

        if sitemap_url in discovered:
            continue

        discovered.add(sitemap_url)

        try:
            response = session.get(
                sitemap_url,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            root = ET.fromstring(response.content)

            for element in root.iter():
                if element.tag.endswith("loc") and element.text:
                    location = normalize_url(element.text.strip())

                    if not location or is_excluded(location):
                        continue

                    # Sitemap index entries usually end in .xml.
                    if urlparse(location).path.lower().endswith(".xml"):
                        queue.append(location)
                    else:
                        yield location

        except requests.RequestException as exc:
            print(f"Could not read sitemap {sitemap_url}: {exc}")
        except ET.ParseError:
            print(f"Invalid sitemap XML: {sitemap_url}")


def extract_page(html, page_url):
    """Extract readable page text and internal links."""

    soup = BeautifulSoup(html, "html.parser")

    title = (
        soup.title.get_text(" ", strip=True)
        if soup.title
        else page_url
    )

    # Remove common non-content elements.
    for element in soup.select(
        "script, style, noscript, iframe, svg, "
        "nav, footer, header, form, aside"
    ):
        element.decompose()

    # Prefer article/main content when the site provides it.
    content = (
        soup.select_one("main")
        or soup.select_one("article")
        or soup.select_one(".entry-content")
        or soup.body
        or soup
    )

    text = content.get_text(
        separator="\n",
        strip=True,
    )

    # Collapse excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    links = []

    for anchor in soup.find_all("a", href=True):
        absolute_url = normalize_url(
            urljoin(page_url, anchor["href"])
        )

        if absolute_url and not is_excluded(absolute_url):
            links.append(absolute_url)

    return title, text, links


def page_filename(url):
    """Generate a stable filename from a page URL."""

    path = urlparse(url).path.strip("/") or "home"

    slug = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        path,
    ).strip("_").lower()

    digest = hashlib.sha1(
        url.encode("utf-8")
    ).hexdigest()[:8]

    return f"{slug[:70]}_{digest}.md"


def save_page(url, title, content):
    """Save extracted website content as Markdown."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = page_filename(url)
    output_path = OUTPUT_DIR / filename

    crawled_at = datetime.now(
        timezone.utc
    ).isoformat()

    markdown = f"""<!--
source_url: {url}
domain: {DOMAIN}
crawled_at: {crawled_at}
-->

# {title}

Source: {url}

Crawled at: {crawled_at}

---

{content}
"""

    output_path.write_text(
        markdown,
        encoding="utf-8",
    )

    return output_path


def crawl_website(max_pages):
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,
        }
    )

    robots = load_robots(session)

    sitemap_pages = list(
        get_sitemap_urls(session, robots)
    )

    queue = deque([BASE_URL] + sitemap_pages)
    visited = set()

    print(f"Sitemap pages discovered: {len(sitemap_pages)}")
    print(f"Maximum pages: {max_pages}")

    while queue and len(visited) < max_pages:
        url = normalize_url(queue.popleft())

        if not url or url in visited or is_excluded(url):
            continue

        # Respect the site's robots.txt rules.
        if not robots.can_fetch(USER_AGENT, url):
            print(f"Blocked by robots.txt: {url}")
            continue

        visited.add(url)

        print(f"\nCrawling {len(visited)}: {url}")

        try:
            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type",
                "",
            ).lower()

            if "text/html" not in content_type:
                print("Skipping non-HTML content.")
                continue

            title, content, links = extract_page(
                response.text,
                url,
            )

            if not content.strip():
                print("Skipping empty page.")
                continue

            saved_path = save_page(
                url,
                title,
                content,
            )

            print(f"Saved: {saved_path}")

            for link in links:
                if link not in visited:
                    queue.append(link)

        except requests.RequestException as exc:
            print(f"Request failed for {url}: {exc}")

        time.sleep(REQUEST_DELAY_SECONDS)

    print("\nCrawling completed.")
    print(f"Pages visited: {len(visited)}")
    print(f"Documents saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Crawl public Ma'din Public School website pages."
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=MAX_PAGES_DEFAULT,
    )

    args = parser.parse_args()

    crawl_website(args.max_pages)