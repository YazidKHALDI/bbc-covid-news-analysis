# BBC Covid news analysis  

# Quickstart
1. Clone repo `git clone https://github.com/YazidKHALDI/bbc-covid-news-analysis`
2. Run `cd bbc-covid-news-analysis`
3. Run `python3.9 -m venv python_env; . python_env/bin/activate`
4. Run `mkdir -p ./logs ./plugins`
5. Run `pip install "apache-airflow[celery]==2.5.1" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.5.1/constraints-3.9.txt"`  **(Chnage 3.9 with your python version)**
6. Run `cd api` and run `pip install -r requirements.txt`
7. Run `cd ..` and run `echo -e "AIRFLOW_UID=$(id -u)" > .env` **(only on first use)**
8. Run `cd docker_build` and run `docker compose build`
9. Run `cd ..` and run `docker-compose up airflow-init` **(only on first use)**
10. Run `docker compose  up -d` then access airflow on http://localhost:8080 and access to mongodb GUI with http://localhost:4321/
11. Run `cd api` and run `uvicorn app:app --reload` then get articls from api using http://localhost:8000/ to get all articls.
12. Run `cd app` and run `npm i`, then `npm run build` 
13. Run `node server.js` then access the web application on  http://localhost:6000/

## 1 - Data Engineering:
### 1.1 scraper
To scrap the data of BBC's new articles using airflow I decide to run airflow using docker, and I used DockerFile to extend Image and install all requirements needed for scrapping.
```Dockerfile
FROM apache/airflow:2.5.1-python3.9
COPY requirements.txt .
RUN pip install --user --upgrade pip
RUN pip install --no-cache-dir --user -r requirements.txt
```
and the script `scraper/main.py` mounted in `- ${AIRFLOW_PROJ_DIR:-.}/scraper:/opt/airflow/scraper` so we can run our scraping script using airflow DAGS.
in The scraper code, we have  2 parts, scraping home page articles `scrap_topos_component()`, and the last news article `scrap_latest_updates()` with a start date and end date as a parameter.

```python
def scrap_corna_news_by_date(start_date, end_date):
    print("Start scrapping Data \nfrom\t"+str(datetime.fromtimestamp(start_date).strftime("%Y-%m-%d %H:%M:%S")) +"\nto\t"+str(datetime.fromtimestamp(end_date).strftime("%Y-%m-%d %H:%M:%S")))
    print("step 1 : scarping of top artics")
    scrap_topos_component(start_date, end_date)
    print("step 1 Done")

    print("step 2 : scarping of Latest Updates artics")
    scrap_latest_updates(start_date, end_date)
    print("step 2 Done")
```
the goal here is to get the URL of the article and then scrap its content, here we have two types of URL, the URLs of the first section in the home page then the section of **Latest Updates**
For the first section, I scraped the HTML to get the URL that respects the date range
```python
def get_topos_component_urls_by_date(start_date=None, end_date=None):
    url = "https://www.bbc.com/news/coronavirus"
    response = requests.get(url)
    if response.status_code == 404:
        exit('Page cannot be found')
    soup = BeautifulSoup(response.content, "html5lib")
    return {url_data['url']: url_data for url_data in [{"url": base_url + str(link.get('href')), "date":  get_lisnk_date(link)} for link in soup.find('div', id="topos-component").findAll('a') if "gs-c-section-link--truncate" not in link['class'] if get_lisnk_date(link) is not None and (start_date <= get_lisnk_date(link) <= end_date) ]}.values()
```
but for the Latest Updates I found **API URL** to git the list of articles paginated  [example page 6](https://push.api.bbci.co.uk/batch?t=/data/bbc-morph-lx-commentary-data-paged/about/63b2bbc8-6bea-4a82-9f6b-6ecc470d0c45/isUk/false/limit/20/nitroKey/lx-nitro/pageNumber/6/version/1.5.6?timeout=5)

```python
def scrap_latest_updates(start_date=None, end_date=None):
    ...
     response = requests.get("https://push.api.bbc....")
        if response.status_code == 404:
            continue
        res = response.json()
        ...
            if ("url" in article) and article['type'] == 'STY':
                    article_url = base_url+str(article['url'])
    ...
```

then we come to the main function `def scrap_article_body_by_url(url):`  the function which accepts the url and return ```dict```:

to scrap the data I found this javascript variable contains all informations about the article as unparsed JSON.

```html
<script nonce="">
window.__INITIAL_DATA__="{\"data\":{\"chameleon-global-navigation?country=ma&language=en-GB\":{\"name........}}";
</script>
```
the result is this object :

```python
{
    "menu" : article_menu,
    "submenu" : article_sub_menu,
    "title" : article_title,
    "date" : article_date,
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
```
and I extract the list of countries using `GeoText` and sentiment from the article using `TextBlob`.

The final step is to insert data to `MongoDB`, the service that I add to `docker-compose.yaml`

so to communicate with DB we use `pymongo`
```python
def get_db():
    CONNECTION_STRING = "mongodb://root:password@mongodb:27017/?directConnection=true&serverSelectionTimeoutMS=2000&appName=mongosh+1.6.2"
    client = MongoClient(CONNECTION_STRING)
    return client.bcc_articles
```
After the extraction of the article we insert the data to collection

```python
def insert_articles_to_db(article_record):
    if article_record is not None:
        db = get_db()
        collection = db.articles
        collection.insert_one(article_record)
        global counter
        counter = counter + 1 
        print("[Done]date: "+str(article_record['date'])+"\ttitle : "+str(article_record['title'])+"\tulr : "+ str(article_record['url'])+"\n")
```
### 1.2 Airflow
to automate the scrapping of articles we create two DAGS, the first schedule `@once` and it scraps all coronavirus news in the last 100 days.
```python
with DAG(
    "scrapignlast_last_100_day_news",
    default_args={
        ...
    },
    description="Scraping new articles every day for 5 days continuously",
    schedule="@once",
    start_date=datetime.now(),
) as dag:
    t1 = BashOperator(
        task_id="scrapignlast_news",
        bash_command="python /opt/airflow/scraper/main.py"
    )
```
 the second DAG to scrap the news `@daily` the articles of the last day

 ```python
with DAG(
    "scrapignlast_news_daily",
    default_args={
        ...
    },
    ...
    schedule="@daily",
    start_date=datetime.now(),
    ...
) as dag:
    t1 = BashOperator(
        task_id="scrapignlast_news_daily",
        bash_command="python /opt/airflow/scraper/main.py --daily"
    )
```
then we need to activate the 2 DAGs, the first one will execute once to store all articles of the last 3 months on DB, then activate the second DAG that will execute daily.

![airflow dags](/img/pic0.png "airflow dags")

You can check the scraping logs of DAG

![airflow scraping DAG](/img/pic6.png "airflow scraping DAG")

you can access mongodb GUI on http://localhost:4321/


## 2 - API:
After the data are collected I created a small API using `FastAPI` 
the goal to get `all articles`.

```
http://localhost:8000/
```

Or the article of `specific date ranger` for example from 01/01/2023 to 01/02/2023.

```
http://localhost:8000/?start_date=2023-01-01&end_date=2023-02-01
```
the results is a this json object:
```json
{
    "articles": [],
    "frequency_of_topics": {
        "Xi Jinping": 5,
        "China": 67,
        "Coronavirus pandemic": 265,
    },
    "frequency_of_authors": {
        "Stephen McDonell": 4,
        "Tessa Wong and Nathan Williams": 1,
        "Katie Razzall": 2,
        "Tessa Wong": 2,
    },
    "frequency_of_countries": {
        "China": 81,
        "Singapore": 8,
        "Australia": 11,
        "Hong Kong": 21,
    },
    "author_by_topics_subjectivity_polarity": {
        "Lola Mayor": {
            "topics": [
                "Brecon",
                "Cardiff",
                "Wrexham",
                "Brecon Beacons",
                "Canada",
                "Social media",
                "Welsh government",
                "TikTok",
                "Social media influencers"
            ],
            "subjectivity": 0.6215147392290248,
            "polarity": 0.32200027485741783,
            "counter": 1
        }
    },
    "count_articls_per_day": [
        {
            "date": 1669935600,
            "count": 4
        },
        {
            "date": 1670022000,
            "count": 2
        },
        {
            "date": 1670108400,
            "count": 1
        }
            ...
    ],
    "unique_list_of_topics_relations": [
        [
            "Coronavirus lockdown measures",
            "Aldridge",
            1
        ],
        [
            "Charities",
            "Scottish government",
            1
        ],
        [
            "Economic growth",
            "Food",
            1
        ]..
    ]
}
```
* `"articles"` : it's a simple list of articles from DB
* `"frequency_of_topics"` : Count number of topics in articles
* `"frequency_of_authors"` : Count number of authors in articles
* `"frequency_of_countries"` : Count number of countries in articles
* `"author_by_topics_subjectivity_polarity"` : The `topics` of every author and the average of `subjectivity` and `polarity`
* `"count_articls_per_day"` : Number of articles published per day, the publish date represented as `timestamp`. 
* `"unique_list_of_topics_relations"` : List of the links between all topics.
* `"start_date_data"` : Lowest date between published news articles.
* `"end_date_data"` : Highest date between published news articles.

## 3 - Visualization:
For the Visualization I decided to use [Highcharts](https://www.highcharts.com/demo).

After you visit the http://localhost:6060/ without specifying the date range you will see the information about all articles on DB  and then you can select the date range needed using the date picker.
![Date picker](/img/date_picker.png "Date picker")

The first chart is a visualization of the frequency of articles published, with the possibility of zooming on a specific period.

![Publication frequency of news articles](/img/pic1.png "Publication frequency of news articles")

The second part is about `Authors`, a simple chart showing the number of articles written per author, and sentiment analysis for all new articles per author to calculate the average value of polarity and subjectivity.

![Polarity and Subjectivity average per author](/img/pic2.png "Polarity and Subjectivity average per author")

The third part is about `Topics`, a simple chart showing the number of topics appear in article, and worldCloud of topics word more used.

I added a Dependency wheel to visualize the relationship between every topic used in the same article, but the Dependency wheel  shows only if the links between topics `are less than 1000` because it's hard to read the chart if there is a lot of relationships.

![Number of articles per topic](/img/pic3.png "Number of articles per topic")

![Number of articles per topic](/img/pic4.png "Number of articles per topic")

the fourth part is about `countries`,  a simple chart showing the number of countries that appears in the article, and a map visualization.

![Number of countries per topic](/img/pic5.png "Number of countries per topic")