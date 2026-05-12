import requests
import json
import os
import re
from datetime import datetime

CACHE_FILE       = os.path.join(os.path.dirname(__file__), "match_stats_cache.json")
LOGOS_CACHE_FILE = os.path.join(os.path.dirname(__file__), "team_logos_cache.json")
BASE    = "https://site.api.espn.com/apis/site/v2/sports/soccer"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# All leagues the app tracks
LEAGUES = ["eng.1", "esp.1", "ita.1", "ger.1", "fra.1", "eng.2", "por.1", "can.1"]

# ESPN stat key → (display label, suffix for display value)
ESPN_STAT_MAP = {
    "possessionPct":  "Possession",
    "shots":          "Shots",
    "shotsOnTarget":  "On Target",
    "saves":          "Saves",
    "cornerKicks":    "Corners",
    "foulsCommitted": "Fouls",
    "yellowCards":    "Yellow Cards",
    "redCards":       "Red Cards",
    "offsides":       "Offsides",
}


# ── Cache ──────────────────────────────────────────────────────────────────────

def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_guardian_date(date_str):
    """'Sunday, 10 May 2026' or 'Sunday 10 May 2026' → '2026-05-10'"""
    date_str = date_str.strip()
    for fmt in ["%A, %d %B %Y", "%A %d %B %Y", "%A, %d %b %Y", "%A %d %b %Y",
                "%d %B %Y", "%d %b %Y"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _normalise(name):
    return re.sub(r"\b(fc|cf|afc|sc|fk|ac|as)\b", "", name.lower()).strip()


def _name_match(a, b):
    na, nb = _normalise(a), _normalise(b)
    return na in nb or nb in na or (len(na) >= 4 and na[:4] == nb[:4])


def _bar_pct(hv, av):
    try:
        h = float(re.sub(r"[^0-9.]", "", str(hv) or "0") or 0)
        a = float(re.sub(r"[^0-9.]", "", str(av) or "0") or 0)
        total = h + a
        return (50, 50) if total == 0 else (round(h / total * 100), round(a / total * 100))
    except Exception:
        return 50, 50


def _minute(clock_str):
    """'45:00' → 45"""
    try:
        parts = clock_str.replace("'", "").split(":")
        return int(parts[0])
    except Exception:
        return None


# ── ESPN API calls ─────────────────────────────────────────────────────────────

def _find_event(date_iso, home_team, away_team):
    """Search all leagues' scoreboards for the match. Returns (league, event_id, event_json)."""
    espn_date = date_iso.replace("-", "")
    for league in LEAGUES:
        try:
            r = requests.get(
                f"{BASE}/{league}/scoreboard",
                params={"dates": espn_date},
                headers=HEADERS,
                timeout=8,
            )
            if r.status_code != 200:
                continue
            for event in r.json().get("events", []):
                comps = event.get("competitions", [{}])[0]
                competitors = comps.get("competitors", [])
                home = next((c for c in competitors if c.get("homeAway") == "home"), {})
                away = next((c for c in competitors if c.get("homeAway") == "away"), {})
                h_name = home.get("team", {}).get("displayName", "")
                a_name = away.get("team", {}).get("displayName", "")
                if _name_match(h_name, home_team) and _name_match(a_name, away_team):
                    return league, event["id"], event
        except Exception:
            continue
    return None, None, None


def _get_summary(league, event_id):
    r = requests.get(
        f"{BASE}/{league}/summary",
        params={"event": event_id},
        headers=HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


# ── Parse summary into display data ───────────────────────────────────────────

def _parse_summary(summary, event, date_iso):
    result = {
        "home_name":  "",
        "away_name":  "",
        "home_score": None,
        "away_score": None,
        "home_logo":  "",
        "away_logo":  "",
        "league":     "",
        "round":      "",
        "stats":      [],
        "events":     [],
        "date_iso":   date_iso,
    }

    # League / round from event
    comps = event.get("competitions", [{}])[0]
    league_info = comps.get("league") or event.get("league", {})
    result["league"] = league_info.get("name", "") or event.get("name", "").split(" -")[0]
    result["round"]  = comps.get("notes", [{}])[0].get("headline", "") if comps.get("notes") else ""

    # Teams & score from competitors
    competitors = comps.get("competitors", [])
    home_comp = next((c for c in competitors if c.get("homeAway") == "home"), {})
    away_comp = next((c for c in competitors if c.get("homeAway") == "away"), {})
    result["home_name"]  = home_comp.get("team", {}).get("displayName", "")
    result["away_name"]  = away_comp.get("team", {}).get("displayName", "")
    result["home_logo"]  = home_comp.get("team", {}).get("logo", "")
    result["away_logo"]  = away_comp.get("team", {}).get("logo", "")
    try:
        result["home_score"] = int(home_comp.get("score", ""))
    except (ValueError, TypeError):
        pass
    try:
        result["away_score"] = int(away_comp.get("score", ""))
    except (ValueError, TypeError):
        pass

    home_team_id = home_comp.get("team", {}).get("id", "")

    # Stats from boxscore
    boxscore_teams = summary.get("boxscore", {}).get("teams", [])
    if len(boxscore_teams) >= 2:
        # ESPN returns away first, home second — verify by team id
        t0 = boxscore_teams[0]
        t1 = boxscore_teams[1]
        if t0.get("team", {}).get("id") == home_team_id:
            home_stats_raw, away_stats_raw = t0, t1
        else:
            home_stats_raw, away_stats_raw = t1, t0

        h_stats = {s["name"]: s.get("displayValue", "0")
                   for s in home_stats_raw.get("statistics", [])}
        a_stats = {s["name"]: s.get("displayValue", "0")
                   for s in away_stats_raw.get("statistics", [])}

        stats = []
        for key, label in ESPN_STAT_MAP.items():
            hv = h_stats.get(key)
            av = a_stats.get(key)
            if hv is None and av is None:
                continue
            hv = hv or "0"
            av = av or "0"
            # Append % sign for possession
            display_hv = f"{hv}%" if key == "possessionPct" else hv
            display_av = f"{av}%" if key == "possessionPct" else av
            hp, ap = _bar_pct(hv, av)
            stats.append({"label": label, "home": display_hv, "away": display_av,
                          "home_pct": hp, "away_pct": ap})
        result["stats"] = stats

    # Events from plays
    events = []
    for play in summary.get("plays", []):
        play_type = play.get("type", {}).get("text", "")
        if play_type not in ("Goal", "Yellow Card", "Red Card", "Own Goal", "Penalty - Scored"):
            continue

        clock = play.get("clock", {}).get("displayValue", "")
        minute = _minute(clock)

        team_id = play.get("team", {}).get("id", "")
        side = "home" if team_id == home_team_id else "away"

        participants = play.get("participants", [])
        player = participants[0].get("athlete", {}).get("displayName", "") if participants else ""
        assist = participants[1].get("athlete", {}).get("displayName", "") if len(participants) > 1 else ""

        if play_type in ("Goal", "Penalty - Scored"):
            ev_type, ev_detail = "Goal", "Normal Goal" if play_type == "Goal" else "Penalty"
        elif play_type == "Own Goal":
            ev_type, ev_detail = "Goal", "Own Goal"
        elif play_type == "Yellow Card":
            ev_type, ev_detail = "Card", "Yellow Card"
        else:
            ev_type, ev_detail = "Card", "Red Card"

        if player and minute is not None:
            events.append({
                "minute": minute,
                "extra":  None,
                "side":   side,
                "player": player,
                "assist": assist,
                "type":   ev_type,
                "detail": ev_detail,
            })

    result["events"] = sorted(events, key=lambda e: e["minute"])
    return result


# ── Team logos ─────────────────────────────────────────────────────────────────

def get_team_logos():
    """Return {normalised_team_name: logo_url} for all teams in tracked leagues.
    Cached to disk — delete team_logos_cache.json to force a refresh."""
    if os.path.exists(LOGOS_CACHE_FILE):
        try:
            with open(LOGOS_CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass

    logos = {}
    for league in LEAGUES:
        try:
            r = requests.get(f"{BASE}/{league}/teams", headers=HEADERS, timeout=8)
            if r.status_code != 200:
                continue
            data = r.json()
            # ESPN wraps teams under sports[0].leagues[0].teams or directly under "teams"
            teams = (data.get("sports", [{}])[0]
                        .get("leagues", [{}])[0]
                        .get("teams", [])) or data.get("teams", [])
            for entry in teams:
                team = entry.get("team", entry)
                logo_list = team.get("logos", [])
                logo = logo_list[0].get("href", "") if logo_list else team.get("logo", "")
                if not logo:
                    continue
                for name in [team.get("displayName"), team.get("shortDisplayName"), team.get("name")]:
                    if name:
                        logos[_normalise(name)] = logo
        except Exception:
            continue

    if logos:
        try:
            with open(LOGOS_CACHE_FILE, "w") as f:
                json.dump(logos, f)
        except Exception:
            pass

    return logos


def find_logo(logos, team_name):
    """Look up a logo by team name with substring-containment fallback."""
    key = _normalise(team_name)
    if key in logos:
        return logos[key]
    # Substring containment — require at least 6 chars to avoid "Man X" collisions
    for k, v in logos.items():
        shorter = min(key, k, key=len)
        if len(shorter) >= 6 and (key in k or k in key):
            return v
    return ""


# ── Public interface ───────────────────────────────────────────────────────────

def get_match_stats(home_team, away_team, date_str, score=None):
    cache = _load_cache()
    cache_key = f"{home_team}|{away_team}|{date_str}"

    if cache_key in cache:
        return cache[cache_key]

    date_iso = parse_guardian_date(date_str)
    if not date_iso:
        return {"error": f"Could not parse date: '{date_str}'"}

    league, event_id, event = _find_event(date_iso, home_team, away_team)
    if not event_id:
        return {"error": "This one's gone wide. We couldn't find this match — it may be from a league we don't track yet."}

    try:
        summary = _get_summary(league, event_id)
    except requests.exceptions.HTTPError as e:
        return {"error": f"ESPN summary returned HTTP {e.response.status_code}."}
    except Exception as e:
        return {"error": str(e)}

    result = _parse_summary(summary, event, date_iso)
    cache[cache_key] = result
    _save_cache(cache)
    return result
