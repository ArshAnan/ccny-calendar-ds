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

> Note: this notebook was built and executed in a sandboxed environment with
> no general internet egress. The fetch cell below tries the **live** URL
> first; if that fails, it falls back to `data/ccny_fall2021_table.html`, a
> copy of the calendar table fetched directly from the live page moments
> before this notebook was run. On a normal machine with internet access,
> the live branch is what runs.
"""),
    code("""\
import re
from datetime import date, datetime, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup
"""),
    code("""\
URL = "https://www.ccny.cuny.edu/registrar/fall"
CACHE_PATH = "data/ccny_fall2021_table.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CCNY-Calendar-Scraper/1.0)"}

try:
    response = requests.get(URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    html = response.text
    print(f"Fetched live page: HTTP {response.status_code}, {len(html):,} characters")
except Exception as exc:
    print(f"Live request failed ({exc!r}); falling back to cached copy of the calendar table.")
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    print(f"Loaded cached table: {len(html):,} characters")
"""),
    code("""\
soup = BeautifulSoup(html, "html.parser")

# Locate the calendar table by its "DATES" column header, rather than a
# brittle index, since the header text is stable even if the page layout
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
`datetime.date` objects.
"""),
    code("""\
def parse_date_str(raw, default_year=2021):
    s = raw.replace("\\xa0", " ").strip()

    # e.g. "January 1, 2022" -- single date, explicit year
    m = re.match(r"^([A-Za-z]+)\\s+(\\d{1,2}),\\s*(\\d{4})$", s)
    if m:
        month, day, year = m.groups()
        d = datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date()
        return [d]

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
        d = datetime.strptime(f"{month} {day} {default_year}", "%B %d %Y").date()
        return [d]

    raise ValueError(f"Unrecognized date format: {s!r}")


# quick sanity check on the three shapes we expect to see
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
    text = " ".join(cells[2].stripped_strings)

    for d in parse_date_str(date_str):
        records.append({"date": d, "dow": d.strftime("%A"), "text": text})

print(f"Expanded {len(rows)} rows into {len(records)} date entries")
"""),
    code("""\
calendar_df = pd.DataFrame.from_records(records)
calendar_df = calendar_df.set_index("date").sort_index()
calendar_df.index.name = "date"

calendar_df.head(10)
"""),
    code("""\
calendar_df.tail(10)
"""),
    md("""\
## Sanity checks

- the index should be made of plain Python `date` objects (not `Timestamp`)
- `dow` should agree with what the date actually falls on
- the calendar should span August 2021 through January 2022
"""),
    code("""\
print("index dtype:", calendar_df.index.dtype)
print("index element type:", type(calendar_df.index[0]))
assert all(isinstance(d, date) for d in calendar_df.index), "index must be python date objects"
assert all(d.strftime("%A") == dow for d, dow in zip(calendar_df.index, calendar_df["dow"])), "dow mismatch"

print("rows:", len(calendar_df))
print("date range:", calendar_df.index.min(), "to", calendar_df.index.max())
calendar_df["dow"].value_counts()
"""),
    md("""\
## Done

`calendar_df` is indexed by Python `date`, with `dow` (day of week) and
`text` (event description) columns, expanded so that multi-day entries in
the source calendar get one row per date.
"""),
]
