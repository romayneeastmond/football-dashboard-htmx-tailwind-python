import requests
import json
import os
from datetime import datetime

API_KEY = os.environ.get("API_FOOTBALL_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "match_stats_cache.json")


def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


def _api_get(path, params):
    headers = {"x-apisports-key": API_KEY}
    r = requests.get(f"{BASE_URL}{path}", headers=headers, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def parse_guardian_date(date_str):
    """Parse Guardian date strings e.g. 'Saturday 10 May 2025' → '2025-05-10'."""
    date_str = date_str.strip()
    for fmt in ["%A %d %B %Y", "%d %B %Y", "%A %d %b %Y", "%d %b %Y"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _name_match(api_name, search_name):
    """Loose team name matching — strips 'FC', compares substrings and prefixes."""
    def normalise(s):
        return s.lower().replace("fc ", "").replace(" fc", "").replace(" cf", "").strip()
    a, b = normalise(api_name), normalise(search_name)
    return a in b or b in a or a[:5] == b[:5]


def _process_stats(raw):
    return {s["type"]: s["value"] for s in raw} if raw else {}


def _bar_pct(home_val, away_val):
    """Return (home_pct, away_pct) for proportional bar widths."""
    try:
        h = float(str(home_val or 0).replace("%", ""))
        a = float(str(away_val or 0).replace("%", ""))
        total = h + a
        if total == 0:
            return 50, 50
        return round(h / total * 100), round(a / total * 100)
    except Exception:
        return 50, 50


DISPLAY_STATS = [
    ("Ball Possession",  "Possession"),
    ("Total Shots",      "Shots"),
    ("Shots on Goal",    "On Target"),
    ("Corner Kicks",     "Corners"),
    ("Fouls",            "Fouls"),
    ("Yellow Cards",     "Yellow Cards"),
    ("Red Cards",        "Red Cards"),
    ("Offsides",         "Offsides"),
    ("passes %",         "Pass Accuracy"),
    ("expected_goals",   "xG"),
]


def get_match_stats(home_team, away_team, date_str, score=None):
    cache = _load_cache()
    cache_key = f"{home_team}|{away_team}|{date_str}"

    if cache_key in cache:
        return cache[cache_key]

    if not API_KEY:
        return {"error": "API_FOOTBALL_KEY is not set. Add it to your .env file."}

    date_iso = parse_guardian_date(date_str)
    if not date_iso:
        return {"error": f"Could not parse date: '{date_str}'"}

    try:
        # 1. Resolve home team ID
        team_resp = _api_get("/teams", {"search": home_team})
        teams = team_resp.get("response", [])
        if not teams:
            return {"error": f"Team not found in API: '{home_team}'"}
        team_id = teams[0]["team"]["id"]

        # 2. Find fixture on that date
        fix_resp = _api_get("/fixtures", {"team": team_id, "date": date_iso})
        fixtures = fix_resp.get("response", [])

        fixture = None
        for f in fixtures:
            if _name_match(f["teams"]["away"]["name"], away_team):
                fixture = f
                break
        if not fixture and fixtures:
            fixture = fixtures[0]
        if not fixture:
            return {"error": "Match not found in API for this date."}

        fixture_id = fixture["fixture"]["id"]

        # 3. Fetch statistics and events
        stats_resp  = _api_get("/fixtures/statistics", {"fixture": fixture_id})
        events_resp = _api_get("/fixtures/events",     {"fixture": fixture_id})

        raw = stats_resp.get("response", [])
        home_raw   = raw[0]["statistics"] if len(raw) > 0 else []
        away_raw   = raw[1]["statistics"] if len(raw) > 1 else []
        home_stats = _process_stats(home_raw)
        away_stats = _process_stats(away_raw)
        home_team_info = raw[0]["team"] if len(raw) > 0 else fixture["teams"]["home"]
        away_team_info = raw[1]["team"] if len(raw) > 1 else fixture["teams"]["away"]

        display_stats = []
        for api_key, label in DISPLAY_STATS:
            hv = home_stats.get(api_key)
            av = away_stats.get(api_key)
            if hv is None and av is None:
                continue
            hp, ap = _bar_pct(hv or 0, av or 0)
            display_stats.append({
                "label":    label,
                "home":     hv if hv is not None else 0,
                "away":     av if av is not None else 0,
                "home_pct": hp,
                "away_pct": ap,
            })

        key_events = []
        for ev in events_resp.get("response", []):
            if ev.get("type") not in ("Goal", "Card"):
                continue
            key_events.append({
                "minute":    ev["time"]["elapsed"],
                "extra":     ev["time"].get("extra"),
                "team_id":   ev["team"]["id"],
                "team_name": ev["team"]["name"],
                "player":    ev.get("player", {}).get("name", ""),
                "assist":    ev.get("assist", {}).get("name", ""),
                "type":      ev.get("type", ""),
                "detail":    ev.get("detail", ""),
            })

        result = {
            "fixture":        fixture,
            "home_team":      home_team_info,
            "away_team":      away_team_info,
            "stats":          display_stats,
            "events":         key_events,
            "date_iso":       date_iso,
        }

        cache[cache_key] = result
        _save_cache(cache)
        return result

    except requests.exceptions.HTTPError as e:
        return {"error": f"API HTTP error {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}
