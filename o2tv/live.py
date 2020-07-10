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
    channels_ordered = load_channels()  
    channels = {}
    channel_data = {}     
    num = 0
    pagesize = int(addon.getSetting("live_pagesize"))

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
          if addon.getSetting("details") == "true" and "live" in channel:
            channel_data.update({channel["channel"]["channelKey"].encode("utf-8") : { "logo" : "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"], "live" : { "epgId" : channel["live"]["epgId"], "name" : channel["live"]["name"], "start" : channel["live"]["start"], "end" : channel["live"]["end"] }}})
          else:
            channel_data.update({channel["channel"]["channelKey"].encode("utf-8") : { "logo" : "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"]}})

    color = get_color(addon.getSetting("label_color_live"))   
    startitem = (int(page)-1) * pagesize
    i = 0
    for num in sorted(channels.keys()):  
      if i >= startitem and i < startitem + pagesize: 
        if channels[num]["channelKey"].encode("utf-8") in channel_data and "live" in channel_data[channels[num]["channelKey"].encode("utf-8")]:
          start = datetime.fromtimestamp(int(channel_data[channels[num]["channelKey"].encode("utf-8")]["live"]["start"])/1000)
          end = datetime.fromtimestamp(int(channel_data[channels[num]["channelKey"].encode("utf-8")]["live"]["end"])/1000)
          live = "[COLOR " + str(color) + "] | " + channel_data[channels[num]["channelKey"].encode("utf-8")]["live"]["name"] + " | " + start.strftime("%H:%M") + " - " + end.strftime("%H:%M") + "[/COLOR]"
          live_noncolor = " | " + channel_data[channels[num]["channelKey"].encode("utf-8")]["live"]["name"] + " | " + start.strftime("%H:%M") + " - " + end.strftime("%H:%M")
          list_item = xbmcgui.ListItem(label=channels[num]["channelName"] + live)
          if addon.getSetting("details_live") == "true": 
            list_item.setInfo("video", {"mediatype":"movie", "title": channels[num]["channelName"] + live_noncolor}) 
            list_item = o2api.get_epg_details(list_item, str(channel_data[channels[num]["channelKey"].encode("utf-8")]["live"]["epgId"]), channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"])
          else:
            list_item.setInfo("video", {"mediatype":"movie", "title": channels[num]["channelName"] + live_noncolor})
            if channels[num]["channelKey"].encode("utf-8") in channel_data: 
              list_item.setArt({'thumb':channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"], 'icon':channel_data[channels[num]["channelKey"].encode("utf-8")]["logo"]})
        else: 
          live = ""
          live_noncolor = ""
          list_item = xbmcgui.ListItem(label=channels[num]["channelName"] + live)
          
        list_item.setContentLookup(False)          
        list_item.setProperty("IsPlayable", "true")                                                                                                                                 
        url = get_url(action='play_live', channelKey = channels[num]["channelKey"].encode("utf-8"), title = (channels[num]["channelName"] + live_noncolor).encode("utf-8"))
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
