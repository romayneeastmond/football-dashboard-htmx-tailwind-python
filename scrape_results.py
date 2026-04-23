import requests
from bs4 import BeautifulSoup
from datetime import datetime

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
