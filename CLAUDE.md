# CLAUDE.md — NSS Lab Website (nss-lab/web)

Guidance for Claude Code (and humans) working in this repository.

## What this is

The website for the **NSS Lab** (Network and System Security Laboratory) at KAIST,
led by Prof. **Seungwon Shin**. It is a **static Jekyll site on GitHub Pages** that
replaced a fragile legacy WordPress site (`nss.kaist.ac.kr`). The lab owns the
original content; assets (logo, faculty photo, paper PDFs, gallery photos) are
copied into this repo because the old server is being retired.

The site is **content/data-driven**: almost everything you'd revise lives in
`docs/_data/*.yml`. Editing those files is the main way to update the site.

## Architecture & deployment

- **Jekyll**, built automatically by **GitHub Pages on every push** — no Action,
  no local build needed to publish.
- **Source:** GitHub Pages serves the **`docs/`** folder on branch **`main`**
  ("Deploy from a branch → main / /docs"). Do **not** add a `.nojekyll` file (it
  disables the Jekyll build).
- A failed build keeps the last good version live and emails the error.
- **URL:** https://nss.kaist.ac.kr/ — the site is served at the domain root, so
  `baseurl: ""`. Still use `relative_url` for every internal link/asset.
- The repo is named **`nss-lab/nss-lab.github.io`** so Pages serves it as the
  organization site (no `/web/` path segment). Renaming it back would reintroduce one.
- **Custom domain:** `docs/CNAME` holds `nss.kaist.ac.kr`; KAIST's DNS has a CNAME
  to `nss-lab.github.io` plus the `_github-pages-challenge-nss-lab` TXT record that
  GitHub required before it would accept the domain. `nss-lab.github.io` now
  permanently redirects to the custom domain.
- Commit/push only when asked. Pushing to `main` is correct here (it's the deploy
  branch); the account in use has **push but not admin** — anything under repo
  Settings (custom domain, Enforce HTTPS, rename) must be done by an org owner.

### Cloudflare mirror (optional, `web.isukim.workers.dev`)

A Workers static-assets project mirrors the site. It is a spare, not the real host:
a Worker custom domain requires the whole `kaist.ac.kr` zone on the Cloudflare
account, which KAIST will never delegate, so the KAIST domain can only live on
GitHub Pages. Workers Builds settings (dashboard, not in-repo):

| Field | Value |
| --- | --- |
| Root directory | `docs` |
| Build command | `LANG=C.UTF-8 bundle exec jekyll build --baseurl ""` |
| Deploy command | `npx wrangler deploy` |

`docs/wrangler.jsonc` supplies the output directory — Workers Builds has no "build
output directory" field (that is Pages-only). **`LANG=C.UTF-8` is required:** the
`github-pages` gem defaults the theme to `jekyll-theme-primer`, whose unused
`style.scss` holds a UTF-8 en dash, and Cloudflare's build container sets no locale,
so Ruby reads it as US-ASCII and the build dies. `--baseurl ""` is now a redundant
no-op (it matches `_config.yml`), harmless to leave.

### Analytics

Cloudflare Web Analytics, beacon in `_layouts/default.html` (which `page.html`
inherits, so every page is covered). Free, cookieless, gives pageviews / visitors /
country. It is client-side, so it reports whatever hostname served the page and
works on any host — GitHub Pages included. It cannot see PDF downloads.

## Repository layout

```
docs/
  _config.yml                 # title, baseurl, lab_email, address
  CNAME                       # custom domain (nss.kaist.ac.kr)
  wrangler.jsonc              # Cloudflare mirror only; excluded from the Jekyll build
  Gemfile                     # local preview only (github-pages gem)
  index.html                  # Homepage            (layout: default, full width)
  research.html               # /research/          (layout: default, full width)
  publications.html           # /publications/      (layout: default, full width)
  gallery.md                  # /gallery/           (layout: default, full width)
  awards.md                   # /awards/            (layout: page,    narrow)
  people/
    index.html                # /people/  combined  (layout: page)
    faculty.md                # /people/faculty/    (layout: page)
    phd.html masters.html alumni.html               (layout: page)
  _layouts/  default.html  page.html
  _includes/ header.html  footer.html  people.html
  _data/
    research.yml news.yml publications.yml
    phd.yml masters.yml alumni.yml awards.yml gallery.yml
  assets/
    css/style.css  js/main.js
    img/  nss-logo.png  nss-logo.svg  seungwon-shin.jpg
    img/gallery/*.jpg|jpeg        # 23 lab photos
    img/research/ai.svg security.svg system.svg   # sample pillar illustrations
    papers/*.pdf                 # 99 paper PDFs (~252 MB)
.github/                         # publication-by-issue automation (not published)
  ISSUE_TEMPLATE/add-publication.yml   # the "Add a publication" issue form
  workflows/add-publication.yml        # issue -> rename PDF, edit YAML, deploy
  scripts/add_publication.py           # form parser + YAML text-inserter (stdlib)
CLAUDE.md  README.md  .gitignore  # repo root (not published)
```

## Page reference (what each page is)

- **Home** — hero, three research cards (from `research.yml`), news feed (from
  `news.yml`), and a "Find Us" Google Map (KAIST place, `cid` embed).
- **People** (`/people/`) — combined page: faculty mini-card + doctoral + master's
  + alumni. The nav "People" link points here; the dropdown still links to the
  individual pages below.
- **Faculty** — Prof. Shin: intro on the left, photo on the right. Title is
  "Principal Investigator" (not "Director").
- **Doctoral / Master's** — name + link buttons (see people include).
- **Alumni** — grouped Ph.D. / Master's; name on the left, current affiliation in
  grey on the right.
- **Research** — three pillars (AI, Security, System) as big alternating figures
  (right/left/right) with detailed write-ups + topic bullets.
- **Publications** — full list by year; title spans the full row, with authors /
  venue / **Paper** button on the line below.
- **Awards** — by year → award → prize → recipients (English).
- **Gallery** — full-width, one photo at a time, prev/next arrows, captions overlaid.

## How to update content (the data files)

Edit a YAML file, commit, push — GitHub rebuilds. Schemas:

- **News** `_data/news.yml` — list of: `date`, `title`, `venue?`, `link?`. Newest first.
- **Publications** `_data/publications.yml` — list of `year` → `papers[]`, each:
  `venue`, `title`, `authors?`, `info?`, and **one of** `pdf:` (filename in
  `assets/papers/`) or `ext:` (external URL). To host a PDF: drop the file in
  `assets/papers/` (convention `venue+year+firstauthor.pdf`, e.g. `ndss2026-you.pdf`)
  and set `pdf:` to its name. Paywalled paper → use `ext:`.
- **Students** `_data/phd.yml`, `_data/masters.yml` — list of: `name`, then any of
  `email`, `homepage`, `scholar`, `cv`, `github`, `linkedin` (store **full URLs**,
  except `email`). CV / GitHub / LinkedIn always render; missing ones show greyed &
  unclickable. **No photos** (privacy) — no image fields.
- **Alumni** `_data/alumni.yml` — list of: `group` ("Ph.D." or "Master's"), `name`,
  `position?` (current job, shown grey on the right). No links by design.
- **Awards** `_data/awards.yml` — list of `year` → `awards[]`, each `name` →
  `items[]` of `prize` + `recipients` (English).
- **Research** `_data/research.yml` — list of: `title`, `summary` (homepage card),
  `detail` + `topics[]` (the /research/ feature row), `image` (file in
  `assets/img/research/`). `detail`/`topics` accept inline HTML — paper/system names
  are wrapped in `<strong>` to bold them. The three figures are **sample SVGs** —
  replace the file or change `image` to use a real paper figure.
- **Gallery** `_data/gallery.yml` — list of: `file` (in `assets/img/gallery/`),
  `caption?`. Drop the image in that folder, add an entry.
- **Contact / lab name** `_config.yml` (`lab_email`, `address`, `title`).
- **Nav / footer** — `_includes/header.html` / `footer.html`.

### Adding a publication from a GitHub issue (automated)

You can add a paper from the **Issues** tab instead of hand-editing YAML:

1. **New issue → "Add a publication"**, fill in year / venue tag / title /
   authors / info line, and **drag the PDF into the "Paper PDF" box** (or give an
   external link for a paywalled paper). Submit.
2. A maintainer eyeballs it and applies a label. The label is both the trigger
   *and* the permission gate — only someone with write access can apply one, so a
   visitor can file the form but cannot publish:
   - **`publication-check`** — dry run: runs the whole pipeline in the runner and
     replies with a preview + any warnings, but **commits nothing**. Safe to run
     anytime to validate an entry.
   - **`publication`** — publishes for real.
3. `.github/workflows/add-publication.yml` then downloads + validates the PDF,
   renames it to `<venuetag><year>-<firstauthor>.pdf` (deduped `-2`, `-3` on
   collision), inserts a matching entry as the newest paper of its year in
   `publications.yml` (creating the year group in the right spot if it's new),
   and — for `publication` only — commits to `main` and forces a Pages rebuild via
   `POST /pages/builds`. It comments the result on the issue and closes it; on any
   problem it comments what went wrong and leaves it open (re-add the label to retry).

**Rigorous checks (hard errors block; warnings just get reported):** required
fields present, year four digits and in a sane range, PDF has a real `%PDF`
header + `%%EOF` (not a truncated upload or a saved web page), the exact PDF isn't
already hosted (content hash) and the exact title isn't already listed, a valid
http(s) external link when there's no PDF. Warnings cover things like a venue
"tag" that's really a full name, an author list with no "Shin", or an info line
missing the year.

The YAML is changed by **targeted text insertion** (`.github/scripts/add_publication.py`,
Python stdlib only), so only the new lines move — comments, quoting, and order
stay put. A CI step `safe_load`s the file to prove it still parses before the
commit. All issue text is untrusted: it reaches the script via an env var (never
the shell), and downloads are restricted to GitHub's attachment hosts.

**One-time setup (needs an org owner):**
- Create two repo **labels**: `publication` and `publication-check`
  (Issues → Labels → New label).
- *Settings → Actions → General → Workflow permissions* → **Read and write
  permissions**. No secret and no PR-creation toggle are needed — this flow
  commits straight to `main` and triggers the rebuild through the Pages API.
- The repo must be public (it is) so the attachment PDF is fetchable, and `main`
  must let the Actions bot push (no blocking branch protection).

### People include

`{% include people.html list=site.data.phd links=true %}` → student style: name +
link buttons. `{% include people.html list=g.items %}` (no `links`) → alumni style:
name + `position` on the right.

### Narrow vs full-width pages

- **Narrow** (820 px reading column): front matter `layout: page` + `title`/`subtitle`
  — the layout adds the page-hero and a `container-narrow` wrapper automatically.
- **Full width** (1140 px): front matter `layout: default`, then write the markup
  yourself — a `<section class="page-hero"><div class="container">…</div></section>`
  for the title, and `<section class="section"><div class="container">…` for content.
  (Research, Publications, Gallery use this.)

## Design system (`assets/css/style.css`)

- Colors: navy `--navy:#000080` (+ `--navy-700:#14148c`, `--navy-900:#07073f`),
  text `--ink:#1c1f2b`, muted `--muted:#6e6e6e`; publication venue red `#ff0000`.
- Font: **Poppins** (Google Fonts). Base size `html { font-size: 17px }`.
- Widths: `.container` 1140 px, `.container-narrow` 820 px. Tokens are CSS
  variables at the top of the file.
- Small JS in `assets/js/main.js`: mobile menu, People dropdown, header shadow,
  gallery prev/next.

## Local preview (optional — GitHub builds for you)

```bash
cd docs && bundle install && bundle exec jekyll serve   # http://localhost:4000/web/
```
A clean `gem install jekyll` needs Ruby dev headers (`sudo apt install ruby-dev`)
to compile a serve-only native extension — local tooling only.

## Open items / TODO

- **Student & alumni social links** — on the legacy site these icons were
  decorative (no URLs), so the buttons render greyed. Add real URLs to the YAML
  to light them up.
- **Real research figures** — swap the three sample SVGs for real paper figures
  when available.
- **Award romanizations** — five non-lab co-author names were best-effort and
  worth verifying: Geon Choi, Sumin Cho, Gilho Lee, Minsu Kim, Hyeonggwon Hong.
- **Legacy server** — `143.248.56.137` no longer receives traffic; it can be retired.

## Conventions & gotchas

- Keep everything inside `docs/`; use `relative_url` for internal links/assets.
- **Don't re-add `.nojekyll`.** Liquid: use `elsif` (not `elif`); `or`/`and` work
  only inside `{% if %}`, not `{% assign %}`.
- **No member photos** (faculty is the only exception).
- **Host assets locally** (`assets/img`, `assets/papers`) — never hot-link the
  legacy `wp-content/uploads/` URLs; that server is being retired.
- Google Maps embeds must use `www.google.com/maps?cid=…&output=embed` (the
  `maps.google.com` host 404s on `cid`); the SAMEORIGIN header is only on the
  redirect, the final response frames fine.
- Data files are the single source of truth — prefer editing YAML over page HTML.
- `docs/_site/`, caches, and `Gemfile.lock` are git-ignored build artifacts.

## Source site reference (legacy, for parity)

Legacy: `https://nss.kaist.ac.kr` (WordPress + Business Gravity + Elementor).
Nav → clean paths: People ▸ Faculty/Doctoral/Master's/Alumni
(`?page_id=29/6554/6448/6447`) → `/people/{faculty,phd,masters,alumni}/`;
Research `7155` → `/research/`; Publication/Talk `6856` → `/publications/`;
Award `7260` → `/awards/`; Gallery `62` → `/gallery/`. Individual person profiles
and the awards/gallery captions were scraped from their own `?page_id=` pages.

- **Verified contact:** lab email `nsslab@kaist.ac.kr`; address
  291 Daehak-ro, Yuseong-gu, Daejeon, Korea.
- The legacy research framing (SDN/NFV, container, blockchain, threat intel) was
  retired in favor of **AI / Security / System** per the advisor.
