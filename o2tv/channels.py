# -*- coding: utf-8 -*-

import os
import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

from urllib import urlencode, quote
import json
import time
import codecs

from o2tv.o2api import call_o2_api
from o2tv import o2api
from o2tv.utils import get_url

_url = sys.argv[0]
if len(sys.argv) > 1:
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
    if addon.getSetting("disable_channels_adding") == "false":
      disable_adding = xbmcgui.Dialog().yesno("Automatické přidávání kanálů", "Pro používání uživatelských sezmamů kanálů je doporučené v nastavení zapnout volbu Nepřidávat nové kanály do seznamu kanálů přidávání. Mám změnu nastavení provést?", yeslabel = "Ponechat", nolabel = "Změnit")
      if not disable_adding:
        addon.setSetting("disable_channels_adding", "true")    
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
    filename = addon_userdata_dir + "channels.txt"
    filename_data = addon_userdata_dir + "channels_data.txt"

    channels_nums, channels_data, channels_key_mapping = get_channels_data() # pylint: disable=unused-variable

    data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/settings/get-user-pref.json?name=nangu.channelListUserChannelNumbers", data = None, header = o2api.header)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením seznamu kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit() 
    if "listUserChannelNumbers" in data and len(data["listUserChannelNumbers"]) > 0:
      for list_name in data["listUserChannelNumbers"]:
        if list == list_name.encode("utf-8"):
          for channel in data["listUserChannelNumbers"][list.decode("utf-8")]:
            channels.update({int(data["listUserChannelNumbers"][list.decode("utf-8")][channel]) : channel})
          with codecs.open(filename, "w", encoding="utf-8") as file:
            for key in sorted(channels.keys()):
              if channels[key] in channels_key_mapping: 
                line = channels_key_mapping[channels[key]]+";"+str(key)
                file.write('%s\n' % line)

          for channelName in channels_data.copy():
            if not channels_data[channelName]["channelKey"] in channels.values():
              del channels_key_mapping[channels_data[channelName]["channelKey"]]
              del channels_data[channelName]
          with codecs.open(filename_data, "w", encoding="utf-8") as file:
            data = json.dumps({"channels_data" : channels_data, "channels_key_mapping" : channels_key_mapping,"valid_to" : int(time.time()) + 60*60*24})
            file.write('%s\n' % data)

      xbmcgui.Dialog().notification("Sledování O2TV","Seznam kanálů byl načtený", xbmcgui.NOTIFICATION_INFO, 4000)          
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Nanalezen žádný seznam v O2", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  
      
def reset_channel_list():     
    filename = addon_userdata_dir + "channels.txt"
    if os.path.exists(filename):
      os.remove(filename) 
    filename = addon_userdata_dir + "channels_data.txt"
    if os.path.exists(filename):
      os.remove(filename) 
    load_channels()
    xbmcgui.Dialog().notification("Sledování O2TV","Seznam kanálů byl resetovaný", xbmcgui.NOTIFICATION_INFO, 4000) 
    
def list_channels_edit(label):
    xbmcplugin.setPluginCategory(_handle, label)
    if addon.getSetting("disable_channels_adding") == "false":
      disable_adding = xbmcgui.Dialog().yesno("Automatické přidávání kanálů", "Pro úpravy sezmamu kanálů je doporučené v nastavení zapnout volbu Nepřidávat nové kanály do seznamu kanálů přidávání. Mám změnu nastavení provést?", yeslabel = "Ponechat", nolabel = "Změnit")
      if not disable_adding:
        addon.setSetting("disable_channels_adding", "true")
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
    if len(channels_nums) > 0:
      list_item = xbmcgui.ListItem(label="Přidat nový kanál")
      url = get_url(action='list_channels_add', label = "Nový kanál")  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
      for num in sorted(channels_nums.keys()):
        list_item = xbmcgui.ListItem(label=str(num) + " " + channels_nums[num])
        url = get_url(action='edit_channel', channelName = channels_nums[num].encode("utf-8"), channelNum = num)  
        list_item.addContextMenuItems([("Smazat kanál", "RunPlugin(plugin://plugin.video.archivo2tv?action=delete_channel&channelName=" + channels_nums[num].encode("utf-8") + "&channelNum=" + str(num) + ")",)])       
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
      xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)

def get_channels_data():
    channels_logos = {}
    channels_nums = {}
    channels_data = {}
    channels_key_mapping = {}

    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/channels/", data = None, header = o2api.header_unity)                                                               
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  
    if "result" in data and len(data["result"]) > 0:
      for channel in data["result"]:
        if "live" in channel:
          channels_logos.update({channel["channel"]["name"] : "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"]})

    for offer in o2api.offers:
      post = {"locality" : o2api.locality, "tariff" : o2api.tariff, "isp" : o2api.isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = o2api.header)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "channels" in data and len(data["channels"]) > 0:
        for channel in data["channels"]:
          if data["channels"][channel]["channelType"] == "TV":
            if data["channels"][channel]["channelName"] in channels_logos:
              logo = channels_logos[data["channels"][channel]["channelName"]]
            else:
              logo = ""
            channels_data.update({ data["channels"][channel]["channelName"] : {"channelKey" : data["channels"][channel]["channelKey"], "logo" : logo }})
            channels_key_mapping.update({ data["channels"][channel]["channelKey"] : data["channels"][channel]["channelName"]})
            channels_nums.update({int(data["channels"][channel]["channelNumber"]) : data["channels"][channel]["channelName"]})
    return channels_nums, channels_data, channels_key_mapping   

def load_channels():
    filename = addon_userdata_dir + "channels.txt"
    filename_data = addon_userdata_dir + "channels_data.txt"
    max_num = 0
    not_found_1 = 0
    not_found_2 = 0
    channels_nums = {}
    channels_data = {}
    channels_key_mapping = {}

    try:
      with codecs.open(filename, "r", encoding="utf-8") as file:
        for line in file:
          channel = line[:-1].split(";")
          channels_nums.update({ int(channel[1]) : channel[0]})
          max_num = int(channel[1])
    except IOError:
      not_found_1 = 1          

    try:
      with codecs.open(filename_data, "r", encoding="utf-8") as file:
        for line in file:
          item = line[:-1]
          data = json.loads(item)
          channels_data = data["channels_data"]
          channels_key_mapping = data["channels_key_mapping"]
    except IOError:
      not_found_2 = 1

    if not_found_1 == 1 or not_found_2 == 1 or (data and len(data) > 0 and "valid_to" in data and data["valid_to"] < int(time.time()) and addon.getSetting("disable_channels_adding") != "true"):
      channels_nums_o2, channels_data_o2, channels_key_mapping_o2 = get_channels_data() # pylint: disable=unused-variable
      if len(channels_nums_o2) > 0:
        for num_o2 in sorted(channels_nums_o2.keys()):
          if not_found_1 == 0:
             for num in sorted(channels_nums.keys()):
               fnd = 0
               if channels_nums[num] == channels_nums_o2[num_o2]:
                 fnd = 1
                 if not_found_1 == 0 and not_found_2 == 1:
                   channels_data.update({channels_nums[num] : channels_data_o2[channels_nums[num]]}) 
                   channels_key_mapping.update({channels_data_o2[channels_nums[num]]["channelKey"] : channels_nums[num]})               
             if fnd == 0 and addon.getSetting("disable_channels_adding") != "true":
               max_num = max_num + 1
               channels_nums.update({max_num : channels_nums_o2[num_o2]}) 
               channels_data.update({channels_nums_o2[num_o2] : channels_data_o2[channels_nums_o2[num_o2]]}) 
               channels_key_mapping.update({channels_data_o2[channels_nums_o2[num_o2]]["channelKey"] : channels_nums_o2[num_o2]})
          else:        
            channels_nums.update({num_o2 : channels_nums_o2[num_o2]}) 
            channels_data.update({channels_nums_o2[num_o2] : channels_data_o2[channels_nums_o2[num_o2]]})             
            channels_key_mapping.update({channels_data_o2[channels_nums_o2[num_o2]]["channelKey"] : channels_nums_o2[num_o2]})
        try:
          with codecs.open(filename, "w", encoding="utf-8") as file:
            for num in sorted(channels_nums.keys()):
              line = channels_nums[num] + ";" + str(num)
              file.write('%s\n' % line)
        except IOError:
          print("Chyba uložení kanálů")   
        try:
          with codecs.open(filename_data, "w", encoding="utf-8") as file:
            data = json.dumps({"channels_data" : channels_data, "channels_key_mapping" : channels_key_mapping,"valid_to" : int(time.time()) + 60*60*24})
            file.write('%s\n' % data)
        except IOError:
          print("Chyba uložení kanálů")  
        return channels_nums, channels_data, channels_key_mapping      
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
    else:
      return channels_nums, channels_data, channels_key_mapping      

def edit_channel(channelName, channelNum):
    filename = addon_userdata_dir + "channels.txt"
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
    new_num = xbmcgui.Dialog().numeric(0, "Číslo kanálu", str(channelNum))
    if int(new_num) > 0:
      if int(new_num) in channels_nums:
        xbmcgui.Dialog().notification("Sledování O2TV","Číslo kanálu " + new_num + " je už použité u kanálu " + channels_nums[int(new_num)].encode("utf-8"), xbmcgui.NOTIFICATION_ERROR, 5000)
      else:  
        del channels_nums[int(channelNum)]
        channels_nums.update({ int(new_num) : channelName})
        with codecs.open(filename, "w", encoding = "utf-8") as file:
          for num in sorted(channels_nums.keys()):
            line = channels_nums[num]+";"+str(num)
            file.write('%s\n' % line)

def delete_channel(channelName, channelNum):
    channelNum = int(channelNum)
    filename = addon_userdata_dir + "channels.txt"
    filename_data = addon_userdata_dir + "channels_data.txt"
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
 
    if channelNum in channels_nums and channels_nums[channelNum] == channelName.decode("utf-8"):
      del channels_key_mapping[channels_data[channels_nums[channelNum]]["channelKey"]]
      del channels_data[channels_nums[channelNum]]
      del channels_nums[channelNum]
      try:
        with codecs.open(filename, "w", encoding="utf-8") as file:
          for num in sorted(channels_nums.keys()):
            line = channels_nums[num] + ";" + str(num)
            file.write('%s\n' % line)
      except IOError:
        print("Chyba uložení kanálů")   
      try:
        with codecs.open(filename_data, "w", encoding="utf-8") as file:
          data = json.dumps({"channels_data" : channels_data, "channels_key_mapping" : channels_key_mapping,"valid_to" : int(time.time()) + 60*60*24})
          file.write('%s\n' % data)
      except IOError:
        print("Chyba uložení kanálů")       
    xbmc.executebuiltin('Container.Refresh')                

def list_channels_add(label):
    new_channels = []
    xbmcplugin.setPluginCategory(_handle, label)  
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
    channels_nums_all, channels_data_all, channels_key_mapping_all = get_channels_data() # pylint: disable=unused-variable
    for channel in channels_data_all.keys():
      if not channel in channels_data:
        new_channels.append(channel)
    for num in sorted(channels_nums_all.keys()):
      if channels_nums_all[num] in new_channels:
        list_item = xbmcgui.ListItem(label=str(num) + " " + channels_nums_all[num])
        url = get_url(action='add_channel', channelName = channels_nums_all[num].encode("utf-8"), channelNum = num)  
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)

def add_channel(channelName, channelNum):
    channelNum = int(channelNum)
    channelName = channelName.decode("utf-8")
    filename = addon_userdata_dir + "channels.txt"
    filename_data = addon_userdata_dir + "channels_data.txt"
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
    channels_nums_all, channels_data_all, channels_key_mapping_all = get_channels_data() # pylint: disable=unused-variable
    if channels_nums_all[channelNum] == channelName:
      if channelNum in channels_nums:
        while channelNum in channels_nums:
          channelNum = channelNum + 1
      channels_nums.update({channelNum : channelName})
      channels_data.update({channelName : channels_data_all[channelName]})
      channels_key_mapping.update({channels_data[channelName]["channelKey"] : channelName})
      try:
        with codecs.open(filename, "w", encoding="utf-8") as file:
          for num in sorted(channels_nums.keys()):
            line = channels_nums[num] + ";" + str(num)
            file.write('%s\n' % line)
      except IOError:
        print("Chyba uložení kanálů")   
      try:
        with codecs.open(filename_data, "w", encoding="utf-8") as file:
          data = json.dumps({"channels_data" : channels_data, "channels_key_mapping" : channels_key_mapping,"valid_to" : int(time.time()) + 60*60*24})
          file.write('%s\n' % data)
      except IOError:
        print("Chyba uložení kanálů")       
      xbmc.executebuiltin('Container.Refresh')                

