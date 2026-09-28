# CCNY Fall 2021 Academic Calendar Scraper

Lab exercise: scrape the CCNY Registrar's [Fall 2021 Academic Calendar](https://www.ccny.cuny.edu/registrar/fall)
page with `requests` + `BeautifulSoup`, and load the result into a `pandas` DataFrame indexed by
Python `date`, with a `dow` (day of week) column and a `text` (explanation) column.

## Contents

- `ccny_calendar_scraper.ipynb` — the notebook (built up commit by commit).
- `data/ccny_fall2021_table.html` — a cached copy of the calendar table, fetched directly from the
  live page. The notebook tries the live URL first; if the network is unavailable it falls back to
  this cached copy so the notebook can still run end-to-end.

## Setup

```bash
pip install -r requirements.txt
jupyter notebook ccny_calendar_scraper.ipynb
```
