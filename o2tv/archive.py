# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from urllib import urlencode, quote
except ImportError:
    from urllib.parse import urlencode, quote
    
from datetime import date, datetime, timedelta
import time

from o2tv.utils import plugin_id, get_url, get_color, decode, encode
from o2tv import utils
from o2tv.epg import get_epg_ts, get_listitem_epg_details
from o2tv.channels import load_channels 

_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id = plugin_id)

def list_archiv(label):
    xbmcplugin.setPluginCategory(_handle, label)

    channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter=1) # pylint: disable=unused-variable 

    for num in sorted(channels_nums.keys()):  
      list_item = xbmcgui.ListItem(label=channels_nums[num])
      if channels_data[channels_nums[num]] and len(channels_data[channels_nums[num]]["logo"]) > 0:
        list_item.setArt({'thumb': channels_data[channels_nums[num]]["logo"], 'icon': channels_data[channels_nums[num]]["logo"]})
      url = get_url(action='list_arch_days', channelKey = encode(channels_data[channels_nums[num]]["channelKey"]), label = encode(label + " / " + channels_nums[num]))  
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
        den = decode(utils.day_translation[day.strftime("%w")]) + " " + day.strftime("%d.%m.%Y")
      list_item = xbmcgui.ListItem(label=den)
      url = get_url(action='list_program', channelKey = channelKey, day_min = i, label = label + " / " + den_label)  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)

def list_program(channelKey, day_min, label):
    label = label.replace("Archiv /","")
    xbmcplugin.setPluginCategory(_handle, label)
    channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter = 1) # pylint: disable=unused-variable 
    if int(day_min) == 0:
      from_datetime = datetime.combine(date.today(), datetime.min.time())
      to_datetime = datetime.now()
    else:
      from_datetime = datetime.combine(date.today(), datetime.min.time()) - timedelta(days = int(day_min))
      to_datetime = datetime.combine(from_datetime, datetime.max.time())
    from_ts = int(time.mktime(from_datetime.timetuple()))
    to_ts = int(time.mktime(to_datetime.timetuple()))

    events = {}
    events = get_epg_ts(decode(channelKey), from_ts, to_ts, 8)
     
    for key in sorted(events.keys()):
      if int(events[key]["endts"]) > int(time.mktime(datetime.now().timetuple()))-60*60*24*7:
        list_item = xbmcgui.ListItem(label = decode(utils.day_translation_short[events[key]["start"].strftime("%w")]) + " " + events[key]["start"].strftime("%d.%m %H:%M") + " - " + events[key]["end"].strftime("%H:%M") + " | " + events[key]["title"])
        list_item = get_listitem_epg_details(list_item, str(events[key]["epgId"]), channels_data[channels_key_mapping[decode(channelKey)]]["logo"])
        list_item.setProperty("IsPlayable", "true")
        list_item.setContentLookup(False)          
        menus = [("Přidat nahrávku", "RunPlugin(plugin://" + plugin_id + "?action=add_recording&epgId=" + str(events[key]["epgId"]) + ")"), 
                ("Související pořady", "Container.Update(plugin://" + plugin_id + "?action=list_related&epgId=" + str(events[key]["epgId"]) + "&label=Související / " + encode(events[key]["title"]) + ")"), 
                ("Vysílání pořadu", "Container.Update(plugin://" + plugin_id + "?action=list_same&epgId=" + str(events[key]["epgId"]) + "&label=" + encode(events[key]["title"]) + ")")]
        if addon.getSetting("download_streams") == "true": 
          menus.append(("Stáhnout", "RunPlugin(plugin://" + plugin_id + "?action=add_to_queue&epgId=" + str(events[key]["epgId"]) + ")"))
        list_item.addContextMenuItems(menus)       
        url = get_url(action='play_archiv', channelKey = channelKey, start = events[key]["startts"], end = events[key]["endts"], epgId = events[key]["epgId"])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)