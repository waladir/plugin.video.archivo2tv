# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
import json

from urllib import urlencode, quote_plus
from datetime import datetime 
import time

from o2tv.o2api import call_o2_api
from o2tv import o2api
from o2tv.utils import get_url
from o2tv import utils
from o2tv.channels import load_channels 
from o2tv.epg import get_category
_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

def list_categories(label):
  xbmcplugin.setPluginCategory(_handle, label)

  data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/lists/?name=catalogue", data = None, header = o2api.header_unity)
  if "err" in data:
    xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kategorií", xbmcgui.NOTIFICATION_ERROR, 4000)
    sys.exit()  
  if "result" in data and len(data["result"]) > 0:
    for category in data["result"]:
      if "name" in category and len(category["name"]) > 0 and "slug" in category and len(category["slug"]) > 0:
        slug = category["slug"]
        data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/lists/slug/?slug=" + slug, data = None, header = o2api.header_unity)
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kategorií", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()  
        if "name" in data and len(data["name"]) > 0:
          if data["type"] == "programs" and "filter" in category and "contentType" in data["filter"] and len(data["filter"]["contentType"]) > 0:
            contentType = data["filter"]["contentType"]
            filtr = json.dumps({"genres" : data["filter"]["genres"], "notGenres" : data["filter"]["notGenres"], "containsAllGenres" : data["filter"]["containsAllGenres"]}).encode("utf-8")
            list_item = xbmcgui.ListItem(label=data["name"].encode("utf-8"))
            url = get_url(action='list_category', category = contentType.encode("utf-8"), dataSource = data["dataSource"], filtr = filtr, label = label + " / " + data["name"].encode("utf-8"))  
            if "images" in category and data["images"] != None and "iconPng" in data["images"] and "url" in data["images"]["iconPng"] and len(data["images"]["iconPng"]["url"]) > 0:
              list_item.setArt({'thumb':"https://www.o2tv.cz" + data["images"]["iconPng"]["url"], 'icon':"https://www.o2tv.cz" + data["images"]["iconPng"]["url"]})
            print(filtr)
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
          
          if data["type"] == "list" and "filter" in category and "name" in data["filter"] and len(data["filter"]["name"]) > 0:
            list_item = xbmcgui.ListItem(label=data["name"].encode("utf-8"))
            url = get_url(action='list_subcategories', category = data["filter"]["name"].encode("utf-8"), dataSource = data["dataSource"], label = label + " / " + data["name"].encode("utf-8"))  
            if "images" in category and data["images"] != None and "iconPng" in data["images"] and "url" in data["images"]["iconPng"] and len(data["images"]["iconPng"]["url"]) > 0:
              list_item.setArt({'thumb':"https://www.o2tv.cz" + data["images"]["iconPng"]["url"], 'icon':"https://www.o2tv.cz" + data["images"]["iconPng"]["url"]})
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)              
  else:
    xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kategorií", xbmcgui.NOTIFICATION_ERROR, 4000)
    sys.exit()  

def list_subcategories(category, label):
  xbmcplugin.setPluginCategory(_handle, label)
  data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/lists/?name=" + category, data = None, header = o2api.header_unity)  
  if "err" in data:
    xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kategorií", xbmcgui.NOTIFICATION_ERROR, 4000)
    sys.exit()  
  if "result" in data and len(data["result"]) > 0:
    for category in data["result"]:
      contentType = ""
      filtr = ""
      if category["type"] == "programs" and "filter" in category and "contentType" in category["filter"] and len(category["filter"]["contentType"]) > 0 and category["filter"]["contentType"].encode("utf-8") != "živý přenos":
        contentType = category["filter"]["contentType"]
        filtr = json.dumps({"genres" : category["filter"]["genres"], "notGenres" : category["filter"]["notGenres"], "containsAllGenres" : category["filter"]["containsAllGenres"]}).encode("utf-8")
        list_item = xbmcgui.ListItem(label=category["name"].encode("utf-8"))
        url = get_url(action='list_category', category = contentType.encode("utf-8"), dataSource = category["dataSource"], filtr = filtr, label = label + " / " + category["name"].encode("utf-8"))  
        if "images" in category and category["images"] != None and "iconPng" in category["images"] and "url" in category["images"]["iconPng"] and len(category["images"]["iconPng"]["url"]) > 0:
          list_item.setArt({'thumb':"https://www.o2tv.cz" + category["images"]["iconPng"]["url"], 'icon':"https://www.o2tv.cz" + category["images"]["iconPng"]["url"]})
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    xbmcplugin.endOfDirectory(_handle)              
  else:
    xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením ketegorií", xbmcgui.NOTIFICATION_ERROR, 4000)
    sys.exit()  

def list_category(category, dataSource, filtr, label):
  xbmcplugin.setPluginCategory(_handle, label)
  filtr = json.loads(filtr)
  params = ""
  genres = []
  nongenres = []
  for genre in filtr["genres"]:
    if len(genre) > 0:
      params = params + "&genres=" + quote_plus(genre.encode("utf8"))
      genres.append(genre)
  for nongenre in filtr["notGenres"]:
    if len(nongenre) > 0:
      params = params + "&notGenres=" + quote_plus(nongenre.encode("utf8"))
      nongenres.append(nongenre)
  
  if 1 == 0:
    channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter=1) # pylint: disable=unused-variable 
    events = get_category(genres, nongenres, series = False)
    print(category)
    print(dataSource)
    print(filtr)
    for event in events:
      epgId = event.keys()[0]
      list_item = xbmcgui.ListItem(label = event[epgId]["title"] + " (" + event[epgId]["channel"] + ")")
      list_item = o2api.get_epg_details(list_item, str(epgId), "")  
      url = get_url(action='play_archiv', channelKey = channels_data[event[epgId]["channel"]]["channelKey"].encode("utf-8"), start = event[epgId]["startts"], end = event[epgId]["endts"], epgId = epgId)
      list_item.setProperty("IsPlayable", "true")
      list_item.setContentLookup(False)         
      xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    xbmcplugin.endOfDirectory(_handle)
  else:
    data = call_o2_api(url = "https://www.o2tv.cz" + dataSource + "?containsAllGenres=" + str(filtr["containsAllGenres"]).lower() + "&contentType=" + category + params + "&encodedChannels=" + o2api.encodedChannels + "&sort=-o2rating&grouped=true&isFuture=false&limit=500&offset=0", data = None, header = o2api.header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kategorie", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()        
    if "result" in data and len(data["result"]) > 0:
      channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter=1) # pylint: disable=unused-variable 
      for event in data["result"]:
        if event["channelKey"] in channels_key_mapping and channels_key_mapping[event["channelKey"]] in channels_nums.values():
          startts = event["start"]/1000
          start = datetime.fromtimestamp(event["start"]/1000)
          endts = event["end"]/1000
          end = datetime.fromtimestamp(event["end"]/1000)
          epgId = event["epgId"]
          isSeries = 0
          if "seriesInfo" in event and "seriesName" in event["seriesInfo"] and len(event["seriesInfo"]["seriesName"]) > 0:
            isSeries = 1
            event["name"] = event["seriesInfo"]["seriesName"]
            if "seasonNumber" in event["seriesInfo"]:
              event["name"] = event["name"] # + " ["+ str(event["seriesInfo"]["seasonNumber"]) + "]"
            list_item = xbmcgui.ListItem(label = event["name"] + " (" + channels_key_mapping[event["channelKey"]] + ")")
          else:
            list_item = xbmcgui.ListItem(label = event["name"] + " (" + channels_key_mapping[event["channelKey"]] + " | " + utils.day_translation_short[start.strftime("%w")].decode("utf-8") + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + ")")
          cast = []
          directors = []
          genres = []
          list_item.setInfo("video", {"mediatype":"movie"})
          if "images" in event and len(event["images"]) > 0:
            list_item.setArt({'poster': "https://www.o2tv.cz/" + event["images"][0]["cover"],'thumb': "https://www.o2tv.cz/" + event["images"][0]["cover"], 'icon': "https://www.o2tv.cz/" + event["images"][0]["cover"]})
          if "longDescription" in event and len(event["longDescription"]) > 0:
            list_item.setInfo("video", {"plot": event["longDescription"]})
          if "ratings" in event and len(event["ratings"]) > 0:
            for rating, rating_value in event["ratings"].items():
              list_item.setRating(rating, int(rating_value)/10)
          if "castAndCrew" in event and len(event["castAndCrew"]) > 0 and "cast" in event["castAndCrew"] and len(event["castAndCrew"]["cast"]) > 0:
            for person in event["castAndCrew"]["cast"]:      
              cast.append(person["name"].encode("utf-8"))
            list_item.setInfo("video", {"cast" : cast})  
          if "castAndCrew" in event and len(event["castAndCrew"]) > 0 and "directors" in event["castAndCrew"] and len(event["castAndCrew"]["directors"]) > 0:
            for person in event["castAndCrew"]["directors"]:      
              directors.append(person["name"].encode("utf-8"))
            list_item.setInfo("video", {"director" : directors})  
          if "origin" in event and len(event["origin"]) > 0:
            if "year" in event["origin"] and len(str(event["origin"]["year"])) > 0:
              list_item.setInfo("video", {"year": event["origin"]["year"]})
            if "country" in event["origin"] and len(event["origin"]["country"]) > 0:
              list_item.setInfo("video", {"country": event["origin"]["country"]["name"]})
          if "origName" in event and len(event["origName"]) > 0:
            list_item.setInfo("video", {"originaltitle": event["origName"]})
          if "ext" in event and len(event["ext"]) > 0 and "imdbId" in event["ext"] and len(event["ext"]["imdbId"]) > 0:
            list_item.setInfo("video", {"imdbnumber": event["ext"]["imdbId"]})
          if "genreInfo" in event and len(event["genreInfo"]) > 0 and "genres" in event["genreInfo"] and len(event["genreInfo"]["genres"]) > 0:
            for genre in event["genreInfo"]["genres"]:      
              genres.append(genre["name"].encode("utf-8"))
            list_item.setInfo("video", {"genre" : genres})    
          if isSeries == 0:
            list_item.setProperty("IsPlayable", "true")
            list_item.setContentLookup(False)          
            url = get_url(action='play_archiv', channelKey = event["channelKey"].encode("utf-8"), start = startts, end = endts, epgId = epgId)
            xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
          else:
            if "seasonNumber" in event["seriesInfo"] and int(event["seriesInfo"]["seasonNumber"]) > 0:
              season = int(event["seriesInfo"]["seasonNumber"])
            else:
              season = -1  
            list_item.setProperty("IsPlayable", "false")
            url = get_url(action='list_series', epgId = epgId, season = season, label = event["name"].encode("utf-8"))
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
      xbmcplugin.endOfDirectory(_handle)

def list_series(epgId, season, label):
  xbmcplugin.setPluginCategory(_handle, label)
  params = ""
  if int(season) > 0:
    params = params + "&seasonNumber=" + str(season)

  data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/programs/" + str(epgId) + "/episodes/?containsAllGenres=false&isFuture=false" + params, data = None, header = o2api.header_unity)
  if "err" in data:
    xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kategorie", xbmcgui.NOTIFICATION_ERROR, 4000)
    sys.exit()        
  if "result" in data and len(data["result"]) > 0:
    channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter=1) # pylint: disable=unused-variable
    for event in data["result"]:
      if event["channelKey"] in channels_key_mapping and channels_key_mapping[event["channelKey"]] in channels_nums.values():
        startts = event["start"]/1000
        start = datetime.fromtimestamp(event["start"]/1000)
        endts = event["end"]/1000
        end = datetime.fromtimestamp(event["end"]/1000)
        epgId = event["epgId"]
        list_item = xbmcgui.ListItem(label = event["name"] + " (" + channels_key_mapping[event["channelKey"]] + " | " + utils.day_translation_short[start.strftime("%w")].decode("utf-8") + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + ")")
        list_item.setInfo("video", {"mediatype":"movie"})
        list_item = o2api.get_epg_details(list_item, str(event["epgId"]), "")
        list_item.setProperty("IsPlayable", "true")
        list_item.setContentLookup(False)          
        url = get_url(action='play_archiv', channelKey = event["channelKey"].encode("utf-8"), start = startts, end = endts, epgId = epgId)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)      
    xbmcplugin.endOfDirectory(_handle)

