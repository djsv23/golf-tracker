# Zebra Golf Tracker

A Flask app for tracking golf rounds, course data, and a World Handicap
System (WHS) handicap index.

## Features

- Course and tee-set management, with hole-by-hole par and stroke index
- Hole-by-hole round entry (strokes, putts, fairways hit, greens in regulation)
- WHS handicap index (best 8 of the last 20 rounds) and net-double-bogey
  adjusted scoring, recalculated automatically as rounds are recorded
- A dashboard with scoring trend and score distribution charts
- Optional course import from [golfcourseapi.com](https://golfcourseapi.com)

## Setup

Requires Python 3.11+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # includes requirements.txt + test deps
```

Create a `.env` file (or export the variables another way) for local
development:

```bash
SECRET_KEY=some-random-value       # required outside debug mode
DATABASE_URL=sqlite:///golf_scores.db   # optional, this is the default
```

Apply the database schema:

```bash
.venv/bin/flask db upgrade
```

Load a few real courses (Pinehurst No. 2, Pebble Beach, Bethpage Black) so
there's something to record rounds against:

```bash
.venv/bin/flask seed-courses
```

Run the dev server:

```bash
.venv/bin/flask run
```

## Running tests

```bash
.venv/bin/pytest
```

The suite runs entirely against an in-memory SQLite database and never
makes a network call — the `golfcourseapi.com` adapter is tested against
recorded fixtures in `tests/fixtures/golfcourseapi/`, not the live API.

## Enabling the course API

Course data can be entered by hand, loaded from `data/courses.yml`, or
imported from [golfcourseapi.com](https://golfcourseapi.com)'s free tier
(50 requests/day, read-only). To enable import, set:

```bash
GOLF_API_KEY=your-api-key-here
```

With no key set, the app falls back to a local provider that only
searches courses already in the database, and the "Import from API" link
is hidden. `flask check-course-api` probes the API's health endpoint
(no auth or quota needed) to confirm a key is working, and
`flask import-course <external_id>` imports a single course by id.

## Useful commands

| Command | Purpose |
|---|---|
| `flask db upgrade` | Apply pending migrations |
| `flask db migrate -m "..."` | Generate a new migration after a model change (review the generated file before applying — SQLite autogenerate isn't always right) |
| `flask seed-courses` | Load `data/courses.yml` |
| `flask import-course <id>` | Import one course from the configured API |
| `flask check-course-api` | Check API connectivity without using quota |
| `flask recalc-handicaps` | Rebuild every round's adjusted score and every user's handicap index from scratch (needed after a scoring change, or to backfill old data) |

## Project layout

```
app/
  __init__.py       create_app() application factory
  extensions.py     db, migrate, login, bootstrap
  cli.py            flask CLI commands
  models/           SQLAlchemy models
  services/         handicap math, dashboard analytics, course providers
  auth/ main/ courses/ rounds/ dashboard/   one blueprint per feature area
  templates/         shared base template and macros
  static/vendor/     vendored Chart.js (no CDN dependency)
data/courses.yml     seed course data
migrations/          Alembic migrations
tests/                pytest suite
```

## Deployment

`boot.sh` runs migrations and starts the app; `wsgi.py` is the production
entrypoint (point uWSGI/gunicorn at `wsgi:app`, with `FLASK_CONFIG=production`
or equivalent). `SECRET_KEY` must be set outside of debug/testing mode, or
the app refuses to start.

`Dockerfile` + `docker-compose.yml` + `app.ini`/`nginx.conf` describe an
nginx/uWSGI deployment, but the `Dockerfile` still targets `alpine:3.9`
(end-of-life, Python 3.6) — too old for this project's current
dependencies (Flask 3.x, SQLAlchemy 2.x need Python 3.8+). It needs a
newer base image before it will build; that update wasn't part of this
round of work.
