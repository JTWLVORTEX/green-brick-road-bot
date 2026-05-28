# Green Brick Road Lead Finder

An automated bot that finds podcast guest leads for **The Green Brick Road**, a podcast where two young entrepreneurs interview successful founders and business people about how they built their careers. The bot discovers local Chicagoland business founders, finds their professional email addresses, and writes them to a Google Sheet for manual outreach review.

The bot runs autonomously on a weekly schedule in the cloud, so new qualified leads appear in the sheet without any manual work.

## Overview

Cold-outreach lead generation is normally a slow manual process: search for businesses, find the right contact, check you haven't already reached out, repeat. This bot automates the discovery half of that workflow while leaving the actual outreach decision to a human.

It does this legally and sustainably by using established business-data APIs rather than scraping websites directly. Scraping violates most sites' terms of service, returns low-quality generic inboxes, and damages sender reputation. The API approach returns verified founder-level contacts and keeps the project on the right side of those rules.

## How it works

The bot runs a four-stage pipeline each time it executes:

1. **Discover businesses.** It queries the Google Places API across 19 Chicagoland search points (north shore, northwest suburbs, west suburbs, and several Chicago neighborhoods), filtered to professional-service business categories such as law firms, accounting practices, financial advisors, insurance brokers, real estate firms, and consultancies.

2. **Extract and filter domains.** Each business website is reduced to a clean domain. Domains are deduplicated, checked against a blacklist of roughly 120 national chains and franchises, and the remaining list is shuffled so each run samples different businesses over time.

3. **Find founder emails.** For a capped number of domains per run, the bot calls the Hunter.io API to retrieve email addresses at that domain, then filters to founder-level roles (founder, owner, CEO, president, managing partner) while explicitly excluding vice presidents, directors, and other non-founder titles.

4. **Write to the database.** New leads are checked against existing emails already in the Google Sheet to prevent duplicates, then appended with full context (name, company, role, domain, location, and the date found).

## Tech stack

- **Python 3.9+** as the core language
- **Google Places API** for local business discovery
- **Hunter.io API** for founder email lookup
- **Google Sheets API** (via OAuth 2.0) as the persistent lead database
- **Railway** for cloud deployment and scheduled execution
- **GitHub** for version control and as the deployment source

## Project structure

```
green-brick-road-bot/
├── main.py                  Orchestrator: runs the full pipeline
├── railway.json             Railway deploy config (start command + no-restart policy)
├── requirements.txt         Python dependencies
├── .env                     Local secrets (gitignored, never committed)
├── .gitignore               Excludes all secrets and local state
├── src/
│   ├── config.py            Loads env vars; injects OAuth credentials on cloud startup
│   ├── places.py            Google Places client (business discovery)
│   ├── apollo.py            Email-finding client (see naming note below)
│   └── sheets.py            Google Sheets client (read for dedup, write new leads)
├── credentials/             OAuth credentials and token (gitignored)
└── data/
    └── seen_domains.json    Local memory of already-checked domains (gitignored)
```

**Naming note:** `src/apollo.py` is named for the project's original email provider (Apollo.io). Apollo's free tier blocked API access to its people-search endpoints, so the project switched to Hunter.io. The file kept its name to avoid a disruptive rename, but its contents use the Hunter.io API. The configuration variable is `HUNTER_API_KEY`.

## Installation

### Prerequisites

- Python 3.9 or higher
- Git
- A Google Cloud account
- A Hunter.io account (free tier is sufficient to start)
- A Google account that owns the destination Google Sheet

### Steps

1. Clone the repository and enter it:

   ```bash
   git clone https://github.com/YOUR_USERNAME/green-brick-road-bot.git && cd green-brick-road-bot
   ```

2. Create and activate a virtual environment, then install dependencies:

   ```bash
   python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
   ```

3. Enable the **Places API (New)** and the **Google Sheets API** in the Google Cloud Console, and create:
   - A **Places API key** (restricted to the Places API)
   - An **OAuth 2.0 client ID** of type "Desktop app", then download its JSON

4. Generate a **Hunter.io API key** from your Hunter account under Settings, Integrations, API.

5. Create a Google Sheet with the column headers listed in the Database schema section below, and copy its Sheet ID from the URL.

6. Place your downloaded OAuth JSON at `credentials/oauth_credentials.json`.

7. Copy `.env.example` to `.env` and fill in your values (see Configuration below).

8. Run the bot once locally to complete the one-time OAuth browser login. This creates `credentials/token.json`:

   ```bash
   python main.py
   ```

   A browser window opens; sign in with the Google account that owns the sheet and grant access. After this, the token is saved and future runs do not require a browser.

## Configuration

### Environment variables

These live in `.env` for local development and in Railway's Variables tab for cloud deployment.

| Variable | Purpose |
|---|---|
| `GOOGLE_PLACES_API_KEY` | Authenticates Google Places requests |
| `HUNTER_API_KEY` | Authenticates Hunter.io requests |
| `GOOGLE_SHEET_ID` | Identifies which sheet to write to |
| `GOOGLE_OAUTH_CREDENTIALS_PATH` | Path to the OAuth client JSON (`credentials/oauth_credentials.json`) |
| `GOOGLE_OAUTH_TOKEN_PATH` | Path to the saved user token (`credentials/token.json`) |
| `GOOGLE_OAUTH_CREDENTIALS_JSON` | Cloud only: full contents of the OAuth client JSON |
| `GOOGLE_OAUTH_TOKEN_JSON` | Cloud only: full contents of the token JSON |

The two `_JSON` variables exist because Railway's containers do not have access to local files. On startup, `config.py` reads these variables and writes their contents into the expected file paths, so the same credential-loading code works both locally and in the cloud.

### Tuning knobs

All operational settings live at the top of `main.py` so they can be adjusted without touching the pipeline logic:

- `MAX_HUNTER_CALLS_PER_RUN` controls how many domains are looked up per run. Set to 5 for the Hunter free tier (50 credits per month). Raise it after upgrading.
- `SEARCH_AREAS` is the list of latitude and longitude points the bot searches. Add entries to widen geographic coverage.
- `SEARCH_RADIUS_METERS` controls how far each search point reaches.
- `INCLUDED_BUSINESS_TYPES` restricts results to professional-service categories.
- `DOMAIN_BLACKLIST` is the set of chain and franchise domains to skip.

## Usage

### Running locally

With the virtual environment active:

```bash
python main.py
```

The bot prints its progress through each stage and reports how many new leads it wrote to the sheet. Each run consumes one Hunter credit per domain looked up.

### Running in the cloud (Railway)

The bot is configured to deploy automatically from GitHub. Railway reads `railway.json`, which sets the start command to `python main.py` and the restart policy to `NEVER`. The no-restart policy is essential: because the bot is a batch job that runs once and exits, a default service would restart it endlessly and exhaust the monthly API budget in minutes.

A weekly cron schedule (`0 14 * * 1`, Monday morning Central time) triggers the bot once per week. To deploy updates, push to the connected GitHub branch and Railway redeploys automatically.

## Database schema

The Google Sheet acts as the lead database with these columns:

`Name | Email | Company | Domain | Role | Location | Source | Date Found | Status | Notes | Story Score`

- `Source` is `manual` for guests added by hand and `bot` for leads the system found.
- `Status` tracks the outreach lifecycle: `new`, `contacted`, `replied`, `interviewed`, or `rejected`.
- Google Sheets Filter Views can be used to view subsets (for example, only `status = new`) without splitting the data across multiple sheets.

## AI-assisted development

This project was built using AI pair-programming with Claude. The AI assistance covered the following concrete elements:

- **Architecture design.** The decision to use a three-API pipeline (Places for discovery, Hunter for emails, Sheets for storage) rather than direct web scraping was reached through AI consultation, including the reasoning about legality, data quality, and deliverability.
- **Code generation.** Each module was produced by feeding structured task specifications ("briefs") to Claude Code, an AI coding agent that wrote and tested the files. The briefs covered project setup, the three API clients, the orchestrator, and the deployment configuration.
- **Debugging.** AI identified a substring-matching bug in the founder filter (job titles containing "vice president" were incorrectly matched because the word "president" was inside them) and rebuilt the logic with negative-pattern checks plus unit tests. It also diagnosed the Google Cloud organization-policy and permissions failures during credential setup, and the Railway deployment crash caused by missing OAuth files in the container.
- **Filtering and efficiency logic.** The professional-service industry filter, the chain and franchise blacklist (including subdomain matching and automatic exclusion of `.gov` and `.edu` domains), and the persistent seen-domains memory were all designed with AI input to reduce wasted API credits.
- **Deployment configuration.** The pattern for injecting OAuth credentials through environment variables, the no-restart policy, and the cron schedule were all worked out through AI assistance.

The human role was direction, judgment, and execution: defining the project goals and guest criteria, evaluating real-world results, deciding which suggestions to accept, running every command, and operating the cloud accounts.

## Known limitations

- **Business discovery is biased toward physical, walk-in businesses.** Google Places indexes places people visit, so it surfaces law firms, accountants, and real estate offices well but misses pure business-to-business companies such as marketing agencies and trading firms that have no foot traffic. Reaching those would require a different data source.
- **Hunter free tier is limited.** At 50 credits per month and 5 lookups per run, the bot realistically produces a handful of qualified leads per week. Higher volume requires a paid Hunter plan, after which `MAX_HUNTER_CALLS_PER_RUN` can be raised.
- **The OAuth token requires occasional manual refresh.** Because Railway's filesystem resets between deployments, a refreshed token is not permanently saved in the cloud. If the cloud logs ever report the token as invalid or expired, regenerate it by running the bot locally to complete a fresh login, then copy the new `token.json` contents into the Railway `GOOGLE_OAUTH_TOKEN_JSON` variable.

## Maintenance notes

- **Credits cost money per request, not per result.** Hunter charges one credit per domain looked up regardless of whether useful emails come back. The blacklist, industry filter, and seen-domains memory all exist to avoid spending credits on domains that will not produce good leads.
- **Never commit secrets.** The `.env` file, the `credentials/` directory, and all token and key files are excluded by `.gitignore`. API keys must never appear in committed code or in a public repository.
- **Extending the blacklist.** As junk results appear in the sheet over time, add their domains to `DOMAIN_BLACKLIST` in `main.py` and redeploy.

## Future work

A planned second phase adds an AI scoring layer: the bot will read each lead's company About page, generate a short synopsis, and assign a 1 to 10 score for how well the person fits the podcast's focus on hard-working founders with a compelling story. Leads scoring below a threshold would be filtered out, sharply reducing manual review time. This phase uses the Google Gemini API free tier to keep ongoing costs at zero.
