import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta
import pytz

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

def scrape_upcoming():    
    url = "https://www.theguardian.com/football/fixtures"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=3)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching upcoming: {e}")
        return []
    soup = BeautifulSoup(response.text, "html.parser")

    events = []
    
    for container in soup.find_all("div", class_="football-matches__day"):
        date = container.find("div", class_={"date-divider"})
        current_date = date.text.strip() if date else ""
        
        events.append({
            "date": current_date,
            "match_values": []
        })
    
        for div in container.find_all("div", class_="football-table__container"):        
            matches = []
            
            for table in div.find_all("table", class_="table--football"):
                anchor = table.find("caption", class_="table__caption")
                anchor_link = anchor.find("a")
                
                anchor_text = anchor_link.text.strip() if anchor else ""
                
                events[-1]["match_values"].append({ "title": anchor_text })                
                
                for row in table.find_all("tr"):
                    time_td = row.find("td", class_="football-match__status")
                    teams_td = row.find("td", class_="football-match__teams")
                    
                    if time_td and teams_td:
                        match_time = time_td.text.strip()
                        team_names = [span.text.strip() for span in teams_td.find_all("span")]
                        
                        if len(team_names) == 2:
                            final_time = convert_time(match_time)
                            matches.append({"time": final_time, "home_team": team_names[0], "away_team": team_names[1]})
       
            events[-1]["match_values"].append({ "matches":  matches })

    wc = scrape_wc_upcoming()
    if len(events) == 0:
        events = scrape_upcoming_alt()
    return wc + events


WC_UPCOMING_STATUSES = {"STATUS_SCHEDULED", "STATUS_IN_PROGRESS", "STATUS_HALFTIME"}

def scrape_wc_upcoming():
    """Fetch scheduled/live WC fixtures from ESPN for the next 10 days."""
    headers = {"User-Agent": "Mozilla/5.0"}
    today = datetime.utcnow()

    all_events = []
    for offset in range(10):
        day = (today + timedelta(days=offset)).strftime("%Y%m%d")
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
        if status_name not in WC_UPCOMING_STATUSES:
            continue

        date_iso = event.get("date", "")
        try:
            dt_utc = datetime.strptime(date_iso, "%Y-%m-%dT%H:%MZ")
            # Convert UTC → BST (+1) so convert_time can apply the user's offset from BST
            dt_bst = dt_utc + timedelta(hours=1)
            date_label = dt_bst.strftime("%A %d %B %Y")
            time_label = convert_time(dt_bst.strftime("%H:%M"))
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

        if date_label not in by_date:
            by_date[date_label] = []
        by_date[date_label].append({"time": time_label, "home_team": home_name, "away_team": away_name, "home_logo": home_logo, "away_logo": away_logo})

    return [
        {"date": date_label, "match_values": [{"title": "FIFA World Cup"}, {"matches": matches}]}
        for date_label, matches in by_date.items()
    ]

def scrape_upcoming_alt():
    url = "https://www.theguardian.com/football/fixtures"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=3)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching upcoming alt: {e}")
        return []
    soup = BeautifulSoup(response.text, "html.parser")
        
    events = []
    
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
            anchor_link = anchor.find("a") if anchor else None
            
            anchor_text = anchor_link.text.strip() if anchor_link else ""
            
            events[-1]["match_values"].append({ "title": anchor_text })   
            
            for table in div.find_all("a"):
                match_time_tag = table.find("time")
                if not match_time_tag:
                    continue
                match_time = match_time_tag.text.strip()
                
                home_team_tag = table.find("span", class_="dcr-iqim6o")
                away_team_tag = table.find("div", class_="dcr-rm7qtf")
                
                home_team = home_team_tag.text.strip() if home_team_tag else "Unknown"
                away_team = away_team_tag.text.strip() if away_team_tag else "Unknown"

                final_time = convert_time(match_time)
                matches.append({"time": final_time, "home_team": home_team, "away_team": away_team})
       
            events[-1]["match_values"].append({ "matches":  matches })       
    
    return events
