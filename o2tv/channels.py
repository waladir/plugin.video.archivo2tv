# -*- coding: utf-8 -*-
import os
import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from urllib import urlencode, quote
except ImportError:
    from urllib.parse import urlencode, quote
    
import json
import time
import codecs

from o2tv.o2api import call_o2_api
from o2tv import o2api
from o2tv.utils import get_url, decode, encode

_url = sys.argv[0]
if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')
addon_userdata_dir = xbmc.translatePath(addon.getAddonInfo('profile')) 

def list_channels_list(label):
    xbmcplugin.setPluginCategory(_handle, label)
    list_item = xbmcgui.ListItem(label="Ruční editace")
    url = get_url(action="list_channels_edit", label = label + " / Ruční editace")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label="Načtení uživatelského seznamu z O2")
    url = get_url(action="get_o2_channels_lists", label = label + " / Načtení z O2")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label="Vlastní skupiny kanálů")
    url = get_url(action="list_channels_groups", label = label + " / Skupiny kanálů")  
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
        url = get_url(action="load_o2_channel_list", list = encode(list))  
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
        if list == encode(list_name):
          for channel in data["listUserChannelNumbers"][decode(list)]:
            channels.update({int(data["listUserChannelNumbers"][decode(list)][channel]) : channel})
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
        url = get_url(action='edit_channel', channelName = encode(channels_nums[num]), channelNum = num)  
        list_item.addContextMenuItems([("Smazat kanál", encode("RunPlugin(plugin://plugin.video.archivo2tv?action=delete_channel&channelName=" + channels_nums[num] + "&channelNum=" + str(num) + ")"),)])       
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

def load_channels(channels_groups_filter = 0):
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
             fnd = 0
             for num in sorted(channels_nums.keys()):
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
          channels_written = []
          with codecs.open(filename, "w", encoding="utf-8") as file:
            for num in sorted(channels_nums.keys()):
              if not channels_nums[num] in channels_written:
                channels_written.append(channels_nums[num])
                line = channels_nums[num] + ";" + str(num)
                file.write('%s\n' % line)
        except IOError:
          xbmc.log("Chyba uložení kanálů")   
        try:
          with codecs.open(filename_data, "w", encoding="utf-8") as file:
            data = json.dumps({"channels_data" : channels_data, "channels_key_mapping" : channels_key_mapping,"valid_to" : int(time.time()) + 60*60*24})
            file.write('%s\n' % data)
        except IOError:
          xbmc.log("Chyba uložení kanálů")  
        for num in sorted(channels_nums.keys()):
          if not channels_nums[num] in channels_data:
            del channels_nums[num] 
        return filter_channels(channels_nums, channels_groups_filter), channels_data, channels_key_mapping      
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
    else:
      for num in sorted(channels_nums.keys()):
        if not channels_nums[num] in channels_data:
          del channels_nums[num]    
      return filter_channels(channels_nums, channels_groups_filter), channels_data, channels_key_mapping      

def edit_channel(channelName, channelNum):
    filename = addon_userdata_dir + "channels.txt"
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
    new_num = xbmcgui.Dialog().numeric(0, "Číslo kanálu", str(channelNum))
    if int(new_num) > 0:
      if int(new_num) in channels_nums:
        xbmcgui.Dialog().notification("Sledování O2TV","Číslo kanálu " + new_num + " je už použité u kanálu " + encode(channels_nums[int(new_num)]), xbmcgui.NOTIFICATION_ERROR, 5000)
      else:  
        channels_nums.update({ int(new_num) : channels_nums[int(channelNum)] })
        del channels_nums[int(channelNum)]
        with codecs.open(filename, "w", encoding = "utf-8") as file:
          for num in sorted(channels_nums.keys()):
            line = channels_nums[num]+";"+str(num)
            file.write('%s\n' % line)

def delete_channel(channelName, channelNum):
    channelNum = int(channelNum)
    filename = addon_userdata_dir + "channels.txt"
    filename_data = addon_userdata_dir + "channels_data.txt"
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
 
    if channelNum in channels_nums and channels_nums[channelNum] == decode(channelName):
      del channels_key_mapping[channels_data[channels_nums[channelNum]]["channelKey"]]
      del channels_data[channels_nums[channelNum]]
      del channels_nums[channelNum]
      try:
        with codecs.open(filename, "w", encoding="utf-8") as file:
          for num in sorted(channels_nums.keys()):
            line = channels_nums[num] + ";" + str(num)
            file.write('%s\n' % line)
      except IOError:
        xbmc.log("Chyba uložení kanálů")   
      try:
        with codecs.open(filename_data, "w", encoding="utf-8") as file:
          data = json.dumps({"channels_data" : channels_data, "channels_key_mapping" : channels_key_mapping,"valid_to" : int(time.time()) + 60*60*24})
          file.write('%s\n' % data)
      except IOError:
        xbmc.log("Chyba uložení kanálů")       
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
        url = get_url(action='add_channel', channelName = encode(channels_nums_all[num]), channelNum = num)  
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)

def add_channel(channelName, channelNum):
    channelNum = int(channelNum)
    channelName = decode(channelName)
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
        xbmc.log("Chyba uložení kanálů")   
      try:
        with codecs.open(filename_data, "w", encoding="utf-8") as file:
          data = json.dumps({"channels_data" : channels_data, "channels_key_mapping" : channels_key_mapping,"valid_to" : int(time.time()) + 60*60*24})
          file.write('%s\n' % data)
      except IOError:
        xbmc.log("Chyba uložení kanálů")       
      xbmc.executebuiltin('Container.Refresh')                

def load_channels_groups():
    filename = addon_userdata_dir + "channels_groups.txt"
    channels_groups = []
    channels_groups_channels = {}
    selected = ""
    try:
      with codecs.open(filename, "r", encoding="utf-8") as file:
        for line in file:
          if line[:-1].find(";") != -1:
            channel_group = line[:-1].split(";")
            if channel_group[0] in channels_groups_channels:
              groups = channels_groups_channels[channel_group[0]]
              groups.append(channel_group[1])
              channels_groups_channels.update({channel_group[0] : groups})
            else:
              channels_groups_channels.update({channel_group[0] : [channel_group[1]]})
          else:
            group = line[:-1]
            if group[0] == "*":
              selected = group[1:]
              channels_groups.append(group[1:])
            else:
              channels_groups.append(group)
    except IOError:
      channels_groups = []
      channels_groups_channels = {}
    return channels_groups, channels_groups_channels, selected

def save_channels_groups(channels_groups, channels_groups_channels, selected):
    filename = addon_userdata_dir + "channels_groups.txt"
    if(len(channels_groups)) > 0:
      try:
        with codecs.open(filename, "w", encoding="utf-8") as file:
          for channel_group in channels_groups:
            if channel_group == selected:
              line = "*" + channel_group
            else:
              line = channel_group
            file.write('%s\n' % line)
          for channel_group in channels_groups:
            if channel_group in channels_groups_channels:
              for channel in channels_groups_channels[channel_group]:
                line = channel_group + ";" + channel
                file.write('%s\n' % line)
      except IOError:
        xbmc.log("Chyba uložení skupiny")   

def list_channels_groups(label):
    xbmcplugin.setPluginCategory(_handle, label)    
    channels_groups, channels_groups_channels, selected = load_channels_groups() # pylint: disable=unused-variable
    list_item = xbmcgui.ListItem(label="Nová skupina")
    url = get_url(action='add_channel_group', label = "Nová skupina")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    if selected == "":
      list_item = xbmcgui.ListItem(label="[B]Všechny kanály[/B]")
    else:  
      list_item = xbmcgui.ListItem(label="Všechny kanály")
    url = get_url(action='list_channels_groups', label = "Seznam kanálů / Skupiny kanálů")  
    list_item.addContextMenuItems([("Vybrat skupinu", "RunPlugin(plugin://plugin.video.archivo2tv?action=select_channel_group&group=all)" ,)])       
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)    
    for channel_group in channels_groups:
      if selected == channel_group:
        list_item = xbmcgui.ListItem(label="[B]" + channel_group + "[/B]")                
      else:
        list_item = xbmcgui.ListItem(label=channel_group)
      url = get_url(action='edit_channel_group', group = encode(channel_group), label = "Skupiny kanálů / " + encode(channel_group)) 
      list_item.addContextMenuItems([("Vybrat skupinu", "RunPlugin(plugin://plugin.video.archivo2tv?action=select_channel_group&group=" + quote(encode(channel_group)) + ")"), 
                                     ("Smazat skupinu", "RunPlugin(plugin://plugin.video.archivo2tv?action=delete_channel_group&group=" + quote(encode(channel_group)) + ")")])       
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)

def add_channel_group(label):
    input = xbmc.Keyboard("", "Název skupiny")
    input.doModal()
    if not input.isConfirmed(): 
      return
    group = input.getText()
    if len(group) == 0:
      xbmcgui.Dialog().notification("Sledování O2TV","Je nutné zadat název skupiny", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()          
    channels_groups, channels_groups_channels, selected = load_channels_groups() # pylint: disable=unused-variable
    if group in channels_groups:
      xbmcgui.Dialog().notification("Sledování O2TV","Název skupiny je už použitý", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()          
    channels_groups.append(decode(group))
    save_channels_groups(channels_groups, channels_groups_channels, selected)

def delete_channel_group(group):
    response = xbmcgui.Dialog().yesno("Smazání skupiny kanálů", "Opravdu smazat skupinu kanálů " + group + "?", nolabel = "Ne", yeslabel = "Ano")
    if response:
      group = decode(group)
      channels_groups, channels_groups_channels, selected = load_channels_groups() # pylint: disable=unused-variable
      channels_groups.remove(group)
      if group in channels_groups_channels:
        del channels_groups_channels[group]
      if selected == group:
        selected = ""
      save_channels_groups(channels_groups, channels_groups_channels, selected)
    xbmc.executebuiltin('Container.Refresh')

def select_channel_group(group):
    group = decode(group)
    channels_groups, channels_groups_channels, selected = load_channels_groups() # pylint: disable=unused-variable
    selected = group
    save_channels_groups(channels_groups, channels_groups_channels, selected)
    xbmc.executebuiltin('Container.Refresh')
    if (not group in channels_groups_channels or len(channels_groups_channels[group]) == 0) and group != "all":
      xbmcgui.Dialog().notification("Sledování O2TV","Vybraná skupina je prázdná", xbmcgui.NOTIFICATION_WARNING, 4000)    

def edit_channel_group(group, label):
    group = decode(group)
    channels_groups, channels_groups_channels, selected = load_channels_groups() # pylint: disable=unused-variable
    xbmcplugin.setPluginCategory(_handle, label)    
   
    list_item = xbmcgui.ListItem(label="Přidat kanál")
    url = get_url(action='edit_channel_group_list_channels', group = encode(group), label = encode(group) + " / Přidat kanál")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    if group in channels_groups_channels:
      for channel in channels_groups_channels[group]:
        list_item = xbmcgui.ListItem(label=channel)
        url = get_url(action='edit_channel_group', group = encode(group), label = label)  
        list_item.addContextMenuItems([("Smazat kanál", "RunPlugin(plugin://plugin.video.archivo2tv?action=edit_channel_group_delete_channel&group=" + quote(encode(group)) + "&channel="  + quote(encode(channel)) + ")",)])       
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)

def edit_channel_group_list_channels(group, label):
    group = decode(group)
    xbmcplugin.setPluginCategory(_handle, label)  
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
    channels_groups, channels_groups_channels, selected = load_channels_groups() # pylint: disable=unused-variable
    
    for num in sorted(channels_nums.keys()):
      if not group in channels_groups or not group in channels_groups_channels or not channels_nums[num] in channels_groups_channels[group]:
        list_item = xbmcgui.ListItem(label=str(num) + " " + channels_nums[num])
        url = get_url(action='edit_channel_group_add_channel', group = encode(group), channel = encode(channels_nums[num]))  
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)

def edit_channel_group_add_channel(group, channel):
    group = decode(group)
    channels = []
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
    channels_groups, channels_groups_channels, selected = load_channels_groups() # pylint: disable=unused-variable
    for num in sorted(channels_nums.keys()):
      if (group in channels_groups_channels and channels_nums[num] in channels_groups_channels[group]) or channels_nums[num] == decode(channel):
         channels.append(channels_nums[num])
    if group in channels_groups_channels:
      del channels_groups_channels[group]
    channels_groups_channels.update({group : channels})
    save_channels_groups(channels_groups, channels_groups_channels, selected)

def edit_channel_group_delete_channel(group, channel):
    group = decode(group)
    channels_groups, channels_groups_channels, selected = load_channels_groups() # pylint: disable=unused-variable
    channels_groups_channels[group].remove(decode(channel))
    save_channels_groups(channels_groups, channels_groups_channels, selected)
    xbmc.executebuiltin('Container.Refresh')

def filter_channels(channels_nums, channels_groups_filter):
    if channels_groups_filter != 1:
      return channels_nums
    channels_groups, channels_groups_channels, selected = load_channels_groups() # pylint: disable=unused-variable
    for num in sorted(channels_nums.keys()):
      if channels_groups_filter == 1 and selected != "" and selected in channels_groups and selected in channels_groups_channels and not channels_nums[num] in channels_groups_channels[selected]:
          del channels_nums[num]    
    return channels_nums
