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
from o2tv.epg import get_epg_ts
from o2tv.channels import load_channels 

_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

def list_archiv(label):
    xbmcplugin.setPluginCategory(_handle, label)

    channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter=1) # pylint: disable=unused-variable 

    for num in sorted(channels_nums.keys()):  
      list_item = xbmcgui.ListItem(label=channels_nums[num])
      if channels_data[channels_nums[num]] and len(channels_data[channels_nums[num]]["logo"]) > 0:
        list_item.setArt({'thumb': channels_data[channels_nums[num]]["logo"], 'icon': channels_data[channels_nums[num]]["logo"]})
      url = get_url(action='list_arch_days', channelKey = channels_data[channels_nums[num]]["channelKey"].encode("utf-8"), label = label + " / " + channels_nums[num].encode("utf-8"))  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)

def list_arch_days(channelKey, label):
    xbmcplugin.setPluginCategory(_handle, label)
    for i in range (8):
      day = date.today() - timedelta(days = i)
      if i == 0:
        den_label = "Dnes"
        den = "Dnes"
      elif i == 1:
        den_label = "Včera"
        den = "Včera"
      else:
        den_label = utils.day_translation_short[day.strftime("%w")] + " " + day.strftime("%d.%m")
        den = utils.day_translation[day.strftime("%w")].decode("utf-8") + " " + day.strftime("%d.%m.%Y")
      list_item = xbmcgui.ListItem(label=den)
      url = get_url(action='list_program', channelKey = channelKey, day_min = i, label = label + " / " + den_label)  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)

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

    events = {}
    if addon.getSetting("use_epg_db") == "true":
      events = get_epg_ts(channelKey.decode("utf-8"), from_ts, to_ts, 5)
    else:
      data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?channelKey=" + quote(channelKey) + "&from=" + str(from_ts*1000) + "&to=" + str(to_ts*1000) + "&forceLimit=true&limit=500", data = None, header = o2api.header_unity)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením programu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  

      if "epg" in data and len(data["epg"]) > 0 and len(data["epg"]["items"]) > 0 and len(data["epg"]["items"][0]["programs"]) > 0:
        for programs in data["epg"]["items"][0]["programs"]:
          startts = programs["start"]/1000
          start = datetime.fromtimestamp(programs["start"]/1000)
          endts = programs["end"]/1000
          end = datetime.fromtimestamp(programs["end"]/1000)
          epgId = programs["epgId"]
          events.update({ startts : { "epgId" : epgId, "startts" : startts, "endts" : endts, "start" : start , "end" : end, "title" : programs["name"]}})
      else:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením programu", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()            
     
    for key in sorted(events.keys()):
      if int(events[key]["endts"]) > int(time.mktime(datetime.now().timetuple()))-60*60*24*7:
        list_item = xbmcgui.ListItem(label = utils.day_translation_short[events[key]["start"].strftime("%w")].decode("utf-8") + " " + events[key]["start"].strftime("%d.%m %H:%M") + " - " + events[key]["end"].strftime("%H:%M") + " | " + events[key]["title"])
        list_item = o2api.get_epg_details(list_item, str(events[key]["epgId"]), "")
        list_item.setProperty("IsPlayable", "true")
        list_item.setContentLookup(False)          
        list_item.addContextMenuItems([("Přidat nahrávku", "RunPlugin(plugin://plugin.video.archivo2tv?action=add_recording&epgId=" + str(events[key]["epgId"]) + ")",)])       
        url = get_url(action='play_archiv', channelKey = channelKey, start = events[key]["startts"], end = events[key]["endts"], epgId = events[key]["epgId"])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)