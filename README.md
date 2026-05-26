# Green Brick Road Lead Finder

Automated lead finder for The Green Brick Road podcast. Finds
local Chicagoland business founders and writes them to a Google
Sheet for manual outreach.

## Tech Stack
- Python 3.9+
- Google Places API (business discovery)
- Apollo.io API (email finding)
- Google Sheets API (storage)
- Railway (deployment with cron schedule)

## Setup
1. Activate venv: source venv/bin/activate
2. Install deps: pip install -r requirements.txt
3. Copy .env.example to .env and fill in values
4. Run: python main.py

## Project Status
In development. Built in milestones via Claude Code briefs.
