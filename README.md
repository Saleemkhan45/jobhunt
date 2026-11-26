# JobHunt: Job & Internship Aggregator for CS Students

A command-line tool that searches **three job boards at the same time**, cleans and
validates the results, removes duplicates, and lets you **track every application**
from "saved" to "selected".

## The problem

CS students looking for jobs or internships open Arbeitnow, Remotive, Himalayas and
several other sites one by one, see the same posting several times, and keep track of
applications in their heads or a messy notes file.

**JobHunt** lets you search once and get one clean, de-duplicated list, newest first.
It also keeps your application pipeline in one place.

## Features

- **One search, three boards**: Arbeitnow, Remotive and Himalayas are queried
  concurrently (free public APIs, no API key needed)
- **Filters**: keyword, location, remote only, job type (internship, full time...), max age in days
- **De-duplication**: the same role posted on two boards shows up once
- **Validation**: broken listings (bad URL, missing title) are skipped and counted, so they never crash the app
- **Resilient**: retries with backoff, per-board rate limiting, and if one board is down the others still answer
- **Application tracker**: save a job and move it through `saved → applied → interview → offer → selected / rejected`, with notes and full history. Invalid moves (e.g. rejected → interview) are blocked
- **Reports**: counts by status and source, plus your interview rate, exportable to JSON
- **Offline mode**: `--offline` runs on bundled sample data, so you can demo it without internet

## Demo

```text
$ jobhunt --offline search python --limit 4
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━┓
┃ # ┃ Title                        ┃ Company       ┃ Location               ┃ Type       ┃   Age ┃ Source    ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━┩
│ 1 │ Junior Full Stack Developer  │ Brightloop    │ Worldwide              │ full time  │ today │ remotive  │
│ 2 │ Junior Python Developer      │ Datawerk GmbH │ Berlin                 │ full time  │    1d │ arbeitnow │
│ 3 │ Python Developer — APIs &    │ Lemonade Labs │ Pakistan, India,       │ full time  │    1d │ himalayas │
│ 4 │ Working Student Software     │ Nordlicht AI  │ Hamburg                │ internship │    2d │ arbeitnow │
└───┴──────────────────────────────┴───────────────┴────────────────────────┴────────────┴───────┴───────────┘
Fetched per board → arbeitnow: 7, remotive: 5, himalayas: 4. 13 keyword matches, 4 shown after
filters and de-duplication.

$ jobhunt update 2b6ae8 interview --note "Tech round Friday"
✓ Python Developer — APIs & Automation → interview

$ jobhunt update 2b6ae8 applied
Error: cannot move from 'interview' to 'applied' (allowed: rejected, selected, offer)
```

## Setup

Requires **Python 3.10+**.

```bash
git clone https://github.com/Saleemkhan45/jobhunt.git
cd jobhunt

# 1. create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. install the app (gives you the `jobhunt` command) and dev tools
pip install -e ".[dev]"            # or: pip install -r requirements.txt
```

## Usage

```bash
jobhunt search python                          # all boards, live
jobhunt search react --remote --limit 10       # remote only
jobhunt search intern -t internship -d 14      # internships from the last 14 days
jobhunt search django -l berlin -s arbeitnow,remotive
jobhunt --offline search python                # no internet needed

jobhunt show 3                                 # details of result #3
jobhunt save 3                                 # start tracking it
jobhunt list                                   # your applications
jobhunt update a1b2c3 applied
jobhunt update a1b2c3 interview --note "Tech round Friday 3pm"
jobhunt list --status interview
jobhunt report --export                        # writes data/report.json
jobhunt -v search python                       # show timing / retry logs
jobhunt sources                                # supported boards
```

Without installing, `python -m jobhunt ...` works the same way.

## Run the tests

```bash
pytest -v
```

26 tests cover validation, de-duplication, filters, sorting, concurrency, retry on
network failure, a board going down, the tracker's status rules, and the CLI end to end.

## Project structure

```text
jobhunt/
├── jobhunt/
│   ├── cli.py            # argparse commands + rich terminal output
│   ├── aggregator.py     # runs all boards concurrently with asyncio.gather
│   ├── models.py         # Pydantic models: Job, SearchQuery, Application
│   ├── pipeline.py       # generator pipeline: filter → dedupe → limit
│   ├── decorators.py     # @timer, @log_call, @retry, @rate_limit
│   ├── tracker.py        # ApplicationTracker with status rules
│   ├── storage.py        # JSON persistence (atomic writes)
│   ├── config.py         # settings from environment variables
│   └── sources/
│       ├── base.py       # abstract JobSource class
│       └── boards.py     # Arbeitnow, Remotive, Himalayas subclasses
├── data/samples/         # sample API responses for offline mode and tests
├── tests/
├── pyproject.toml
└── requirements.txt
```

## Where each course concept is used

| Concept | Where | How |
|---|---|---|
| **Abstraction** | `sources/base.py` | `JobSource` is an `ABC` with abstract `build_params`, `extract_items`, `to_job` |
| **Inheritance** | `sources/boards.py` | `ArbeitnowSource`, `RemotiveSource`, `HimalayasSource` extend `JobSource` and reuse fetching, retry, validation and offline mode |
| **Polymorphism** | `aggregator.py` | calls `source.fetch(query)` on every board; each parses its own JSON format |
| **Encapsulation** | `tracker.py`, `base.py` | private `_apps` dict changed only through `update_status()`, which enforces the rules; `stats` is a read-only property |
| **Async programming** | `aggregator.py`, `base.py` | `aiohttp.ClientSession` + `asyncio.gather(..., return_exceptions=True)`; per-board `asyncio.Lock` for rate limiting; an async generator `stream()` |
| **API handling** | `sources/boards.py` | 3 real REST APIs, query params, timeouts, HTTP 429 handling, `raise_for_status` |
| **JSON** | `storage.py`, `data/samples/` | parsing API responses, saving results and tracker, exporting reports; writes are atomic (temp file + rename) |
| **Decorators** | `decorators.py` | `@timer`, `@log_call`, `@retry(attempts, base_delay)` (a decorator factory with exponential backoff), `@rate_limit`; all work for sync and async functions |
| **Generators** | `pipeline.py`, `JobSource.parse`, `tracker.iter_by_status` | lazy chain `keyword → location → remote → type → age → dedupe → take`; `take()` stops upstream as soon as it has enough |
| **Pydantic** | `models.py`, `config.py` | `field_validator` (strip HTML, parse unix/ISO dates, clean tags), `model_validator`, `computed_field` fingerprint, `HttpUrl`, `Field` limits, enums, `TypeAdapter` for JSON |
| **Virtual environment** | Setup | `python -m venv .venv`, `pyproject.toml` with a console script |
| **GitHub** | repo | `.gitignore` keeps `.venv` and personal data out; sample data and tests are committed |

## Design decisions

- **Keyless APIs only**, so anyone can clone and run it in one minute.
- **Bad data is skipped, not fatal.** Real APIs return broken listings; each source counts them (`stats["skipped"]`).
- **De-dup by fingerprint**: a hash of the normalised title (with "(m/f/d)" etc. removed) and company.
- **Status rules live in data** (`ALLOWED_TRANSITIONS`), not scattered `if` statements.

## Future improvements

- Add more boards (Jobicy, RemoteOK) by writing one subclass each
- A Streamlit dashboard on top of `aggregator.py`
- Email or Telegram alerts for new matches (scheduled search)
- SQLite instead of JSON once the tracker grows
