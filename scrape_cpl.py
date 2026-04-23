import requests
import json

def scrape_cpl():
    url = "https://api-sdp.cplsoccer.com/v1/cpl/football/seasons/cpl::Football_Season::c479ab0916a24c3390f1ce2c021ace54/standings/overall?locale=en-US&orderBy=rank&direction=asc"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        with open("cpl_api_dump.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        standings = []
        
        # Find the overall table which has "type": "table"
        overall_table = []
        for s in data.get("standings", []):
            if s.get("type") == "table":
                overall_table = s.get("teams", [])
                break
                
        for team_info in overall_table:
            team_name = team_info.get("officialName", "")
            stats_list = team_info.get("stats", [])
            stats_dict = { s.get("statsId"): s.get("statsValue") for s in stats_list }
            
            standings.append({
                "team": team_name, 
                "points": str(stats_dict.get("points", 0)), 
                "games_played": str(stats_dict.get("matches-played", 0)),
                "wins": str(stats_dict.get("win", 0)),
                "draws": str(stats_dict.get("draw", 0)),
                "losses": str(stats_dict.get("lose", 0)),
                "goal_difference": str(stats_dict.get("goal-difference", 0)),
                "zone": ""
            })
            
        return standings
    except Exception as e:
        print(f"Error fetching CPL: {e}")
        return []
