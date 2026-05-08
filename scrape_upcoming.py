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
        clean_time = time_str.replace(".", ":").strip()
        parts = clean_time.split()
        time_part = parts[0]
        
        try:
            dt = datetime.strptime(time_part, "%H:%M")
        except ValueError:
            dt = datetime.strptime(time_part, "%I:%M")
        
        dt = dt + timedelta(hours=offset)
        
        formatted_time = dt.strftime("%I:%M %p").lstrip("0")
        
        #tz_part = " ".join(parts[1:])
        
        result = f"{formatted_time}"
        #if tz_part:
        #    result += f" {tz_part}"
        
        return result
    except Exception:
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

    if len(events) == 0:
        return scrape_upcoming_alt()

    return events

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
