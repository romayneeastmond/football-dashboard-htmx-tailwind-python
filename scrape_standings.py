import requests
from bs4 import BeautifulSoup

QUALIFICATION_ZONES = {
    "English Premier League": { "UCL": [1, 2, 3, 4], "UEL": [5], "UECL": [6], "REL": [18, 19, 20] },
    "Spanish La Liga": { "UCL": [1, 2, 3, 4], "UEL": [5], "UECL": [6], "REL": [18, 19, 20] },
    "Italian Serie A": { "UCL": [1, 2, 3, 4], "UEL": [5], "UECL": [6], "REL": [18, 19, 20] },
    "German Bundesliga": { "UCL": [1, 2, 3, 4], "UEL": [5], "UECL": [6], "REL_PO": [16], "REL": [17, 18] },
    "French Ligue 1": { "UCL": [1, 2, 3], "UCL_Q": [4], "UEL": [5], "UECL": [6], "REL_PO": [16], "REL": [17, 18] },
    "Portuguese Primeira Liga": { "UCL": [1, 2], "UCL_Q": [3], "UEL": [4], "UECL": [5], "REL_PO": [16], "REL": [17, 18] },
    "English Championship": { "UCL": [1, 2], "UCL_Q": [3, 4, 5, 6], "REL": [22, 23, 24] }
}

def scrape_standings(url, league_name=None):    
    # Extract league code from URL (e.g., 'eng.1' from '.../league/eng.1')
    league_code = url.split("/")[-1]
    api_url = f"https://site.api.espn.com/apis/v2/sports/soccer/{league_code}/standings"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching standings API for {league_code}: {e}")
        return []

    standings = []
    try:
        entries = data.get("children", [{}])[0].get("standings", {}).get("entries", [])
        
        for counter, entry in enumerate(entries, 1):
            team_data = entry.get("team", {})
            stats_list = entry.get("stats", [])
            
            # Convert stats list to a dictionary for easy access
            stats = { s.get("name"): s.get("displayValue") for s in stats_list }
            
            team_name = team_data.get("displayName", "Unknown")
            points = stats.get("points", "0")
            games_played = stats.get("gamesPlayed", "0")
            wins = stats.get("wins", "0")
            draws = stats.get("ties", "0")
            losses = stats.get("losses", "0")
            goal_difference = stats.get("pointDifferential", "0")

            team_logo = team_data.get("logos", [{}])[0].get("href", "")

            zone = ""
            if league_name and league_name in QUALIFICATION_ZONES:
                mapping = QUALIFICATION_ZONES[league_name]
                if counter in mapping.get("UCL", []): zone = "ucl"
                elif counter in mapping.get("UCL_Q", []): zone = "ucl-q"
                elif counter in mapping.get("UEL", []): zone = "uel"
                elif counter in mapping.get("UECL", []): zone = "uecl"
                elif counter in mapping.get("REL", []): zone = "rel"
                elif counter in mapping.get("REL_PO", []): zone = "rel-po"

            standings.append({
                "team": team_name, 
                "logo": team_logo,
                "points": points, 
                "games_played": games_played,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "goal_difference": goal_difference,
                "zone": zone
            })
            
    except (KeyError, IndexError) as e:
        print(f"Error parsing API response for {league_code}: {e}")
        return []

    return standings


def scrape_wc_standings():
    """Return WC group tables: [{name, teams: [{team, logo, gp, w, d, l, gf, ga, gd, pts}]}]"""
    api_url = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching WC standings: {e}")
        return []

    groups = []
    for group in data.get("children", []):
        group_name = group.get("name", "")
        entries = group.get("standings", {}).get("entries", [])
        teams = []
        for entry in entries:
            team_data = entry.get("team", {})
            stats = {s.get("name"): s.get("displayValue") for s in entry.get("stats", [])}
            logo_list = team_data.get("logos", [])
            teams.append({
                "team": team_data.get("displayName", "Unknown"),
                "logo": logo_list[0].get("href", "") if logo_list else "",
                "games_played": stats.get("gamesPlayed", "0"),
                "wins": stats.get("wins", "0"),
                "draws": stats.get("ties", "0"),
                "losses": stats.get("losses", "0"),
                "goals_for": stats.get("pointsFor", "0"),
                "goals_against": stats.get("pointsAgainst", "0"),
                "goal_difference": stats.get("pointDifferential", "0"),
                "points": stats.get("points", "0"),
            })
        if teams:
            groups.append({"name": group_name, "teams": teams})

    return groups
