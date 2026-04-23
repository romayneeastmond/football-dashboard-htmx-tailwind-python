from bs4 import BeautifulSoup
import re

with open("dom.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

table = soup.find("table", class_="Table Table--align-right")
if table:
    rows = table.find_all("tr")
    print("Table Points First row:")
    print(rows[1].prettify())
