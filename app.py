import requests
from scrape_standings import scrape_standings
from scrape_upcoming import scrape_upcoming
from scrape_cpl import scrape_cpl
from scrape_results import scrape_results
from scrape_espn import get_match_stats, get_team_logos, find_logo
from flask import Flask, render_template, request, jsonify
import os

try:
    __import__('dotenv').load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.jinja_env.globals["find_logo"] = find_logo

@app.route("/debug-scrape")
def debug_scrape():
    league_code = "eng.1"
    url = f"https://site.api.espn.com/apis/v2/sports/soccer/{league_code}/standings"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return jsonify({
            "status_code": response.status_code,
            "url": url,
            "response_json_preview": response.json().get("name", "Unknown League"),
            "is_success": response.status_code == 200,
            "using_api": True
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "url": url,
            "is_success": False
        })

def filter_events(events, search_term):
    if not search_term:
        return events
    
    filtered_events = []
    search_term = search_term.lower()
    
    for event in events:
        new_event = event.copy()
        new_match_values = []
        
        current_title = ""
        for val in event.get("match_values", []):
            if "title" in val:
                current_title = val["title"]
            elif "matches" in val:
                filtered_matches = [
                    m for m in val["matches"] 
                    if search_term in m["home_team"].lower() or search_term in m["away_team"].lower()
                ]
                if filtered_matches:
                    if current_title:
                        new_match_values.append({"title": current_title})
                        current_title = ""
                    new_match_values.append({"matches": filtered_matches})
        
        if new_match_values:
            new_event["match_values"] = new_match_values
            filtered_events.append(new_event)
            
    return filtered_events

@app.route("/submit-blind-mode", methods=["POST"])
def submit_blind_mode():
    return """<button hx-post="/submit-night-mode" hx-on::before-request="toggleDarkMode(true);" hx-swap="outerHTML"><i class="fas fa-moon"></i></button>"""

@app.route("/submit-night-mode", methods=["POST"])
def submit_night_mode():
    return """<button class="text-white" hx-post="/submit-blind-mode" hx-on::before-request="toggleDarkMode(false);" hx-swap="outerHTML"><i class="fas fa-sun"></i></button>"""

@app.route("/get-upcoming")
def get_upcoming():
    events = scrape_upcoming()
    logos  = get_team_logos()
    return render_template("partials/events.html", events=events, logos=logos)

@app.route("/match-stats")
def match_stats():
    home  = request.args.get("home",  "").strip()
    away  = request.args.get("away",  "").strip()
    date  = request.args.get("date",  "").strip()
    score = request.args.get("score", "").strip()
    data  = get_match_stats(home, away, date, score)
    return render_template("partials/match_stats.html", **data)

@app.route("/get-results")
def get_results():
    events = scrape_results()
    logos  = get_team_logos()
    return render_template("partials/results.html", events=events, logos=logos)

@app.route("/search")
def search():
    search_term = request.args.get('q', '').strip()
    if not search_term:
        return ""
    
    upcoming_data = scrape_upcoming()
    results_data = scrape_results()
    
    filtered_upcoming = filter_events(upcoming_data, search_term)
    filtered_results = filter_events(results_data, search_term)
    
    return render_template("partials/search_results.html",
                           upcoming=filtered_upcoming,
                           results=filtered_results,
                           query=search_term,
                           logos=get_team_logos())

@app.route("/")
def index():
    data_england = scrape_standings("https://www.espn.com/soccer/standings/_/league/eng.1", "English Premier League")
    data_spanish = scrape_standings("https://www.espn.com/soccer/standings/_/league/esp.1", "Spanish La Liga")
    data_italian = scrape_standings("https://www.espn.com/soccer/standings/_/league/ita.1", "Italian Serie A")
    data_german = scrape_standings("https://www.espn.com/soccer/standings/_/league/ger.1", "German Bundesliga")
    data_french = scrape_standings("https://www.espn.com/soccer/standings/_/league/fra.1", "French Ligue 1")
    data_portuguese = scrape_standings("https://www.espn.com/soccer/standings/_/league/por.1", "Portuguese Primeira Liga")
    data_championship = scrape_standings("https://www.espn.com/soccer/standings/_/league/eng.2", "English Championship")
    data_cpl = scrape_cpl()
    leagues = {
        "English Premier League": data_england,
        "Spanish La Liga": data_spanish,
        "Italian Serie A": data_italian,
        "German Bundesliga": data_german,
        "French Ligue 1": data_french,
        "Portuguese Primeira Liga": data_portuguese,
        "English Championship": data_championship,
        "Canadian Premier League": data_cpl
    }    

    leagues = {name: data for name, data in leagues.items() if data}
    
    return render_template("index.html", leagues=leagues)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
