import os
from fastapi import FastAPI,Query , Body, HTTPException, status , Depends
from fastapi.responses import Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from typing import Union
from datetime import date, datetime, timedelta
from typing import  List
import motor.motor_asyncio as motor
import pymongo
import operator
import itertools
import collections
import copy
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()


origins = [
   "http://localhost",
   "http://localhost:6060",
]
app.add_middleware(
   CORSMiddleware,
   allow_origins=origins,
   allow_credentials=True,
   allow_methods=["*"],
   allow_headers=["*"],
)

client = motor.AsyncIOMotorClient("mongodb://root:password@127.0.0.1/bcc_articles?retryWrites=true&w=majority&authSource=admin")
db = client.bcc_articles


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class ArticleModel(BaseModel):
    #id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    menu : Union[str,None] = Field(title="menu of the article", alias="menu")
    submenu : Union[str,None] = Field(title="Sub-menu of the article", alias="submenu")
    title : Union[str,None] = Field(title="Title of the article", alias="title")
    date : Union[str,None] = Field(title="Formated date of the article",example="2023-03-01", alias="date")
    date_time : Union[str,None] = Field(title="Formated date of the article",example="2023-03-01 02:27:25", alias="date_time")
    date_timestamp : Union[int,None] = Field(title="Timestampdate of the article",example="1677634045", alias="date_timestamp")
    main_image : Union[str,None] = Field(title="Url of main image of the article", alias="main_image")
    authors : Union[list[str],None]  = Field(title="Authors of the article", alias="authors")
    topics : Union[list[str],None] = Field(title="Topics of the article", alias="topics")
    article_images : Union[ list[str],None] = Field(title="Images of the article", alias="article_images")
    text : Union[str,None] = Field(title="body ofthe article", alias="text")
    url : Union[str,None] = Field(title="url of the article", alias="url")
    countries : Union[list[str],None] = Field(title="countries of the article", alias="countries")
    subjectivity : Union[str,None] = Field(title="subjectivity of the article", alias="subjectivity")
    polarity : Union[str,None] = Field(title="polarity of the article", alias="polarity")
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

@app.get(
    "/", response_description="List all articls btweendate  " , response_model=None
)
async def list_articls_by_date(start_date: Union[date, None]  = Query(default=None) , end_date: Union[date, None] = Query(default=None)):
    if (start_date is None and end_date is not None )  or (end_date is None and start_date is not None):
        raise HTTPException(
            status_code=400,
            detail="The start date and end date should be bouth as parameter",
        )
    if start_date and end_date:
        if start_date > end_date:
            raise HTTPException(
            status_code=400,
            detail="Incorrect date, end date should be geater than start date",)
        articles = await db["articles"].find({ "date": { "$gte" :start_date.strftime("%Y-%m-%d"), "$lt": end_date.strftime("%Y-%m-%d") } },{'_id': 0}).sort([('date', pymongo.ASCENDING),]).to_list(length=None)
    else:
        articles = await db["articles"].find({},{'_id': 0}).sort([('date', pymongo.ASCENDING),]).to_list(length=None)
    

    if len(articles) == 0:
        raise HTTPException(
            status_code=404,
            detail="No articls found in this date range :  ["+start_date.strftime("%Y-%m-%d")+" -> "+end_date.strftime("%Y-%m-%d")+"]",)
    start_date_data = articles[0]['date']
    end_date_data = articles[-1]['date']
    #topics
    listes_of_topics = list(filter(None, list(map(operator.itemgetter("topics"), articles))))
    list_topics= list(itertools.chain(*listes_of_topics))
    list_topics_unique = set(list_topics)
    frequency_of_topics = collections.Counter(list_topics)
    frequency_of_topics = sorted([ {"topic" : k, "count": v} for k,v in frequency_of_topics.items()] , key=lambda i: i['count'], reverse=True )

    #authors
    listes_of_authors = list(filter(None, list(map(operator.itemgetter("authors"), articles))))
    list_authors = list(itertools.chain(*listes_of_authors))
    list_authors_unique = set(list_authors)
    init_author_data = {"topics":[],"subjectivity":[],"polarity":[],"counter" : 0}
    author_by_topics_subjectivity_polarity = dict(map(lambda el : (el , copy.deepcopy(init_author_data) ),list_authors_unique))
    frequency_of_authors = dict(collections.Counter(list_authors))
    frequency_of_authors = sorted([{"author" : k, "count": v} for k,v in frequency_of_authors.items()], key=lambda i: i['count'], reverse=True )

    #countries
    listes_of_countries = list(filter(None, list(map(operator.itemgetter("countries"), articles))))
    list_countries= list(itertools.chain(*listes_of_countries))
    frequency_of_countries = dict(collections.Counter(list_countries))
    frequency_of_countries = sorted([ {"country" : k, "count": v} for k,v in frequency_of_countries.items()], key=lambda i: i['count'], reverse=True )

    #dates
    listes_of_dates= list(filter(None, list(map(operator.itemgetter("date"), articles))))
    frequency_of_dates = dict(collections.Counter(listes_of_dates))
    frequency_of_dates = [ {"date" : k, "count": v} for k,v in frequency_of_dates.items()]

    start_date_data_obj = datetime.strptime(start_date_data, '%Y-%m-%d')
    end_date_data_obj = datetime.strptime(end_date_data, '%Y-%m-%d')
    delta = end_date_data_obj - start_date_data_obj
    count_articls_in_date_tange = list()
    """ for i in range(delta.days + 1):
        day = start_date_data_obj + timedelta(days=i)
        searched_date = next((item for item in frequency_of_dates if item["date"] == day.strftime("%Y-%m-%d")),None)
        if  searched_date != None:
            count_articls_in_date_tange.append(searched_date)
        else:
            count_articls_in_date_tange.append({"date" : day.strftime("%Y-%m-%d"), "count" : 0}) """

    for i in range(delta.days + 1):
        day = start_date_data_obj + timedelta(days=i)
        searched_date = next((item for item in frequency_of_dates if item["date"] == day.strftime("%Y-%m-%d")),None)
        if  searched_date != None:
            searched_date['date'] = datetime.timestamp(datetime.strptime(searched_date['date'], '%Y-%m-%d'))
            count_articls_in_date_tange.append(searched_date)
        else:
            count_articls_in_date_tange.append({"date" : datetime.timestamp(day), "count" : 0})

    
    list_of_topics_relations = list()
    #Authors by topics and sentiment
    for article in articles:
        if article["authors"] is  not None:
            for author in article["authors"]:
                author_by_topics_subjectivity_polarity[author]["topics"] =  list(set(author_by_topics_subjectivity_polarity[author]['topics'] + article['topics'] ))
                author_by_topics_subjectivity_polarity[author]["subjectivity"].append(float(article['subjectivity']))
                author_by_topics_subjectivity_polarity[author]["polarity"].append(float(article['polarity']))
                author_by_topics_subjectivity_polarity[author]["counter"] = int(author_by_topics_subjectivity_polarity[author]["counter"]) + 1
        if article["topics"] is  not None:
            for topic in article["topics"]:
                topics_copy = copy.deepcopy(article["topics"])
                topics_copy.remove(topic)
                for cpy_topic in topics_copy:
                    list_of_topics_relations.append([topic,cpy_topic , 1])
    unique_list_of_topics_relations = [list(x) for x in set(tuple(x) for x in list_of_topics_relations)]
    for key ,val in  author_by_topics_subjectivity_polarity.items():
        val["subjectivity"] = sum(val["subjectivity"])/val["counter"]
        val["polarity"] = sum(val["polarity"])/val["counter"]
 
    return {
            "articles" : articles, 
            "frequency_of_topics" :frequency_of_topics ,
            "frequency_of_authors" :frequency_of_authors ,
            "frequency_of_countries" :frequency_of_countries ,
            "author_by_topics_subjectivity_polarity" : author_by_topics_subjectivity_polarity,
            "count_articls_per_day" : count_articls_in_date_tange,
            "unique_list_of_topics_relations" : unique_list_of_topics_relations,
            "start_date_data" : start_date_data,
            "end_date_data" : end_date_data
        }

        