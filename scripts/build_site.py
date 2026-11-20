#!/usr/bin/env python3
"""Generate the static public-requests site from data/requests.json."""

import html
import shutil
from pathlib import Path

from common import DATA_PATH, GENERATED_FILES, SITE_DIR, load_data


def esc(value):
    return html.escape(str(value), quote=True)


def head(data, title, description, canonical, *, indexable):
    full_title = f"{title} | BAS1S Ventures"
    robots = "index, follow" if indexable else "noindex, follow"
    base = data["site"]["basePath"]
    canonical_tags = ""
    if canonical:
        canonical_tags = f"""
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(full_title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{esc(full_title)}">
  <meta name="twitter:description" content="{esc(description)}">"""
    return f"""<!DOCTYPE html>
<html lang="{esc(data["site"]["language"])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="{robots}">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <meta name="format-detection" content="telephone=no, email=no">
  <meta name="theme-color" content="#f6f3ec">
  <title>{esc(full_title)}</title>
  <link rel="icon" href="{esc(base)}assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{esc(base)}assets/site.css">
  <link rel="alternate" type="application/json" href="{esc(base)}requests.json" title="Public requests as JSON">
  <link rel="sitemap" type="application/xml" href="{esc(base)}sitemap.xml" title="Sitemap">{canonical_tags}
</head>"""


def header(data, *, index_current):
    base = data["site"]["basePath"]
    current = ' aria-current="page"' if index_current else ""
    return f"""<body>
  <a class="skip" href="#content">Skip to content</a>
  <header class="site-header">
    <div class="wrap header-inner">
      <a class="brand" href="{esc(base)}">BAS1S Ventures<span>Public requests</span></a>
      <nav class="primary-nav" aria-label="Primary">
        <a href="{esc(base)}"{current}>Index</a>
      </nav>
    </div>
  </header>"""


def footer(data):
    site = data["site"]
    base = site["basePath"]
    publisher = data["publisher"]
    return f"""  <footer class="site-footer">
    <div class="wrap">
      <p>BAS1S Ventures public requests. Static HTML. No analytics. This index restates public requests and links to the original pages.</p>
      <ul class="footer-links">
        <li><a href="{esc(publisher["url"])}">BAS1S Ventures website</a></li>
        <li><a href="{esc(base)}">Public requests</a></li>
        <li><a href="{esc(base)}requests.json">Public request data (JSON)</a></li>
        <li><a href="{esc(base)}sitemap.xml">Sitemap</a></li>
        <li><a href="{esc(base)}llms.txt">llms.txt (plain text)</a></li>
        <li><a href="{esc(site["repository"])}">Repository</a></li>
      </ul>
    </div>
  </footer>
</body>
</html>
"""


def request_path(data, request):
    return data["site"]["basePath"] + "requests/" + request["slug"] + "/"


def index_page(data):
    site = data["site"]
    cards = []
    for request in data["requests"]:
        path = request_path(data, request)
        reviewed = request["source"]["lastReviewedAsStated"]
        cards.append(
            f"""        <article class="card">
          <h3><a href="{esc(path)}">{esc(request["title"])}</a></h3>
          <p>{esc(request["description"])}</p>
          <p class="reviewed">The source page states last reviewed <time datetime="{esc(request["source"]["lastReviewedDate"])}">{esc(reviewed)}</time>.</p>
          <div class="actions">
            <a class="button" href="{esc(request["source"]["url"])}">{esc(request["source"]["linkText"])}</a>
            <a href="{esc(path)}">Read this request</a>
            <a href="{esc(path)}#contact">Contact pathway</a>
          </div>
        </article>"""
        )
    count = len(data["requests"])
    count_label = "1 public request is listed." if count == 1 else f"{count} public requests are listed."
    notes = "\n".join(f"        <p>{esc(note)}</p>" for note in site["readingNotes"])
    body = f"""{head(data, site["indexTitle"], site["indexDescription"], site["indexUrl"], indexable=True)}
{header(data, index_current=True)}
  <main id="content" tabindex="-1">
    <div class="wrap">
      <div class="measure">
        <p class="kicker">BAS1S Ventures</p>
        <h1>{esc(site["indexTitle"])}</h1>
        <p class="lead">{esc(site["indexDescription"])}</p>
      </div>
      <section class="wide" aria-labelledby="published-requests">
        <h2 id="published-requests">Published requests</h2>
        <p>{count_label}</p>
{chr(10).join(cards)}
      </section>
      <section class="measure" aria-labelledby="how-to-read">
        <h2 id="how-to-read">How to read this site</h2>
{notes}
      </section>
    </div>
  </main>
{footer(data)}"""
    return body


def request_page(data, request):
    path = request_path(data, request)
    source = request["source"]
    contact = request["contact"]
    facts = []
    for fact in request["facts"]:
        facts.append(
            f"""          <div>
            <dt>{esc(fact["label"])}</dt>
            <dd>{esc(fact["value"])}</dd>
          </div>"""
        )
    extra = "\n".join(f"        <p>{esc(paragraph)}</p>" for paragraph in request["paragraphs"])
    notes = []
    for note in request["notes"]:
        body = "\n".join(f"          <p>{esc(paragraph)}</p>" for paragraph in note["paragraphs"])
        notes.append(
            f"""        <div class="note">
          <h3>{esc(note["heading"])}</h3>
{body}
        </div>"""
        )
    email = contact.get("email")
    email_line = ""
    if email:
        email_line = f'\n          <p><a href="mailto:{esc(email)}">{esc(email)}</a></p>'
    page = f"""{head(data, request["title"], request["description"], request["canonical"], indexable=True)}
{header(data, index_current=False)}
  <main id="content" tabindex="-1">
    <div class="wrap">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li><a href="{esc(data["site"]["basePath"])}">Public requests</a></li>
          <li aria-current="page">{esc(request["title"])}</li>
        </ol>
      </nav>
      <div class="measure">
        <p class="kicker">Public request</p>
        <h1>{esc(request["title"])}</h1>
        <p class="lead">{esc(request["description"])}</p>
{extra}
      </div>
      <section class="wide" aria-labelledby="published-terms">
        <h2 id="published-terms">Published terms</h2>
        <dl class="facts">
{chr(10).join(facts)}
        </dl>
      </section>
      <section class="measure" aria-labelledby="limits">
        <h2 id="limits">Limits of this request</h2>
{chr(10).join(notes)}
      </section>
      <section class="measure" id="contact" aria-labelledby="contact-heading">
        <h2 id="contact-heading">Contact pathway</h2>
        <p>The contact pathway is the original mandate. That page is where BAS1S Ventures asks direct shareholders to start a confidential discussion. It publishes the contact below and its own form. This site has no form and does not collect names, addresses or financial information.</p>
        <div class="contact">
          <p class="kicker">Contact published on the source page</p>
          <p class="name">{esc(contact["name"])}</p>
          <p class="org">{esc(contact["organizationAsPublished"])}</p>{email_line}
          <p>{esc(contact["note"])}</p>
          <div class="actions">
            <a class="button" href="{esc(source["url"])}">{esc(source["linkText"])}</a>
          </div>
        </div>
        <p>Do not send share certificates, capitalization tables, identification or other sensitive documents to this site. It cannot receive them.</p>
      </section>
      <section class="measure" aria-labelledby="source-heading">
        <h2 id="source-heading">Source and canonical URL</h2>
        <p><a href="{esc(source["url"])}">{esc(source["linkText"])}</a></p>
        <p class="url">{esc(source["url"])}</p>
        <p>This page's canonical URL is the original mandate, because that page is the authoritative public statement. Systems that honor canonical links should treat the original as the primary copy. This HTML page stays available to read and is linked from the <a href="{esc(data["site"]["basePath"])}">requests index</a>.</p>
        <p>The source page states last reviewed <time datetime="{esc(source["lastReviewedDate"])}">{esc(source["lastReviewedAsStated"])}</time>. This page does not add a review date, a verification status, or a transaction status.</p>
        <p>This page's own address, which is not its canonical URL, is <a href="{esc(path)}">{esc(request["pageUrl"])}</a>.</p>
      </section>
    </div>
  </main>
{footer(data)}"""
    return page


def not_found_page(data):
    title = "Page not found"
    description = "This address is not a public request on the BAS1S Ventures site."
    base = data["site"]["basePath"]
    return f"""{head(data, title, description, None, indexable=False)}
{header(data, index_current=False)}
  <main id="content" tabindex="-1">
    <div class="wrap measure">
      <p class="kicker">BAS1S Ventures</p>
      <h1>{esc(title)}</h1>
      <p class="lead">{esc(description)}</p>
      <p>The link may be mistyped, or the request is not published here.</p>
      <div class="actions">
        <a class="button" href="{esc(base)}">Back to public requests</a>
      </div>
    </div>
  </main>
{footer(data)}"""


def robots_txt(data):
    sitemap = data["site"]["pagesHost"].rstrip("/") + data["site"]["basePath"] + "sitemap.xml"
    return f"""# Project-site robots file for the BAS1S Ventures public requests site.
# Host-level crawlers request /robots.txt from the github.io host root,
# which this project repository does not control. This file applies when
# it is fetched at the project path.

User-agent: *
Allow: /

Sitemap: {sitemap}
"""


def sitemap_xml(data):
    host = data["site"]["pagesHost"].rstrip("/")
    base = data["site"]["basePath"]
    locs = [host + base, host + base + "requests.json", host + base + "llms.txt"]
    for request in data["requests"]:
        locs.append(host + request_path(data, request))
    body = "\n".join(f"  <url><loc>{esc(loc)}</loc></url>" for loc in locs)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{body}
</urlset>
"""


def llms_txt(data):
    site = data["site"]
    lines = [
        "# BAS1S Ventures public requests",
        "",
        "> Static public index of requests BAS1S Ventures has already published. This file is a plain-text complement to the HTML. It does not ask for search ranking, preferential treatment, or automatic distribution.",
        "",
        "Request pages use the original public mandate as their canonical URL.",
        "",
        "## Pages",
        "",
        f"- [Public requests]({site['indexUrl']}): {site['indexDescription']}",
    ]
    for request in data["requests"]:
        source = request["source"]["url"]
        lines.append(f"- [{request['title']}]({request['pageUrl']}): {request['description']}")
        for fact in request["facts"]:
            lines.append(f"  - {fact['label']}: {fact['value']}")
        lines.append(f"  - Authoritative mandate: {source}")
        lines.append(
            f"  - The source page states last reviewed {request['source']['lastReviewedAsStated']}."
        )
        lines.append("  - This is not a statement that a purchase has been agreed or completed.")
        lines.append(f"  - Contact published on the source page: {request['contact']['name']}, {request['contact']['organizationAsPublished']}, {request['contact']['email']}")
    lines.extend(
        [
            "",
            "## Data",
            "",
            f"- [requests.json]({site['pagesHost'].rstrip('/')}{site['basePath']}requests.json)",
            "",
            "## Contact",
            "",
            "Use the original mandate linked from each request. This site does not collect inquiries.",
            "",
        ]
    )
    return "\n".join(lines)


def generated_map(data):
    files = {
        "index.html": index_page(data),
        "404.html": not_found_page(data),
        "robots.txt": robots_txt(data),
        "sitemap.xml": sitemap_xml(data),
        "llms.txt": llms_txt(data),
    }
    for request in data["requests"]:
        relative = f"requests/{request['slug']}/index.html"
        files[relative] = request_page(data, request)
    return files


def write_site(directory: Path, data):
    directory.mkdir(parents=True, exist_ok=True)
    for name in GENERATED_FILES:
        target = directory / name
        if target.is_file():
            target.unlink()
    # Remove generated request pages that no longer exist, without touching assets.
    requests_dir = directory / "requests"
    if requests_dir.exists():
        expected = {request["slug"] for request in data["requests"]}
        for child in requests_dir.iterdir():
            if child.is_dir() and child.name not in expected:
                shutil.rmtree(child)
    for relative, content in generated_map(data).items():
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    shutil.copyfile(DATA_PATH, directory / "requests.json")


def main():
    data = load_data()
    write_site(SITE_DIR, data)
    print(f"Wrote static site to {SITE_DIR}")


if __name__ == "__main__":
    main()
