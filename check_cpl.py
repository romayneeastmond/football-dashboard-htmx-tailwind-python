import sys
import json
from scrape_cpl import scrape_cpl
res = scrape_cpl()
with open("cpl_debug.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2)
