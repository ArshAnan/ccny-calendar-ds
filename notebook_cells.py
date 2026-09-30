from build_notebook import md, code

CELLS = [
    md("""\
# CCNY Fall 2021 Academic Calendar Scraper

**Lab exercise.** Scrape the CCNY Registrar's
[Fall 2021 Academic Calendar](https://www.ccny.cuny.edu/registrar/fall) page using
`requests` and `BeautifulSoup`, then load the parsed calendar into a `pandas`
DataFrame:

- **index** — a Python `date` for each calendar entry
- **`dow`** — the day of the week for that date
- **`text`** — the explanation / event text for that date

If a calendar entry spans a range of dates (e.g. "August 25 - 31"), it is
expanded into one row per date in the range, each carrying the same `text`.

## A note on the data source

Two things have changed since this assignment was written, and the fetch cell
below handles both:

1. `www.ccny.cuny.edu` now sits behind a Cloudflare JavaScript challenge. It
   answers a plain `requests.get` with **HTTP 403** (`cf-mitigated: challenge`),
   and no amount of header spoofing gets around it, because passing the
   challenge requires executing JavaScript.
2. That URL is not versioned by semester — it serves whichever fall calendar is
   current. Scraping it today would return the *wrong term*, not Fall 2021.

So the notebook tries the live URL first (as the exercise specifies), then falls
back to a **Wayback Machine snapshot of the Fall 2021 page** taken 2021-12-05.
That is still a real `requests` fetch over the network, and it returns the
authentic Fall 2021 calendar. A local copy of the table is the last resort so
the notebook runs offline too.
"""),
    code("""\
import re
from datetime import date, datetime, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup
"""),
    code("""\
LIVE_URL = "https://www.ccny.cuny.edu/registrar/fall"
# "id_" asks the Wayback Machine for the original bytes, without its own banner.
ARCHIVE_URL = (
    "https://web.archive.org/web/20211205212206id_/"
    "https://www.ccny.cuny.edu/registrar/fall"
)
CACHE_PATH = "data/ccny_fall2021_table.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CCNY-Calendar-Scraper/1.0)"}


def fetch(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


html = source = None
for label, url in [("live page", LIVE_URL), ("Wayback snapshot", ARCHIVE_URL)]:
    try:
        html = fetch(url)
        source = label
        print(f"Fetched {label}: {len(html):,} characters")
        break
    except Exception as exc:
        print(f"{label} unavailable: {exc}")

if html is None:
    with open(CACHE_PATH, encoding="utf-8") as f:
        html = f.read()
    source = "local cache"
    print(f"Loaded {source}: {len(html):,} characters")

print(f"\\n--> parsing from: {source}")
"""),
    code("""\
soup = BeautifulSoup(html, "html.parser")

# Locate the calendar table by its "DATES" column header rather than by a
# positional index, since the header text is stable even when the page layout
# around the table changes.
dates_header = soup.find("th", string=lambda s: s and s.strip() == "DATES")
calendar_table = dates_header.find_parent("table")

rows = calendar_table.find("tbody").find_all("tr")
print(f"Found {len(rows)} calendar rows")
"""),
    md("""\
## Parsing the date column

The `DATES` column mixes a few formats:

- a single date with no year, e.g. `August 01` (year defaults to 2021)
- a single date with an explicit year, e.g. `January 1, 2022`
- a date **range** within the same month, e.g. `August 25 - 31`

`parse_date_str` below turns any of these into a list of one or more
`datetime.date` objects, and raises on anything it does not recognise so that a
future change to the page's formatting fails loudly instead of silently
dropping rows.
"""),
    code("""\
def parse_date_str(raw, default_year=2021):
    s = raw.replace("\\xa0", " ").strip()

    # e.g. "January 1, 2022" -- single date, explicit year
    m = re.match(r"^([A-Za-z]+)\\s+(\\d{1,2}),\\s*(\\d{4})$", s)
    if m:
        month, day, year = m.groups()
        return [datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date()]

    # e.g. "August 25 - 31" -- range within the same month
    m = re.match(r"^([A-Za-z]+)\\s+(\\d{1,2})\\s*-\\s*(\\d{1,2})$", s)
    if m:
        month, day_start, day_end = m.groups()
        start = datetime.strptime(f"{month} {day_start} {default_year}", "%B %d %Y").date()
        end = datetime.strptime(f"{month} {day_end} {default_year}", "%B %d %Y").date()
        return [start + timedelta(days=i) for i in range((end - start).days + 1)]

    # e.g. "August 01" -- single date, default year
    m = re.match(r"^([A-Za-z]+)\\s+(\\d{1,2})$", s)
    if m:
        month, day = m.groups()
        return [datetime.strptime(f"{month} {day} {default_year}", "%B %d %Y").date()]

    raise ValueError(f"Unrecognized date format: {s!r}")


# quick check on the three shapes we expect to see
for sample in ["August 01", "August 25 - 31", "January 1, 2022"]:
    print(sample, "->", parse_date_str(sample))
"""),
    code("""\
records = []
for row in rows:
    cells = row.find_all("td")
    if len(cells) < 3:
        continue
    date_str = cells[0].get_text(" ", strip=True)
    # The third column holds the explanation; its lines are separated by <br>,
    # so join the stripped strings rather than taking raw text.
    text = " ".join(cells[2].stripped_strings)
    days_col = cells[1].get_text(" ", strip=True)

    for d in parse_date_str(date_str):
        records.append(
            {"date": d, "dow": d.strftime("%A"), "text": text, "_days_col": days_col}
        )

print(f"Expanded {len(rows)} rows into {len(records)} date entries")
"""),
    md("""\
## Validating `dow` against the page itself

The page has its own `DAYS` column, which the scraper does not use — `dow` is
computed from the parsed date. That makes `DAYS` a free answer key: for every
single-date row the computed weekday must equal what the page says, and for
every range row the page's `"Wednesday - Tuesday"` must match the weekdays of
the first and last date in the expanded range.
"""),
    code("""\
checked = mismatches = 0
for row in rows:
    cells = row.find_all("td")
    if len(cells) < 3:
        continue
    dates = parse_date_str(cells[0].get_text(" ", strip=True))
    page_days = cells[1].get_text(" ", strip=True).replace("\\xa0", " ").strip()

    if "-" in page_days:
        computed = f"{dates[0].strftime('%A')} - {dates[-1].strftime('%A')}"
    else:
        computed = dates[0].strftime("%A")

    checked += 1
    if computed != page_days:
        mismatches += 1
        print(f"MISMATCH {cells[0].get_text(' ', strip=True)!r}: "
              f"page={page_days!r} computed={computed!r}")

print(f"Checked {checked} rows against the page's own DAYS column; "
      f"{mismatches} mismatches")
assert mismatches == 0, "computed dow disagrees with the page's DAYS column"
"""),
    code("""\
calendar_df = pd.DataFrame.from_records(records).drop(columns="_days_col")
calendar_df = calendar_df.set_index("date").sort_index()
calendar_df.index.name = "date"

calendar_df.head(10)
"""),
    code("""\
calendar_df.tail(10)
"""),
    md("""\
## Sanity checks

- the index must be made of plain Python `date` objects (not `Timestamp`)
- `dow` must agree with what the date actually falls on
- the calendar should span August 2021 through January 2022

Note that the index is deliberately **not unique**: a single day can carry more
than one calendar entry (for instance August 25 is both "Classes begin" and the
first day of the "Change of program period" range). Each `(date, text)` pair is
unique, and the check below confirms it.
"""),
    code("""\
print("index dtype:", calendar_df.index.dtype)
print("index element type:", type(calendar_df.index[0]))
assert all(isinstance(d, date) for d in calendar_df.index), "index must be python date objects"
assert not isinstance(calendar_df.index, pd.DatetimeIndex), "index must not be a DatetimeIndex"
assert all(
    d.strftime("%A") == dow for d, dow in zip(calendar_df.index, calendar_df["dow"])
), "dow mismatch"
assert list(calendar_df.columns) == ["dow", "text"], "expected exactly dow + text columns"
assert not calendar_df.reset_index().duplicated(["date", "text"]).any(), "duplicate (date, text)"

print("rows:", len(calendar_df))
print("unique dates:", calendar_df.index.nunique())
print("date range:", calendar_df.index.min(), "to", calendar_df.index.max())
calendar_df["dow"].value_counts()
"""),
    code("""\
# A date carrying more than one entry, e.g. the start of the term:
calendar_df.loc[date(2021, 8, 25)]
"""),
    md("""\
## Done

`calendar_df` is indexed by Python `date`, with `dow` (day of week) and `text`
(event description) columns, expanded so that multi-day entries in the source
calendar get one row per date. Every `dow` value has been cross-checked against
the `DAYS` column published on the page itself.
"""),
]
