#!/usr/bin/env python3
"""Validate the static site: raw HTML, base-path links, and data consistency."""

import re
import sys
import threading
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from build_site import generated_map
from common import DATA_PATH, SITE_DIR, load_data
from preview import make_server

BASE = "/bas1s-requests/"
SOURCE_URL = "https://bas1s.ventures/secondaries/openevidence"
EMAIL = "wonder@bas1s.ventures"
REVIEWED = "19 November 2026"
REVIEWED_ISO = "2026-11-19"
ALLOWED_HOSTS = {"bas1s.ventures", "github.com", "wonderwonder26.github.io"}
BANNED = (
    "invest@",
    "lorem ipsum",
    "todo",
    "tbd",
    "coming soon",
    "placeholder request",
    "colocation",
    "private inbox",
    "guaranteed return",
    "guaranteed execution",
    "guaranteed ranking",
    "published exclusively",
    "example.com",
)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.text_parts = []
        self.h1 = []
        self.h1_buf = None
        self.lead = []
        self.lead_buf = None
        self.lead_depth = 0
        self.title = []
        self.title_buf = None
        self.hrefs = []
        self.canonical = []
        self.metas = []
        self.ids = []
        self.nav_labels = []
        self.images = []
        self.forms = 0
        self.scripts = 0
        self.iframes = 0
        self.hidden = 0
        self.has_main = False
        self.main_tabindex = None
        self.lang = None
        self.tags = []

    def handle_starttag(self, tag, attrs):
        attr = {key: value or "" for key, value in attrs}
        self.tags.append(tag)
        if tag in {"script", "style"}:
            self.skip_depth += 1
        if tag == "script":
            self.scripts += 1
        elif tag == "form":
            self.forms += 1
        elif tag == "iframe":
            self.iframes += 1
        if "hidden" in attr:
            self.hidden += 1
        if tag == "html":
            self.lang = attr.get("lang")
        elif tag == "h1":
            self.h1_buf = []
        elif tag == "title":
            self.title_buf = []
        elif tag == "p" and "lead" in attr.get("class", "").split():
            self.lead_buf = []
            self.lead_depth = 1
        elif self.lead_buf is not None:
            self.lead_depth += 1
        elif tag == "main":
            self.has_main = True
            self.main_tabindex = attr.get("tabindex")
        elif tag == "nav":
            self.nav_labels.append(attr.get("aria-label"))
        elif tag == "img":
            self.images.append(attr)
        if "id" in attr:
            self.ids.append(attr["id"])
        if tag in {"a", "link"} and "href" in attr:
            self.hrefs.append((tag, attr.get("rel", ""), attr["href"]))
        if tag == "link" and "canonical" in attr.get("rel", "").split():
            self.canonical.append(attr.get("href", ""))
        if tag == "meta":
            self.metas.append(attr)

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "h1" and self.h1_buf is not None:
            self.h1.append(clean("".join(self.h1_buf)))
            self.h1_buf = None
        elif tag == "title" and self.title_buf is not None:
            self.title.append(clean("".join(self.title_buf)))
            self.title_buf = None
        elif self.lead_buf is not None:
            self.lead_depth -= 1
            if self.lead_depth <= 0:
                self.lead.append(clean("".join(self.lead_buf)))
                self.lead_buf = None

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.h1_buf is not None:
            self.h1_buf.append(data)
        if self.title_buf is not None:
            self.title_buf.append(data)
        if self.lead_buf is not None:
            self.lead_buf.append(data)
        self.text_parts.append(data)


def clean(value):
    return re.sub(r"\s+", " ", value).strip()


def visible_text(page: Page):
    return clean(" ".join(page.text_parts))


def meta_content(page: Page, name):
    for attr in page.metas:
        if attr.get("name") == name:
            return attr.get("content", "")
    return None


def contrast(foreground, background):
    def channel(hex_color):
        value = int(hex_color, 16) / 255
        if value <= 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    def luminance(hex_color):
        red, green, blue = hex_color[1:3], hex_color[3:5], hex_color[5:7]
        r, g, b = channel(red), channel(green), channel(blue)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    lighter = max(luminance(foreground), luminance(background))
    darker = min(luminance(foreground), luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


class Check:
    def __init__(self):
        self.failures = []
        self.passed = 0

    def ok(self, condition, message):
        if condition:
            self.passed += 1
        else:
            self.failures.append(message)

    def require(self, condition, message):
        self.ok(condition, message)


def parse_file(path: Path):
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    return page


def check_colors(check: Check):
    css = (SITE_DIR / "assets" / "site.css").read_text(encoding="utf-8")
    variables = dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6})", css))
    pairs = (
        ("ink", "paper", 4.5),
        ("soft", "paper", 4.5),
        ("muted", "paper", 4.5),
        ("muted", "raised", 4.5),
        ("on-accent", "accent", 4.5),
        ("accent", "paper", 4.5),
        ("on-accent", "accent-hover", 4.5),
    )
    for foreground, background, minimum in pairs:
        ratio = contrast(variables[foreground], variables[background])
        check.require(ratio >= minimum, f"contrast {foreground} on {background} is {ratio:.2f}, need {minimum}")
    display_none = css.count("display: none")
    check.require(display_none == 1, "display:none should only hide chrome in the print stylesheet")
    check.require("@media print" in css, "print stylesheet missing")
    check.require(not re.search(r"font-size:\s*0(;|\s)", css) and "text-indent: -999" not in css, "CSS hides text")
    check.require("@import" not in css and "url(http" not in css, "CSS loads an external asset")


def check_data(check: Check, data):
    site = data["site"]
    check.require(site["basePath"] == BASE, "base path must stay /bas1s-requests/")
    check.require(site["pagesHost"] == "https://wonderwonder26.github.io", "unexpected pages host")
    check.require(site["indexUrl"] == "https://wonderwonder26.github.io/bas1s-requests/", "index URL mismatch")
    check.require(site["language"] == "en", "site language should be English")
    check.require(data["publisher"]["url"] == "https://bas1s.ventures/", "publisher URL mismatch")
    check.require(len(data["requests"]) == 1, "this version publishes exactly one request")
    request = data["requests"][0]
    check.require(request["slug"] == "openevidence", "unexpected request slug")
    check.require(request["canonical"] == SOURCE_URL, "request canonical must be the original mandate")
    check.require(request["source"]["url"] == SOURCE_URL, "source URL mismatch")
    check.require(request["source"]["lastReviewedAsStated"] == REVIEWED, "review label mismatch")
    check.require(request["source"]["lastReviewedDate"] == REVIEWED_ISO, "review date mismatch")
    check.require(request["contact"]["email"] == EMAIL, "contact email mismatch")
    check.require(request["contact"]["name"] == "Wonder Xu", "contact name mismatch")
    check.require(request["pagePath"] == "/bas1s-requests/requests/openevidence/", "request path mismatch")
    check.require(
        request["pageUrl"] == "https://wonderwonder26.github.io/bas1s-requests/requests/openevidence/",
        "request page URL mismatch",
    )
    fact_values = {fact["label"]: fact["value"] for fact in request["facts"]}
    check.require(fact_values["Target purchase amount"] == request["amountSought"]["label"], "amount label drift")
    check.require(fact_values["Target implied valuation"] == request["targetImpliedValuation"]["label"], "valuation label drift")
    check.require(fact_values["Preferred structure"] == request["preferredStructure"], "structure drift")
    check.require(fact_values["Security sought"] == request["security"], "security drift")
    check.require(request["amountSought"]["approximate"] is True, "amount must stay approximate")
    check.require(request["amountSought"]["amount"] == 10000000, "amount number mismatch")
    check.require(request["targetImpliedValuation"]["approximate"] is True, "valuation must stay approximate")
    check.require(request["targetImpliedValuation"]["amount"] == 12000000000, "valuation number mismatch")
    for flag in ("affiliatedWithIssuer", "completed", "termsAgreed", "companyApprovalRepresented"):
        check.require(request[flag] is False, f"{flag} must stay false")
    joined = json_text(data)
    check.require(
        "Not a statement of OpenEvidence's current market valuation" in joined,
        "valuation meaning missing from data",
    )


def json_text(data):
    import json

    return json.dumps(data)


def check_html_page(check: Check, path: Path, *, h1, description, canonical):
    raw = path.read_text(encoding="utf-8")
    page = parse_file(path)
    text = visible_text(page)
    check.require(page.lang == "en", f"{path} lang")
    check.require(page.scripts == 0 and "<script" not in raw.lower(), f"{path} contains a script")
    check.require(page.forms == 0 and "<form" not in raw.lower(), f"{path} contains a form")
    check.require(page.iframes == 0, f"{path} contains an iframe")
    check.require(page.hidden == 0, f"{path} uses the hidden attribute")
    check.require(page.has_main and page.main_tabindex == "-1", f"{path} main landmark")
    check.require(page.h1 == [h1], f"{path} h1 is {page.h1!r}, expected {h1!r}")
    check.require(page.title == [f"{h1} | BAS1S Ventures"], f"{path} title is {page.title!r}")
    check.require(meta_content(page, "description") == description, f"{path} meta description drift")
    check.require(page.lead == [description], f"{path} visible lead does not match the meta description")
    check.require(description in text, f"{path} description is not visible")
    check.require(meta_content(page, "viewport") == "width=device-width, initial-scale=1", f"{path} viewport")
    check.require(all(label for label in page.nav_labels), f"{path} nav is missing an accessible name")
    check.require("content" in page.ids, f"{path} skip target")
    check.require(len(page.ids) == len(set(page.ids)), f"{path} duplicate ids")
    check.require(not page.images, f"{path} has an image without the expected favicon-only design")
    if canonical is None:
        check.require(page.canonical == [], f"{path} should not declare a canonical URL")
    else:
        check.require(page.canonical == [canonical], f"{path} canonical is {page.canonical!r}")
        og_url = [attr.get("content") for attr in page.metas if attr.get("property") == "og:url"]
        check.require(og_url == [canonical], f"{path} og:url does not match canonical")
    lowered = raw.lower()
    for banned in BANNED:
        check.require(banned not in lowered, f"{path} contains banned text {banned!r}")
    return page, text


def href_target(href):
    if href.startswith("#"):
        return "fragment", href
    if href.startswith("mailto:"):
        return "mailto", href[len("mailto:") :]
    parsed = urlparse(href)
    if parsed.scheme in {"http", "https"}:
        return "external", parsed
    if href.startswith("/"):
        return "internal", href.split("#", 1)[0]
    return "relative", href


def check_links(check: Check, files):
    emails = set()
    internal = []
    for path, page in files:
        for tag, rel, href in page.hrefs:
            kind, value = href_target(href)
            if kind == "fragment":
                fragment = value[1:]
                check.require(fragment in page.ids, f"{path} fragment #{fragment} is missing")
            elif kind == "mailto":
                emails.add(value)
                check.require(value == EMAIL, f"{path} unexpected mailto {value}")
            elif kind == "external":
                check.require(value.scheme == "https", f"{path} non-https link {href}")
                check.require(value.hostname in ALLOWED_HOSTS, f"{path} unexpected host {value.hostname}")
            elif kind == "internal":
                check.require(value.startswith(BASE.rstrip("/")) or value == BASE.rstrip("/"), f"{path} link escapes base path: {href}")
                check.require(value.startswith(BASE), f"{path} internal link should include /bas1s-requests/: {href}")
                check.require(not value.endswith("index.html"), f"{path} links to an index.html duplicate: {href}")
                internal.append((path, value))
            else:
                check.require(False, f"{path} uses a relative link that ignores the base path: {href}")
    check.require(emails == {EMAIL}, f"mailto links were {emails}")
    return internal


def resolve_internal(path):
    relative = path[len(BASE) :].lstrip("/")
    candidate = SITE_DIR / relative
    if path.endswith("/"):
        candidate = candidate / "index.html"
    return candidate


def check_request_page(check: Check, data, text, raw):
    request = data["requests"][0]
    for fact in request["facts"]:
        check.require(fact["label"] in text, f"missing fact label {fact['label']}")
        check.require(fact["value"] in text, f"missing fact value {fact['value']}")
    required = (
        EMAIL,
        "Wonder Xu",
        "Bas1s Ventures",
        SOURCE_URL,
        REVIEWED,
        "not affiliated with or endorsed by OpenEvidence",
        "Company approval is not represented",
        "not a statement that a purchase has been agreed or completed",
        "Direct shareholders",
        "Brokers, intermediaries or introducers",
        "canonical URL is the original mandate",
        "does not add a review date",
        "This site has no form",
        "not a statement of OpenEvidence's current market valuation or latest financing valuation",
    )
    for snippet in required:
        check.require(snippet in text or snippet in raw, f"request page missing {snippet!r}")
    check.require(f'datetime="{REVIEWED_ISO}"' in raw, "review date datetime missing")


def check_generated(check: Check, data):
    fresh = generated_map(data)
    for relative, content in fresh.items():
        committed = SITE_DIR / relative
        check.require(committed.is_file(), f"missing generated file {relative}")
        if committed.is_file():
            check.require(committed.read_text(encoding="utf-8") == content, f"{relative} is stale; run scripts/build_site.py")
    check.require((SITE_DIR / "requests.json").read_bytes() == DATA_PATH.read_bytes(), "site/requests.json drifted from data/requests.json")


def start_server():
    server = make_server("127.0.0.1", 0, quiet=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)

    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302


def fetch(server, path):
    url = f"http://127.0.0.1:{server.server_address[1]}{path}"
    request = urllib.request.Request(url, method="GET")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=5) as response:
            return response.status, dict(response.headers), response.read(), response.geturl()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read(), url


def check_server(check: Check, data):
    server = start_server()
    try:
        cases = {
            "/bas1s-requests/": SITE_DIR / "index.html",
            "/bas1s-requests/requests/openevidence/": SITE_DIR / "requests" / "openevidence" / "index.html",
            "/bas1s-requests/requests.json": SITE_DIR / "requests.json",
            "/bas1s-requests/sitemap.xml": SITE_DIR / "sitemap.xml",
            "/bas1s-requests/robots.txt": SITE_DIR / "robots.txt",
            "/bas1s-requests/llms.txt": SITE_DIR / "llms.txt",
            "/bas1s-requests/assets/site.css": SITE_DIR / "assets" / "site.css",
            "/bas1s-requests/assets/favicon.svg": SITE_DIR / "assets" / "favicon.svg",
        }
        for path, file_path in cases.items():
            status, headers, body, _final = fetch(server, path)
            check.require(status == 200, f"{path} returned {status}")
            check.require(body == file_path.read_bytes(), f"{path} body does not match the static file")
            content_type = headers.get("Content-Type", headers.get("content-type", ""))
            if path.endswith("/"):
                check.require(content_type.startswith("text/html"), f"{path} content type {content_type}")
                check.require(b"<script" not in body.lower(), f"{path} response contains a script")
        status, headers, body, _ = fetch(server, "/bas1s-requests/requests/openevidence")
        location = headers.get("Location", headers.get("location", ""))
        check.require(status == 302 and location.endswith("/bas1s-requests/requests/openevidence/"), f"slash redirect failed: {status} {location}")
        status, headers, body, _ = fetch(server, "/bas1s-requests/not-a-real-request")
        check.require(status == 404, f"missing page status {status}")
        check.require(body == (SITE_DIR / "404.html").read_bytes(), "404 body is not the site 404 page")
        check.require(b"/bas1s-requests/" in body, "404 page lost the base-path home link")
        status, _, body, _ = fetch(server, "/bas1s-requests/../../scripts/check_site.py")
        check.require(status == 404, "path traversal was not rejected")
        check.require(b"def check_server" not in body, "path traversal returned source")
        status, _, body, _ = fetch(server, "/outside")
        check.require(status == 404, "host-root path should not serve the project index")
        home_status, _, home_body, _ = fetch(server, "/bas1s-requests/")
        check.require(b"US$10 million" in home_body and b"US$12 billion" in home_body, "index response lost the mandate amounts")
        detail_status, _, detail_body, _ = fetch(server, "/bas1s-requests/requests/openevidence/")
        check.require(detail_status == 200 and b"wonder@bas1s.ventures" in detail_body, "detail response lost the published contact")
        check.require(home_status == 200, "index fetch failed during content check")
    finally:
        server.shutdown()
        server.server_close()


def check_discovery_files(check: Check, data):
    robots = (SITE_DIR / "robots.txt").read_text(encoding="utf-8")
    sitemap_url = "https://wonderwonder26.github.io/bas1s-requests/sitemap.xml"
    check.require(f"Sitemap: {sitemap_url}" in robots, "robots.txt sitemap line")
    check.require("Disallow: /" not in robots, "robots.txt blocks the site")
    sitemap = (SITE_DIR / "sitemap.xml").read_text(encoding="utf-8")
    locs = re.findall(r"<loc>(.*?)</loc>", sitemap)
    expected = {
        data["site"]["indexUrl"],
        data["requests"][0]["pageUrl"],
        "https://wonderwonder26.github.io/bas1s-requests/requests.json",
        "https://wonderwonder26.github.io/bas1s-requests/llms.txt",
    }
    check.require(set(locs) == expected, f"sitemap locs {locs}")
    check.require("404.html" not in sitemap, "sitemap lists the 404 page")
    llms = (SITE_DIR / "llms.txt").read_text(encoding="utf-8")
    for snippet in (
        SOURCE_URL,
        "Approximately US$10 million",
        "Approximately US$12 billion",
        "does not ask for search ranking, preferential treatment, or automatic distribution",
        "not a statement that a purchase has been agreed or completed",
        EMAIL,
    ):
        check.require(snippet in llms, f"llms.txt missing {snippet!r}")
    check.require("will rank" not in llms.lower(), "llms.txt promises ranking")


def main():
    check = Check()
    data = load_data()
    check_data(check, data)
    check_colors(check)
    check_generated(check, data)
    check.require((SITE_DIR / ".nojekyll").is_file(), ".nojekyll missing")
    check.require((SITE_DIR / "assets" / "favicon.svg").is_file(), "favicon missing")

    index = check_html_page(
        check,
        SITE_DIR / "index.html",
        h1=data["site"]["indexTitle"],
        description=data["site"]["indexDescription"],
        canonical=data["site"]["indexUrl"],
    )
    detail = check_html_page(
        check,
        SITE_DIR / "requests" / "openevidence" / "index.html",
        h1=data["requests"][0]["title"],
        description=data["requests"][0]["description"],
        canonical=SOURCE_URL,
    )
    missing = check_html_page(
        check,
        SITE_DIR / "404.html",
        h1="Page not found",
        description="This address is not a public request on the BAS1S Ventures site.",
        canonical=None,
    )
    check.require(meta_content(missing[0], "robots") == "noindex, follow", "404 should be noindex")
    check.require("not a statement that a purchase has been agreed or completed" in index[1], "index omits the open-request caveat")
    for note in data["site"]["readingNotes"]:
        check.require(note in index[1], "index is missing a reading note")
    check.require("do not ask for search ranking or automatic distribution" in index[1], "index ranking disclaimer missing")
    check_request_page(check, data, detail[1], (SITE_DIR / "requests" / "openevidence" / "index.html").read_text(encoding="utf-8"))
    pages = [
        (SITE_DIR / "index.html", index[0]),
        (SITE_DIR / "requests" / "openevidence" / "index.html", detail[0]),
        (SITE_DIR / "404.html", missing[0]),
    ]
    internal = check_links(check, pages)
    ids_by_url = {
        "/bas1s-requests/": set(index[0].ids),
        "/bas1s-requests/requests/openevidence/": set(detail[0].ids),
    }
    for path, page in pages:
        for _tag, _rel, href in page.hrefs:
            if href.startswith(BASE) and "#" in href:
                url, fragment = href.split("#", 1)
                check.require(fragment in ids_by_url.get(url, ()), f"{path} fragment {href} is missing")
    for path, href in internal:
        target = resolve_internal(href if href.endswith("/") else href)
        # Directory URLs end with /. File URLs such as requests.json do not.
        if href.endswith("/"):
            target = resolve_internal(href)
        else:
            target = SITE_DIR / href[len(BASE) :].lstrip("/")
        check.require(target.is_file(), f"{path} internal link {href} does not resolve to a file")
    check_discovery_files(check, data)
    check_server(check, data)

    print(f"Passed {check.passed} checks")
    if check.failures:
        print(f"Failed {len(check.failures)} checks:")
        for failure in check.failures:
            print(f"- {failure}")
        return 1
    print("Site checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
