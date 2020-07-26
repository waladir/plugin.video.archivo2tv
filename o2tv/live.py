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

from o2tv.channels import load_channels 

_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

def list_live(page, label):
    xbmcplugin.setPluginCategory(_handle, label)

    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable 
    channels_details = {} 
    num = 0
    pagesize = int(addon.getSetting("live_pagesize"))
    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/channels/", data = None, header = o2api.header_unity)                                                               
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  
    if "result" in data and len(data["result"]) > 0:
      for channel in data["result"]:
        if addon.getSetting("details") == "true" and "live" in channel:
          channels_details.update({channel["channel"]["name"] : { "logo" : "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"], "live" : { "epgId" : channel["live"]["epgId"], "name" : channel["live"]["name"], "start" : channel["live"]["start"], "end" : channel["live"]["end"] }}})
        else:
          channels_details.update({channel["channel"]["name"] : { "logo" : "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"]}})

    color = get_color(addon.getSetting("label_color_live"))   
    startitem = (int(page)-1) * pagesize
    i = 0
    for num in sorted(channels_nums.keys()):  
      if i >= startitem and i < startitem + pagesize: 
        if channels_nums[num] in channels_details and "live" in channels_details[channels_nums[num]]:
          start = datetime.fromtimestamp(int(channels_details[channels_nums[num]]["live"]["start"])/1000)
          end = datetime.fromtimestamp(int(channels_details[channels_nums[num]]["live"]["end"])/1000)
          live = "[COLOR " + str(color) + "] | " + channels_details[channels_nums[num]]["live"]["name"].encode("utf-8") + " | " + start.strftime("%H:%M") + " - " + end.strftime("%H:%M") + "[/COLOR]"
          live_noncolor = " | " + channels_details[channels_nums[num]]["live"]["name"].encode("utf-8") + " | " + start.strftime("%H:%M") + " - " + end.strftime("%H:%M")
          
          list_item = xbmcgui.ListItem(label=channels_nums[num].encode("utf-8") + live)
          if addon.getSetting("details_live") == "true": 
            list_item.setInfo("video", {"mediatype":"movie", "title": channels_nums[num].encode("utf-8") + live_noncolor}) 
            list_item = o2api.get_epg_details(list_item, str(channels_details[channels_nums[num]]["live"]["epgId"]), channels_details[channels_nums[num]]["logo"])

          else:
            list_item.setInfo("video", {"mediatype":"movie", "title": channels_nums[num].encode("utf-8") + live_noncolor})
            if channels_nums[num] in channels_details: 
              list_item.setArt({'thumb': channels_details[channels_nums[num]]["logo"], 'icon': channels_details[channels_nums[num]]["logo"]})
        else: 
          live = ""
          live_noncolor = ""
          list_item = xbmcgui.ListItem(label=channels_nums[num].encode("utf-8") + live)
          
        list_item.setContentLookup(False)          
        list_item.setProperty("IsPlayable", "true")      
        url = get_url(action='play_live', channelKey = channels_data[channels_nums[num]]["channelKey"].encode("utf-8"), title = channels_nums[num].encode("utf-8") + live_noncolor)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
      i = i + 1

    if int(page) * pagesize <= i:
      list_item = xbmcgui.ListItem(label="další strana")
      url = get_url(action='list_live', page = int(page) + 1, label = "další strana")  
      list_item.setProperty("IsPlayable", "false")
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)     
    if addon.getSetting("details_live") == "true":
      xbmcplugin.endOfDirectory(_handle)
    else:
      xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)
