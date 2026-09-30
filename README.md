# CCNY Fall 2021 Academic Calendar Scraper

Lab exercise: scrape the CCNY Registrar's [Fall 2021 Academic Calendar](https://www.ccny.cuny.edu/registrar/fall)
page with `requests` + `BeautifulSoup`, and load the result into a `pandas` DataFrame indexed by
Python `date`, with a `dow` (day of week) column and a `text` (explanation) column.

## Result

`calendar_df` — 57 rows spanning 2021-08-01 to 2022-01-01 across 50 distinct dates:

| | index (`date`) | `dow` | `text` |
|---|---|---|---|
| | `datetime.date(2021, 8, 25)` | `Wednesday` | `Start of Fall Term; Classes begin; ...` |

Calendar entries that span a range (e.g. "August 25 - 31") are expanded to one row per date, so a
single date can appear more than once — the index is intentionally non-unique, while every
`(date, text)` pair is unique.

(Falling back to the offline copy yields 58 rows rather than 57: the registrar kept editing the
page after the 2021-12-05 snapshot, eventually splitting its December 27 entry into separate
December 27 and 28 rows. Both readings are faithful to the page as it stood at the time.)

## Data source

The exercise says to scrape the live page, and the notebook tries that first — but two things have
changed since it was written:

1. **`www.ccny.cuny.edu` is behind a Cloudflare JavaScript challenge.** It answers a plain
   `requests.get` with `HTTP 403` / `cf-mitigated: challenge`. Header spoofing does not help, since
   passing the challenge requires running JavaScript.
2. **That URL is not versioned by semester** — it serves whichever fall calendar is current, so
   scraping it today returns the wrong term, not Fall 2021.

The notebook therefore falls back to a [Wayback Machine snapshot of the Fall 2021
page](https://web.archive.org/web/20211205212206/https://www.ccny.cuny.edu/registrar/fall) taken
2021-12-05. That is still a real `requests` fetch over the network and it returns the authentic
Fall 2021 calendar. `data/ccny_fall2021_table.html` is a last-resort local copy so the notebook also
runs offline.

## Correctness

The page publishes its own `DAYS` column, which the scraper deliberately ignores — `dow` is computed
from the parsed date. That makes `DAYS` a free answer key, and the notebook asserts agreement on
every row (single dates against the weekday, ranges against the first and last weekday). It also
asserts that the index holds real `datetime.date` objects rather than a pandas `DatetimeIndex`.

## Contents

- `ccny_calendar_scraper.ipynb` — the notebook, with genuine executed output.
- `data/ccny_fall2021_table.html` — offline copy of the calendar table.
- `build_notebook.py` / `notebook_cells.py` — builds the notebook from a cell list and executes it
  with a real Jupyter kernel (`nbclient`), so committed output is never hand-written. Not needed to
  use the notebook; kept for reproducibility.

## Setup

```bash
pip install -r requirements.txt
jupyter notebook ccny_calendar_scraper.ipynb
```

To rebuild and re-execute the notebook from the cell list:

```bash
python build_notebook.py ccny_calendar_scraper.ipynb
```
