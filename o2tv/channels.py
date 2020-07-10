# -*- coding: utf-8 -*-

import os
import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

from urllib import urlencode, quote

from o2tv.o2api import call_o2_api
from o2tv import o2api
from o2tv.utils import get_url

_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')
addon_userdata_dir = xbmc.translatePath(addon.getAddonInfo('profile')) 


def list_channels_list(label):
    xbmcplugin.setPluginCategory(_handle, label)
    list_item = xbmcgui.ListItem(label="Ruční editace")
    url = get_url(action="list_channels_edit", label = label + " / " + "Ruční editace")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label="Načtení uživatelského seznamu z O2")
    url = get_url(action="get_o2_channels_lists", label = label + " / " + "Načtení z O2")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label="Resetovat seznam kanálů")
    url = get_url(action="reset_channel_list")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def get_o2_channels_lists(label):
    xbmcplugin.setPluginCategory(_handle, label)
    data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/settings/get-user-pref.json?name=nangu.channelListUserChannelNumbers", data = None, header = o2api.header)
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

    for offer in o2api.offers:
      post = {"locality" : o2api.locality, "tariff" : o2api.tariff, "isp" : o2api.isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = o2api.header)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "channels" in data and len(data["channels"]) > 0:
        for channel in data["channels"]:
          if data["channels"][channel]["channelType"] == "TV":
             channels_mapping.update({data["channels"][channel]["channelKey"] : data["channels"][channel]["channelName"].encode("utf-8")})

    data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/settings/get-user-pref.json?name=nangu.channelListUserChannelNumbers", data = None, header = o2api.header)
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
    load_channels()
    xbmcgui.Dialog().notification("Sledování O2TV","Seznam kanálů byl resetovaný", xbmcgui.NOTIFICATION_INFO, 4000) 
    
def list_channels_edit(label):
    xbmcplugin.setPluginCategory(_handle, label)
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
    max_num = 0

    try:
      with open(filename, "r") as file:
        for line in file:
          channel = line[:-1].split(";")
          channels_ordered.append((channel[0], int(channel[1])))
          max_num = int(channel[1])

      if addon.getSetting("disable_channels_adding") != "true":
        for offer in o2api.offers:
          post = {"locality" : o2api.locality, "tariff" : o2api.tariff, "isp" : o2api.isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
          data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = o2api.header)                                                               
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
      for offer in o2api.offers:
        post = {"locality" : o2api.locality, "tariff" : o2api.tariff, "isp" : o2api.isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
        data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = o2api.header)                                                               
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
    max_num = 0
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
      for offer in o2api.offers:
        post = {"locality" : o2api.locality, "tariff" : o2api.tariff, "isp" : o2api.isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
        data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = o2api.header)                                                               
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
