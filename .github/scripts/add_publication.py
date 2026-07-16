#!/usr/bin/env python3
"""Turn an "Add a publication" issue form into a real publication.

Driven by .github/workflows/add-publication.yml. Given the rendered issue-form
body (env ISSUE_BODY), this:

  1. Parses the form fields and validates them rigorously.
  2. Downloads the attached PDF, checks it is a real, untruncated PDF, and makes
     sure the exact file (and the exact title) isn't already in the repo.
  3. Renames it to the repo convention  <venuetag><year>-<firstauthor>.pdf
     (deduped with -2, -3 ... on a name clash).
  4. Inserts a matching entry into docs/_data/publications.yml as the newest
     paper of its year, creating the year group in the right spot if it's new.

The YAML file is edited by *targeted text insertion*, never a load/dump, so its
comments, quoting, and ordering stay byte-for-byte unchanged and the diff is
just the new lines. The caller then re-parses the file to prove it's still valid.

The same run serves the dry-run path: the workflow runs everything here and, for
a check-only label, simply doesn't commit what lands in the working tree.

Every value comes from the issue and is treated as untrusted: it arrives via an
environment variable (never the shell), downloads are restricted to GitHub's own
attachment hosts, and the bytes must be a valid PDF.

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


def yaml_dq(s):
    """A double-quoted YAML scalar, matching the file's style."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


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


def title_exists(text, title):
    """Approximate guard against adding the same paper twice."""
    want = clean_line(title).lower()
    for ln in text.splitlines():
        m = re.match(r"^\s+title:\s*(.*\S)\s*$", ln)
        if not m:
            continue
        val = m.group(1).strip()
        val = re.sub(r'^"|"$', "", val).replace('\\"', '"').replace("\\\\", "\\")
        if clean_line(val).lower() == want:
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


def main():
    body = os.environ.get("ISSUE_BODY", "")
    if not body.strip():
        fail("The issue body is empty — was this opened with the "
             '"Add a publication" form?')
    f = parse_form(body)

    def g(label):
        return f.get(label, "").strip()

    year = clean_line(g("Year"))
    venue = clean_line(g("Venue tag"))
    title = clean_line(g("Title"))
    authors = clean_line(g("Authors"))
    info = clean_line(g("Info line"))
    pdf_field = g("Paper PDF")
    ext = clean_line(g("External link"))
    override = clean_line(g("Filename override"))

    # --- required fields + sanity -------------------------------------------
    if not re.fullmatch(r"\d{4}", year):
        fail(f"Year must be four digits (got '{year}').")
    max_year = datetime.date.today().year + 2
    if not (MIN_YEAR <= int(year) <= max_year):
        fail(f"Year {year} is outside the sensible range {MIN_YEAR}-{max_year}.")
    if not venue:
        fail("Venue tag is required.")
    if not title:
        fail("Title is required.")

    if len(venue) > 20 or re.search(
            r"\b(conference|symposium|proceedings|transactions|journal|"
            r"international|workshop)\b", venue, re.I):
        warn(f'Venue tag "{venue}" looks like a full name — the list shows this '
             "in parentheses, so a short tag (NDSS, CCS, TCC) reads better.")
    if len(title) < 8:
        warn(f'Title "{title}" is very short — is it complete?')
    if not authors:
        warn("No authors given.")
    elif "shin" not in authors.lower():
        warn('The author list doesn\'t mention "Shin" — double-check this is a '
             "lab paper and the names are right.")
    if info and year not in info:
        warn(f'The info line doesn\'t contain the year {year} — double-check it.')

    with open(PUBS_YML, encoding="utf-8") as fh:
        text = fh.read()
    if title_exists(text, title):
        fail(f'A paper titled "{title}" is already in publications.yml.')

    # --- resolve the PDF or the external link -------------------------------
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
        if override:
            base = re.sub(r"\.pdf$", "", os.path.basename(override), flags=re.I)
            base = re.sub(r"[^A-Za-z0-9._-]", "", base) or f"{venue_slug(venue)}{year}"
        else:
            base = f"{venue_slug(venue)}{year}-{surname_of(authors)}"
        pdf_name = unique_filename(base)
        os.makedirs(PAPERS_DIR, exist_ok=True)
        with open(os.path.join(PAPERS_DIR, pdf_name), "wb") as fh:
            fh.write(data)
    elif ext:
        if not valid_url(ext):
            fail(f"The external link '{ext}' is not a valid http(s) URL.")
    else:
        fail("Attach a Paper PDF (drop it in the upload box) or give an External link.")

    # --- write the new entry -------------------------------------------------
    entry = build_entry(venue, title, authors, info, pdf_name, ext)
    with open(PUBS_YML, "w", encoding="utf-8") as fh:
        fh.write(insert_entry(text, year, entry))

    set_output("filename", pdf_name)
    set_output("year", year)
    set_output("title", title)
    if WARNINGS:
        set_output("warnings", "\n".join(f"- {w}" for w in WARNINGS))
    print(f"Added '{title}' ({year}); pdf={pdf_name or '(external link)'}; "
          f"warnings={len(WARNINGS)}")


if __name__ == "__main__":
    main()
