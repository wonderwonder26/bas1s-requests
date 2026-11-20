# BAS1S Ventures public requests

Static index of public requests BAS1S Ventures has already published. The first entry restates the OpenEvidence preferred-share buying mandate and links to the original page:

https://bas1s.ventures/secondaries/openevidence

This repository is the source for a GitHub Pages project site. It is not a second home for the mandate, and it does not collect inquiries.

## Canonical approach

The original mandate already has a public address. This site does not create another canonical copy of it.

- The OpenEvidence request page repeats the published facts in ordinary HTML. Its `<link rel="canonical">` and `og:url` point at `https://bas1s.ventures/secondaries/openevidence`. Systems that honor canonical links should treat that original page as the authoritative copy.
- The index is a different document: a list of public requests. Its canonical URL is the index on the GitHub Pages project site, `https://wonderwonder26.github.io/bas1s-requests/`.
- The request page says this in visible text, not only in a link element. Its own project-site address is labeled as not canonical.
- `sitemap.xml` lists the index, the request page, the JSON file, and `llms.txt` so a crawler that fetches the project sitemap can find them. The request page still declares the original mandate as canonical.
- `llms.txt` is a plain-text complement for readers that look for that filename. It does not ask for search ranking, preferential treatment, or automatic distribution.

The source page states last reviewed 19 November 2026. Pages here repeat that label. They do not add a new review date, verification status, or transaction status, and they do not say a purchase has been agreed or completed.

## What is published

BAS1S Ventures has published that it is buying approximately US$10 million of OpenEvidence preferred shares, preferably through a direct secondary share transfer, at a target implied company valuation of approximately US$12 billion. Direct shareholders are invited to contact Wonder Xu at Bas1s Ventures. The US$12 billion figure is an indicative acquisition target, not a statement of OpenEvidence's current market valuation.

The contact pathway is the original mandate. That page publishes the contact and its own form. This site links to it and repeats the published name, organization, and email. It does not invent another phone number or address, and it has no form.

BAS1S Ventures is not affiliated with or endorsed by OpenEvidence. Company approval is not represented.

## Repository layout

- `data/requests.json` is the editable source for the published facts.
- `scripts/build_site.py` generates HTML, `robots.txt`, `sitemap.xml`, `llms.txt`, and the public JSON copy.
- `site/` is the GitHub Pages artifact. Do not edit generated files by hand.
- `site/assets/` holds the hand-written stylesheet and icon.
- `scripts/check_site.py` checks raw HTML, base-path links, contrast, and data consistency.
- `scripts/preview.py` serves the site at `/bas1s-requests/`.

There is no site JavaScript, no analytics, no backend, and no form.

## Preview and checks

```bash
python3 scripts/build_site.py
python3 scripts/check_site.py
python3 scripts/preview.py
```

Open http://127.0.0.1:8765/bas1s-requests/

The checker reads the HTML files directly and also requests them through the preview server, which does not execute JavaScript. It fails if a generated file is stale, if an internal link leaves `/bas1s-requests/`, or if the visible text drifts from `data/requests.json`.

## Add a request

Add a request only when it is already public on a page you can cite. Do not add drafts, private notes, placeholders, or anything presented as real before it is public.

1. Read the original page and record only facts it states, including its contact pathway. If it does not publish an email, phone, or personal name, do not invent one. Link to the original page instead.
2. Add one object to `requests` in `data/requests.json`. Use a new lowercase `slug`. Set `canonical` and `source.url` to the original page, not to the GitHub Pages copy.
3. Set `pagePath` to `/bas1s-requests/requests/<slug>/` and `pageUrl` to `https://wonderwonder26.github.io` plus that path.
4. Keep approximate amounts labeled as approximate. Do not mark a purchase completed, terms agreed, or company approval represented unless the original page actually says that, and do not say it here while those flags are false.
5. This first version's checker expects exactly the OpenEvidence request. When you add another public request, update that expected set in `scripts/check_site.py` in the same change.
6. Run `python3 scripts/build_site.py` and `python3 scripts/check_site.py`.
7. Commit `data/requests.json` and the generated files under `site/` together.

## GitHub Pages

The project base path is `/bas1s-requests/`, from the repository name `wonderwonder26/bas1s-requests`. Links, the stylesheet, the icon, the 404 page, the sitemap, and `robots.txt` use that path.

This repository prepares deployment. It does not enable Pages.

After review:

1. Merge the accepted pull request into `main`.
2. Open Settings, then Pages.
3. Under Build and deployment, set Source to GitHub Actions. Do not choose Deploy from a branch. The workflow publishes only the `site` directory.
4. `.github/workflows/pages.yml` runs on pushes to `main`. If Pages is not yet set to GitHub Actions, that run fails at deploy. Save the setting, then re-run the workflow.
5. The project site address is https://wonderwonder26.github.io/bas1s-requests/
6. Do not add a custom domain unless the public host should change. A custom domain changes canonical URLs. Update `pagesHost` in `data/requests.json`, rebuild, and redeploy if you add one.
7. After it is live, open the index, the OpenEvidence request, a bad address (the 404 page), `requests.json`, `sitemap.xml`, `robots.txt`, and `llms.txt`.

`robots.txt` in this repository is served at `https://wonderwonder26.github.io/bas1s-requests/robots.txt`. Crawlers that only read `https://wonderwonder26.github.io/robots.txt` are looking at the user-site root, which this project repository does not control. The HTML pages also link to the project sitemap.

Pull requests run `.github/workflows/check.yml`. That check does not deploy the site.
