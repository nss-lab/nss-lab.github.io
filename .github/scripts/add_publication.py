#!/usr/bin/env python3
"""Add, update, or delete a publication from an issue form.

Driven by .github/workflows/add-publication.yml. The issue form carries an
"Operation" dropdown; given the rendered body (env ISSUE_BODY) this script:

  * Add    — insert a new paper as the newest of its year (creating the year
             group if needed). The paper may carry an uploaded PDF, an external
             link, or neither (an announce-only "to appear" entry).
  * Update — find an existing paper by its exact title and attach/replace its
             PDF or link, and/or fix its venue / authors / info in place.
  * Delete — find an existing paper by its exact title and remove it (and its
             PDF), dropping the year group if it becomes empty. (Mostly for
             cleaning up test entries.)

publications.yml is edited by *targeted text* work — a new entry is inserted as
formatted lines, and update/delete rewrite or drop only the matched entry's
lines — so the rest of the file stays byte-for-byte unchanged. The caller then
re-parses the whole file to prove it is still valid before committing. The dry
run does all of this in the runner's working tree and simply doesn't commit.

Every value comes from the issue and is untrusted: it arrives via an environment
variable (never the shell), downloads are restricted to GitHub's own attachment
hosts, and the bytes must be a valid PDF.

Hard problems append `error=<message>` to GITHUB_OUTPUT and exit 1 so the
workflow can post the message on the issue. Non-fatal concerns are collected in
`warnings` and reported alongside a success.
"""

import datetime
import hashlib
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAPERS_DIR = os.path.join(REPO_ROOT, "docs", "assets", "papers")
PUBS_YML = os.path.join(REPO_ROOT, "docs", "_data", "publications.yml")

# We only fetch attachments GitHub itself hosts (the upload URL plus the CDNs it
# redirects to). Keeps a maintainer-labelled issue from pointing us elsewhere.
ALLOWED_HOSTS = {
    "github.com",
    "raw.githubusercontent.com",
    "user-images.githubusercontent.com",
    "objects.githubusercontent.com",
    "media.githubusercontent.com",
}
MAX_PDF_BYTES = 40 * 1024 * 1024  # GitHub caps attachments well below this
MIN_PDF_BYTES = 1024              # anything smaller is empty/truncated
BIG_PDF_BYTES = 15 * 1024 * 1024  # warn (don't block) above this
MIN_YEAR = 1990

WARNINGS = []


def warn(msg):
    WARNINGS.append(msg)


def set_output(key, value):
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a", encoding="utf-8") as fh:
        if "\n" in value:  # GitHub Actions multi-line output needs a delimiter
            delim = "GHADELIM_" + hashlib.sha1(value.encode()).hexdigest()[:12]
            fh.write(f"{key}<<{delim}\n{value}\n{delim}\n")
        else:
            fh.write(f"{key}={value}\n")


def fail(msg):
    """Report a handled error to the workflow, then stop."""
    set_output("error", msg)
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_form(body):
    """Turn an issue-form body ('### Label\\n\\nvalue') into {label: value}."""
    fields, current, buf = {}, None, []
    for line in body.splitlines():
        m = re.match(r"^###\s+(.*\S)\s*$", line)
        if m:
            if current is not None:
                fields[current] = "\n".join(buf).strip()
            current, buf = m.group(1).strip(), []
        elif current is not None:
            buf.append(line)
    if current is not None:
        fields[current] = "\n".join(buf).strip()
    # GitHub renders an empty optional field as "_No response_".
    return {k: ("" if v.strip() == "_No response_" else v) for k, v in fields.items()}


def clean_line(s):
    """Collapse any run of whitespace to a single space."""
    return re.sub(r"\s+", " ", s).strip()


def extract_url(field):
    """First URL in a field — from a [text](url) link or a bare https URL."""
    m = re.search(r"\((https?://[^)\s]+)\)", field)
    if m:
        return m.group(1)
    m = re.search(r"https?://\S+", field)
    return m.group(0) if m else ""


def valid_url(u):
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except ValueError:
        return False


def venue_slug(venue):
    return re.sub(r"[^a-z0-9]", "", venue.lower())


def surname_of(authors):
    first = authors.split(",")[0].replace("*", "").strip()
    parts = first.split()
    sur = re.sub(r"[^a-z0-9]", "", parts[-1].lower()) if parts else ""
    return sur or "paper"


def unique_filename(base):
    """'ndss2026-you' -> 'ndss2026-you.pdf', deduped with -2, -3 ... on collision."""
    if not os.path.exists(os.path.join(PAPERS_DIR, f"{base}.pdf")):
        return f"{base}.pdf"
    n = 2
    while os.path.exists(os.path.join(PAPERS_DIR, f"{base}-{n}.pdf")):
        n += 1
    return f"{base}-{n}.pdf"


def fetch_attachment(url):
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        fail(f"Refusing to download from '{host}'. Drop the PDF into the form's "
             "upload box so it is hosted on GitHub.")
    req = urllib.request.Request(url, headers={"User-Agent": "nss-add-publication"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read(MAX_PDF_BYTES + 1)
    except urllib.error.URLError as e:
        fail(f"Could not download the PDF ({e}). On a private repo the attachment "
             "link needs a login — this site's repo must stay public.")
    if len(data) > MAX_PDF_BYTES:
        fail("The PDF is larger than the 40 MB limit.")
    return data


def validate_pdf(data):
    """Reject anything that isn't a real, whole PDF."""
    if len(data) < MIN_PDF_BYTES:
        fail(f"The PDF is only {len(data)} bytes — it looks empty or truncated.")
    if not re.search(rb"%PDF-\d", data[:1024]):
        fail("That download has no %PDF header, so it isn't a PDF (a saved web "
             "page or an error page?). Re-attach the real file.")
    if b"%%EOF" not in data:
        fail("The PDF has no %%EOF marker — the upload looks truncated. Re-attach it.")
    if len(data) > BIG_PDF_BYTES:
        warn(f"Large PDF ({len(data) // (1024 * 1024)} MB) — consider compressing it.")


def find_duplicate_pdf(data):
    """Name of an existing paper with byte-identical content, or '' if none."""
    if not os.path.isdir(PAPERS_DIR):
        return ""
    target_len, digest = len(data), None
    for fn in sorted(os.listdir(PAPERS_DIR)):
        if not fn.lower().endswith(".pdf"):
            continue
        path = os.path.join(PAPERS_DIR, fn)
        try:
            if os.path.getsize(path) != target_len:  # cheap pre-filter
                continue
            if digest is None:
                digest = hashlib.sha256(data).hexdigest()
            with open(path, "rb") as fh:
                if hashlib.sha256(fh.read()).hexdigest() == digest:
                    return fn
        except OSError:
            continue
    return ""


def save_pdf(data, venue, year, authors, override):
    """Write the PDF under the naming convention; return its filename."""
    if override:
        base = re.sub(r"\.pdf$", "", os.path.basename(override), flags=re.I)
        base = re.sub(r"[^A-Za-z0-9._-]", "", base) or f"{venue_slug(venue)}{year}"
    else:
        base = f"{venue_slug(venue)}{year}-{surname_of(authors)}"
    name = unique_filename(base)
    os.makedirs(PAPERS_DIR, exist_ok=True)
    with open(os.path.join(PAPERS_DIR, name), "wb") as fh:
        fh.write(data)
    return name


def remove_pdf(name):
    if name:
        try:
            os.remove(os.path.join(PAPERS_DIR, name))
        except OSError:
            pass


def yaml_dq(s):
    """A double-quoted YAML scalar, matching the file's style."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _unquote(v):
    v = v.strip()
    v = re.sub(r'^"|"$', "", v)
    return v.replace('\\"', '"').replace("\\\\", "\\")


def build_entry(venue, title, authors, info, pdf, ext, indent="    "):
    cont = indent + "  "
    lines = [f"{indent}- venue: {yaml_dq(venue)}", f"{cont}title: {yaml_dq(title)}"]
    if authors:
        lines.append(f"{cont}authors: {yaml_dq(authors)}")
    if info:
        lines.append(f"{cont}info: {yaml_dq(info)}")
    if pdf:
        lines.append(f"{cont}pdf: {yaml_dq(pdf)}")
    elif ext:
        lines.append(f"{cont}ext: {yaml_dq(ext)}")
    return "\n".join(lines) + "\n"


YEAR_RE = re.compile(r'^-\s+year:\s*["\']?(\d{4})')
PAPERS_RE = re.compile(r"^\s+papers:\s*$")
ITEM_RE = re.compile(r"^(\s{2,})-\s")
TITLE_LINE_RE = re.compile(r"^\s*(?:-\s+)?title:\s*(.*\S)\s*$")
FIELD_RE = re.compile(r"^\s*(?:-\s+)?(venue|title|authors|info|pdf|ext):\s*(.*)$")


def title_exists(text, title):
    """Approximate guard against adding the same paper twice."""
    want = clean_line(title).lower()
    for ln in text.splitlines():
        m = TITLE_LINE_RE.match(ln)
        if m and clean_line(_unquote(m.group(1))).lower() == want:
            return True
    return False


def insert_entry(text, year, entry_block):
    lines = text.splitlines(keepends=True)
    years = [(i, int(m.group(1))) for i, ln in enumerate(lines)
             for m in [YEAR_RE.match(ln)] if m]

    target = next((i for i, y in years if y == int(year)), None)
    if target is not None:
        papers_idx = None
        for j in range(target + 1, len(lines)):
            if PAPERS_RE.match(lines[j]):
                papers_idx = j
                break
            if YEAR_RE.match(lines[j]):
                break
        if papers_idx is None:
            fail(f'Found year {year} but no "papers:" list beneath it.')
        return "".join(lines[:papers_idx + 1] + [entry_block] + lines[papers_idx + 1:])

    # New year group: place it so years stay in descending order.
    block = f'- year: "{year}"\n  papers:\n{entry_block}'
    before = next((i for i, y in years if int(year) > y), None)
    if before is None:  # older than every existing year -> end of file
        joined = "".join(lines)
        if joined and not joined.endswith("\n"):
            joined += "\n"
        return joined + block
    return "".join(lines[:before] + [block] + lines[before:])


def find_entry_span(lines, title):
    """(start, end, year, indent) for the entry whose title matches, else None."""
    want = clean_line(title).lower()
    ti = next((i for i, ln in enumerate(lines)
               for m in [TITLE_LINE_RE.match(ln)]
               if m and clean_line(_unquote(m.group(1))).lower() == want), None)
    if ti is None:
        return None
    start = ti
    while start >= 0 and not ITEM_RE.match(lines[start]):
        start -= 1
    if start < 0:
        return None
    indent = len(ITEM_RE.match(lines[start]).group(1))
    end = start + 1
    while end < len(lines):
        if YEAR_RE.match(lines[end]):
            break
        m = ITEM_RE.match(lines[end])
        if m and len(m.group(1)) <= indent:
            break
        end += 1
    year = next((m.group(1) for j in range(start, -1, -1)
                 for m in [YEAR_RE.match(lines[j])] if m), None)
    return start, end, year, indent


def parse_entry_fields(entry_lines):
    out = {}
    for ln in entry_lines:
        m = FIELD_RE.match(ln)
        if m:
            out[m.group(1)] = _unquote(m.group(2))
    return out


def remove_entry(text, title):
    """Drop the matched entry (and an emptied year group). Return (text, pdf)."""
    lines = text.splitlines(keepends=True)
    span = find_entry_span(lines, title)
    if not span:
        fail(f'No publication titled "{title}" was found to delete. Paste the '
             "exact current title.")
    start, end, year, _ = span
    pdf = parse_entry_fields(lines[start:end]).get("pdf", "")
    del lines[start:end]
    yi = next((i for i, ln in enumerate(lines)
               for m in [YEAR_RE.match(ln)] if m and m.group(1) == year), None)
    if yi is not None:
        has_entry = False
        j = yi + 1
        while j < len(lines) and not YEAR_RE.match(lines[j]):
            if ITEM_RE.match(lines[j]):
                has_entry = True
                break
            j += 1
        if not has_entry:
            k = yi + 1
            while k < len(lines) and not YEAR_RE.match(lines[k]):
                k += 1
            del lines[yi:k]
    return "".join(lines), pdf


# --------------------------------------------------------------------------- #
# Operations
# --------------------------------------------------------------------------- #

def _write_pubs(text):
    with open(PUBS_YML, "w", encoding="utf-8") as fh:
        fh.write(text)


def _field_warnings(year, venue, title, authors, info):
    if len(venue) > 20 or re.search(
            r"\b(conference|symposium|proceedings|transactions|journal|"
            r"international|workshop)\b", venue, re.I):
        warn(f'Venue tag "{venue}" looks like a full name — the list shows this '
             "in parentheses, so a short tag (NDSS, CCS, TCC) reads better.")
    if title and len(title) < 8:
        warn(f'Title "{title}" is very short — is it complete?')
    if not authors:
        warn("No authors given.")
    elif "shin" not in authors.lower():
        warn('The author list doesn\'t mention "Shin" — double-check this is a '
             "lab paper and the names are right.")
    if info and year and year not in info:
        warn(f"The info line doesn't contain the year {year} — double-check it.")


def do_add(text, year, venue, title, authors, info, pdf_field, ext, override):
    max_year = datetime.date.today().year + 2
    if not re.fullmatch(r"\d{4}", year):
        fail(f"Year must be four digits to add a paper (got '{year}').")
    if not (MIN_YEAR <= int(year) <= max_year):
        fail(f"Year {year} is outside the sensible range {MIN_YEAR}-{max_year}.")
    if not venue:
        fail("Venue tag is required to add a paper.")
    if not title:
        fail("Title is required.")
    _field_warnings(year, venue, title, authors, info)
    if title_exists(text, title):
        fail(f'A paper titled "{title}" is already in publications.yml. Use the '
             '"Update" operation to change it.')

    pdf_url = extract_url(pdf_field) if pdf_field else ""
    pdf_name = ""
    if pdf_url:
        if ext:
            warn("Both a PDF and an external link were given — using the PDF.")
            ext = ""
        data = fetch_attachment(pdf_url)
        validate_pdf(data)
        dup = find_duplicate_pdf(data)
        if dup:
            fail(f'This exact PDF is already hosted as "{dup}" — the paper may '
                 "already be listed.")
        pdf_name = save_pdf(data, venue, year, authors, override)
        detail = f"PDF `{pdf_name}`"
    elif ext:
        if not valid_url(ext):
            fail(f"The external link '{ext}' is not a valid http(s) URL.")
        detail = "an external link"
    else:
        detail = "no PDF or link yet (announce-only)"

    _write_pubs(insert_entry(text, year, build_entry(venue, title, authors, info,
                                                     pdf_name, ext)))
    return "add", pdf_name, year, title, f'"{title}" under {year} — {detail}'


def do_update(text, year, venue, title, authors, info, pdf_field, ext, override):
    if not title:
        fail("Give the exact title of the paper to update.")
    lines = text.splitlines(keepends=True)
    span = find_entry_span(lines, title)
    if not span:
        fail(f'No publication titled "{title}" was found to update. Paste the '
             'exact current title, or use "Add" for a new paper.')
    start, end, cur_year, _ = span
    old = parse_entry_fields(lines[start:end])
    real_title = old.get("title", title)
    old_pdf = old.get("pdf", "")
    new_pdf, new_ext = old_pdf, old.get("ext", "")
    changed = []

    if year and year != cur_year:
        warn(f"This paper is under {cur_year}; update keeps it there. To move "
             "years, delete it and add it again.")

    pdf_url = extract_url(pdf_field) if pdf_field else ""
    if pdf_url:
        data = fetch_attachment(pdf_url)
        validate_pdf(data)
        dup = find_duplicate_pdf(data)
        if dup and dup != old_pdf:
            fail(f'That PDF is already hosted as "{dup}" (a different paper).')
        if dup and dup == old_pdf:
            warn("The uploaded PDF is identical to the current one — left as is.")
        else:
            if old_pdf:
                remove_pdf(old_pdf)  # free the name so the new file can reuse it
            new_pdf = save_pdf(data, venue or old.get("venue", ""), cur_year,
                               authors or old.get("authors", ""), override)
            new_ext = ""
            changed.append(f"PDF → `{new_pdf}`")
    elif ext:
        if not valid_url(ext):
            fail(f"The external link '{ext}' is not a valid http(s) URL.")
        new_ext, new_pdf = ext, ""
        if old_pdf:
            remove_pdf(old_pdf)
        changed.append("external link")

    venue_f = venue or old.get("venue", "")
    authors_f = authors or old.get("authors", "")
    info_f = info or old.get("info", "")
    for label, new, cur in (("venue", venue, old.get("venue", "")),
                            ("authors", authors, old.get("authors", "")),
                            ("info", info, old.get("info", ""))):
        if new and new != cur:
            changed.append(label)
    if not changed:
        fail("Nothing to update — attach a PDF, add an external link, or change "
             "the venue / authors / info.")

    entry = build_entry(venue_f, real_title, authors_f, info_f, new_pdf, new_ext)
    _write_pubs("".join(lines[:start] + [entry] + lines[end:]))
    return ("update", new_pdf, cur_year, real_title,
            f'"{real_title}" ({cur_year}) — {", ".join(changed)}')


def do_delete(text, title):
    if not title:
        fail("Give the exact title of the paper to delete.")
    new_text, pdf = remove_entry(text, title)
    lines = text.splitlines(keepends=True)
    _, _, year, _ = find_entry_span(lines, title)
    remove_pdf(pdf)
    _write_pubs(new_text)
    tail = f" and its PDF `{pdf}`" if pdf else ""
    return "delete", "", year, title, f'"{title}" from {year}{tail}'


def main():
    body = os.environ.get("ISSUE_BODY", "")
    if not body.strip():
        fail("The issue body is empty — was this opened with the "
             '"Add or update a publication" form?')
    f = parse_form(body)

    def g(label):
        return clean_line(f.get(label, ""))

    op_raw = g("Operation").lower()
    if op_raw.startswith("update"):
        op = "update"
    elif op_raw.startswith("delete"):
        op = "delete"
    else:
        op = "add"

    year = g("Year")
    venue = g("Venue tag")
    title = g("Title")
    authors = g("Authors")
    info = g("Info line")
    pdf_field = f.get("Paper PDF", "").strip()
    ext = g("External link")
    override = g("Filename override")

    with open(PUBS_YML, encoding="utf-8") as fh:
        text = fh.read()

    if op == "update":
        operation, pdf_name, yr, ttl, summary = do_update(
            text, year, venue, title, authors, info, pdf_field, ext, override)
    elif op == "delete":
        operation, pdf_name, yr, ttl, summary = do_delete(text, title)
    else:
        operation, pdf_name, yr, ttl, summary = do_add(
            text, year, venue, title, authors, info, pdf_field, ext, override)

    set_output("operation", operation)
    set_output("filename", pdf_name)
    set_output("year", yr or "")
    set_output("title", ttl)
    set_output("summary", summary)
    if WARNINGS:
        set_output("warnings", "\n".join(f"- {w}" for w in WARNINGS))
    print(f"{operation}: {summary}  (warnings={len(WARNINGS)})")


if __name__ == "__main__":
    main()
