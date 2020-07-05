# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

from urllib import urlencode, quote
from datetime import date, datetime, timedelta 
import time

from o2tv.o2api import call_o2_api
from o2tv import o2api
from o2tv.utils import get_url, get_color
from o2tv import utils

from o2tv.channels import load_channels 

_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

def list_archiv(label):
    xbmcplugin.setPluginCategory(_handle, label)
    channels_ordered = load_channels()  
    channels = {}
    channel_data = {}
    num = 0

    for offer in o2api.offers:
      post = {"locality" : o2api.locality, "tariff" : o2api.tariff, "isp" : o2api.isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = o2api.header)                                                               
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

      data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/channels/", data = None, header = o2api.header_unity)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "result" in data and len(data["result"]) > 0:
        for channel in data["result"]:
          channel_data.update({channel["channel"]["channelKey"].encode("utf-8") : { "logo" : "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"]}})

    for num in sorted(channels.keys()):  
      list_item = xbmcgui.ListItem(label=channels[num]["channelName"])
      if addon.getSetting("details") == "true" and channels[num]["channelKey"].encode("utf-8") in channel_data:
        list_item.setArt({'thumb':channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"], 'icon':channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"]})
      url = get_url(action='list_arch_days', channelKey = channels[num]["channelKey"].encode("utf-8"), label = label + " / " + channels[num]["channelName"].encode("utf-8"))  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def list_arch_days(channelKey, label):
    xbmcplugin.setPluginCategory(_handle, label)
    for i in range (7):
      day = date.today() - timedelta(days = i)
      if i == 0:
        den_label = "Dnes"
        den = "Dnes"
      elif i == 1:
        den_label = "Včera"
        den = "Včera"
      else:
        den_label = utils.day_translation_short[day.strftime("%A")] + " " + day.strftime("%d.%m")
        den = utils.day_translation[day.strftime("%A")].decode("utf-8") + " " + day.strftime("%d.%m.%Y")
      list_item = xbmcgui.ListItem(label=den)
      url = get_url(action='list_program', channelKey = channelKey, day_min = i, label = label + " / " + den_label)  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def list_program(channelKey, day_min, label):
    label = label.replace("Archiv /","")
    xbmcplugin.setPluginCategory(_handle, label)
    if int(day_min) == 0:
      from_datetime = datetime.combine(date.today(), datetime.min.time())
      to_datetime = datetime.now()
    else:
      from_datetime = datetime.combine(date.today(), datetime.min.time()) - timedelta(days = int(day_min))
      to_datetime = datetime.combine(from_datetime, datetime.max.time())
    from_ts = int(time.mktime(from_datetime.timetuple()))
    to_ts = int(time.mktime(to_datetime.timetuple()))

    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?channelKey=" + quote(channelKey) + "&from=" + str(from_ts*1000) + "&to=" + str(to_ts*1000) + "&forceLimit=true&limit=500", data = None, header = o2api.header_unity)
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
            img, plot, ratings, cast, directors = o2api.get_epg_details(str(epgId))
   
          list_item = xbmcgui.ListItem(label = utils.day_translation_short[start.strftime("%A")].decode("utf-8") + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + " | " + programs["name"])
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
          url = get_url(action='play_archiv', channelKey = channelKey, start = startts, end = endts, epgId = epgId)
          xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením programu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()    
    xbmcplugin.endOfDirectory(_handle)