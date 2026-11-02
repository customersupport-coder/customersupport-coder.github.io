#!/usr/bin/env python3
"""Copy the run schedule from index.html into everything that repeats it.

    python3 tools/sync_schedule.py           update the files
    python3 tools/sync_schedule.py --check   exit 1 if any file is out of date

The .sched-row elements in index.html are the only place a run is written down.
This script reads them and writes, as plain HTML that search engines can read
without running JavaScript:

  index.html     the event data for Google (SportsEvent JSON-LD) and the
                 "Next run" line in the hero
  napoli.html    the list of upcoming Napoli runs, its event data and the RSVP
  caserta.html   button in the top bar, same for Caserta

Run it after every schedule change, then run tools/build_it.py so the Italian
home page picks up the same changes. Standard library only.
"""
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://lacenapoli.com"
ROME = ZoneInfo("Europe/Rome")
LUMA_ALL = "https://luma.com/user/lacenapoli"
DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS_IT = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
MONTHS_IT = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
WHERE_IT = {"Villa Floridiana gates": "Cancelli della Villa Floridiana"}  # English place words on the Italian city pages
KEEP_AFTER_START = timedelta(hours=3)  # same as the page: a run stays listed for 3h after it starts

ROW_RE = re.compile(r'<div class="sched-row[^"]*"([^>]*)>(.*?)\n    </div>', re.S)


def attr(attrs, name):
    m = re.search(name + r'="([^"]*)"', attrs)
    return html.unescape(m.group(1)) if m else ""


def text_of(body, cls):
    m = re.search(r'<div class="' + cls + r'"([^>]*)>(.*?)</div>', body, re.S)
    if not m:
        return "", ""
    key = attr(m.group(1), "data-i18n")
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip(), key


def italian_strings(src):
    """key -> Italian text, from the it: block of the I18N table."""
    start = src.index("\nit: {")
    end = src.index("\n};", start)
    out = {}
    for k, v in re.findall(r'(\w+):"((?:[^"\\]|\\.)*)"', src[start:end]):
        out[k] = v.replace('\\"', '"')
    return out


def read_runs(src):
    it = italian_strings(src)
    runs = []
    for m in ROW_RE.finditer(src):
        attrs, body = m.group(1), m.group(2)
        start = attr(attrs, "data-start")
        if not start:
            continue
        title, key = text_of(body, "sched-title")
        city, _ = text_of(body, "sched-city")
        at = datetime.strptime(start, "%Y-%m-%dT%H:%M").replace(tzinfo=ROME)
        runs.append({
            "at": at,
            "url": attr(attrs, "data-luma"),
            "title": title,
            "title_it": it.get(key, title),
            "where": city,
            "city": "caserta" if re.search(r"caserta", city, re.I) else "napoli",
        })
    runs.sort(key=lambda r: r["at"])
    return runs


def upcoming(runs, now):
    return [r for r in runs if r["url"] and r["at"] + KEEP_AFTER_START > now]


def event_ld(runs):
    graph = []
    for r in runs:
        place = r["where"]
        locality = "Caserta" if r["city"] == "caserta" else "Napoli"
        graph.append({
            "@type": "SportsEvent",
            "name": "LACE " + r["title"],
            "startDate": r["at"].isoformat(),
            "endDate": (r["at"] + timedelta(minutes=90)).isoformat(),
            "eventStatus": "https://schema.org/EventScheduled",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "isAccessibleForFree": True,
            "url": r["url"],
            "image": SITE + "/og-image.jpg",
            "description": "Free group run with LACE. " + place + ". RSVP on Luma.",
            "location": {"@type": "Place", "name": place,
                         "address": {"@type": "PostalAddress", "streetAddress": place,
                                     "addressLocality": locality, "addressRegion": "Campania",
                                     "addressCountry": "IT"}},
            "organizer": {"@type": "SportsClub", "name": "LACE", "url": SITE + "/"},
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR",
                       "availability": "https://schema.org/InStock", "url": r["url"]},
        })
    if not graph:
        return "<!-- EVENTS:START -->\n<!-- EVENTS:END -->"
    body = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)
    return ('<!-- EVENTS:START -->\n<script type="application/ld+json">\n' + body +
            "\n</script>\n<!-- EVENTS:END -->")


def put(src, marker, block):
    pat = re.compile(r"[ \t]*<!-- " + marker + r":START -->.*?<!-- " + marker + r":END -->", re.S)
    if not pat.search(src):
        sys.exit("missing <!-- %s:START/END --> markers" % marker)
    indent = re.search(r"([ \t]*)<!-- " + marker + ":START", src).group(1)
    block = "\n".join(indent + line if line else line for line in block.split("\n"))
    return pat.sub(lambda _: block, src, count=1)


def label_en(r):
    d = r["at"]
    where = r["where"].split("·")[-1].strip()
    return "%s %d %s · %s — %s" % (DAYS_EN[d.weekday()], d.day, MONTHS_EN[d.month - 1], d.strftime("%H:%M"), where)


def runs_list(runs, city_name):
    if not runs:
        return ('<!-- RUNS:START -->\n<p class="runs-empty">Le nuove date escono prima su Luma. '
                '<a href="%s" target="_blank" rel="noopener">Guarda tutte le prossime corse →</a></p>\n'
                "<!-- RUNS:END -->" % LUMA_ALL)
    lines = ["<!-- RUNS:START -->", '<ul class="runs">']
    for r in runs:
        d = r["at"]
        where = r["where"]
        for en, it in WHERE_IT.items():
            where = where.replace(en, it)
        title = re.sub(r"\s*[—-]\s*" + city_name + r"$", "", r["title_it"], flags=re.I)
        lines += [
            '  <li class="run">',
            '    <div class="run-when"><b>%s %d %s</b>%s</div>' % (DAYS_IT[d.weekday()], d.day, MONTHS_IT[d.month - 1], d.strftime("%H:%M")),
            '    <div class="run-title">%s<span class="run-where">%s</span></div>' % (html.escape(title), html.escape(where)),
            '    <a class="btn is-blue" href="%s" target="_blank" rel="noopener">RSVP →</a>' % html.escape(r["url"]),
            "  </li>",
        ]
    lines += ["</ul>", "<!-- RUNS:END -->"]
    return "\n".join(lines)


def update_index(src, runs):
    src = put(src, "EVENTS", event_ld(runs))
    nxt = runs[0] if runs else None
    label = label_en(nxt) if nxt else "Wednesdays · 20:00 — Vomero, Napoli"
    href = nxt["url"] if nxt else LUMA_ALL
    src = re.sub(r'(<span class="hn-when" id="hero-next-when">)[^<]*(</span>)', lambda m: m.group(1) + html.escape(label) + m.group(2), src, count=1)
    src = re.sub(r'(<a class="hero-next" id="hero-next" href=")[^"]*(")', lambda m: m.group(1) + href + m.group(2), src, count=1)
    src = re.sub(r'(<div class="clock-meta" id="clock-meta">)[^<]*(</div>)', lambda m: m.group(1) + html.escape(label) + m.group(2), src, count=1)
    return src


def update_city(src, runs, city_name):
    src = put(src, "EVENTS", event_ld(runs))
    src = put(src, "RUNS", runs_list(runs, city_name))
    href = runs[0]["url"] if runs else LUMA_ALL
    src = re.sub(r'(<a class="btn is-blue" id="next-rsvp" href=")[^"]*(")', lambda m: m.group(1) + href + m.group(2), src, count=1)
    return src


def main():
    check = "--check" in sys.argv
    now = datetime.now(ROME)
    path = os.path.join(ROOT, "index.html")
    index = open(path, encoding="utf-8").read()
    runs = upcoming(read_runs(index), now)
    jobs = [("index.html", lambda s: update_index(s, runs))]
    for slug, name in (("napoli", "Napoli"), ("caserta", "Caserta")):
        city_runs = [r for r in runs if r["city"] == slug]
        jobs.append((slug + ".html", lambda s, c=city_runs, n=name: update_city(s, c, n)))
    stale = []
    for name, fn in jobs:
        p = os.path.join(ROOT, name)
        old = open(p, encoding="utf-8").read()
        new = fn(old)
        if new != old:
            stale.append(name)
            if not check:
                open(p, "w", encoding="utf-8").write(new)
    print("%d upcoming runs (%s)" % (len(runs), ", ".join(r["at"].strftime("%d %b") for r in runs)))
    if check:
        if stale:
            sys.exit("out of date: " + ", ".join(stale) + " (run python3 tools/sync_schedule.py)")
        print("schedule copies are up to date.")
    else:
        print("written: " + (", ".join(stale) or "nothing changed"))


if __name__ == "__main__":
    main()
