import requests
import json
import os
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

CACHE_FILE = os.path.join(os.path.dirname(__file__), "match_stats_cache.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://fbref.com/en/",
}

# FBref stat labels → display labels
STAT_LABEL_MAP = {
    "possession":           "Possession",
    "shots on target":      "On Target",
    "saves":                "Saves",
    "corner kicks":         "Corners",
    "fouls":                "Fouls",
    "offsides":             "Offsides",
    "yellow cards":         "Yellow Cards",
    "red cards":            "Red Cards",
    "total shots":          "Shots",
    "shots":                "Shots",
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
    """'Saturday 10 May 2025' → '2025-05-10'"""
    date_str = date_str.strip()
    for fmt in ["%A, %d %B %Y", "%A %d %B %Y", "%A, %d %b %Y", "%A %d %b %Y", "%d %B %Y", "%d %b %Y"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _normalise(name):
    return re.sub(r"\bfc\b|\bcf\b|\bafc\b|\bsc\b", "", name.lower()).strip()


def _name_match(a, b):
    na, nb = _normalise(a), _normalise(b)
    return na in nb or nb in na or na[:5] == nb[:5]


def _bar_pct(home_val, away_val):
    try:
        h = float(re.sub(r"[^0-9.]", "", str(home_val)) or 0)
        a = float(re.sub(r"[^0-9.]", "", str(away_val)) or 0)
        total = h + a
        if total == 0:
            return 50, 50
        return round(h / total * 100), round(a / total * 100)
    except Exception:
        return 50, 50


def _parse_minute(text):
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else None


def _parse_extra(text):
    m = re.search(r"\+(\d+)", text)
    return int(m.group(1)) if m else None


# ── Step 1: find match report URL from FBref date page ─────────────────────────

def _find_report_url(date_iso, home_team, away_team):
    url = f"https://fbref.com/en/matches/{date_iso}"
    r = requests.get(url, headers=HEADERS, timeout=12)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    for row in soup.find_all("tr"):
        home_td = row.find("td", {"data-stat": "home_team"})
        away_td = row.find("td", {"data-stat": "away_team"})
        if not home_td or not away_td:
            continue
        if _name_match(home_td.get_text(strip=True), home_team) and \
           _name_match(away_td.get_text(strip=True), away_team):
            report_td = row.find("td", {"data-stat": "match_report"})
            if report_td:
                link = report_td.find("a")
                if link and link.get("href"):
                    return "https://fbref.com" + link["href"]

    return None


# ── Step 2: scrape the match report page ───────────────────────────────────────

def _scrape_report(url, date_iso):
    time.sleep(4)  # polite delay — FBref rate-limits aggressive scrapers
    r = requests.get(url, headers=HEADERS, timeout=12)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    data = {
        "home_name":  "",
        "away_name":  "",
        "home_score": None,
        "away_score": None,
        "league":     "",
        "round":      "",
        "stats":      [],
        "events":     [],
        "date_iso":   date_iso,
    }

    # ── Scorebox ───────────────────────────────────────────────────────────────
    scorebox = soup.find("div", class_="scorebox")
    if scorebox:
        performers = scorebox.find_all("div", itemprop="performer")
        if len(performers) >= 2:
            h_link = performers[0].find("a")
            a_link = performers[1].find("a")
            data["home_name"] = h_link.get_text(strip=True) if h_link else ""
            data["away_name"] = a_link.get_text(strip=True) if a_link else ""

        scores = scorebox.find_all("div", class_="score")
        if len(scores) >= 2:
            try:
                data["home_score"] = int(scores[0].get_text(strip=True))
                data["away_score"] = int(scores[1].get_text(strip=True))
            except ValueError:
                pass

        meta = scorebox.find("div", class_="scorebox_meta")
        if meta:
            links = meta.find_all("a")
            if links:
                data["league"] = links[0].get_text(strip=True)
            # Round / matchweek is usually in the same line as the league
            meta_text = meta.get_text(" ", strip=True)
            m = re.search(r"(Matchweek|Round|Week|GW)\s*(\d+)", meta_text, re.I)
            if m:
                data["round"] = m.group(0)

    # ── Team stats table (#team_stats) ────────────────────────────────────────
    stats = []
    ts_div = soup.find("div", id="team_stats")
    if ts_div:
        for row in ts_div.find_all("tr"):
            th = row.find("th")
            tds = row.find_all("td")
            if not th or len(tds) < 2:
                continue
            raw_label = th.get_text(" ", strip=True).lower()
            label = next((v for k, v in STAT_LABEL_MAP.items() if k in raw_label), None)
            if not label:
                continue
            # Values like "7 of 20" → keep just "7"
            hv = tds[0].get_text(strip=True).split(" of ")[0]
            av = tds[1].get_text(strip=True).split(" of ")[0]
            hp, ap = _bar_pct(hv, av)
            stats.append({"label": label, "home": hv, "away": av, "home_pct": hp, "away_pct": ap})

    # ── Extra stats (#team_stats_extra) ───────────────────────────────────────
    ts_extra = soup.find("div", id="team_stats_extra")
    if ts_extra:
        # FBref uses groups of 3 inner divs: [home_val, label, away_val]
        for group in ts_extra.find_all("div", recursive=False):
            children = [d for d in group.find_all("div", recursive=False) if d.get_text(strip=True)]
            if len(children) == 3:
                raw_label = children[1].get_text(strip=True).lower()
                label = next((v for k, v in STAT_LABEL_MAP.items() if k in raw_label), None)
                if not label:
                    continue
                hv = children[0].get_text(strip=True)
                av = children[2].get_text(strip=True)
                hp, ap = _bar_pct(hv, av)
                stats.append({"label": label, "home": hv, "away": av, "home_pct": hp, "away_pct": ap})

    # Deduplicate by label, keeping first occurrence
    seen = set()
    deduped = []
    for s in stats:
        if s["label"] not in seen:
            seen.add(s["label"])
            deduped.append(s)
    data["stats"] = deduped

    # ── Events (#events_wrap) ─────────────────────────────────────────────────
    events = []
    ew = soup.find("div", id="events_wrap")
    if ew:
        for ev in ew.find_all("div", class_="event"):
            classes = " ".join(ev.get("class", []))
            side = "home" if " a" in f" {classes}" else "away"

            # Minute — look for text matching digits + optional +digits + '
            minute_text = ""
            for small in ev.find_all("small"):
                t = small.get_text(strip=True)
                if re.search(r"\d+", t):
                    minute_text = t
                    break
            if not minute_text:
                # Fallback: any text node with minute pattern
                raw = ev.get_text(" ", strip=True)
                m = re.search(r"(\d+(?:\+\d+)?)'", raw)
                minute_text = m.group(0) if m else ""

            minute = _parse_minute(minute_text)
            extra  = _parse_extra(minute_text)

            # Event type — infer from icon classes and text
            icon_classes = ""
            for el in ev.find_all(True):
                ic = " ".join(el.get("class", []))
                if "icon" in ic or "card" in ic or "goal" in ic or "own" in ic:
                    icon_classes += " " + ic

            raw_text = ev.get_text(" ", strip=True).lower()

            if "own_goal" in icon_classes or "own goal" in raw_text:
                ev_type, ev_detail = "Goal", "Own Goal"
            elif "penalty" in icon_classes or "penalty" in raw_text:
                ev_type, ev_detail = "Goal", "Penalty"
            elif "goal" in icon_classes:
                ev_type, ev_detail = "Goal", "Normal Goal"
            elif "red_card" in icon_classes or "red card" in raw_text:
                ev_type, ev_detail = "Card", "Red Card"
            elif "yellow_red" in icon_classes or "second yellow" in raw_text:
                ev_type, ev_detail = "Card", "Yellow Red Card"
            elif "yellow_card" in icon_classes or "yellow card" in raw_text:
                ev_type, ev_detail = "Card", "Yellow Card"
            else:
                continue  # skip substitutions and other events

            # Player and assist links
            links = ev.find_all("a")
            player = links[0].get_text(strip=True) if links else ""
            assist = ""
            if ev_type == "Goal" and len(links) > 1:
                assist_text = ev.get_text(" ", strip=True)
                if "assist" in assist_text.lower():
                    assist = links[1].get_text(strip=True)

            if player and minute is not None:
                events.append({
                    "minute": minute,
                    "extra":  extra,
                    "side":   side,
                    "player": player,
                    "assist": assist,
                    "type":   ev_type,
                    "detail": ev_detail,
                })

    data["events"] = sorted(events, key=lambda e: (e["minute"] or 0, e["extra"] or 0))
    return data


# ── Public API (same interface as api_football.py) ─────────────────────────────

def get_match_stats(home_team, away_team, date_str, score=None):
    cache = _load_cache()
    cache_key = f"{home_team}|{away_team}|{date_str}"

    if cache_key in cache:
        return cache[cache_key]

    date_iso = parse_guardian_date(date_str)
    if not date_iso:
        return {"error": f"Could not parse date: '{date_str}'"}

    try:
        report_url = _find_report_url(date_iso, home_team, away_team)
        if not report_url:
            return {"error": f"Match not found on FBref for {date_iso}."}

        result = _scrape_report(report_url, date_iso)
        cache[cache_key] = result
        _save_cache(cache)
        return result

    except requests.exceptions.HTTPError as e:
        return {"error": f"FBref returned HTTP {e.response.status_code}. Try again later."}
    except requests.exceptions.Timeout:
        return {"error": "FBref request timed out. Try again."}
    except Exception as e:
        return {"error": str(e)}
