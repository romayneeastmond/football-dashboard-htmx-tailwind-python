import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

def convert_time(gmt_time_str):    
    local_tz = pytz.timezone("America/Phoenix")
    
    gmt_tz = pytz.timezone("GMT")
    gmt_time = datetime.strptime(gmt_time_str.replace(u'\xa0', u' '), "%H:%M %Z")
    gmt_time = gmt_tz.localize(gmt_time)
    local_time = gmt_time.astimezone(local_tz)
    
    return local_time.strftime("%I:%M %p")

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
                            matches.append({"time": match_time, "home_team": team_names[0], "away_team": team_names[1]})
       
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
            anchor_link = anchor.find("a")
            
            anchor_text = anchor_link.text.strip() if anchor else ""
            
            events[-1]["match_values"].append({ "title": anchor_text })   
            
            for table in div.find_all("a"):
                match_time = table.find("time").text.strip()
                home_team = table.find("span", class_="dcr-iqim6o").text.strip()
                away_team = table.find("div", class_="dcr-rm7qtf").text.strip()

                matches.append({"time": match_time, "home_team": home_team, "away_team": away_team})
       
            events[-1]["match_values"].append({ "matches":  matches })       
    
    return events