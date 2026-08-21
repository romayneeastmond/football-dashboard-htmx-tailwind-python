import requests
from datetime import datetime, timedelta
from scrape_espn import LEAGUE_NAMES

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
                    # JS formatTimesToLocal() expects BST (UTC+1) and converts to the viewer's local time
                    dt_bst = dt_utc + timedelta(hours=1)
                    date_label = dt_bst.strftime("%A %d %B %Y")
                    time_label = dt_bst.strftime("%H:%M")
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
