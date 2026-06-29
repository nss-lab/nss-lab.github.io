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
- **URL:** https://nss-lab.github.io/web/ → `baseurl: "/web"` in `_config.yml`.
  Use the `relative_url` filter for every internal link/asset so it respects baseurl.
- **Custom domain (nss.kaist.ac.kr):** set `baseurl: ""` in `_config.yml` and add
  `docs/CNAME` containing the domain (DNS handled by KAIST).
- Commit/push only when asked. Pushing to `main` is correct here (it's the deploy
  branch); the account in use has write access to `nss-lab/web`.

## Repository layout

```
docs/
  _config.yml                 # title, baseurl, lab_email, address
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
- **Custom domain** — attach `nss.kaist.ac.kr` (baseurl + CNAME, see above).

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
