# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
from urllib import urlencode, quote
from urlparse import parse_qsl
from urllib2 import urlopen, Request, HTTPError

import json
import uuid
from datetime import datetime, timedelta 
from datetime import date
import time
import string, random 
import os                     

############### init ################
_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')
addon_userdata_dir = xbmc.translatePath( addon.getAddonInfo('profile') ) 

header_unity = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type":"application/json"}
header = {"X-NanguTv-App-Version" : "Android#6.4.1", "User-Agent" : "Dalvik/2.1.0", "Accept-Encoding" : "gzip", "Connection" : "Keep-Alive", "Content-Type" : "application/x-www-form-urlencoded;charset=UTF-8", "X-NanguTv-Device-Name" : addon.getSetting("deviceid"), "X-NanguTv-Device-Name" : addon.getSetting("devicename")}

def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urlencode(kwargs))

def check_settings():
    if not addon.getSetting("deviceid"):
      addon.setSetting("deviceid",''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(15)))

    if not addon.getSetting("username") or not addon.getSetting("password") or not addon.getSetting("deviceid") or not addon.getSetting("devicename") or  not addon.getSetting("devicetype"):
      xbmcgui.Dialog().notification("Sledování O2TV","V nastavení je nutné mít vyplněné všechny přihlašovací údaje", xbmcgui.NOTIFICATION_ERROR, 10000)
      sys.exit()

    if (addon.getSetting("stream_type") == "MPEG-DASH" or addon.getSetting("stream_type") == "MPEG-DASH-web") and not xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)'):
      xbmcgui.Dialog().notification("Sledování O2TV","Při použítí streamu MPEG-DASH je nutné mít nainstalovaný doplněk InputStream Adaptive", xbmcgui.NOTIFICATION_ERROR, 20000)
      sys.exit()

def get_color(settings_color):
    if len(settings_color) >2 and settings_color.find("]") > 1:
      color = settings_color[1:settings_color.find("]")].replace("COLOR ","")
      return color
    else:
      return ""
      
############### hledani - historie ################

def save_search_history(query):
    max_history = int(addon.getSetting("search_history"))
    cnt = 0
    history = []
    filename = addon_userdata_dir + "search_history.txt"
    
    try:
      with open(filename, "r") as file:
        for line in file:
          item = line[:-1]
          history.append(item)
    except IOError:
      history = []
      
    history.insert(0,query)

    with open(filename, "w") as file:
      for item  in history:
        cnt = cnt + 1
        if cnt <= max_history:
            file.write('%s\n' % item)

def load_search_history():
    history = []
    filename = addon_userdata_dir + "search_history.txt"
    try:
      with open(filename, "r") as file:
        for line in file:
          item = line[:-1]
          history.append(item)
    except IOError:
      history = []
    return history

############### O2 API ################

def call_o2_api(url, data, header):
    request = Request(url = url , data = data, headers = header)
    if addon.getSetting("log_request_url") == "true":
      xbmc.log(url)
    if addon.getSetting("log_request_data") == "true" and data <> None:
      xbmc.log(data)

    try:
      html = urlopen(request).read()
      if addon.getSetting("log_response") == "true":
        xbmc.log(html)

      if html and len(html) > 0:
        data = json.loads(html)
        return data
      else:
        return []
    except HTTPError as e:
      return { "err" : e.reason }                
      
def get_auth_token():
    global header_unity
    post = {"username" : addon.getSetting("username"), "password" : addon.getSetting("password")} 
    data = call_o2_api(url = "https://ottmediator.o2tv.cz:4443/ottmediator-war/login", data = urlencode(post), header = header)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()            

    if "services" in data and "remote_access_token" in data and len(data["remote_access_token"]) > 0 and "service_id" in data["services"][0] and len(data["services"][0]["service_id"]) > 0:
        remote_access_token = data["remote_access_token"]
        service_id = data["services"][0]['service_id']

        post = {"service_id" : service_id, "remote_access_token" : remote_access_token}
        data = call_o2_api(url = "https://ottmediator.o2tv.cz:4443/ottmediator-war/loginChoiceService", data = urlencode(post), header = header)
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()  

        post = {"grant_type" : "remote_access_token", "client_id" : "tef-web-portal-etnetera", "client_secret" : "2b16ac9984cd60dd0154f779ef200679", "platform_id" : "231a7d6678d00c65f6f3b2aaa699a0d0", "language" : "cs", "remote_access_token" : str(remote_access_token), "authority" :  "tef-sso", "isp_id" : "1"}
        data = call_o2_api(url = "https://oauth.o2tv.cz/oauth/token", data = urlencode(post), header = header)
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()  

        if "access_token" in data and len(data["access_token"]) > 0:
          access_token = data["access_token"]
          header.update({"X-NanguTv-Access-Token" : str(access_token), "X-NanguTv-Device-Id" : addon.getSetting("deviceid")})
          data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/settings/subscription-configuration.json", data = None, header = header)
          if "err" in data:
            xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
            sys.exit()  
          if "isp" in data and len(data["isp"]) > 0 and "locality" in data and len(data["locality"]) > 0 and "billingParams" in data and len(data["billingParams"]) > 0 and "offers" in data["billingParams"] and len(data["billingParams"]["offers"]) > 0 and "tariff" in data["billingParams"] and len(data["billingParams"]["tariff"]) > 0:
            subscription = data["subscription"]
            isp = data["isp"]
            locality = data["locality"]
            offers = data["billingParams"]["offers"]
            tariff = data["billingParams"]["tariff"]
            header_unity = {"User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type" : "application/json", "x-o2tv-access-token" : str(access_token), "x-o2tv-device-id" : addon.getSetting("deviceid"), "x-o2tv-device-name" : addon.getSetting("devicename")}
            data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/user/profile/", data = None, header = header_unity)
            if "err" in data:
              xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
              sys.exit()   
            sdata = data["sdata"]
            header_unity.update({"x-o2tv-sdata" : str(sdata)})
            return access_token, subscription, isp, locality, offers, tariff, sdata
          else:
              xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
              sys.exit()            
        else:
            xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
            sys.exit()
    else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()

def get_auth_password():
    global header_unity
    post = {"grant_type" : "password", "client_id" : "tef-web-portal-etnetera", "client_secret" : "2b16ac9984cd60dd0154f779ef200679", "platform_id" : "231a7d6678d00c65f6f3b2aaa699a0d0", "language" : "cs", "username" : addon.getSetting("username"), "password" : addon.getSetting("password")}
    data = call_o2_api(url = "https://oauth.o2tv.cz/oauth/token", data = urlencode(post), header = header)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  

    if "access_token" in data and len(data["access_token"]) > 0:
      access_token = data["access_token"]
      header.update({"X-NanguTv-Access-Token" : str(access_token), "X-NanguTv-Device-Id" : addon.getSetting("deviceid")})
      data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/settings/subscription-configuration.json", data = None, header = header)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
         
      if "isp" in data and len(data["isp"]) > 0 and "locality" in data and len(data["locality"]) > 0 and "billingParams" in data and len(data["billingParams"]) > 0 and "offers" in data["billingParams"] and len(data["billingParams"]["offers"]) > 0 and "tariff" in data["billingParams"] and len(data["billingParams"]["tariff"]) > 0:
        subscription = data["subscription"]
        isp = data["isp"]
        locality = data["locality"]
        offers = data["billingParams"]["offers"]
        tariff = data["billingParams"]["tariff"]
        header_unity = {"User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type" : "application/json", "x-o2tv-access-token" : str(access_token), "x-o2tv-device-id" : addon.getSetting("deviceid"), "x-o2tv-device-name" : addon.getSetting("devicename")}
        data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/user/profile/", data = None, header = header_unity)
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()   
        sdata = data["sdata"]
        header_unity.update({"x-o2tv-sdata" : str(sdata)})
        return access_token, subscription, isp, locality, offers, tariff, sdata
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()            
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()

def get_epg_details(epgId):
    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/programs/" + str(epgId) + "/", data = None, header = header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením programu", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  
    img = "";
    plot = "";
    ratings = {} 
    cast = []
    directors = []
    if "images" in data and len(data["images"]) > 0:
       img = data["images"][0]["cover"] 
    if "longDescription" in data and len(data["longDescription"]) > 0:
       plot = data["longDescription"]
    if "ratings" in data and len(data["ratings"]) > 0:
       for rating, rating_value in data["ratings"].items():
         ratings.update({ rating : rating_value })
    if "castAndCrew" in data and len(data["castAndCrew"]) > 0 and "cast" in data["castAndCrew"] and len(data["castAndCrew"]["cast"]) > 0:
       for person in data["castAndCrew"]["cast"]:      
         cast.append(person["name"].encode("utf-8"))
    if "castAndCrew" in data and len(data["castAndCrew"]) > 0 and "directors" in data["castAndCrew"] and len(data["castAndCrew"]["directors"]) > 0:
       for person in data["castAndCrew"]["directors"]:      
         directors.append(person["name"].encode("utf-8"))
    return img, plot, ratings, cast, directors

############### menu ################
def list_menu():
    list_item = xbmcgui.ListItem(label="Živé vysílání")
    url = get_url(action='list_live', page = 1)  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label="Archiv")
    url = get_url(action='list_archiv')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label="Nahrávky")
    url = get_url(action='list_recordings')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label="Vyhledávání")
    url = get_url(action='list_search')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    if addon.getSetting("hide_channel_list_edit") <> "true":
      list_item = xbmcgui.ListItem(label="Pořadí kanálů")
      url = get_url(action='list_channels_list')  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

############### live streamy ################
def list_live(page):
    channels_ordered = load_channels()  
    channels = {}
    channel_data = {}     
    num = 0
    pagesize = int(addon.getSetting("live_pagesize"))

    for offer in offers:
      post = {"locality" : locality, "tariff" : tariff, "isp" : isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = header)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "channels" in data and len(data["channels"]) > 0:
        for channel in data["channels"]:
          if data["channels"][channel]["channelType"] == "TV":
            for channel_ordered in channels_ordered:
              if(channel_ordered[0] == data["channels"][channel]["channelName"].encode("utf-8")):
                num = channel_ordered[1]
                channels.update({ num : {"channelName" : data["channels"][channel]["channelName"], "channelKey" : data["channels"][channel]["channelKey"]}})

      data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/channels/", data = None, header = header_unity)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "result" in data and len(data["result"]) > 0:
        for channel in data["result"]:
          if addon.getSetting("details") == "true" and "live" in channel:
            channel_data.update({channel["channel"]["channelKey"].encode("utf-8") : { "logo" : "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"], "live" : { "epgId" : channel["live"]["epgId"], "name" : channel["live"]["name"], "start" : channel["live"]["start"], "end" : channel["live"]["end"] }}});
          else:
            channel_data.update({channel["channel"]["channelKey"].encode("utf-8") : { "logo" : "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"]}});

    color = get_color(addon.getSetting("label_color_live"))   
    startitem = (int(page)-1) * pagesize
    i = 0
    for num in sorted(channels.keys()):  
      if i >= startitem and i < startitem + pagesize: 
        if channels[num]["channelKey"].encode("utf-8") in channel_data and "live" in channel_data[channels[num]["channelKey"].encode("utf-8")]:
          print(str(channel_data[channels[num]["channelKey"].encode("utf-8")]["live"]["epgId"]))
          if addon.getSetting("details_live") == "true":  
            img, plot, ratings, cast, directors = get_epg_details(str(channel_data[channels[num]["channelKey"].encode("utf-8")]["live"]["epgId"]))
          start = datetime.fromtimestamp(int(channel_data[channels[num]["channelKey"].encode("utf-8")]["live"]["start"])/1000)
          end = datetime.fromtimestamp(int(channel_data[channels[num]["channelKey"].encode("utf-8")]["live"]["end"])/1000)
          
          live = "[COLOR " + str(color) + "] | " + channel_data[channels[num]["channelKey"].encode("utf-8")]["live"]["name"] + " | " + start.strftime("%H:%M") + " - " + end.strftime("%H:%M") + "[/COLOR]"
          live_noncolor = " | " + channel_data[channels[num]["channelKey"].encode("utf-8")]["live"]["name"] + " | " + start.strftime("%H:%M") + " - " + end.strftime("%H:%M")
        else: 
          live = ""
          live_noncolor = ""
          
        list_item = xbmcgui.ListItem(label=channels[num]["channelName"] + live)
        if addon.getSetting("details_live") == "true" and channels[num]["channelKey"].encode("utf-8") in channel_data:
          if len(img) > 0:
            list_item.setArt({'thumb': "https://www.o2tv.cz/" + img, 'icon': "https://www.o2tv.cz/" + img})
          else:
            list_item.setArt({'thumb':channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"], 'icon':channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"]})
          if len(plot) > 0:
            list_item.setInfo("video", {"mediatype":"movie", "title": channels[num]["channelName"] + live_noncolor, "plot":plot})
          else:
            list_item.setInfo("video", {"mediatype":"movie", "title": channels[num]["channelName"] + live_noncolor})
          if len(directors) > 0:
            list_item.setInfo("video", {"director" : directors})
          if len(cast) > 0:
            list_item.setInfo("video", {"cast" : cast})
          for rating_name,rating in ratings.items():
            list_item.setRating(rating_name, int(rating)/10)
        else:
          list_item.setInfo("video", {"mediatype":"movie", "title": channels[num]["channelName"] + live_noncolor})
          if channels[num]["channelKey"].encode("utf-8") in channel_data: 
            list_item.setArt({'thumb':channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"], 'icon':channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"]})
  
        list_item.setContentLookup(False)          
        list_item.setProperty("IsPlayable", "true")                                                                                                                                 
        url = get_url(action='play_live', channelKey = channels[num]["channelKey"].encode("utf-8"), title = (channels[num]["channelName"] + live_noncolor).encode("utf-8"))
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
      i = i + 1
    if int(page) * pagesize <= i:
      list_item = xbmcgui.ListItem(label="další strana")
      url = get_url(action='list_live', page = int(page) + 1)  
      list_item.setProperty("IsPlayable", "false")
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)     
    if addon.getSetting("details_live") == "true":
      xbmcplugin.endOfDirectory(_handle)
    else:
      xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)
      
############### archiv ################
def list_archiv():
    channels_ordered = load_channels()  
    channels = {}
    channel_data = {}
    num = 0

    for offer in offers:
      post = {"locality" : locality, "tariff" : tariff, "isp" : isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = header)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  

      if "channels" in data and len(data["channels"]) > 0:
        for channel in data["channels"]:
          if data["channels"][channel]["channelType"] == "TV":
            for channel_ordered in channels_ordered:
              if(channel_ordered[0] == data["channels"][channel]["channelName"].encode("utf-8")):
                num = channel_ordered[1]
                channels.update({ num : {"channelName" : data["channels"][channel]["channelName"], "channelKey" : data["channels"][channel]["channelKey"]}})

      data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/channels/", data = None, header = header_unity)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "result" in data and len(data["result"]) > 0:
        for channel in data["result"]:
          channel_data.update({channel["channel"]["channelKey"].encode("utf-8") : { "logo" : "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"]}});

    for num in sorted(channels.keys()):  
      list_item = xbmcgui.ListItem(label=channels[num]["channelName"])
      if addon.getSetting("details") == "true" and channels[num]["channelKey"].encode("utf-8") in channel_data:
        list_item.setArt({'thumb':channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"], 'icon':channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"]})
      url = get_url(action='list_arch_days', channelKey = channels[num]["channelKey"].encode("utf-8"))  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def list_arch_days(channelKey):
    for i in range (7):
      day = date.today() - timedelta(days = i)
      if i == 0:
        den = "Dnes"
      elif i == 1:
        den = "Včera"
      else:
        den = day_translation[day.strftime("%A")].decode("utf-8") + " " + day.strftime("%d.%m.%Y");
      list_item = xbmcgui.ListItem(label=den)
      url = get_url(action='list_program', channelKey = channelKey, day_min = i)  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def list_program(channelKey, day_min):
    if int(day_min) == 0:
      from_datetime = datetime.combine(date.today(), datetime.min.time())
      to_datetime = datetime.now()
    else:
      from_datetime = datetime.combine(date.today(), datetime.min.time()) - timedelta(days = int(day_min))
      to_datetime = datetime.combine(from_datetime, datetime.max.time())
    from_ts = int(time.mktime(from_datetime.timetuple()))
    to_ts = int(time.mktime(to_datetime.timetuple()))

    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?channelKey=" + quote(channelKey) + "&from=" + str(from_ts*1000) + "&to=" + str(to_ts*1000) + "&forceLimit=true&limit=500", data = None, header = header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením programu", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  

    if "epg" in data and len(data["epg"]) > 0 and len(data["epg"]["items"]) > 0 and len(data["epg"]["items"][0]["programs"]) > 0:
      for programs in data["epg"]["items"][0]["programs"]:
        startts = programs["start"]
        start = datetime.fromtimestamp(programs["start"]/1000)
        endts = programs["end"]
        end = datetime.fromtimestamp(programs["end"]/1000)
        epgId = programs["epgId"]

        if to_ts > int(programs["end"]/1000):      
          if addon.getSetting("details") == "true":  
            img, plot, ratings, cast, directors = get_epg_details(str(epgId))
   
          list_item = xbmcgui.ListItem(label= day_translation_short[start.strftime("%A")].decode("utf-8") + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + " | " + programs["name"])
          list_item.setProperty("IsPlayable", "true")
          if addon.getSetting("details") == "true":  
            list_item.setArt({'thumb': "https://www.o2tv.cz/" + img, 'icon': "https://www.o2tv.cz/" + img, 'poster': "https://www.o2tv.cz/" + img})
            list_item.setInfo("video", {"mediatype":"movie", "title":programs["name"], "plot":plot})
            if len(directors) > 0:
              list_item.setInfo("video", {"director" : directors})
            if len(cast) > 0:
              list_item.setInfo("video", {"cast" : cast})
            for rating_name,rating in ratings.items():
              list_item.setRating(rating_name, int(rating)/10)
          else:
            list_item.setInfo("video", {"mediatype":"movie", "title":programs["name"]})
    
          list_item.setContentLookup(False)          
          list_item.addContextMenuItems([("Přidat nahrávku", "RunPlugin(plugin://plugin.video.archivo2tv?action=add_recording&epgId=" + str(epgId) + ")",)])       
          url = get_url(action='play_video', channelKey = channelKey, start = startts, end = endts, epgId = epgId)
          xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením programu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()    
    xbmcplugin.endOfDirectory(_handle)
        
############### nahravky ################

def list_planning_recordings():
    channels_ordered = load_channels()  
    channels = {}
    channel_data = {}
    num = 0
    
    for offer in offers:
      post = {"locality" : locality, "tariff" : tariff, "isp" : isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = header)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  

      if "channels" in data and len(data["channels"]) > 0:
        for channel in data["channels"]:
          if data["channels"][channel]["channelType"] == "TV":
            for channel_ordered in channels_ordered:
              if(channel_ordered[0] == data["channels"][channel]["channelName"].encode("utf-8")):
                num = channel_ordered[1]
                channels.update({ num : {"channelName" : data["channels"][channel]["channelName"], "channelKey" : data["channels"][channel]["channelKey"]}})

      data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/channels/", data = None, header = header_unity)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "result" in data and len(data["result"]) > 0:
        for channel in data["result"]:
          channel_data.update({channel["channel"]["channelKey"].encode("utf-8") : { "logo" : "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"]}});

    for num in sorted(channels.keys()):  
      list_item = xbmcgui.ListItem(label=channels[num]["channelName"])
      if addon.getSetting("details") == "true" and channels[num]["channelKey"].encode("utf-8") in channel_data:
        list_item.setArt({'thumb':channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"], 'icon':channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"]})
      url = get_url(action='list_rec_days', channelKey = channels[num]["channelKey"].encode("utf-8"))  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)
    
def list_rec_days(channelKey):
    for i in range (7):
      day = date.today() + timedelta(days = i)
      if i == 0:
        den = "Dnes"
      elif i == 1:
        den = "Zítra"
      else:
        den = day_translation[day.strftime("%A")].decode("utf-8") + " " + day.strftime("%d.%m.%Y");
      list_item = xbmcgui.ListItem(label=den)
      url = get_url(action='future_program', channelKey = channelKey, day = i)  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def future_program(channelKey, day):
    if int(day) == 0:
      from_datetime = datetime.now()
      to_datetime = datetime.combine(date.today(), datetime.max.time())
    else:
      from_datetime = datetime.combine(date.today(), datetime.min.time()) + timedelta(days = int(day))
      to_datetime = datetime.combine(from_datetime, datetime.max.time())
    from_ts = int(time.mktime(from_datetime.timetuple()))
    to_ts = int(time.mktime(to_datetime.timetuple()))

    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?channelKey=" + quote(channelKey) + "&from=" + str(from_ts*1000) + "&to=" + str(to_ts*1000) + "&forceLimit=true&limit=500", data = None, header = header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením programu", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  

    if "epg" in data and len(data["epg"]) > 0 and len(data["epg"]["items"]) > 0 and len(data["epg"]["items"][0]["programs"]) > 0:
      for programs in data["epg"]["items"][0]["programs"]:
        startts = programs["start"]
        start = datetime.fromtimestamp(programs["start"]/1000)
        endts = programs["end"]
        end = datetime.fromtimestamp(programs["end"]/1000)
        epgId = programs["epgId"]

        if addon.getSetting("details") == "true":  
          img, plot, ratings, cast, directors = get_epg_details(str(epgId))

        list_item = xbmcgui.ListItem(label= day_translation_short[start.strftime("%A")].decode("utf-8") + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + " | " + programs["name"])
        list_item.setProperty("IsPlayable", "false")
        if addon.getSetting("details") == "true":  
          list_item.setArt({'thumb': "https://www.o2tv.cz/" + img, 'icon': "https://www.o2tv.cz/" + img})
          list_item.setInfo("video", {"mediatype":"video", "title":programs["name"], "plot":plot})
          if len(directors) > 0:
            list_item.setInfo("video", {"director" : directors})
          if len(cast) > 0:
            list_item.setInfo("video", {"cast" : cast})
          for rating_name,rating in ratings.items():
            list_item.setRating(rating_name, int(rating)/10)
        else:
          list_item.setInfo("video", {"mediatype":"video", "title":programs["name"]})
        list_item.addContextMenuItems([("Přidat nahrávku", "RunPlugin(plugin://plugin.video.archivo2tv?action=add_recording&epgId=" + str(epgId) + ")",)])       
        url = get_url(action='add_recording', channelKey = channelKey, epgId = epgId)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením programu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()    
    
    xbmcplugin.endOfDirectory(_handle)

def list_recordings():
    recordings = {}

    list_item = xbmcgui.ListItem(label="Plánování nahrávek")
    url = get_url(action='list_planning_recordings')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label="Naplánované nahrávky")
    url = get_url(action='list_future_recordings')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/recordings/", data = None, header = header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením nahrávek, zkuste to znovu", xbmcgui.NOTIFICATION_ERROR, 6000)
     
    if "result" in data and len(data["result"]) > 0:
      for program in data["result"]:
        if program["state"] == "DONE":
          pvrProgramId = program["pvrProgramId"]
          epgId = program["program"]["epgId"]
          if "ratings" in program["program"] and len(program["program"]["ratings"]) > 0:
            ratings = program["program"]["ratings"]
          else:
            ratings = {}
          if "longDescription" in program["program"] and len(program["program"]["longDescription"]) > 0:
            plot = program["program"]["longDescription"]
          else:
            plot = ""
          if "images" in program["program"] and len(program["program"]["images"]) > 0 and "cover" in program["program"]["images"][0]:
            img = program["program"]["images"][0]["cover"]
          else:
            img = ""
          recordings.update({program["program"]["start"]+random.randint(0,100) : {"pvrProgramId" : pvrProgramId, "name" : program["program"]["name"], "channelKey" : program["program"]["channelKey"], "start" : day_translation_short[datetime.fromtimestamp(program["program"]["start"]/1000).strftime("%A")].decode("utf-8") + " " + datetime.fromtimestamp(program["program"]["start"]/1000).strftime("%d.%m %H:%M"), "end" : datetime.fromtimestamp(program["program"]["end"]/1000).strftime("%H:%M"), "plot" : plot, "img" : img, "ratings" : ratings}}) 

      for recording in sorted(recordings.keys(), reverse = True):
        list_item = xbmcgui.ListItem(label = recordings[recording]["name"] + " (" + recordings[recording]["channelKey"] + " | " + recordings[recording]["start"] + " - " + recordings[recording]["end"] + ")")
        list_item.setProperty("IsPlayable", "true")
        if addon.getSetting("details") == "true":  
          list_item.setArt({'thumb': "https://www.o2tv.cz/" + recordings[recording]["img"], 'icon': "https://www.o2tv.cz/" + recordings[recording]["img"]})
          list_item.setInfo("video", {"mediatype":"movie", "title":recordings[recording]["name"], "plot":recordings[recording]["plot"]})
          for rating, rating_value in recordings[recording]["ratings"].items():
            list_item.setRating(rating, rating_value/10)
        else:
          list_item.setInfo("video", {"mediatype":"movie", "title":recordings[recording]["name"]})
        list_item.setContentLookup(False)   
        list_item.addContextMenuItems([("Smazat nahrávku", "RunPlugin(plugin://plugin.video.archivo2tv?action=delete_recording&pvrProgramId=" + str(recordings[recording]["pvrProgramId"]) + ")",)])       
        url = get_url(action='play_recording', pvrProgramId = recordings[recording]["pvrProgramId"], title = recordings[recording]["name"].encode("utf-8"))
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
      xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)
    else:
       if "err" not in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Nenalezena žádná nahrávka", xbmcgui.NOTIFICATION_INFO, 4000)
        sys.exit() 

def list_future_recordings():
    recordings = {}
    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/recordings/", data = None, header = header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením nahrávek", xbmcgui.NOTIFICATION_ERROR, 4000)
    
    if "result" in data and len(data["result"]) > 0:
      for program in data["result"]:
        if program["state"] != "DONE":
          pvrProgramId = program["pvrProgramId"]
          epgId = program["program"]["epgId"]
          if "ratings" in program["program"] and len(program["program"]["ratings"]) > 0:
            ratings = program["program"]["ratings"]
          else:
            ratings = {}
          if "longDescription" in program["program"] and len(program["program"]["longDescription"]) > 0:
            plot = program["program"]["longDescription"]
          else:
            plot = ""
          if "images" in program["program"] and len(program["program"]["images"]) > 0 and "cover" in program["program"]["images"][0]:
            img = program["program"]["images"][0]["cover"]
          else:
            img = ""

          recordings.update({program["program"]["start"]+random.randint(0,100) : {"pvrProgramId" : pvrProgramId, "name" : program["program"]["name"], "channelKey" : program["program"]["channelKey"], "start" : day_translation_short[datetime.fromtimestamp(program["program"]["start"]/1000).strftime("%A")].decode("utf-8") + " " + datetime.fromtimestamp(program["program"]["start"]/1000).strftime("%d.%m %H:%M"), "end" : datetime.fromtimestamp(program["program"]["end"]/1000).strftime("%H:%M"), "plot" : plot, "img" : img, "ratings" : ratings}}) 

      for recording in sorted(recordings.keys(), reverse = True):
        list_item = xbmcgui.ListItem(label = recordings[recording]["name"] + " (" + recordings[recording]["channelKey"] + " | " + recordings[recording]["start"] + " - " + recordings[recording]["end"] + ")")
        list_item.setProperty("IsPlayable", "true")
        if addon.getSetting("details") == "true":  
          list_item.setArt({'thumb': "https://www.o2tv.cz/" + recordings[recording]["img"], 'icon': "https://www.o2tv.cz/" + recordings[recording]["img"]})
          list_item.setInfo("video", {"mediatype":"movie", "title":recordings[recording]["name"], "plot":recordings[recording]["plot"]})
          for rating, rating_value in recordings[recording]["ratings"].items():
            list_item.setRating(rating, rating_value/10)
        else:
          list_item.setInfo("video", {"mediatype":"movie", "title":recordings[recording]["name"]})
        list_item.addContextMenuItems([("Smazat nahrávku", "RunPlugin(plugin://plugin.video.archivo2tv?action=delete_recording&pvrProgramId=" + str(recordings[recording]["pvrProgramId"]) + ")",)])       
        url = get_url(action='list_future_recordings')  
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
      xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)
    else:
        xbmcgui.Dialog().notification("Sledování O2TV","Nenalezena žádná nahrávka", xbmcgui.NOTIFICATION_INFO, 4000)
        sys.exit() 

def delete_recording(pvrProgramId):
    post = {"pvrProgramId" : int(pvrProgramId)}
    data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/vod/pvr-remove-program.json", data = urlencode(post), header = header)
    xbmcgui.Dialog().notification("Sledování O2TV","Nahrávka odstraněna", xbmcgui.NOTIFICATION_INFO, 4000)
    xbmc.executebuiltin('Container.Refresh')

def add_recording(epgId):
    post = {"epgId" : int(epgId)}
    data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/vod/pvr-add-program.json", data = urlencode(post), header = header)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s přidáním nahrávky", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit() 
    xbmcgui.Dialog().notification("Sledování O2TV","Nahrávka přidána", xbmcgui.NOTIFICATION_INFO, 4000)

############### prehravani ################
    
def play_video(type, channelKey, start, end, epgId, title):
    if addon.getSetting("select_resolution") == "true" and addon.getSetting("stream_type") == "HLS" and addon.getSetting("only_sd") <> "true":
      resolution = xbmcgui.Dialog().select('Rozlišení', ['HD', 'SD' ], preselect = 0)
    else:
      resolution = -1  

    if addon.getSetting("stream_type") == "MPEG-DASH":
      stream_type = "DASH"
    else:
      stream_type = "HLS"

    if addon.getSetting("stream_type") == "MPEG-DASH-web":
      if type == "archiv" or type == "archiv_iptv":
        data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/programs/" + str(epgId) +"/playlist/", data = None, header = header_unity)
      if type == "live" or type == "live_iptv":
        data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/channels/playlist/?channelKey=" + quote(channelKey), data = None, header = header_unity)
      if type == "recording":
        data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/recordings/" + str(epgId) +"/playlist/", data = None, header = header_unity)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s přehráním streamu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "playlist" in data and len(data["playlist"]) > 0 and "streamUrls" in data["playlist"][0] and "main" in data["playlist"][0]["streamUrls"] and len(data["playlist"][0]["streamUrls"]["main"]) > 0:
        url = data["playlist"][0]["streamUrls"]["main"]
        request = Request(url = url , data = None, headers = header)
        response = urlopen(request)
        url = response.geturl()
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s přehráním streamu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
    else:
      if type == "archiv" or type == "archiv_iptv":
        post = {"serviceType" : "TIMESHIFT_TV", "deviceType" : addon.getSetting("devicetype"), "streamingProtocol" : stream_type,  "subscriptionCode" : subscription, "channelKey" : channelKey, "fromTimestamp" : start, "toTimestamp" : str(int(end) + (int(addon.getSetting("offset"))*60*1000)), "id" : epgId, "encryptionType" : "NONE"}
      if type == "live" or type == "live_iptv":
        post = {"serviceType" : "LIVE_TV", "deviceType" : addon.getSetting("devicetype"), "streamingProtocol" : stream_type, "subscriptionCode" : subscription, "channelKey" : channelKey, "encryptionType" : "NONE"}
      if type == "recording":
        post = {"serviceType" : "NPVR", "deviceType" : addon.getSetting("devicetype"), "streamingProtocol" : stream_type, "subscriptionCode" : subscription, "contentId" : epgId, "encryptionType" : "NONE"}
      if addon.getSetting("stream_type") <> "MPEG-DASH" and (addon.getSetting("only_sd") == "true" or resolution == 1):
        post.update({"resolution" : "SD"})
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/streaming/uris.json", data = urlencode(post), header = header)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s přehráním streamu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      url = ""
      if "uris" in data and len(data["uris"]) > 0 and "uri" in data["uris"][0] and len(data["uris"][0]["uri"]) > 0 :
        for uris in data["uris"]:
          if addon.getSetting("only_sd") <> "true" and resolution <> 1 and uris["resolution"] == "HD":
            url = uris["uri"]
          if (addon.getSetting("only_sd") == "true" or resolution == 1) and uris["resolution"] == "SD": 
            url = uris["uri"]
        if url == "":
          url = data["uris"][0]["uri"]
        if addon.getSetting("stream_type") == "MPEG-DASH":
          request = Request(url = url , data = None, headers = header)
          response = urlopen(request)
          url = response.geturl()
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s přehráním streamu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()

    if type == "live_iptv":
      data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/channels/", data = None, header = header_unity)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "result" in data and len(data["result"]) > 0:
        img = ""
        plot = ""
        ratings = {}
        logo = ""
        live = channelKey
        for channel in data["result"]:
          if "live" in channel and channel["channel"]["channelKey"].encode("utf-8") == channelKey:
            start = datetime.fromtimestamp(int(channel["live"]["start"])/1000)
            end = datetime.fromtimestamp(int(channel["live"]["end"])/1000)
            live = channel["channel"]["name"] + " | " + channel["live"]["name"] + " | " + start.strftime("%H:%M") + " - " + end.strftime("%H:%M")
            logo = "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"]
            img, plot, ratings, cast, directors = get_epg_details(str(channel["live"]["epgId"]))
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      list_item = xbmcgui.ListItem(live)

      if len(img) > 0:
        list_item.setArt({'thumb': "https://www.o2tv.cz/" + img, 'icon': "https://www.o2tv.cz/" + img})
      elif len(logo) > 0:
        list_item.setArt({'thumb': logo, 'icon': logo})
      if len(plot) > 0:
        list_item.setInfo("video", {"mediatype":"movie", "title": live, "plot":plot})
      else:
        list_item.setInfo("video", {"mediatype":"movie", "title": live})
      if len(directors) > 0:
        list_item.setInfo("video", {"director" : directors})
      if len(cast) > 0:
        list_item.setInfo("video", {"cast" : cast})
      for rating_name,rating in ratings.items():
        list_item.setRating(rating_name, int(rating)/10)
    elif type == "archiv_iptv":
      img = ""
      plot = ""
      ratings = {}
      list_item = xbmcgui.ListItem(title)
      img, plot, ratings, cast, directors = get_epg_details(str(epgId))
      if len(img) > 0:
        list_item.setArt({'thumb': "https://www.o2tv.cz/" + img, 'icon': "https://www.o2tv.cz/" + img})
      if len(plot) > 0:
        list_item.setInfo("video", {"mediatype":"movie", "title": title, "plot":plot})
      else:
        list_item.setInfo("video", {"mediatype":"movie", "title": title})
      if len(directors) > 0:
        list_item.setInfo("video", {"director" : directors})
      if len(cast) > 0:
        list_item.setInfo("video", {"cast" : cast})
      for rating_name,rating in ratings.items():
        list_item.setRating(rating_name, int(rating)/10)
    else:
      list_item = xbmcgui.ListItem(path = url)

    if addon.getSetting("stream_type") == "MPEG-DASH" or addon.getSetting("stream_type") == "MPEG-DASH-web":
      list_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
      list_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
      list_item.setMimeType('application/dash+xml')
      
    if type == "live_iptv" or type == "archiv_iptv":
      playlist=xbmc.PlayList(1)
      playlist.clear()
      xbmc.PlayList(1).add(url, list_item)
      xbmc.Player().play(playlist)
    else:
      list_item.setContentLookup(False)       
      xbmcplugin.setResolvedUrl(_handle, True, list_item)


############### hledani ################

def list_search():
    list_item = xbmcgui.ListItem(label="Nové hledání")
    url = get_url(action='program_search', query = "-----")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    history = load_search_history()
    for item in history:
      list_item = xbmcgui.ListItem(label=item)
      url = get_url(action='program_search', query = item)  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)

def program_search(query):
    if query == "-----":
      input = xbmc.Keyboard("", "Hledat")
      input.doModal()
      if not input.isConfirmed(): 
        return
      query = input.getText()
      if len(query) == 0:
        xbmcgui.Dialog().notification("Sledování O2TV","Je potřeba zadat vyhledávaný řetězec", xbmcgui.NOTIFICATION_ERROR, 4000)
        return   
      else:
        save_search_history(query)
        
    max_ts = int(time.mktime(datetime.now().timetuple()))
    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/search/tv/depr/?groupLimit=1&maxEnd=" + str(max_ts*1000) + "&q=" + quote(query), data = None, header = header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém při hledání", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  
    
    if "groupedSearch" in data and "groups" in data["groupedSearch"] and len(data["groupedSearch"]["groups"]) > 0:
      for item in data["groupedSearch"]["groups"]:
        programs = item["programs"][0]
        startts = programs["start"]
        start = datetime.fromtimestamp(programs["start"]/1000)
        endts = programs["end"]
        end = datetime.fromtimestamp(programs["end"]/1000)
        epgId = programs["epgId"]
        
        if addon.getSetting("details") == "true":
          img, plot, ratings, cast, directors = get_epg_details(str(epgId))
        list_item = xbmcgui.ListItem(label = programs["name"] + " (" + programs["channelKey"] + " | " + day_translation_short[start.strftime("%A")].decode("utf-8") + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + ")")
        list_item.setProperty("IsPlayable", "true")
        if addon.getSetting("details") == "true":  
          list_item.setArt({'thumb': "https://www.o2tv.cz/" + img, 'icon': "https://www.o2tv.cz/" + img})
          list_item.setInfo("video", {"mediatype":"movie", "title":programs["name"], "plot":plot})
          if len(directors) > 0:
            list_item.setInfo("video", {"director" : directors})
          if len(cast) > 0:
            list_item.setInfo("video", {"cast" : cast})
          for rating_name,rating in ratings.items():
            list_item.setRating(rating_name, int(rating)/10)
        else:
          list_item.setInfo("video", {"mediatype":"movie", "title":programs["name"]})
        list_item.setContentLookup(False)          
        url = get_url(action='play_video', channelKey = programs["channelKey"].encode("utf-8"), start = startts, end = endts, epgId = epgId)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
      xbmcplugin.endOfDirectory(_handle)
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Nic nenalezeno", xbmcgui.NOTIFICATION_INFO, 3000)

############### editace kanalu ################

def list_channels_list():
    list_item = xbmcgui.ListItem(label="Ruční editace")
    url = get_url(action="list_channels_edit")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label="Načtení uživatelského seznamu z O2")
    url = get_url(action="get_o2_channels_lists")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label="Resetovat seznam kanálů")
    url = get_url(action="reset_channel_list")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def get_o2_channels_lists():
    data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/settings/get-user-pref.json?name=nangu.channelListUserChannelNumbers", data = None, header = header)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením seznamu kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  
    if "listUserChannelNumbers" in data and len(data["listUserChannelNumbers"]) > 0:
      for list in data["listUserChannelNumbers"]:
        list_item = xbmcgui.ListItem(label= list.replace("user::",""))
        url = get_url(action="load_o2_channel_list", list = list.encode("utf-8"))  
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
      xbmcplugin.endOfDirectory(_handle)
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Nanalezen žádný seznam v O2", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  

def load_o2_channel_list(list):
    channels = {}
    channels_mapping = {}
    filename = addon_userdata_dir + "channels.txt"

    for offer in offers:
      post = {"locality" : locality, "tariff" : tariff, "isp" : isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = header)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "channels" in data and len(data["channels"]) > 0:
        for channel in data["channels"]:
          if data["channels"][channel]["channelType"] == "TV":
             channels_mapping.update({data["channels"][channel]["channelKey"] : data["channels"][channel]["channelName"].encode("utf-8")})

    data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/settings/get-user-pref.json?name=nangu.channelListUserChannelNumbers", data = None, header = header)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením seznamu kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit() 
    if "listUserChannelNumbers" in data and len(data["listUserChannelNumbers"]) > 0:
      for list2 in data["listUserChannelNumbers"]:
        if list == list2.encode("utf-8"):
          for channel in data["listUserChannelNumbers"][list.decode("utf-8")]:
            channels.update({int(data["listUserChannelNumbers"][list.decode("utf-8")][channel]) : channel})
          with open(filename, "w") as file:
            for key in sorted(channels.keys()):
              if channels[key] in channels_mapping: 
                line = channels_mapping[channels[key]]+";"+str(key)
                file.write('%s\n' % line)
      xbmcgui.Dialog().notification("Sledování O2TV","Seznam kanálů byl načtený", xbmcgui.NOTIFICATION_INFO, 4000)          
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Nanalezen žádný seznam v O2", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  
      
def reset_channel_list():     
    filename = addon_userdata_dir + "channels.txt"
    if os.path.exists(filename):
      os.remove(filename) 
    channels = load_channels()
    xbmcgui.Dialog().notification("Sledování O2TV","Seznam kanálů byl resetovaný", xbmcgui.NOTIFICATION_INFO, 4000) 
    
def list_channels_edit():
    channels = load_channels()
    if len(channels) > 0:
      for channel in channels:
        list_item = xbmcgui.ListItem(label=str(channel[1]) + " " + channel[0])
        url = get_url(action='edit_channel', channelName = channel[0])  
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
      xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)
    
def load_channels():
    channels = {}
    channels_ordered = []
    channels_to_add = {}
    filename = addon_userdata_dir + "channels.txt"

    try:
      with open(filename, "r") as file:
        for line in file:
          channel = line[:-1].split(";")
          channels_ordered.append((channel[0], int(channel[1])))
          max_num = int(channel[1])

      if addon.getSetting("disable_channels_adding") != "true":
        for offer in offers:
          post = {"locality" : locality, "tariff" : tariff, "isp" : isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
          data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = header)                                                               
          if "err" in data:
            xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
            sys.exit()  
          if "channels" in data and len(data["channels"]) > 0:
            for channel in data["channels"]:
              if data["channels"][channel]["channelType"] == "TV":
               
                fnd = 0
                for channel_ordered in channels_ordered:
                  if channel_ordered[0] == data["channels"][channel]["channelName"].encode("utf-8"):
                    fnd = 1
                if fnd == 0:
                  channels_to_add.update({int(data["channels"][channel]["channelNumber"]) : data["channels"][channel]["channelName"]})
          for key in sorted(channels_to_add.keys()):
            max_num = max_num + 1
            with open(filename, "a+") as file:
              line = channels_to_add[key].encode("utf-8")+";"+str(max_num)
              channels_ordered.append((channels_to_add[key].encode("utf-8"), max_num)) 
              file.write('%s\n' % line)

    except IOError:
      for offer in offers:
        post = {"locality" : locality, "tariff" : tariff, "isp" : isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
        data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = header)                                                               
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()  
        if "channels" in data and len(data["channels"]) > 0:
          for channel in data["channels"]:
            if data["channels"][channel]["channelType"] == "TV":
              channels.update({data["channels"][channel]["channelNumber"] : data["channels"][channel]["channelName"]})
      if len(channels) > 0:
        with open(filename, "w") as file:
          for key in sorted(channels.keys()):
            line = channels[key].encode("utf-8")+";"+str(key)
            channels_ordered.append((channels[key].encode("utf-8"), key)) 
            file.write('%s\n' % line)
    return channels_ordered         

def edit_channel(channelName):
    num = -1
    channels = {}
    channels_ordered = []
    filename = addon_userdata_dir + "channels.txt"
    try:
      with open(filename, "r") as file:
        for line in file:
          channel = line[:-1].split(";")
          channels_ordered.append((channel[0], int(channel[1])))
    except IOError:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)

    if addon.getSetting("disable_channels_adding") != "true":
      for offer in offers:
        post = {"locality" : locality, "tariff" : tariff, "isp" : isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
        data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = header)                                                               
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()  
        if "channels" in data and len(data["channels"]) > 0:
          for channel in data["channels"]:
            if data["channels"][channel]["channelType"] == "TV":
              fnd = 0
              for channel_ordered in channels_ordered:
                if channel_ordered[0] == data["channels"][channel]["channelName"].encode("utf-8"):
                  fnd = 1
              if fnd == 0:
                max_num = max_num + 1
                with open(filename, "a+") as file:
                  line = data["channels"][channel]["channelName"].encode("utf-8")+";"+str(max_num)
                  channels_ordered.append((data["channels"][channel]["channelName"].encode("utf-8"), max_num)) 
                  file.write('%s\n' % line)

    for channel in channels_ordered:
      if channel[0] == channelName:
        num = channel[1]
      else:
        channels.update({channel[1] : channel[0]})
      
    new_num = xbmcgui.Dialog().numeric(0, "Číslo kanálu", str(num))
    if int(new_num) > 0:
      if int(new_num) in channels.keys():
        xbmcgui.Dialog().notification("Sledování O2TV","Číslo kanálu " + new_num + " je už použité u kanálu " + channels[int(new_num)], xbmcgui.NOTIFICATION_ERROR, 4000)
      else:  
        channels[int(new_num)] = channelName
        channels.update({ int(new_num) : channelName})
        with open(filename, "w") as file:
          for key in sorted(channels.keys()):
            line = channels[key]+";"+str(key)
            file.write('%s\n' % line)

############### IPTV ################

def generate_playlist():
    if addon.getSetting("output_dir") is None or len(addon.getSetting("output_dir")) == 0:
      xbmcgui.Dialog().notification("Sledování O2TV","Nastav adresář pro playlist!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit() 
             
    channels_ordered = load_channels()    
    channels = {}
    channel_data = {}

    filename = addon.getSetting("output_dir") + "playlist.m3u"

    for offer in offers:
      post = {"locality" : locality, "tariff" : tariff, "isp" : isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = header)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  

      if "channels" in data and len(data["channels"]) > 0:
        for channel in data["channels"]:
          if data["channels"][channel]["channelType"] == "TV":
            for channel_ordered in channels_ordered:
              if(channel_ordered[0] == data["channels"][channel]["channelName"].encode("utf-8")):
                num = channel_ordered[1]
              
            channels.update({ num : {"channelName" : data["channels"][channel]["channelName"], "channelKey" : data["channels"][channel]["channelKey"]}})

    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/channels/", data = None, header = header_unity)                                                               
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  
    if "result" in data and len(data["result"]) > 0:
      for channel in data["result"]:
        channel_data.update({channel["channel"]["channelKey"] : "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"]});

    with open(filename, "w") as file:
      file.write('%s\n' % "#EXTM3U")
      for channel in sorted(channels.keys()):  
        if channels[channel]["channelKey"] in channel_data:   
          logo = channel_data[channels[channel]["channelKey"]].encode("utf-8")
        else:
          logo = ""  
        line = "#EXTINF:-1 tvh-epg=\"0\" tvg-logo=\"" + logo + "\"," + channels[channel]["channelName"].encode("utf-8")
        file.write('%s\n' % line)
        line = "plugin://plugin.video.archivo2tv/?action=get_stream_url&channelKey=" + channels[channel]["channelKey"].encode("utf-8")
        file.write('%s\n' % line)
          
    xbmcgui.Dialog().notification("Sledování O2TV","Playlist byl uložený", xbmcgui.NOTIFICATION_INFO, 4000)    

def generate_epg():
    import epg
    epg.load_epg()  
    
def iptv_sc_play(channelName, startdatetime):
    epgId = -1
    channels_mapping = {}

    from_ts = int(time.mktime(time.strptime(startdatetime, "%d.%m.%Y %H:%M")))
    if from_ts > int(time.mktime(datetime.now().timetuple())):
        xbmcgui.Dialog().notification("Sledování O2TV","Nelze přehrát budoucí pořad!", xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit()  
    else:
      for offer in offers:
        post = {"locality" : locality, "tariff" : tariff, "isp" : isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
        data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = header)                                                               
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()  
        if "channels" in data and len(data["channels"]) > 0:
          for channel in data["channels"]:
            if data["channels"][channel]["channelType"] == "TV":
               channels_mapping.update({data["channels"][channel]["channelName"].encode("utf-8") : data["channels"][channel]["channelKey"].encode("utf-8")})

      data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?channelKey=" + quote(channels_mapping[channelName]) + "&from=" + str(from_ts*1000) + "&forceLimit=true&limit=500", data = None, header = header_unity)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit() 
      if "epg" in data and len(data["epg"]) > 0 and len(data["epg"]["items"]) > 0 and len(data["epg"]["items"][0]["programs"]) > 0:
        for programs in data["epg"]["items"][0]["programs"]:
          if str(programs["start"]) == str(from_ts*1000):
            startts = programs["start"]
            start = datetime.fromtimestamp(programs["start"]/1000)
            endts = programs["end"]
            end = datetime.fromtimestamp(programs["end"]/1000)        
            epgId = programs["epgId"]
            title = day_translation_short[start.strftime("%A")].decode("utf-8") + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + " | " + programs["name"]
      if int(epgId) > 0:
        if int(endts/1000) < int(time.mktime(datetime.now().timetuple())):
          play_video(type = "archiv_iptv", channelKey = channels_mapping[channelName], start = startts, end = endts, epgId = epgId, title = title)
        else:
          play_video(type = "live_iptv", channelKey =channels_mapping[channelName], start = None, end = None, epgId = None, title = None)
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Pořad u O2 nenalezen! Používáte EPG z doplňku Sledování O2TV?", xbmcgui.NOTIFICATION_ERROR, 10000)
        sys.exit()  

def iptv_sc_rec(channelName, startdatetime):
    epgId = -1
    channels_mapping = {}

    from_ts = int(time.mktime(time.strptime(startdatetime, "%d.%m.%Y %H:%M")))

    for offer in offers:
      post = {"locality" : locality, "tariff" : tariff, "isp" : isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = header)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "channels" in data and len(data["channels"]) > 0:
        for channel in data["channels"]:
          if data["channels"][channel]["channelType"] == "TV":
             channels_mapping.update({data["channels"][channel]["channelName"].encode("utf-8") : data["channels"][channel]["channelKey"].encode("utf-8")})

    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?channelKey=" + quote(channels_mapping[channelName]) + "&from=" + str(from_ts*1000) + "&forceLimit=true&limit=500", data = None, header = header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit() 
    if "epg" in data and len(data["epg"]) > 0 and len(data["epg"]["items"]) > 0 and len(data["epg"]["items"][0]["programs"]) > 0:
      for programs in data["epg"]["items"][0]["programs"]:
        if str(programs["start"]) == str(from_ts*1000):
          startts = programs["start"]
          start = datetime.fromtimestamp(programs["start"]/1000)
          endts = programs["end"]
          end = datetime.fromtimestamp(programs["end"]/1000)        
          epgId = programs["epgId"]
          title = day_translation_short[start.strftime("%A")].decode("utf-8") + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + " | " + programs["name"]
    if int(epgId) > 0:
      add_recording(epgId)
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Pořad u O2 nenalezen! Používáte EPG z doplňku Sledování O2TV?", xbmcgui.NOTIFICATION_ERROR, 10000)
      sys.exit()  
        
############### main ################
check_settings() 
if "@" in addon.getSetting("username"):
  access_token, subscription, isp, locality, offers, tariff, sdata = get_auth_token()
else:
  access_token, subscription, isp, locality, offers, tariff, sdata = get_auth_password()

day_translation = {"Monday" : "Pondělí", "Tuesday" : "Úterý", "Wednesday" : "Středa", "Thursday" : "Čtvrtek", "Friday" : "Pátek", "Saturday" : "Sobota", "Sunday" : "Neděle"}  
day_translation_short = {"Monday" : "Po", "Tuesday" : "Út", "Wednesday" : "St", "Thursday" : "Čt", "Friday" : "Pá", "Saturday" : "So", "Sunday" : "Ne"}  

def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params["action"] == "list_live":
            list_live(params["page"])
        elif params["action"] == "list_archiv":
            list_archiv()
        elif params["action"] == "list_arch_days":
            list_arch_days(params["channelKey"])
        elif params['action'] == 'list_program':
            list_program(params["channelKey"], params["day_min"])
        elif params['action'] == 'list_planning_recordings':
            list_planning_recordings()
        elif params["action"] == "list_rec_days":
            list_rec_days(params["channelKey"])
        elif params['action'] == 'future_program':
            future_program(params["channelKey"], params["day"])
        elif params["action"] == "list_recordings":
            list_recordings()
        elif params["action"] == "list_future_recordings":
            list_future_recordings()
        elif params["action"] == "delete_recording":
            delete_recording(params["pvrProgramId"])
        elif params["action"] == "add_recording":
            add_recording(params["epgId"])
        elif params['action'] == 'play_video':
            play_video(type = "archiv", channelKey = params["channelKey"], start = params["start"], end = params["end"], epgId = params["epgId"], title = None)
        elif params['action'] == 'play_live':
            play_video(type = "live", channelKey = params["channelKey"], start = None, end = None, epgId = None, title = params["title"])
        elif params['action'] == 'play_recording':
            play_video(type = "recording", channelKey = None, start = None, end = None, epgId = params["pvrProgramId"], title = params["title"])
        elif params['action'] == 'list_search':
            list_search()
        elif params['action'] == 'program_search':
            program_search(params["query"])
        elif params['action'] == 'list_channels_list':
            list_channels_list()
        elif params['action'] == 'get_o2_channels_lists':
            get_o2_channels_lists()
        elif params['action'] == 'load_o2_channel_list':
            load_o2_channel_list(params["list"])            
        elif params['action'] == 'reset_channel_list':
            reset_channel_list()            
        elif params['action'] == 'list_channels_edit':
            list_channels_edit()
        elif params['action'] == 'edit_channel':
            edit_channel(params["channelName"])
        elif params['action'] == 'generate_playlist':
            generate_playlist()
        elif params['action'] == 'generate_epg':
            generate_epg()
        elif params['action'] == 'get_stream_url':
            play_video(type = "live_iptv", channelKey = params["channelKey"], start = None, end = None, epgId = None, title = None)
        elif params['action'] == 'iptv_sc_play':
            iptv_sc_play(params["channel"], params["startdatetime"])
        elif params['action'] == 'iptv_sc_rec':
            iptv_sc_rec(params["channel"], params["startdatetime"])
        else:
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        list_menu()

if __name__ == '__main__':
    router(sys.argv[2][1:])
