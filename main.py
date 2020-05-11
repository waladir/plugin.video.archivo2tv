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

_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type":"application/json"}

def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urlencode(kwargs))

def check_settings():
    if not addon.getSetting("username") or not addon.getSetting("password") or not addon.getSetting("deviceid") or not addon.getSetting("devicename") or  not addon.getSetting("devicetype"):
      xbmcgui.Dialog().notification("Archiv O2TV","V nastavení je nutné mít vyplněné všechny údaje", xbmcgui.NOTIFICATION_ERROR, 5000)
      sys.exit()
      
      
def get_auth_token():
    post = {"username":addon.getSetting("username"),"password":addon.getSetting("password")}
    request = Request("https://www.o2tv.cz/unity/api/v1/services/", data = json.dumps(post), headers = headers)
    try:
      html = urlopen(request).read()
    except HTTPError as e:
      if e.reason == "Unauthorized":
        xbmcgui.Dialog().notification("Archiv O2TV","Chybné přihlašovací údaje!", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()            
      xbmcgui.Dialog().notification("Archiv O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()            

    data = json.loads(html)
    if "remoteAccessToken" in data and data["remoteAccessToken"] <>'' and "services" in data and len(data["services"]) > 0:
        remoteAccessToken = data["remoteAccessToken"]
        serviceId = data["services"][0]['serviceId']
        post = {"remoteAccessToken":remoteAccessToken}
        request = Request("https://www.o2tv.cz/unity/api/v1/services/selection/" + serviceId + "/", data = json.dumps(post), headers = headers)
        html = urlopen(request).read()
        data = json.loads(html)

        if "accessToken" in data and data["accessToken"] <> '':
          accessToken = data["accessToken"]
          headers_auth = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type":"application/json", "x-o2tv-access-token":accessToken, "x-o2tv-device-name":addon.getSetting("devicename"), "x-o2tv-device_id":addon.getSetting("deviceid")}
          request = Request("https://www.o2tv.cz/unity/api/v1/user/profile/", data = None, headers = headers_auth)
          html = urlopen(request).read()
          data = json.loads(html)
          if "sdata" in data and data["sdata"] <> '':
            sdata = data["sdata"]
            channels = []
            for channel in data["ottChannels"]["live"]:
              channels.append(channel.encode("utf-8"))
            return accessToken, sdata, channels
          else:
              xbmcgui.Dialog().notification("Archiv O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
              sys.exit()            
        else:
            xbmcgui.Dialog().notification("Archiv O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
            sys.exit()
    else:
        xbmcgui.Dialog().notification("Archiv O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()

def list_menu():
    list_item = xbmcgui.ListItem(label="Kanály")
    url = get_url(action='list_channels')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label="Vyhledávání")
    url = get_url(action='program_search')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

    
def list_channels():
    request = Request("https://www.o2tv.cz/unity/api/v1/channels/", data = None, headers = headers)
    html = urlopen(request).read()   
    data = json.loads(html)
    if "result" in data and len(data["result"]) > 0:
      for channel in data["result"]:
        if  channel["channel"]["channelKey"].encode("utf-8") in channels:
          list_item = xbmcgui.ListItem(label=channel["channel"]["name"])
          logo_url = "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"];
          list_item.setArt({'thumb':logo_url, 'icon':logo_url})
          url = get_url(action='list_days', channelKey = channel["channel"]["channelKey"].encode("utf-8"))  
          xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
      xbmcplugin.endOfDirectory(_handle)
    else:
        xbmcgui.Dialog().notification("Archiv O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()    
        
def list_days(channelKey):
    list_item = xbmcgui.ListItem(label="Živě")
    list_item.setProperty("IsPlayable", "true")
    list_item.setInfo("video", {"mediatype":"movie", "title":channelKey})
    list_item.setContentLookup(False)          
    url = get_url(action='play_live', channelKey = channelKey)  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
   
    for i in range (7):
      day = date.today() - timedelta(days = i)
      if i == 0:
        den = "Dnes"
      elif i == 1:
        den = "Včera"
      else:
        den = day.strftime("%d.%m.%Y");
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
    request = Request("https://www.o2tv.cz/unity/api/v1/epg/depr/?channelKey=" + quote(channelKey) + "&from=" + str(from_ts*1000) + "&to=" + str(to_ts*1000) + "&forceLimit=true&limit=500", data = None, headers = headers)
    html = urlopen(request).read()   
    data = json.loads(html)
    if "epg" in data and len(data["epg"]["items"][0]["programs"]) > 0:
      for programs in data["epg"]["items"][0]["programs"]:
        start = datetime.fromtimestamp(programs["start"]/1000)
        end = datetime.fromtimestamp(programs["end"]/1000)
        epgId = programs["epgId"]
        if to_ts > int(programs["end"]/1000):        
          request = Request("https://www.o2tv.cz/unity/api/v1/programs/" + str(epgId) + "/", data = None, headers = headers)
          html = urlopen(request).read()   
          data = json.loads(html)
          img = "";
          plot = "";
          if "images" in data and len(data["images"]) > 0:
             plot = data["longDescription"]
             img = data["images"][0]["cover"]
   
          list_item = xbmcgui.ListItem(label= start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + " " + programs["name"])
          list_item.setProperty("IsPlayable", "true")
          list_item.setArt({'thumb': "https://www.o2tv.cz/" + img, 'icon': "https://www.o2tv.cz/" + img})
          list_item.setInfo("video", {"mediatype":"movie", "title":programs["name"], "plot":plot})

          if "ratings" in data and len(data["ratings"]) > 0:
            for rating, rating_value in data["ratings"].items():
              list_item.setRating(rating, rating_value/10)
    
          list_item.setContentLookup(False)          
          url = get_url(action='play_video', epgId = epgId)
          xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    else:
        xbmcgui.Dialog().notification("Archiv O2TV","Problém s načtením programu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()    
    xbmcplugin.endOfDirectory(_handle)
    
def play_video(epgId):
    headers_auth = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type":"application/json", "x-o2tv-access-token":accessToken, "x-o2tv-device-name":addon.getSetting("devicename"), "x-o2tv-device_id":addon.getSetting("deviceid"), "x-o2tv-sdata":sdata}
    request = Request("https://www.o2tv.cz/unity/api/v1/programs/" + str(epgId) +"/playlist/", data = None, headers = headers_auth)
    html = urlopen(request).read()   
    data = json.loads(html)
    url = data["playlist"][0]["streamUrls"]["main"].replace("https://stc.o2tv.cz", "https://vst05-2.o2tv.cz:443")
    listitem = xbmcgui.ListItem(path = url)
    listitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
    listitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    listitem.setMimeType('application/dash+xml')
    listitem.setContentLookup(False)       
    xbmcplugin.setResolvedUrl(_handle, True, listitem)

def play_live(channelKey):
    headers_auth = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type":"application/json", "x-o2tv-access-token":accessToken, "x-o2tv-device-name":addon.getSetting("devicename"), "x-o2tv-device_id":addon.getSetting("deviceid"), "x-o2tv-sdata":sdata}
    request = Request("https://www.o2tv.cz/unity/api/v1/channels/playlist/?channelKey=" + quote(channelKey), data = None, headers = headers_auth)
    html = urlopen(request).read()   
    data = json.loads(html)
    url = data["playlist"][0]["streamUrls"]["main"].replace("https://stc.o2tv.cz", "https://vst22-3.o2tv.cz:443")
    listitem = xbmcgui.ListItem(path = url)
    listitem.setInfo("video", {"mediatype":"movie", "title":data["setup"]["description"]})
    listitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
    listitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    listitem.setMimeType('application/dash+xml')
    listitem.setContentLookup(False)       
    xbmcplugin.setResolvedUrl(_handle, True, listitem)

def program_search():
    input = xbmc.Keyboard('', 'Hledat')
    input.doModal()
    if not input.isConfirmed(): 
        return
    query = input.getText()
    if len(query) == 0:
      xbmcgui.Dialog().notification("Archiv O2TV","Je potřeba zadat vyhledávaný řetězec", xbmcgui.NOTIFICATION_ERROR, 4000)
      return   

    max_ts = int(time.mktime(datetime.now().timetuple()))
    request = Request("https://www.o2tv.cz/unity/api/v1/search/tv/depr/?groupLimit=1&maxEnd=" + str(max_ts*1000) + "&q=" + quote(query), data = None, headers = headers)
    html = urlopen(request).read()   
    data = json.loads(html)
    
    if "groupedSearch" in data and "groups" in data["groupedSearch"] and len(data["groupedSearch"]["groups"]) > 0:
      for item in data["groupedSearch"]["groups"]:
        programs = item["programs"][0]
        start = datetime.fromtimestamp(programs["start"]/1000)
        end = datetime.fromtimestamp(programs["end"]/1000)
        epgId = programs["epgId"]
        
        request = Request("https://www.o2tv.cz/unity/api/v1/programs/" + str(epgId) + "/", data = None, headers = headers)
        html = urlopen(request).read()   
        data = json.loads(html)
        img = "";
        plot = "";
        if "images" in data and len(data["images"]) > 0:
           plot = data["longDescription"]
           img = data["images"][0]["cover"]
 
        list_item = xbmcgui.ListItem(label= start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + " " + programs["channelKey"] + " - " + programs["name"])
        list_item.setProperty("IsPlayable", "true")
        list_item.setArt({'thumb': "https://www.o2tv.cz/" + img, 'icon': "https://www.o2tv.cz/" + img})
        list_item.setInfo("video", {"mediatype":"movie", "title":programs["name"], "plot":plot})

        if "ratings" in data and len(data["ratings"]) > 0:
          for rating, rating_value in data["ratings"].items():
            list_item.setRating(rating, rating_value/10)
  
        list_item.setContentLookup(False)          
        url = get_url(action='play_video', epgId = epgId)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
      xbmcplugin.endOfDirectory(_handle)
    else:
      xbmcgui.Dialog().notification("Archiv O2TV","Nic nenalezeno", xbmcgui.NOTIFICATION_INFO, 3000)

check_settings() 
accessToken, sdata, channels = get_auth_token()
   
def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params["action"] == "list_channels":
            list_channels()
        elif params["action"] == "list_days":
            list_days(params["channelKey"])
        elif params['action'] == 'list_program':
            list_program(params["channelKey"], params["day_min"])
        elif params['action'] == 'play_video':
            play_video(params["epgId"])
        elif params['action'] == 'play_live':
            play_live(params["channelKey"])
        elif params['action'] == 'program_search':
            program_search()
        else:
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        list_menu()


if __name__ == '__main__':
    router(sys.argv[2][1:])
