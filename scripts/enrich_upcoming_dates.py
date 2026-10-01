#!/usr/bin/env python3
"""Fill a 'deadline' field for upcoming IPOs.

Many pipeline IPOs have no announced open/close dates yet. Their source article
(e.g. ipocentral.in) does publish a SEBI *approval-lapsing* deadline for them.
This script reads each upcoming entry's own source_url, extracts that date, and
stores it as `deadline` so the terminal can show "Expected by <date>".

Safe by design: it never invents a date, only copies one it can actually parse,
and it leaves the files untouched when nothing changed.
"""
import json
import pathlib
import re
import urllib.request

FILES = ["data/ipos.json", "data/ipo-data.json"]
UA = {"User-Agent": "Mozilla/5.0 (compatible; ipobodh-deadlines/1.0)"}
MONTHS = {m: i + 1 for i, m in enumerate([
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"])}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def to_text(html):
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    html = re.sub(r"(?s)<[^>]+>", "\n", html)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&#8217;", "'"), ("&#8211;", "-")):
        html = html.replace(a, b)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{2,}", "\n", html))


def parse_deadline(text, name):
    """Find '<name>' then the nearest 'Approval Lapsing: <date>' after it."""
    return extract_deadlines(text, [name]).get(name)


def extract_deadlines(text, names):
    """Map each company to its own 'Approval Lapsing' date.

    Each company's block ends where the next company's block begins, so one
    company can never borrow the next company's deadline.
    """
    out = {}
    if not text:
        return out
    pos = []
    for n in names:
        if not n:
            continue
        i = text.lower().find(n.lower())
        if i >= 0:
            pos.append((i, n))
    pos.sort()
    for idx, (i, name) in enumerate(pos):
        end = pos[idx + 1][0] if idx + 1 < len(pos) else len(text)
        m = re.search(r"Approval Lapsing:\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text[i:end])
        if not m:
            continue
        day, mon, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        if mon in MONTHS and 1 <= day <= 31:
            out[name] = "%04d-%02d-%02d" % (year, MONTHS[mon], day)
    return out


def main():
    cache, total = {}, 0
    for path in FILES:
        f = pathlib.Path(path)
        if not f.exists():
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else data.get("ipos", [])
        # every upcoming name on the page, so each block can be bounded
        names = [str(x.get("name") or "") for x in rows
                 if str(x.get("status", "")).lower() == "upcoming"]
        changed = False
        for x in rows:
            if str(x.get("status", "")).lower() != "upcoming":
                continue
            if x.get("open_date") and x.get("close_date"):
                continue                       # dates already known
            url = str(x.get("source_url") or "")
            if not url.startswith("http"):
                continue
            if url not in cache:
                try:
                    cache[url] = to_text(fetch(url))
                except Exception:
                    cache[url] = ""
            dl = extract_deadlines(cache[url], names).get(str(x.get("name") or ""))
            if dl and x.get("deadline") != dl:
                x["deadline"] = dl
                changed = True
                total += 1
        if changed:
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("deadlines updated:", total)


if __name__ == "__main__":
    main()
