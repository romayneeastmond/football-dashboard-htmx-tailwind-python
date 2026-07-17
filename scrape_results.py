import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def scrape_results():
    url = "https://www.theguardian.com/football/results"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching results: {e}")
        return []
        
    soup = BeautifulSoup(response.text, "html.parser")
    events = []
    
    # Guardian's new react-based layout classes
    for container in soup.find_all("section", class_="dcr-jjtqpb"):
        date = container.find("h2")
        current_date = date.text.strip() if date else ""
        
        events.append({
            "date": current_date,
            "match_values": []
        })    
        
        for div in container.find_all("ul"):        
            matches = []        
            
            anchor = div.find_previous_sibling("h3")
            if not anchor:
                continue
            anchor_link = anchor.find("a")
            anchor_text = anchor_link.text.strip() if anchor_link else anchor.text.strip()
            
            events[-1]["match_values"].append({ "title": anchor_text })   
            
            for li in div.find_all("li"):
                a_tag = li.find("a")
                if not a_tag:
                    continue
                    
                home_team_tag = a_tag.find("span", class_="dcr-iqim6o")
                away_team_tag = a_tag.find("div", class_="dcr-rm7qtf")
                
                # Filter out the image tag text from away team
                home_team = home_team_tag.text.strip() if home_team_tag else "Unknown"
                away_team = away_team_tag.text.strip() if away_team_tag else "Unknown"
                
                # Fetching the score
                score_container = a_tag.find("span", class_="dcr-17v2nd5")
                match_result = "N/A"
                if score_container:
                    home_score = score_container.find("span", class_="dcr-79z44d")
                    away_score = score_container.find("span", class_="dcr-1c2czlv")
                    if home_score and away_score:
                        match_result = f"{home_score.text.strip()} - {away_score.text.strip()}"
                
                # Fallback: Sometimes postponed games or pens have different structures
                if match_result == "N/A":
                    status = a_tag.find("span", class_="dcr-yb9mnm")
                    if status:
                        match_result = status.text.strip()

                matches.append({"time": match_result, "home_team": home_team, "away_team": away_team})
       
            events[-1]["match_values"].append({ "matches":  matches })

    return events


WC_COMPLETED_STATUSES = {"STATUS_FULL_TIME", "STATUS_FINAL", "STATUS_FT", "STATUS_FINAL_AET", "STATUS_FINAL_PEN"}

def scrape_wc_results():
    """Fetch completed WC matches from ESPN for the last 10 days."""
    headers = {"User-Agent": "Mozilla/5.0"}
    today = datetime.utcnow()

    all_events = []
    for offset in range(10):
        day = (today - timedelta(days=offset)).strftime("%Y%m%d")
        try:
            r = requests.get(
                "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard",
                params={"dates": day},
                headers=headers,
                timeout=8,
            )
            if r.status_code == 200:
                all_events.extend(r.json().get("events", []))
        except Exception:
            continue

    by_date = {}
    for event in all_events:
        status_name = event.get("status", {}).get("type", {}).get("name", "")
        if status_name not in WC_COMPLETED_STATUSES:
            continue

        date_iso = event.get("date", "")
        try:
            dt_utc = datetime.strptime(date_iso, "%Y-%m-%dT%H:%MZ")
            dt_bst = dt_utc + timedelta(hours=1)
            date_label = dt_bst.strftime("%A %d %B %Y")
        except Exception:
            date_label = "TBD"

        comp = event.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away = next((c for c in competitors if c.get("homeAway") == "away"), {})
        home_team = home.get("team", {})
        away_team = away.get("team", {})
        home_name = home_team.get("displayName", "")
        away_name = away_team.get("displayName", "")
        home_score = home.get("score", "")
        away_score = away.get("score", "")
        score = f"{home_score} - {away_score}" if home_score != "" and away_score != "" else "N/A"

        if not home_name or not away_name:
            continue
        home_logos = home_team.get("logos", [])
        away_logos = away_team.get("logos", [])
        home_logo = home_logos[0].get("href", "") if home_logos else home_team.get("logo", "")
        away_logo = away_logos[0].get("href", "") if away_logos else away_team.get("logo", "")

        if date_label not in by_date:
            by_date[date_label] = []
        by_date[date_label].append({"time": score, "home_team": home_name, "away_team": away_name, "home_logo": home_logo, "away_logo": away_logo})

    # Most recent first
    sorted_dates = sorted(by_date.keys(), reverse=True)
    return [
        {"date": date_label, "match_values": [{"title": "FIFA World Cup"}, {"matches": by_date[date_label]}]}
        for date_label in sorted_dates
    ]
