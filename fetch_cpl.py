import requests

url = "https://api-sdp.cplsoccer.com/v1/cpl/football/seasons/cpl::Football_Season::c479ab0916a24c3390f1ce2c021ace54/standings/overall?locale=en-US&orderBy=rank&direction=asc"
headers = {"User-Agent": "Mozilla/5.0"}
try:
    r = requests.get(url, headers=headers, timeout=10)
    print(r.json().get('standings', [])[0])
except Exception as e:
    print(e)
