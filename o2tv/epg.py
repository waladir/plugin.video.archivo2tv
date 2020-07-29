# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

import sqlite3
import json
from urllib import quote
from datetime import date, datetime, timedelta
import time

from o2tv.o2api import call_o2_api
from o2tv import o2api
from o2tv.channels import load_channels 

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')
addon_userdata_dir = xbmc.translatePath(addon.getAddonInfo('profile')) 
current_version = 6


def open_db():
    global db, version
    db = sqlite3.connect(addon_userdata_dir + "epg.db", timeout = 20)
    db.execute('CREATE TABLE IF NOT EXISTS version (version INTEGER PRIMARY KEY)')
    db.execute('CREATE TABLE IF NOT EXISTS epg (epgId INTEGER PRIMARY KEY, startTime INTEGER, endTime INTEGER, channel VARCHAR(255), title VARCHAR(255))')
    db.execute('CREATE TABLE IF NOT EXISTS epg_details (epgId INTEGER PRIMARY KEY, cover VARCHAR(255), description VARCHAR(255), ratings VARCHAR(255), cast VARCHAR(255), directors VARCHAR(255), year VARCHAR(255), country VARCHAR(255), original VARCHAR(255), genres VARCHAR(255), imdb VARCHAR(255))')
    
    row = None
    for row in db.execute('SELECT version FROM version'):
      version = row[0]
    if not row:
        db.execute('INSERT INTO version VALUES (?)', [current_version])
        db.commit()     
        version = current_version
    if version != current_version:
      version = migrate_db(version)
    db.commit()     

def close_db():
    global db
    db.close()    

def migrate_db(version):
    global db
    if version == 4:
      version = 5
      db.execute('ALTER TABLE epg ADD COLUMN startTime INTEGER')
      db.execute('ALTER TABLE epg ADD COLUMN endTime INTEGER')
      db.execute('ALTER TABLE epg ADD COLUMN channel INTEGER')
      db.execute('ALTER TABLE epg ADD COLUMN title INTEGER')
      db.execute('UPDATE version SET version = ?', str(version))
      db.commit()       
    if version == 5:
      version = 6
      db.execute('DELETE FROM epg_details WHERE description=\'\' AND cover=\'\'')
      db.execute('UPDATE version SET version = ?', str(version))
      db.commit()       

    return version

def load_epg_details():
    global db
    events_detailed_data = {}
    url = "https://www.o2tv.cz/unity/api/v1/epg/"
    data = o2api.call_o2_api(url = url, data = None, header = o2api.header_unity)
    if "err" in data:
      print("Chyba API O2 při načítání detailních dat pro EPG!")
      sys.exit()
    if "result" in data and len(data["result"]) > 0 and "count" in data and data["count"] > 0:
      offset = 0
      step = 50
      cnt = data["count"]
      for offset in range(0, cnt + step, step):
        url = "https://www.o2tv.cz/unity/api/v1/epg/?offset=" + str(offset)
        data = o2api.call_o2_api(url = url, data = None, header = o2api.header_unity)
        if "err" in data:
          print("Chyba API O2 při načítání detailních dat pro EPG!")
          sys.exit()
        if "result" in data and len(data["result"]) > 0:
          for event in data["result"]:
            cover = ""
            description = ""
            ratings = {}
            cast = []
            directors = []
            year = ""
            country = ""
            original = ""
            imdb = ""
            genres = []
            if "images" in event and len(event["images"]) > 0:
              cover = event["images"][0]["cover"]
            elif "picture" in event and len(event["picture"]) > 0:
              cover = event["picture"]
            if "longDescription" in event and len(event["longDescription"]) > 0:
              description = event["longDescription"]
            elif "shortDescription" in event and len(event["shortDescription"]) > 0:
              description = event["shortDescription"]
            if "ratings" in event and len(event["ratings"]) > 0:
              for rating, rating_value in event["ratings"].items():
                ratings.update({ rating : int(rating_value)/10})
            if "castAndCrew" in event and len(event["castAndCrew"]) > 0 and "cast" in event["castAndCrew"] and len(event["castAndCrew"]["cast"]) > 0:
              for person in event["castAndCrew"]["cast"]:      
                cast.append(person["name"].encode("utf-8"))
            if "castAndCrew" in event and len(event["castAndCrew"]) > 0 and "directors" in event["castAndCrew"] and len(event["castAndCrew"]["directors"]) > 0:
              for person in event["castAndCrew"]["directors"]:      
                directors.append(person["name"].encode("utf-8"))
            if "origin" in event and len(event["origin"]) > 0:
              if "year" in event["origin"] and len(str(event["origin"]["year"])) > 0:
                year = event["origin"]["year"]
              if "country" in event["origin"] and len(event["origin"]["country"]) > 0:
                country = event["origin"]["country"]["name"]
            if "origName" in event and len(event["origName"]) > 0:
              original = event["origName"]
            if "ext" in event and len(event["ext"]) > 0 and "imdbId" in event["ext"] and len(event["ext"]["imdbId"]) > 0:
              imdb = event["ext"]["imdbId"]
            if "genreInfo" in event and len(event["genreInfo"]) > 0 and "genres" in event["genreInfo"] and len(event["genreInfo"]["genres"]) > 0:
              for genre in event["genreInfo"]["genres"]:      
                genres.append(genre["name"].encode("utf-8"))
            events_detailed_data.update({event["epgId"] : {"cover" : cover, "description" : description, "ratings" : ratings, "cast" : cast, "directors" : directors, "year" : year, "country" : country, "original" : original, "genres" : genres, "imdb" : imdb}})    
    cnt = 0
    open_db()
    for epgId in events_detailed_data.keys():
      row = None
      for row in db.execute('SELECT * FROM epg WHERE epgId = ?', [epgId]):
        event = row
      if row:
        row = None
        for row in db.execute('SELECT * FROM epg_details WHERE epgId = ?', [epgId]):
          event = row
        if not row:
          cnt = cnt + 1
          db.execute('INSERT INTO epg_details VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (epgId, events_detailed_data[epgId]["cover"], events_detailed_data[epgId]["description"], json.dumps(events_detailed_data[epgId]["ratings"]), json.dumps(events_detailed_data[epgId]["cast"]), json.dumps(events_detailed_data[epgId]["directors"]), events_detailed_data[epgId]["year"], events_detailed_data[epgId]["country"], events_detailed_data[epgId]["original"], json.dumps(events_detailed_data[epgId]["genres"]), events_detailed_data[epgId]["imdb"]))      
    db.commit()
    close_db()
    print("INSERTED epg_details: " + str(cnt))

def load_epg_ts(channelKeys, from_ts, to_ts):
    global db
    events_data = {}
    params = ""
    for channelKey in channelKeys:
      params = params + ("&channelKey=" + quote(channelKey.encode("utf-8"))) 
    url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?forceLimit=true&limit=500" + params + "&from=" + str(from_ts*1000) + "&to=" + str(to_ts*1000) 
    data = o2api.call_o2_api(url = url, data = None, header = o2api.header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Chyba API O2 při načítání EPG!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()
    if "epg" in data and len(data["epg"]) > 0 and "items" in data["epg"] and len(data["epg"]["items"]) > 0:
      for channel in data["epg"]["items"]:
        for event in channel["programs"]:
          events_data.update({event["epgId"] : {"startTime" : int(event["start"]/1000), "endTime" : int(event["end"]/1000), "channel" : channel["channel"]["name"], "title" : event["name"]}})
    cnt = 0
    open_db()
    for epgId in events_data.keys():
      row = None
      for row in db.execute('SELECT * FROM epg WHERE epgId = ?', [epgId]):
        event = row
      if not row:
        cnt = cnt + 1
        db.execute('INSERT INTO epg VALUES(?, ?, ?, ?, ?)', (epgId, events_data[epgId]["startTime"], events_data[epgId]["endTime"], events_data[epgId]["channel"], events_data[epgId]["title"]))      
    db.commit()
    close_db()
    print("INSERTED epg: " + str(cnt))

def load_epg_all():
    if int(addon.getSetting("epg_min")) < 1 or int(addon.getSetting("epg_min")) > 10:
      xbmcgui.Dialog().notification("Sledování O2TV","Počet dnů pro EPG musí být v intervalu 1 až 10!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()
    if int(addon.getSetting("epg_fut")) < 1 or int(addon.getSetting("epg_fut")) > 10:
      xbmcgui.Dialog().notification("Sledování O2TV","Počet dnů pro EPG musí být v intervalu 1 až 10!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()

    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
    channelKeys = []
    for num in sorted(channels_nums.keys()):
      channelKeys.append(channels_data[channels_nums[num]]["channelKey"])

    # open_db()
    # for row in db.execute('SELECT min(max_startTime) FROM (SELECT channel, max(startTime) max_startTime FROM epg GROUP BY channel)'):
    #   if row and len(row) > 0 and row[0] != None:
    #     min_ts = int(row[0])
    # if not row or row[0] == None:
    #   min_ts = 0
    # close_db()
    min_ts = 0

    for day in range(int(addon.getSetting("epg_min"))*-1,int(addon.getSetting("epg_fut")),1):
      from_datetime = datetime.combine(date.today(), datetime.min.time()) - timedelta(days = -1*int(day))
      from_ts = int(time.mktime(from_datetime.timetuple()))
      to_ts = from_ts+(24*60*60)-1
      if to_ts > min_ts:
        if from_ts < min_ts:
          from_ts = min_ts
        load_epg_ts(channelKeys, from_ts, to_ts)

    load_epg_details()  

    obsolete_ts = datetime.combine(date.today(), datetime.min.time()) - timedelta(days = -30*int(day))
    open_db()
    db.execute('DELETE FROM epg WHERE startTime < ?', [obsolete_ts])
    db.execute('DELETE FROM epg_details WHERE epgId NOT IN (SELECT epgId FROM epg)')
    close_db()

def get_epg_details(epgId):
    global db

    open_db()
    row = None
    for row in db.execute('SELECT * FROM epg_details WHERE epgId = ?', [epgId]):
      epgId = row[0]
      cover = row[1]
      description = row[2]
      ratings = json.loads(row[3])
      cast = json.loads(row[4])
      directors = json.loads(row[5])
      year = row[6]
      country = row[7]
      original = row[8]
      genres = json.loads(row[9])
      imdb = row[10]
    if not row:
      cover = ""
      description = ""
      ratings = {}
      cast = []
      directors = []
      year = ""
      country = ""
      original = ""
      imdb = ""
      genres = []

      data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/programs/" + str(epgId) + "/", data = None, header = o2api.header_unity)
      if not "err" in data:
        if "images" in data and len(data["images"]) > 0:
          cover = data["images"][0]["cover"]
        elif "picture" in data and len(data["picture"]) > 0:
          cover = data["picture"]
        if "longDescription" in data and len(data["longDescription"]) > 0:
          description = data["longDescription"]
        elif "shortDescription" in data and len(data["shortDescription"]) > 0:
          description = data["shortDescription"]
        if "ratings" in data and len(data["ratings"]) > 0:
          for rating, rating_value in data["ratings"].items():
            ratings.update({ rating : int(rating_value/10)})
        if "castAndCrew" in data and len(data["castAndCrew"]) > 0 and "cast" in data["castAndCrew"] and len(data["castAndCrew"]["cast"]) > 0:
          for person in data["castAndCrew"]["cast"]:      
            cast.append(person["name"])
        if "castAndCrew" in data and len(data["castAndCrew"]) > 0 and "directors" in data["castAndCrew"] and len(data["castAndCrew"]["directors"]) > 0:
          for person in data["castAndCrew"]["directors"]:      
            directors.append(person["name"])
        if "origin" in data and len(data["origin"]) > 0:
          if "year" in data["origin"] and len(str(data["origin"]["year"])) > 0:
            year = data["origin"]["year"]
          if "country" in data["origin"] and len(data["origin"]["country"]) > 0:
            country = data["origin"]["country"]["name"]
        if "origName" in data and len(data["origName"]) > 0:
          original = data["origName"]
        if "ext" in data and len(data["ext"]) > 0 and "imdbId" in data["ext"] and len(data["ext"]["imdbId"]) > 0:
          imdb = data["ext"]["imdbId"]
        if "genreInfo" in data and len(data["genreInfo"]) > 0 and "genres" in data["genreInfo"] and len(data["genreInfo"]["genres"]) > 0:
          for genre in data["genreInfo"]["genres"]:      
            genres.append(genre["name"])
        db.execute('INSERT INTO epg_details VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (epgId, cover, description, json.dumps(ratings), json.dumps(cast), json.dumps(directors), year, country, original, json.dumps(genres), imdb))      
        db.commit()
    close_db()
    event = { "epgId" : epgId, "cover" : cover, "description" : description, "ratings" : ratings, "cast" : cast, "directors" : directors, "year" : year, "country" : country, "original" : original, "genres" : genres, "imdb" : imdb }
    return event

def get_listitem_epg_details(list_item, epgId, img):
    event = get_epg_details(epgId)
    cast = []
    directors = []
    genres = []
    list_item.setInfo("video", {"mediatype":"movie"})
    if "cover" in event and len(event["cover"]) > 0:
       list_item.setArt({'poster': "https://www.o2tv.cz/" + event["cover"],'thumb': "https://www.o2tv.cz/" + event["cover"], 'icon': "https://www.o2tv.cz/" + event["cover"]})
    else:
       list_item.setArt({'thumb': img, 'icon': img})    
    if "description" in event and len(event["description"]) > 0:
       list_item.setInfo("video", {"plot": event["description"]})
    if "ratings" in event and len(event["ratings"]) > 0:
       for rating, rating_value in event["ratings"].items():
         list_item.setRating(rating, int(rating_value))
    if "cast" in event and len(event["cast"]) > 0:
       for person in event["cast"]:      
         cast.append(person.encode("utf-8"))
       list_item.setInfo("video", {"cast" : cast})  
    if "directors" in event and len(event["directors"]) > 0:
       for person in event["directors"]:      
         directors.append(person.encode("utf-8"))
       list_item.setInfo("video", {"director" : directors})  
    if "year" in event and len(str(event["year"])) > 0:
      list_item.setInfo("video", {"year": int(event["year"])})
    if "country" in event and len(event["country"]) > 0:
      list_item.setInfo("video", {"country": event["country"]})
    if "original" in event and len(event["original"]) > 0:
       list_item.setInfo("video", {"originaltitle": event["original"]})
    if "imdb" in event and len(event["imdb"]) > 0:
       list_item.setInfo("video", {"imdbnumber": event["imdb"]})
    if "genres" in event and len(event["genres"]) > 0:
       for genre in event["genres"]:      
         genres.append(genre.encode("utf-8"))
       list_item.setInfo("video", {"genre" : genres})    
    return list_item

def get_epg_all():
    events_data = {}
    events_detailed_data = {}
    
    limit = 8
    limit_ts = int(time.mktime(datetime.now().timetuple())) - 60*60*24*limit

    open_db()
    row = None
    for row in db.execute('SELECT * FROM epg WHERE startTime >= ?',[str(limit_ts)]):
      epgId = int(row[0])
      startTime = int(row[1])
      endTime = int(row[2])    
      channel = row[3]
      title = row[4]

      if channel not in events_data:
        events_data[channel] = { startTime : {"epgId" : epgId, "startTime" : startTime, "endTime" : endTime, "channel" : channel, "title" : title }}
      else:  
        events_data[channel].update({ startTime : {"epgId" : epgId, "startTime" : startTime, "endTime" : endTime, "channel" : channel, "title" : title }})

    for row in db.execute('SELECT * FROM epg_details'):
      epgId = int(row[0])
      cover = row[1]
      description = row[2]
      ratings = json.loads(row[3])
      cast = json.loads(row[4])
      directors = json.loads(row[5])
      year = row[6]
      country = row[7]
      original = row[8]
      genres = json.loads(row[9])
      imdb = row[10]
      events_detailed_data.update({ epgId : {"name" : title, "desc" : description, "icon" : "https://www.o2tv.cz" + cover, "cast" : cast, "directors" : directors, "year" : year, "country" : country, "genres" : genres, "ratings" : ratings, "imdb" : imdb, "original" : original }})

    close_db()
    return events_data, events_detailed_data

def get_epg_ts(channelKey, from_ts, to_ts, min_limit):
    events_data = {}
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable    
    channelName = channels_key_mapping[channelKey]    

    open_db()
    row = None
    cnt = 0
    for row in db.execute('SELECT count(1) FROM epg WHERE startTime >= ? AND startTime <=? AND channel = ?', [from_ts, to_ts, channelName]):
      cnt = row[0]
    if cnt < min_limit:
      channelKeys = [channelKey]
      load_epg_ts(channelKeys, from_ts, to_ts)  
      open_db()
    for row in db.execute('SELECT epgId, startTime, endTime, title FROM epg WHERE startTime >= ? AND startTime <=? AND channel = ?', [from_ts, to_ts, channelName]):
      epgId = int(row[0])
      startTime = int(row[1])
      endTime = int(row[2])    
      title = row[3]
      start = datetime.fromtimestamp(startTime)
      end = datetime.fromtimestamp(endTime)
      events_data.update({ startTime : { "epgId" : epgId, "startts" : startTime, "endts" : endTime, "start" : start , "end" : end, "title" : title}})
    close_db()
    return events_data

def get_epg_live(min_limit):
    events_data = {}
    current_ts = int(time.mktime(datetime.now().timetuple()))
    open_db()
    row = None    
    cnt = 0    
    for row in db.execute('SELECT count(1) FROM epg WHERE startTime <= ? AND endTime >=?', [current_ts, current_ts]):
      cnt = row[0]
    if cnt+3 < min_limit:
      channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
      load_epg_ts(channels_key_mapping.keys(), current_ts-60*60*3, current_ts+60*60*3)  
      open_db()
    for row in db.execute('SELECT channel, epgId, startTime, endTime, title FROM epg WHERE startTime <= ? AND endTime >=?', [current_ts, current_ts]):
      channel = row[0]
      epgId = int(row[1])
      startTime = int(row[2])
      endTime = int(row[3])    
      title = row[4]
      start = datetime.fromtimestamp(startTime)
      end = datetime.fromtimestamp(endTime)
      events_data.update({ channel : { "epgId" : epgId, "start" : start, "end" : end, "title" : title }})
    close_db()
    return events_data

