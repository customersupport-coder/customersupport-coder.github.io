# customersupport-coder.github.io
LACE — Naples Running Network. Source for https://lacenapoli.com (GitHub Pages).

## Pages

| File | What it is |
|---|---|
| `index.html` | Home page: schedule, membership, private runs |
| `brands.html` | Brand collaborations |
| `road-to-hyrox.html` | HYROX training blocks |
| `contact.html`, `privacy.html`, `terms.html` | Legal pages (English only) |
| `404.html` | Page-not-found page |
| `consent.js` | Cookie banner. Google Analytics loads only after the visitor accepts |
| `it/` | Italian copies of the three main pages. **Generated, never edit by hand** |

## Rule for every edit

After any change to `index.html`, `brands.html` or `road-to-hyrox.html`, rebuild the Italian pages and commit them in the same push:

```
python3 tools/build_it.py
```

`python3 tools/build_it.py --check` exits with an error if the Italian pages are out of date.

Italian text for the home page lives in the `I18N` table inside `index.html`. Italian text for the other two pages lives in the `data-it` spans next to each `data-en` span.

## Schedule

Each run is one `.sched-row` in `index.html` with `data-start` (Naples time) and `data-luma` (the RSVP link). The countdown, the RSVP bar and the hiding of past runs all read those rows.
