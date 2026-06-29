# CLAUDE.md — NSS Lab Website (nss-lab/web)

Guidance for Claude Code (and humans) working in this repository.

## What this project is

This repo hosts the **new** website for the **NSS Lab** (Network and System
Security Laboratory) at KAIST, led by Prof. **Seungwon Shin**.

We migrated away from the legacy site at https://nss.kaist.ac.kr — a 10+ year old
WordPress install on a 15+ year old machine that could die at any time — to a
**static Jekyll site on GitHub Pages**: stable, free, easy to maintain. The new
site reproduces the legacy site's structure, content, and navy/Poppins identity.

The lab owns the source site, so copying its text/images/data is authorized. The
legacy server is being retired, so **assets are copied into this repo** (logo,
faculty photo, ~99 paper PDFs, gallery photos) rather than hot-linked.

## Current status — built & verified (real `jekyll build`)

- **Homepage:** hero, research cards, news feed, location map.
- **People:**
  - Faculty — Prof. Shin with photo + bio.
  - Doctoral Students (11) and Master's Students (3) — name + link buttons
    (Email/Homepage/Scholar/CV/GitHub/LinkedIn), **no photos**.
  - Alumni (28: 14 Ph.D. + 14 Master's) — grouped by degree, name + **current
    position** in grey.
  - A combined **/people/** page (the nav "People" link) shows everyone together;
    the dropdown still links to the individual pages.
- **Research** — three pillars: **AI, Security, System** (data-driven in
  `_data/research.yml`, grounded in the last 5 years of papers). The legacy
  SDN/container/blockchain framing was retired per the advisor.
- **Publications** — full list, **120 papers (2015–2026)** grouped by year in the
  legacy format (venue, title, authors, venue/year), each row with a **Paper**
  button on the right. **99 paper PDFs hosted locally** in `assets/papers/`; 8
  paywalled ones link out via the same button.
- **Awards** — full list (8 years, 2018–2025) grouped by year → award → prize →
  recipients (Korean names/competitions preserved from the original).
- **Gallery** — 23 lab photos as a left-right carousel (prev/next arrows) with
  event-name caption overlays.
- **Branding** — transparent NSS logo + faculty photo from the legacy site.

**Still to do / verify:** add the social links that were decorative-only on the
legacy site (the LinkedIn/GitHub icons there had no URL behind them — need real
ones); verify names/emails; attach the custom domain.

## Architecture — Jekyll on GitHub Pages

- **Jekyll** builds on GitHub on every push (no Action, no local build needed to
  publish). Content = Markdown/HTML + YAML data files; shared chrome in one layout.
- **Publish source:** GitHub Pages serves the **`docs/`** dir on `main`
  ("Deploy from a branch → `main` / `/docs`").
- **No `.nojekyll`** — its presence would disable the Jekyll build.
- A failed build keeps the last working version live and emails the error.

### Repository layout

```
docs/                          # GitHub Pages builds & serves this folder
  _config.yml                  # title, baseurl, lab_email, address
  Gemfile                      # local preview only
  index.html                   # Homepage
  research.html publications.html awards.md gallery.md
  people/ faculty.md phd.html masters.html alumni.html
  _layouts/  default.html page.html
  _includes/ header.html footer.html people.html
  _data/
    research.yml news.yml                  # homepage sections
    publications.yml                        # 120 papers, by year
    phd.yml masters.yml alumni.yml awards.yml gallery.yml
  assets/
    css/style.css  js/main.js
    img/  nss-logo.png  seungwon-shin.jpg   # logo + faculty photo
    img/gallery/  *.jpg                      # 23 gallery photos
    papers/  *.pdf                           # 99 paper PDFs (~252 MB)
CLAUDE.md  README.md  .gitignore             # repo root (not published)
```

## How to update content

Edit one file, commit, push — GitHub rebuilds automatically.

- **News item:** `docs/_data/news.yml` — add a block at the top (`date`, `title`,
  `venue?`, `link?`).
- **Publication:** `docs/_data/publications.yml` — under the right `- year:`, add a
  paper block:
  ```yaml
  - venue: "CCS"
    title: "Paper Title"
    authors: "A. Author, B. Author"
    info: "Full venue name, 2026"
    pdf: "ccs2026-author.pdf"   # file in assets/papers/  (or use: ext: "https://...")
  ```
  To host a new PDF: drop the file in `docs/assets/papers/` and set `pdf:` to its
  filename (convention: `<venue><year>-<firstauthor>.pdf`). For paywalled papers
  use `ext:` with the external URL instead.
- **Student (PhD/Master's):** `docs/_data/phd.yml` / `masters.yml` — one block per
  person; a button shows only for fields present:
  ```yaml
  - name: "Jane Doe"
    email: "jane@kaist.ac.kr"
    github: "https://github.com/jane"
    linkedin: "https://www.linkedin.com/in/jane/"
    cv: "https://jane.github.io/"
  ```
  **No photos** (privacy) — don't add image fields.
- **Alumni:** `docs/_data/alumni.yml` — `group` ("Ph.D." or "Master's"), `name`,
  and `position` (current job, shown in grey). No links by design.
- **Award:** `docs/_data/awards.yml` — `year` → `awards` (each `name` → `items`
  of `prize` + `recipients`).
- **Gallery photo:** drop the image in `docs/assets/img/gallery/`, then add
  `- file: "name.jpg"` (+ optional `alt:`) to `docs/_data/gallery.yml`.
- **Research areas:** `docs/_data/research.yml` — `title`, `summary` (homepage
  card), `detail` + `topics` (the /research/ feature rows), and `image` (figure in
  `assets/img/research/`). The three figures are **sample SVG illustrations** —
  replace the file (or change `image`) to drop in a real paper figure.
- **Contact / lab name:** `docs/_config.yml`. **Nav / footer:** the includes.

## Local preview (optional — GitHub builds for you)

```bash
cd docs && bundle install && bundle exec jekyll serve   # http://localhost:4000/web/
```
A clean `gem install jekyll` needs Ruby dev headers (`sudo apt install ruby-dev`)
to compile a serve-only native extension — local tooling only, unrelated to the
GitHub build.

## Deployment & URLs

- Push to `main`; GitHub Pages rebuilds `docs/`.
- URL: **https://nss-lab.github.io/web/** → `baseurl: "/web"` in `_config.yml`.
  **All internal links/assets use the `relative_url` filter** so they respect it.
- **Custom domain (nss.kaist.ac.kr):** set `baseurl: ""` and add `docs/CNAME`
  with the domain (DNS managed by KAIST).

### Repo size note

The repo carries ~252 MB of paper PDFs + ~23 MB of photos. That's within GitHub
limits (100 MB/file hard limit; ~1 GB repo / 1 GB Pages site recommended), and
the largest PDF is ~13 MB. If the PDF collection grows much larger, consider
**Git LFS** for `assets/papers/` (note: LFS has its own storage/bandwidth quota).

## Source site reference (legacy, for ongoing parity)

Legacy: https://nss.kaist.ac.kr — WordPress + Business Gravity + Elementor.
Navigation → clean paths:

| Menu | Legacy | New |
|---|---|---|
| Home | `/` | `/` |
| People ▸ Faculty / Doctoral / Master's / Alumni | `?page_id=29/6554/6448/6447` | `/people/{faculty,phd,masters,alumni}/` |
| Research | `?page_id=7155` | `/research/` |
| Publication/Talk | `?page_id=6856` | `/publications/` |
| Award | `?page_id=7260` | `/awards/` |
| Gallery | `?page_id=62` | `/gallery/` |

Individual person profiles on the legacy site live at their own `?page_id=N`
(that's where each student's links were scraped from). Awards page (`?page_id=7260`)
still needs importing.

### Design system (in `assets/css/style.css`)

- Primary navy `#000080`; text `#1c1f2b` / muted `#6e6e6e`; publication venue red
  `#c0392b`. Font **Poppins** (300–800). Tokens are CSS variables at the top.

## Verified contact details

- **Lab email:** `nsslab@kaist.ac.kr` · **Address:** 291 Daehak-ro, Yuseong-gu, Daejeon, Korea

## Conventions & gotchas

- **Everything inside `docs/`**; use `relative_url` for internal links/assets.
- **Don't re-add `.nojekyll`.** Liquid: use `elsif` (not `elif`), and `or`/`and`
  only inside `{% if %}` (not in `{% assign %}`).
- **No member photos** (faculty is the only exception).
- **Host assets locally** (`assets/img`, `assets/papers`) — never hot-link the
  legacy `wp-content/uploads/` URLs; that server is being retired.
- Data files are the single source of truth for people, publications, gallery,
  research, and news — prefer editing YAML over hand-editing page HTML.
- `docs/_site/`, caches, and `Gemfile.lock` are git-ignored build artifacts.
