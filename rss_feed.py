import random
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

def get_fss_feed(url, source):
    response = requests.get(url)
    
    if response.status_code != 200:
        return []

    root = ET.fromstring(response.content)
    articles = []
    randomized_articles = []

    for item in root.findall(".//item"):
        title = item.find("title").text
        link = item.find("link").text
        
        pub_date = item.find("pubDate").text
        
        formatted_date = ""
        
        if pub_date:
            try:
                formatted_date = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z").strftime("%B %d, %Y")
            except ValueError:
                formatted_date = pub_date
        
        image = "/static/fallback.png"
        image_url = item.find(".//media:content", {"media": "http://search.yahoo.com/mrss/"})
        
        if image_url is not None:
            image = image_url.attrib['url']
        else:
            image_url = item.find(".//media:thumbnail", {"media": "http://search.yahoo.com/mrss/"})
            
            if image_url is not None:
                image = image_url.attrib['url']

        articles.append({
            "title": title,
            "date": formatted_date,
            "link": link,
            "image": image,
            "source": source
        })
    
    random.shuffle(articles)
    randomized_articles.extend(articles)
   
    return randomized_articles if randomized_articles else None
