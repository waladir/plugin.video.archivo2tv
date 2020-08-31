# -*- coding: utf-8 -*-
import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from datetime import datetime 

from o2tv.utils import get_url, get_color, encode
from o2tv.epg import get_epg_live, get_listitem_epg_details
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

    channels_details = get_epg_live(len(channels_nums.keys()))
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
          live = "[COLOR " + str(color) + "] | " + title + " | " + start.strftime("%H:%M") + " - " + end.strftime("%H:%M") + "[/COLOR]"
          live_noncolor = " | " + title + " | " + start.strftime("%H:%M") + " - " + end.strftime("%H:%M")
          list_item = xbmcgui.ListItem(label=encode(channelName) + encode(live))
          list_item.setInfo("video", {"mediatype":"movie", "title": encode(channelName) + encode(live_noncolor)}) 
          list_item = get_listitem_epg_details(list_item, str(channels_details[channels_nums[num]]["epgId"]), channels_data[channels_nums[num]]["logo"])
        else: 
          live = ""
          live_noncolor = ""
          list_item = xbmcgui.ListItem(label=encode(channelName) + encode(live))
        list_item.setContentLookup(False)          
        list_item.setProperty("IsPlayable", "true")
        if channels_nums[num] in channels_details:
          list_item.addContextMenuItems([("Související pořady", "Container.Update(plugin://plugin.video.archivo2tv?action=list_related&epgId=" + str(channels_details[channels_nums[num]]["epgId"]) + "&label=Související / " + encode(channels_details[channels_nums[num]]["title"]) + ")"),
                                         ("Vysílání pořadu", "Container.Update(plugin://plugin.video.archivo2tv?action=list_same&epgId=" + str(channels_details[channels_nums[num]]["epgId"]) + "&label=" + encode(channels_details[channels_nums[num]]["title"]) + ")")])       
        url = get_url(action='play_live', channelKey = encode(channels_data[channels_nums[num]]["channelKey"]), title = encode(channelName) + encode(live_noncolor))
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
      i = i + 1

    if int(page) * pagesize <= i:
      list_item = xbmcgui.ListItem(label="další strana")
      url = get_url(action='list_live', page = int(page) + 1, label = "další strana")  
      list_item.setProperty("IsPlayable", "false")
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)     
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)
