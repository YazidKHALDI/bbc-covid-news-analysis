import requests
import sys
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timedelta, time
from pymongo import MongoClient
from textblob import TextBlob
from geotext import GeoText
import os



base_url = "https://www.bbc.com"
counter = 1

def get_db():
    CONNECTION_STRING = "mongodb://root:password@mongodb:27017/?directConnection=true&serverSelectionTimeoutMS=2000&appName=mongosh+1.6.2"
    client = MongoClient(CONNECTION_STRING)
    return client.bcc_articles

def get_lisnk_date(link):
    if link.parent.parent.find('time', {"class": "qa-status-date"}) is not None:
        return int(link.parent.parent.find('time', {"class": "qa-status-date"})['data-seconds'])
    return None


def get_topos_component_urls_by_date(start_date=None, end_date=None):
    url = "https://www.bbc.com/news/coronavirus"
    response = requests.get(url)
    if response.status_code == 404:
        exit('Page cannot be found')
    soup = BeautifulSoup(response.content, "html5lib")
    return {url_data['url']: url_data for url_data in [{"url": base_url + str(link.get('href')), "date":  get_lisnk_date(link)} for link in soup.find('div', id="topos-component").findAll('a') if "gs-c-section-link--truncate" not in link['class'] if get_lisnk_date(link) is not None and (start_date <= get_lisnk_date(link) <= end_date) ]}.values()

def scrap_latest_updates(start_date=None, end_date=None):
    page = 1
    time_to_beak = False
    while True:
        print("page "+str(page))
        response = requests.get("https://push.api.bbci.co.uk/batch?t=/data/bbc-morph-lx-commentary-data-paged/about/63b2bbc8-6bea-4a82-9f6b-6ecc470d0c45/isUk/false/limit/20/nitroKey/lx-nitro/pageNumber/"+str(page)+"/version/1.5.6?timeout=5")
        if response.status_code == 404:
            continue
        res = response.json()
        articles = res['payload'][0]['body']['results']
        for article in articles:
            article_date_added = datetime.fromisoformat(article['dateAdded'].removesuffix("Z"))
            if start_date is not None and end_date is not None and ( start_date <= datetime.timestamp(article_date_added) <= end_date):
                if ("url" in article) and article['type'] == 'STY':
                    article_url = base_url+str(article['url'])
                    article_record = scrap_article_body_by_url(article_url)
                    insert_articles_to_db(article_record)
            else:
                time_to_beak = True
                break
        if time_to_beak:
            break
        page = page + 1
        
        
def insert_articles_to_db(article_record):
    if article_record is not None:
        db = get_db()
        collection = db.articles
        collection.insert_one(article_record)
        global counter
        counter = counter + 1 
        print("[Done]date: "+str(article_record['date'])+"\ttitle : "+str(article_record['title'])+"\tulr : "+ str(article_record['url'])+"\n")

def scrap_topos_component(start_date, end_date):
    topos_urls = get_topos_component_urls_by_date(start_date, end_date)
    for url in topos_urls:
        article_url = url['url']
        article_record = scrap_article_body_by_url(article_url)
        insert_articles_to_db(article_record)
        



def scrap_article_body_by_url(url):
    print("[inProgress] url : "+url)
    response = requests.get(url)
    if response.status_code == 404:
        exit('Page cannot be found')
    soup = BeautifulSoup(response.content, "html5lib")
    script = soup.find("script", string=re.compile(
        "__INITIAL_DATA__")).string.strip().replace('window.__INITIAL_DATA__="', "")
    if script[len(script)-2:] == '";':
        script = script[:-2]
    script = script.replace('\\"', '"').replace('\\\"', '"')
    jsonR = json.loads(script)
    props = None
    for story in jsonR["page"]["entry"]["stores"]:
        if story['name'] == "article":
            props = story["initialState"]["props"]
    if props is None:
        return props
    for prop in props:
        if prop['name'] == "metadata":
            metadata = prop['value']
        if prop['name'] == "articleBodyContent":
            articleBodyContent = prop['value']   
    article_title = metadata['title']['short']
    article_date_fromtimestamp = metadata['lastPublished']/ 1000
    article_date_time = datetime.fromtimestamp(metadata['lastPublished'] / 1000).strftime("%Y-%m-%d %H:%M:%S")
    article_date = datetime.fromtimestamp(metadata['lastPublished'] / 1000).strftime("%Y-%m-%d")
    article_main_img = metadata['indexImage']['originalSrc']
    article_authors = [word.strip() for word in metadata['contributor']['title'].replace('By ', '').split('&') ] if metadata['contributor'] is not None else None
    article_topics = [link.string for link in soup.find("div",attrs={"data-component": "topic-list"}).findAll('a')]
    article_menu = "coronavirus"
    article_sub_menu = metadata['section']['name'] if  'section' in metadata else None
    article_text = ""
    article_images = list()
    for paragraphe in articleBodyContent:
        if paragraphe['type'] == "text":
            article_text = article_text + str(paragraphe['model']['blocks'][0]['model']['text'])
        if paragraphe['type'] == "image":
            for block in paragraphe['model']['blocks']:
                if block['type'] == "rawImage":
                    article_images.append("https://ichef.bbci.co.uk/news/" + str(block['model']['width']) + "/" + str(block['model']['originCode']) + "/" + str(block['model']['locator']))
    print("\t[\u2713] Scrap data")
    if article_text == "":
        print("\t[\u0078] Article skipped")
        return None
    countries = list(set(GeoText(article_title + article_text).countries))
    print("\t[\u2713] Extract countries") 
    analysis= TextBlob(article_text)
    subjectivity = analysis.sentiment.subjectivity
    polarity = analysis.sentiment.polarity
    print("\t[\u2713] Calculate subjectivity & polarity")
    print("\t[\u2713] Article N° "+str(counter))
    article_record = {
                    "menu" : article_menu,
                    "submenu" : article_sub_menu,
                    "title" : article_title,
                    "date" : article_date,
                    "date_time" : article_date_time,
                    "date_timestamp" : article_date_fromtimestamp,
                    "main_image" : article_main_img,
                    "authors" : article_authors,
                    "topics" : article_topics,
                    "article_images" : article_images,
                    "text" : article_text,
                    "url" : url,
                    "countries" : countries if countries  else None,
                    "subjectivity" : subjectivity,
                    "polarity" : polarity
                } 
    return article_record



def scrap_corna_news_by_date(start_date, end_date):
    print("Start scrapping Data \nfrom\t"+str(datetime.fromtimestamp(start_date).strftime("%Y-%m-%d %H:%M:%S")) +"\nto\t"+str(datetime.fromtimestamp(end_date).strftime("%Y-%m-%d %H:%M:%S")))
    print("step 1 : scarping of top artics")
    scrap_topos_component(start_date, end_date)
    print("step 1 Done")

    print("step 2 : scarping of Latest Updates artics")
    scrap_latest_updates(start_date, end_date)
    print("step 2 Done")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--daily":
        scrap_corna_news_by_date((datetime.combine(datetime.today(), time.min) - timedelta(days=1)).timestamp(),datetime.combine(datetime.today(), time.min).timestamp())
    else:
        scrap_corna_news_by_date(datetime.timestamp(datetime.now() - timedelta(days=100)),datetime.timestamp(datetime.now() ))