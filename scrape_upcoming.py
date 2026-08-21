import requests
import os
from datetime import datetime, timedelta
from scrape_espn import LEAGUE_NAMES

def convert_time(time_str):
    try:
        offset = int(os.environ.get("TIMEZONE_OFFSET", 0))
    except (ValueError, TypeError):
        offset = 0

    if offset == 0:
        return time_str

    try:
        # Normalize: replace "." with ":"
        clean_time = time_str.replace(".", ":").strip()
        parts = clean_time.split()
        time_part = parts[0]

        try:
            dt = datetime.strptime(time_part, "%H:%M")
        except ValueError:
            dt = datetime.strptime(time_part, "%I:%M")

        # Apply the hourly offset
        new_dt = dt + timedelta(hours=offset)

        # Format to 12h clock
        formatted_time = new_dt.strftime("%I:%M %p").lstrip("0")

        # Return ONLY the formatted time (no BST/EDT labels)
        return formatted_time
    except Exception as e:
        print(f"DEBUG TIME ERROR: {e}")
        return time_str


UPCOMING_STATUSES = {"STATUS_SCHEDULED", "STATUS_IN_PROGRESS", "STATUS_HALFTIME"}

def scrape_upcoming():
    """Fetch scheduled/live fixtures from ESPN for all tracked leagues, next 10 days."""
    headers = {"User-Agent": "Mozilla/5.0"}
    today = datetime.utcnow()

    by_date = {}
    for league_code, league_name in LEAGUE_NAMES.items():
        for offset in range(10):
            day = (today + timedelta(days=offset)).strftime("%Y%m%d")
            try:
                r = requests.get(
                    f"https://site.web.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard",
                    params={"dates": day},
                    headers=headers,
                    timeout=8,
                )
            except Exception as e:
                print(f"Error fetching upcoming for {league_code}: {e}")
                continue
            if r.status_code != 200:
                continue

            for event in r.json().get("events", []):
                status_name = event.get("status", {}).get("type", {}).get("name", "")
                if status_name not in UPCOMING_STATUSES:
                    continue

                date_iso = event.get("date", "")
                try:
                    dt_utc = datetime.strptime(date_iso, "%Y-%m-%dT%H:%MZ")
                    date_label = dt_utc.strftime("%A %d %B %Y")
                    time_label = convert_time(dt_utc.strftime("%H:%M"))
                except Exception:
                    date_label = "TBD"
                    time_label = "TBD"

                comp = event.get("competitions", [{}])[0]
                competitors = comp.get("competitors", [])
                home = next((c for c in competitors if c.get("homeAway") == "home"), {})
                away = next((c for c in competitors if c.get("homeAway") == "away"), {})
                home_team = home.get("team", {})
                away_team = away.get("team", {})
                home_name = home_team.get("displayName", "")
                away_name = away_team.get("displayName", "")
                if not home_name or not away_name:
                    continue
                home_logos = home_team.get("logos", [])
                away_logos = away_team.get("logos", [])
                home_logo = home_logos[0].get("href", "") if home_logos else home_team.get("logo", "")
                away_logo = away_logos[0].get("href", "") if away_logos else away_team.get("logo", "")

                match = {
                    "time": time_label,
                    "home_team": home_name,
                    "away_team": away_name,
                    "home_logo": home_logo,
                    "away_logo": away_logo,
                }
                by_date.setdefault(date_label, {}).setdefault(league_name, []).append(match)

    events = []
    for date_label in sorted(by_date.keys(), key=lambda d: _sort_key(d)):
        match_values = []
        for league_name, matches in by_date[date_label].items():
            match_values.append({"title": league_name})
            match_values.append({"matches": matches})
        events.append({"date": date_label, "match_values": match_values})

    return events


def _sort_key(date_label):
    try:
        return datetime.strptime(date_label, "%A %d %B %Y")
    except ValueError:
        return datetime.max
