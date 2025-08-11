# HomiMeet

HomiMeet is a web app that schedules meetups, prevents "drawing" culture, tracks punctuality, and integrates Google Maps ETA for privacy-conscious arrival sharing.

## Features
- User Sign Up / Log In
- Schedule Meetups
- Punctuality Scoring System
- Leaderboard per group
- Google Maps ETA
- CRUD Operations
- Location Permission Prompt

## Setup

### Requirements
- Python 3.8+
- MySQL Server
- pip

### Installation

```bash
pip install -r requirements.txt
```

### MySQL Setup
1. Import the SQL file from `/sql/schema.sql` into your MySQL server.
2. Update MySQL credentials in `app.py` if needed.

### Run App

```bash
python app.py
```

Then open your browser to: [http://localhost:5000](http://localhost:5000)

### Google Maps
Your Google Maps API key is already injected. Enable:
- Maps JavaScript API
- Directions API
- Geolocation API
