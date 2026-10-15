#!/usr/bin/env python3
"""Collect the lessons, wrong theories and corrections from every making-of under a folder.

Walks ROOT for MAKING-OF.md / making-of.md files and pulls out every passage marked
`The lesson`, `WRONG THEORY` or `Correction to`. Each passage is tied to the `##` heading
it sits under (Act N, Session N, or whatever that heading is) by parsing the file, never by
line number, and dated from the nearest heading or list item that carries a date.

Writes one dated markdown digest: passages grouped by project, plus the passages that
weren't in the previous digest. Each digest ends with a manifest of passage ids, so the
next run can tell what is new even for entries with no date.

Optional: a file of error-signature counts (pasted from a transcript search), merged with
the making-of passages and rule files into an evidence table.

Deterministic: standard library only, no network, no model calls. Same files in, same
digest out.

    python3 -I lessons_digest.py ROOT --out-dir DIR [--signatures FILE] [--rules FILE ...]
"""

import argparse
import datetime as dt
import hashlib
import os
import re
import shlex
import sys

MAKING_OF_NAMES = {"making-of.md"}
DEFAULT_SKIP_DIRS = {"node_modules", ".git", "_archive"}
DEFAULT_SKIP_PATHS = (os.path.join(".claude", "worktrees"),)
MANIFEST_START = "<!-- lessons-digest manifest v1"
DIGEST_PREFIX = "lessons-"

KINDS = ("lesson", "wrong", "correction")
KIND_LABEL = {"lesson": "Lesson", "wrong": "Wrong theory", "correction": "Correction"}

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
ISO_DATE = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")
TEXT_DATE = re.compile(
    r"\b(\d{1,2})(?:\s*[–-]\s*(\d{1,2}))?\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?\s+(20\d\d)\b")

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+\.)\s+")
LINE_PREFIX = re.compile(r"^\s*(?:>\s?)*(?:[-*+]\s+|\d+\.\s+)?")

# A marker counts only where it is used as a marker: at the start of a line, paragraph,
# list item or sentence, or bolded. "the lesson lived" or "a wrong theory cheaper than"
# in running prose doesn't.
MARKERS = {
    "lesson": [
        re.compile(r"^(?:\*\*)?The lesson\b"),
        re.compile(r"\*\*The lesson\b"),
        re.compile(r"(?<=[.!?] )(?:\*\*)?The lesson\b"),
    ],
    "wrong": [
        re.compile(r"WRONG THEORY"),
        re.compile(r"\*\*(?:A )?[Ww]rong theory\b"),
    ],
    "correction": [
        re.compile(r"^(?:\*\*)?(?:(?:Second|Third|Another|A further) correction to|"
                   r"Correction to|CORRECTION TO)\b"),
        re.compile(r"(?:\*\*|(?<=[.!?] )|(?<=— ))(?:(?:Second|Third|Another|A further) "
                   r"correction to|Correction to|CORRECTION TO)\b"),
    ],
}


# ---------------------------------------------------------------- dates

def find_dates(text):
    """Every date in text, as (position, date). A range like '5–6 Oct' gives its last day."""
    found = []
    for m in ISO_DATE.finditer(text):
        try:
            found.append((m.start(), dt.date(int(m[1]), int(m[2]), int(m[3]))))
        except ValueError:
            pass
    for m in TEXT_DATE.finditer(text):
        day = int(m[2] or m[1])
        try:
            found.append((m.start(), dt.date(int(m[4]), MONTHS[m[3][:3].lower()], day)))
        except ValueError:
            pass
    return [d for _, d in sorted(found)]


def first_date(text):
    dates = find_dates(text)
    return dates[0] if dates else None


def fmt_date(d):
    return f"{d.day} {d:%b %Y}" if d else "n.d."


# ---------------------------------------------------------------- discovery

def find_making_ofs(root, skip_dirs, skip_paths):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        keep = []
        for d in sorted(dirnames):
            sub = os.path.normpath(os.path.join(rel, d))
            if d in skip_dirs or any(sub == p or sub.endswith(os.sep + p) for p in skip_paths):
                continue
            keep.append(d)
        dirnames[:] = keep
        for f in sorted(filenames):
            if f.lower() in MAKING_OF_NAMES:
                out.append(os.path.join(dirpath, f))
    return sorted(out, key=lambda p: os.path.relpath(p, root))


# ---------------------------------------------------------------- parsing

class Section:
    def __init__(self, line, title, prev_numbered):
        self.line = line              # 0-based line of the ## heading
        self.title = title
        self.label = section_label(title, prev_numbered)
        self.numbered = numbered_label(title)
        self.date = first_date(title)


def numbered_label(title):
    m = re.match(r"(Act|Session)\s+(\d+)\b", title)
    if m:
        return f"{m[1]} {m[2]}"
    m = re.match(r"(D-\d+)\b", title)
    return m[1] if m else None


def section_label(title, prev_numbered):
    label = numbered_label(title)
    if label:
        return label
    short = re.sub(r"\s*\((?:[^()]*\d{4}[^()]*)\)\s*$", "", title)
    short = short if len(short) <= 48 else short[:47].rstrip() + "…"
    after = f", after {prev_numbered}" if prev_numbered else ""
    return f"“{short}”{after}"


class Passage:
    def __init__(self, relpath, kind, line, section, date, date_src, text):
        self.relpath = relpath
        self.kind = kind
        self.line = line              # 1-based
        self.section = section
        self.date = date
        self.date_src = date_src      # "heading", "item", "section" or None
        self.text = text
        norm = re.sub(r"\s+", " ", text).strip().lower()
        self.id = hashlib.sha1(f"{relpath}\0{kind}\0{norm}".encode()).hexdigest()[:12]


def strip_prefix(line):
    return LINE_PREFIX.sub("", line, count=1)


def marker_kinds(line, is_heading):
    """Kinds of marker on this line, each with the column its passage text starts at."""
    body = HEADING.match(line)[2] if is_heading else strip_prefix(line)
    offset = 0 if is_heading else len(line) - len(body)
    hits = {}
    for kind, patterns in MARKERS.items():
        for p in patterns:
            m = p.search(body)
            if m:
                start = m.start()
                if body[max(0, start - 2):start] == "**":
                    start -= 2
                hits[kind] = min(hits.get(kind, start + offset), start + offset)
                break
    return hits


def block_bounds(lines, i, fenced):
    """Start and end (inclusive) of the paragraph, quote or list item holding line i."""
    def blank(j):
        return not lines[j].strip() or fenced[j] or HEADING.match(lines[j])

    if lines[i].lstrip().startswith(">"):
        end = i
        while end + 1 < len(lines) and lines[end + 1].lstrip().startswith(">"):
            end += 1
        return i, end
    start = i
    while start > 0 and not blank(start - 1):
        start -= 1
    end = i
    while end + 1 < len(lines) and not blank(end + 1):
        end += 1
    # Inside a list, keep to the one item.
    item = next((j for j in range(i, start - 1, -1) if LIST_ITEM.match(lines[j])), None)
    if item is not None:
        indent = len(LIST_ITEM.match(lines[item])[1])
        start = item
        for j in range(item + 1, end + 1):
            m = LIST_ITEM.match(lines[j])
            if m and len(m[1]) <= indent:
                end = j - 1
                break
    return start, end


def clean(lines):
    text = " ".join(strip_prefix(l).strip() for l in lines)
    return re.sub(r"\s+", " ", text).strip()


def parse_file(path, root, today):
    relpath = os.path.relpath(path, root)
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()

    fenced, inside = [], False
    for l in lines:
        if FENCE.match(l):
            fenced.append(True)
            inside = not inside
        else:
            fenced.append(inside)

    title = None
    sections, headings = [], []       # headings: (line, level, text) for every level
    prev_numbered = None
    for i, l in enumerate(lines):
        m = None if fenced[i] else HEADING.match(l)
        if not m:
            continue
        level, text = len(m[1]), m[2]
        headings.append((i, level, text))
        if level == 1 and title is None:
            title = text
        if level == 2:
            s = Section(i, text, prev_numbered)
            sections.append(s)
            prev_numbered = s.numbered or prev_numbered

    # A section with no date in its heading gets the latest date in its text that falls
    # between the dates around it (an append-only file runs forward in time). Text also
    # names past and planned dates, hence the bounds, and the `~` in the digest.
    lower = None
    for idx, s in enumerate(sections):
        s.body_date = None
        if not s.date:
            end = sections[idx + 1].line if idx + 1 < len(sections) else len(lines)
            upper = min([t.date for t in sections[idx + 1:] if t.date] + [today])
            fits = [d for d in find_dates("\n".join(lines[s.line + 1:end]))
                    if d <= upper and (lower is None or d >= lower)]
            s.body_date = max(fits) if fits else None
        lower = max(filter(None, [lower, s.date, s.body_date]), default=None)

    def section_at(i):
        current = None
        for s in sections:
            if s.line > i:
                break
            current = s
        return current

    def date_for(i, start, section, own_heading):
        m = LIST_ITEM.match(lines[start])
        if m:
            d = first_date(strip_prefix(lines[start])[:40])
            if d:
                return d, "item"
        for hl, level, htext in reversed(headings):
            if hl > i or (hl == i and own_heading):
                continue
            if hl < section.line:
                break
            d = first_date(htext)
            if d:
                return d, "heading"
        if section.date:
            return section.date, "heading"
        if section.body_date:
            return section.body_date, "section"
        return None, None

    passages, covered = [], {k: set() for k in KINDS}
    for i, l in enumerate(lines):
        if fenced[i] or not l.strip():
            continue
        hm = HEADING.match(l)
        hits = marker_kinds(l, bool(hm))
        section = section_at(i)
        if not hits or section is None:  # nothing before the first ## heading counts
            continue
        if hm:
            start = i
            nxt = i + 1
            while nxt < len(lines) and not lines[nxt].strip():
                nxt += 1
            if nxt < len(lines) and not fenced[nxt] and not HEADING.match(lines[nxt]):
                _, end = block_bounds(lines, nxt, fenced)
                follow = clean(lines[nxt:end + 1])
            else:
                end, follow = i, ""
        else:
            start, end = block_bounds(lines, i, fenced)
        if lines[end].rstrip().endswith(":"):
            nxt = end + 1
            while nxt < len(lines) and not lines[nxt].strip():
                nxt += 1
            if nxt < len(lines) and not fenced[nxt] and not HEADING.match(lines[nxt]):
                end = nxt
                while end + 1 < len(lines) and lines[end + 1].strip() \
                        and not HEADING.match(lines[end + 1]) and not fenced[end + 1]:
                    end += 1
                if hm:
                    follow = clean(lines[i + 1:end + 1])
        for kind, col in sorted(hits.items(), key=lambda kv: kv[1]):
            if i in covered[kind]:
                continue
            if hm:
                head = hm[2]
                text = f"{head} — {follow}" if follow else head
            else:
                text = clean([l[col:]] + lines[i + 1:end + 1])
            covered[kind].update(range(start if not hm else i, end + 1))
            d, src = date_for(i, start, section, bool(hm))
            passages.append(Passage(relpath, kind, i + 1, section, d, src, text))
    return title, passages


# ---------------------------------------------------------------- previous digest

def previous_digest(out_dir, today):
    """Latest earlier digest in out_dir: (path, date, ids or None)."""
    best = None
    if not os.path.isdir(out_dir):
        return None
    for f in os.listdir(out_dir):
        m = re.fullmatch(rf"(?:{DIGEST_PREFIX})?(\d{{4}}-\d\d-\d\d)\.md", f)
        if not m:
            continue
        d = dt.date.fromisoformat(m[1])
        own = f.startswith(DIGEST_PREFIX)
        if d > today or (own and d == today):
            continue
        key = (d, own)  # on the same date, a script digest beats a hand-written report
        if best is None or key > best[0]:
            best = (key, os.path.join(out_dir, f))
    if not best:
        return None
    path = best[1]
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    ids = None
    if MANIFEST_START in text:
        block = text.split(MANIFEST_START, 1)[1].split("-->", 1)[0]
        ids = set(re.findall(r"^[0-9a-f]{12}$", block, re.M))
    return path, best[0][0], ids


# ---------------------------------------------------------------- signatures

COUNT = re.compile(r"^(≥|>=|>)?\s*(\d+)\s*(\+)?$")


def parse_signatures(path):
    """Lines of `count | query | last seen | note`, in any order, `|` or tab separated.

    Also takes `count  query` or `query  count` with no separators. Lines starting with #
    and markdown table header/rule rows are skipped. A count written ≥40 or 40+ is a floor.
    """
    rows = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or re.fullmatch(r"[|:\-\s]+", line):
                continue
            parts = [p.strip() for p in re.split(r"\s*\|\s*|\t+", line.strip("|"))]
            parts = [p for p in parts if p]
            if len(parts) == 1:
                m = (re.match(r"^(≥|>=|>)?\s*(\d+)(\+)?\s+(.+)$", line)
                     or re.match(r"^(.+?)\s+(≥|>=|>)?\s*(\d+)(\+)?$", line))
                if not m:
                    continue
                if m.re.pattern.startswith("^(≥"):
                    parts = [f"{m[1] or ''}{m[2]}{m[3] or ''}", m[4]]
                else:
                    parts = [m[1], f"{m[2] or ''}{m[3]}{m[4] or ''}"]
            count = floor = None
            date = None
            rest = []
            for p in parts:
                cm = COUNT.match(p.replace(" ", ""))
                if count is None and cm:
                    count, floor = int(cm[2]), bool(cm[1] or cm[3])
                    continue
                if date is None and re.fullmatch(r"(?:last seen:?\s*)?.{0,4}\d.{3,20}", p, re.I):
                    d = first_date(p)
                    if d:
                        date = d
                        continue
                rest.append(p)
            if count is None or not rest:
                continue
            query = rest[0].strip("`")
            if query.lower() in {"query", "signature", "search"}:
                continue
            rows.append({"query": query, "count": count, "floor": floor, "last": date,
                         "note": " · ".join(rest[1:])})
    return rows


# ---------------------------------------------------------------- output

def cite(p, project):
    return f"{project} {p.section.label}"


def project_of(relpath):
    d = os.path.dirname(relpath)
    return d if d else "(root)"


def md_cell(s):
    return s.replace("|", "\\|")


def short(text, limit):
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    # Don't leave an unclosed ` or ** in a cut passage.
    if cut.count("`") % 2:
        cut = cut[:cut.rfind("`")].rstrip()
    if cut.count("**") % 2:
        cut = cut[:cut.rfind("**")].rstrip()
    return cut + " …"


def passage_line(p, limit, with_project=False):
    date = fmt_date(p.date) + ("~" if p.date_src == "section" else "")
    where = f"{project_of(p.relpath)} · " if with_project else ""
    return (f"- **{where}{p.section.label}** · {date} · {KIND_LABEL[p.kind]} "
            f"(L{p.line}): {short(p.text, limit)}")


def render(args, root, files, passages, today, prev, sig_rows, rule_texts):
    out = []
    w = out.append
    by_kind = {k: sum(1 for p in passages if p.kind == k) for k in KINDS}
    projects = sorted({project_of(p.relpath) for p in passages})

    w(f"# Lessons digest, {fmt_date(today)}")
    w("")
    w(f"Generated by `lessons_digest.py` from the {len(files)} making-of files under "
      f"`{root}`. No model, no network: the same files give the same digest.")
    w("")
    w(f"**{len(passages)} passages**: {by_kind['lesson']} lessons, {by_kind['wrong']} wrong "
      f"theories, {by_kind['correction']} corrections, in {len(projects)} of {len(files)} files.")
    w("")
    w("Each passage is cited by the `##` heading it sits under, found by parsing the file "
      "(not by line number). A heading without a number is quoted, with the last numbered "
      "heading before it. Dates come from the nearest heading or list item that carries one; "
      "`~` means the date was taken from the section's text, `n.d.` that there was none. "
      f"`L` is the line number on {fmt_date(today)}, for jumping to it; it drifts as files grow.")
    w("")
    cmd = [os.path.abspath(sys.argv[0]), root, "--out-dir",
           os.path.abspath(args.out_dir)]
    if args.signatures:
        cmd += ["--signatures", os.path.abspath(args.signatures)]
    for r in args.rules or []:
        cmd += ["--rules", os.path.abspath(r)]
    for s in args.skip or []:
        cmd += ["--skip", s]
    w("```bash")
    w("python3 -I " + " ".join(shlex.quote(c) for c in cmd))
    w("```")
    w("")

    # New since the last digest
    w("## New since the last digest")
    w("")
    if prev is None:
        new = passages
        w("No earlier digest in the output folder, so every passage is new.")
    elif prev[2] is not None:
        new = [p for p in passages if p.id not in prev[2]]
        w(f"Compared with `{os.path.basename(prev[0])}` by passage id.")
    else:
        new = [p for p in passages if p.date and p.date >= prev[1]]
        w(f"`{os.path.basename(prev[0])}` has no manifest (it wasn't written by this script), "
          f"so this compares by date: passages dated {fmt_date(prev[1])} or later, the same "
          f"day included. Undated passages are left out.")
    w("")
    if new:
        for p in sorted(new, key=lambda p: (p.date or dt.date.min, p.relpath, p.line),
                        reverse=True):
            w(passage_line(p, args.max_chars, with_project=True))
    else:
        w("Nothing new.")
    w("")

    # Evidence
    if sig_rows is not None:
        w("## Evidence: error signatures")
        w("")
        w(f"Counts from `{os.path.basename(args.signatures)}` (sessions with a hit; ≥ marks a "
          "count at the search cap, so a floor). Making-of columns search these files for "
          "the query text, case-insensitive. `Rules` lists the rule files that mention it.")
        w("")
        w("| Query | Sessions | Last seen | Making-of passages | Other making-of lines | Rules | Note |")
        w("|---|---|---|---|---|---|---|")
        for row in sorted(sig_rows, key=lambda r: -r["count"]):
            q = row["query"].lower()
            hits = [p for p in passages if q in p.text.lower()]
            cites = sorted({cite(p, project_of(p.relpath)) for p in hits})
            hit_lines = {(p.relpath, p.line) for p in hits}
            other = 0
            for f, lines in files.items():
                rel = os.path.relpath(f, root)
                other += sum(1 for n, l in enumerate(lines, 1)
                             if q in l.lower() and (rel, n) not in hit_lines)
            ruled = [os.path.basename(r) for r, t in rule_texts.items() if q in t.lower()]
            count = f"{'≥ ' if row['floor'] else ''}{row['count']}"
            cite_text = "; ".join(cites[:4]) + (f"; +{len(cites) - 4}" if len(cites) > 4 else "")
            w(f"| `{md_cell(row['query'])}` | {count} | {fmt_date(row['last'])} | "
              f"{len(hits)}{': ' + md_cell(cite_text) if cites else ''} | {other} | "
              f"{', '.join(ruled) if ruled else ('none' if rule_texts else '—')} | "
              f"{md_cell(row['note'])} |")
        w("")
        if not rule_texts:
            w("No `--rules` files given, so the Rules column is empty.")
            w("")

    # Summary
    w("## By project")
    w("")
    w("| Project | File | Lessons | Wrong theories | Corrections | Newest dated |")
    w("|---|---|---|---|---|---|")
    for f in files:
        rel = os.path.relpath(f, root)
        ps = [p for p in passages if p.relpath == rel]
        counts = [sum(1 for p in ps if p.kind == k) for k in KINDS]
        newest = max((p.date for p in ps if p.date), default=None)
        w(f"| {project_of(rel)} | `{os.path.basename(rel)}` | " +
          " | ".join(str(c) for c in counts) + f" | {fmt_date(newest) if ps else ''} |")
    w("")

    for f in files:
        rel = os.path.relpath(f, root)
        ps = [p for p in passages if p.relpath == rel]
        if not ps:
            continue
        title = args.titles.get(rel)
        w(f"### {project_of(rel)}" + (f" — {title}" if title else ""))
        w("")
        w(f"`{rel}`")
        w("")
        for p in ps:
            w(passage_line(p, args.max_chars))
        w("")

    w(MANIFEST_START)
    for p in sorted(passages, key=lambda p: p.id):
        w(p.id)
    w("-->")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("root", help="folder to search for making-of files")
    ap.add_argument("--out-dir", required=True,
                    help="where digests live; the previous one is looked for here too")
    ap.add_argument("--date", help="digest date, YYYY-MM-DD (default: today)")
    ap.add_argument("--signatures", help="text file of error-signature counts")
    ap.add_argument("--rules", action="append",
                    help="rule file to check signatures against (repeatable)")
    ap.add_argument("--skip", action="append",
                    help="extra directory name to skip (repeatable); node_modules, .git, "
                         "_archive and .claude/worktrees are always skipped")
    ap.add_argument("--max-chars", type=int, default=420,
                    help="passage length in the digest (default 420)")
    ap.add_argument("--stdout", action="store_true", help="print instead of writing a file")
    ap.add_argument("--force", action="store_true", help="overwrite today's digest")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    today = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    skip_dirs = DEFAULT_SKIP_DIRS | set(args.skip or [])

    paths = find_making_ofs(root, skip_dirs, DEFAULT_SKIP_PATHS)
    if not paths:
        sys.exit(f"no making-of files under {root}")
    files, passages, args.titles = {}, [], {}
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as fh:
            files[path] = fh.read().splitlines()
        title, ps = parse_file(path, root, today)
        args.titles[os.path.relpath(path, root)] = title
        passages.extend(ps)

    sig_rows = parse_signatures(args.signatures) if args.signatures else None
    if args.signatures and not sig_rows:
        sys.exit(f"no signature rows could be read from {args.signatures}")
    rule_texts = {}
    for r in args.rules or []:
        with open(r, encoding="utf-8", errors="replace") as fh:
            rule_texts[r] = fh.read()

    prev = previous_digest(args.out_dir, today)
    digest = render(args, root, files, passages, today, prev, sig_rows, rule_texts)

    if args.stdout:
        sys.stdout.write(digest)
        return
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, f"{DIGEST_PREFIX}{today.isoformat()}.md")
    if os.path.exists(out) and not args.force:
        sys.exit(f"{out} exists; pass --force to overwrite")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(digest)
    new_note = "" if prev is None else f", previous: {os.path.basename(prev[0])}"
    print(f"{out}: {len(passages)} passages from {len(paths)} files{new_note}")


if __name__ == "__main__":
    main()
