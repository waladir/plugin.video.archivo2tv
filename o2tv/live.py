# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

from urllib import urlencode
from datetime import datetime 

from o2tv.o2api import call_o2_api
from o2tv import o2api
from o2tv.utils import get_url, get_color
from o2tv.epg import get_epg_live
from o2tv.channels import load_channels 

_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

def list_live(page, label):
    xbmcplugin.setPluginCategory(_handle, label)

    channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter = 1) # pylint: disable=unused-variable 
    channels_details = {} 
    num = 0
    pagesize = int(addon.getSetting("live_pagesize"))

    if addon.getSetting("use_epg_db") == "true":
      channels_details = get_epg_live(len(channels_nums.keys()))
    else:
      data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/channels/", data = None, header = o2api.header_unity)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "result" in data and len(data["result"]) > 0:
        for channel in data["result"]:
          if "live" in channel:
            start = datetime.fromtimestamp(int(channel["live"]["start"]/1000))
            end = datetime.fromtimestamp(int(channel["live"]["end"]/1000))
            channels_details.update({channel["channel"]["name"] : { "epgId" : channel["live"]["epgId"], "title" : channel["live"]["name"], "start" : start, "end" : end }})
    color = get_color(addon.getSetting("label_color_live"))   
    startitem = (int(page)-1) * pagesize
    i = 0
    for num in sorted(channels_nums.keys()):  
      if i >= startitem and i < startitem + pagesize: 
        channelName = channels_nums[num]
        if channels_nums[num] in channels_details:
          title = channels_details[channels_nums[num]]["title"]
          start = channels_details[channels_nums[num]]["start"]
          end = channels_details[channels_nums[num]]["end"]
          live = "[COLOR " + str(color) + "] | " + title.encode("utf-8") + " | " + start.strftime("%H:%M") + " - " + end.strftime("%H:%M") + "[/COLOR]"
          live_noncolor = " | " + title.encode("utf-8") + " | " + start.strftime("%H:%M") + " - " + end.strftime("%H:%M")
          list_item = xbmcgui.ListItem(label=channelName.encode("utf-8") + live)
          list_item.setInfo("video", {"mediatype":"movie", "title": channelName.encode("utf-8") + live_noncolor}) 
          list_item = o2api.get_epg_details(list_item, str(channels_details[channels_nums[num]]["epgId"]), channels_data[channels_nums[num]]["logo"])
        else: 
          live = ""
          live_noncolor = ""
          list_item = xbmcgui.ListItem(label=channelName.encode("utf-8") + live)
        list_item.setContentLookup(False)          
        list_item.setProperty("IsPlayable", "true")  
        url = get_url(action='play_live', channelKey = channels_data[channels_nums[num]]["channelKey"].encode("utf-8"), title = channelName.encode("utf-8") + live_noncolor)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
      i = i + 1

    if int(page) * pagesize <= i:
      list_item = xbmcgui.ListItem(label="další strana")
      url = get_url(action='list_live', page = int(page) + 1, label = "další strana")  
      list_item.setProperty("IsPlayable", "false")
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)     
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)
