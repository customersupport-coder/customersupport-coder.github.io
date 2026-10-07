#!/usr/bin/env python3
"""Build the Italian twins of the main pages.

    python3 tools/build_it.py           write it/index.html, it/brands.html, it/road-to-hyrox.html
    python3 tools/build_it.py --check   exit 1 if the files on disk are out of date

Why: the English pages switch language in the browser, so search engines only
ever read the English text. This script writes a static Italian copy of each
page under /it/ that opens in Italian for everyone.

The English pages are the only source. Never edit anything under /it/ by hand:
edit index.html, brands.html or road-to-hyrox.html, then run this script and
commit the result. No dependencies beyond the Python standard library.
"""
import html
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://lacenapoli.com"
MONTHS_IT = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
TWINS = ("brands.html", "road-to-hyrox.html")  # pages that exist under /it/ besides the home page

PAGES = {
    "index.html": {
        "out": "it/index.html",
        "url": SITE + "/it/",
        "title": "LACE — Running club a Napoli, Caserta, Milano e Salerno",
        "description": "LACE è un network di running nato nelle strade di Napoli. Corse settimanali gratuite a Napoli, Caserta, Milano e Salerno. Membership Laced In limitata a 100 posti, aperta a Napoli, Caserta e Milano.",
        "og_description": "Un network di running nato nelle strade di Napoli. Oltre 3.000 runner in quattro città. Le corse settimanali sono gratuite e aperte a tutti. Laced In è limitata a 100 posti, aperta a Napoli, Caserta e Milano.",
        "twitter_description": "Corse settimanali gratuite a Napoli, Caserta, Milano e Salerno. Laced In limitata a 100 posti, aperta a Napoli, Caserta e Milano.",
    },
    "brands.html": {
        "out": "it/brands.html",
        "url": SITE + "/it/brands.html",
        "title": "Collaborazioni con i brand | LACE",
        "description": "Lavora con LACE, il network di running di Napoli, Caserta, Milano e Salerno. Shoe test, serate di lancio, weekend di gara e shooting con una community di oltre 3.000 runner.",
        "og_description": "Shoe test, serate di lancio, weekend di gara e shooting con una community di running di oltre 3.000 persone in quattro città italiane.",
    },
    "road-to-hyrox.html": {
        "out": "it/road-to-hyrox.html",
        "url": SITE + "/it/road-to-hyrox.html",
        "title": "Road to HYROX Milano | LACE",
        "description": "Dodici settimane di preparazione HYROX con coach, organizzate da LACE a Napoli. Il blocco per Milano è in corso. Entra in lista d'attesa per il prossimo.",
        "og_description": "Gli 8 km li corri già. Ora corrili con la slitta in mezzo. Blocchi di preparazione gara con coach a Napoli.",
    },
}

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


# ---------------------------------------------------------------- I18N table
def js_string(tok):
    """Decode one JS string literal ("..." or '...') to a Python str."""
    body = tok[1:-1]
    if tok[0] == "'":
        body = body.replace("\\'", "'")
        body = re.sub(r'(?<!\\)"', '\\"', body)
    else:
        body = body.replace("\\'", "'")
    return json.loads('"' + body + '"')


def read_it_strings(src):
    """Pull the `it:{...}` block out of `const I18N = {...}` in index.html."""
    start = src.index("const I18N")
    m = re.search(r"\n\s*it\s*:\s*\{", src[start:])
    if not m:
        raise SystemExit("build_it: could not find the it:{ block in I18N")
    i = start + m.end()
    depth, j, quote = 1, i, None
    while depth:
        c = src[j]
        if quote:
            if c == "\\":
                j += 1
            elif c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        j += 1
    block = src[i:j - 1]
    out = {}
    for k, v in re.findall(r"""(\w+)\s*:\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')""", block):
        out[k] = js_string(v)
    return out


# ------------------------------------------------------- static text swapping
class Locator(HTMLParser):
    """Find the inner-content span of every element whose text must change."""

    def __init__(self, src, strings):
        super().__init__(convert_charrefs=False)
        self.src, self.strings = src, strings
        self.line_starts = [0]
        for line in src.split("\n"):
            self.line_starts.append(self.line_starts[-1] + len(line) + 1)
        self.stack = []      # (tag, replacement or None, content_start, is_ticker_track, row_start)
        self.edits = []      # (content_start, content_end, new_inner_html)
        self.missing = set()

    def abs_pos(self):
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        parent = self.stack[-1] if self.stack else None
        row_start = a.get("data-start") if "sched-row" in cls else (parent[4] if parent else None)
        new = None
        if tag == "span" and parent and parent[3] and "ticker" in self.strings:
            new = self.strings["ticker"]          # the ticker string carries its own <b> bullets
        elif "data-i18n" in a:
            k = a["data-i18n"]
            if k in self.strings:
                new = html.escape(self.strings[k], quote=False)
            else:
                self.missing.add(k)
        elif "data-i18n-html" in a:
            k = a["data-i18n-html"]
            if k in self.strings:
                new = self.strings[k]
            else:
                self.missing.add(k)
        elif "sched-date" in cls and row_start:
            m = re.match(r"\d{4}-(\d{2})-(\d{2})T", row_start)
            if m:
                new = "%d %s" % (int(m.group(2)), MONTHS_IT[int(m.group(1)) - 1])
        content_start = self.abs_pos() + len(self.get_starttag_text())
        self.stack.append((tag, new, content_start, "ticker-track" in cls, row_start))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                break
        else:
            return
        end = self.abs_pos()
        popped = self.stack[i:]
        del self.stack[i:]
        el = popped[0]
        if el[1] is not None:
            self.edits.append((el[2], end, el[1]))


def swap_static_text(src, strings):
    loc = Locator(src, strings)
    loc.feed(src)
    loc.close()
    # keep only outermost edits, then apply from the end backwards
    edits = sorted(loc.edits)
    kept, last_end = [], -1
    for s, e, new in edits:
        if s >= last_end:
            kept.append((s, e, new))
            last_end = e
    for s, e, new in reversed(kept):
        src = src[:s] + new + src[e:]
    return src, sorted(loc.missing), len(kept)


# ------------------------------------------------------------------- URLs
def fix_url(u):
    if not u or re.match(r"(?i)^(https?:|//|mailto:|tel:|#|data:|javascript:|sms:)", u):
        return u
    if not u.startswith("/"):
        u = "/" + u                      # the twin lives one folder down
    if u == "/" or u == "/index.html":
        return "/it/"
    if u.startswith("/#") or u.startswith("/?"):
        return "/it/" + u[1:]
    for twin in TWINS:
        if u == "/" + twin or u.startswith("/" + twin + "#") or u.startswith("/" + twin + "?"):
            return "/it" + u
    return u


def fix_urls(src):
    def one(m):
        return m.group(1) + fix_url(m.group(2))

    def srcset(m):
        parts = []
        for cand in m.group(2).split(","):
            bits = cand.strip().split(" ", 1)
            bits[0] = fix_url(bits[0])
            parts.append(" ".join(bits))
        return m.group(1) + ", ".join(parts)

    # works for real attributes and for markup held inside JS strings (\" quoted)
    src = re.sub(r"""(\b(?:href|src|poster|action)=\\?["'])([^"'\\\s>]+)""", one, src)
    src = re.sub(r"""(\bsrcset=\\?["'])([^"'\\>]+)""", srcset, src)
    return src


# ------------------------------------------------------------------- head
def set_meta(src, key, value):
    value = html.escape(value, quote=True)
    pat = re.compile(r'(<meta\s+(?:name|property)="%s"\s+content=")[^"]*(")' % re.escape(key))
    return pat.sub(lambda m: m.group(1) + value + m.group(2), src)


def fix_head(src, name, cfg):
    src = re.sub(r"<html lang=\"[a-z-]+\"", '<html lang="it"', src, count=1)
    src = re.sub(r"<title>.*?</title>", "<title>%s</title>" % html.escape(cfg["title"], quote=False), src, count=1, flags=re.S)
    src = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s">' % cfg["url"], src, count=1)
    src = set_meta(src, "description", cfg["description"])
    src = set_meta(src, "og:title", cfg["title"])
    src = set_meta(src, "og:description", cfg["og_description"])
    src = set_meta(src, "og:url", cfg["url"])
    src = set_meta(src, "og:locale", "it_IT")
    src = set_meta(src, "og:locale:alternate", "en_US")
    src = set_meta(src, "twitter:title", cfg["title"])
    if "twitter_description" in cfg:
        src = set_meta(src, "twitter:description", cfg["twitter_description"])
    banner = ("<!-- GENERATED from /%s by tools/build_it.py. Do not edit this file: "
              "edit the English page, then run the script. -->\n" % name)
    force = '<script>window.LACE_PAGE_LANG="it";</script>\n'
    m = re.search(r"<meta charset=[^>]*>\n", src)
    if not m:
        raise SystemExit("build_it: no <meta charset> in " + name)
    src = src[:m.end()] + force + src[m.end():]
    return src.replace("<!DOCTYPE html>\n", "<!DOCTYPE html>\n" + banner, 1)


# ------------------------------------------------------------------- main
def build():
    out = {}
    notes = []
    for name, cfg in PAGES.items():
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            src = f.read()
        if name == "index.html":
            strings = read_it_strings(src)
            src, missing, n = swap_static_text(src, strings)
            notes.append("%s: %d Italian strings read, %d text blocks swapped" % (name, len(strings), n))
            if missing:
                notes.append("%s: WARNING no Italian string for: %s" % (name, ", ".join(missing)))
        src = fix_urls(src)
        src = fix_head(src, name, cfg)
        out[cfg["out"]] = src
    return out, notes


def main():
    check = "--check" in sys.argv
    out, notes = build()
    stale = []
    for rel, text in out.items():
        path = os.path.join(ROOT, rel)
        old = None
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                old = f.read()
        if old != text:
            stale.append(rel)
            if not check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
    for n in notes:
        print(n)
    if check:
        if stale:
            print("OUT OF DATE: " + ", ".join(stale) + "  (run: python3 tools/build_it.py)")
            sys.exit(1)
        print("Italian pages are up to date.")
    else:
        print("written: " + (", ".join(stale) if stale else "nothing changed"))


if __name__ == "__main__":
    main()
