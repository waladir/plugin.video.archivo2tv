# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

try:
    from urllib import urlencode, quote
except ImportError:
    from urllib.parse import urlencode, quote
    
from datetime import datetime 
import time

from o2tv.o2api import call_o2_api
from o2tv import o2api
from o2tv.utils import plugin_id, get_url, get_color, decode, encode, PY3
from o2tv import utils
from o2tv.channels import load_channels 
from o2tv.epg import get_listitem_epg_details

_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id = plugin_id)
addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 


def openfile(fname, mode):
  return open(fname, mode, encoding = 'utf-8') if PY3 else open(fname, mode)

def test_epg():
  from  o2tv.epg import load_epg_all
  load_epg_all()

def list_search(label):
  #  test_epg():
    xbmcplugin.setPluginCategory(_handle, label)
    list_item = xbmcgui.ListItem(label="Nové hledání")
    url = get_url(action='program_search', query = "-----", label = label + " / " + "Nové hledání")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    history = load_search_history()
    for item in history:
      list_item = xbmcgui.ListItem(label=item)
      url = get_url(action='program_search', query = item, label = label + " / " + item)  
      list_item.addContextMenuItems([("Smazat", "RunPlugin(plugin://" + plugin_id + "?action=delete_search&query=" + quote(item) + ")")])
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)

def program_search(query, label):
    xbmcplugin.setPluginCategory(_handle, label)
    if query == "-----":
      input = xbmc.Keyboard("", "Hledat")
      input.doModal()
      if not input.isConfirmed(): 
        return
      query = input.getText()
      if len(query) == 0:
        xbmcgui.Dialog().notification("Sledování O2TV","Je potřeba zadat vyhledávaný řetězec", xbmcgui.NOTIFICATION_ERROR, 4000)
        return   
      else:
        save_search_history(query)
        
    max_ts = int(time.mktime(datetime.now().timetuple()))
    data = call_o2_api(url = "https://api.o2tv.cz/unity/api/v1/search/tv/depr/?groupLimit=1&maxEnd=" + str(max_ts*1000) + "&q=" + quote(query), data = None, header = o2api.header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém při hledání", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  
    
    if "groupedSearch" in data and "groups" in data["groupedSearch"] and len(data["groupedSearch"]["groups"]) > 0:
      channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter=1) # pylint: disable=unused-variable 

      for item in data["groupedSearch"]["groups"]:
        programs = item["programs"][0]
        if programs["channelKey"] in channels_key_mapping:
          startts = programs["start"]/1000
          start = datetime.fromtimestamp(programs["start"]/1000)
          endts = programs["end"]/1000
          end = datetime.fromtimestamp(programs["end"]/1000)
          epgId = programs["epgId"]
          list_item = xbmcgui.ListItem(label = programs["name"] + " (" + programs["channelKey"] + " | " + decode(utils.day_translation_short[start.strftime("%w")]) + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + ")")
          list_item = get_listitem_epg_details(list_item, str(epgId), channels_data[channels_key_mapping[programs["channelKey"]]]["logo"])
          list_item.setProperty("IsPlayable", "true")
          list_item.setContentLookup(False)          
          url = get_url(action='play_archiv', channelKey = encode(programs["channelKey"]), start = startts, end = endts, epgId = epgId)
          menus = [("Přidat nahrávku", "RunPlugin(plugin://" + plugin_id + "?action=add_recording&epgId=" + str(epgId) + ")"), 
                ("Související pořady", "Container.Update(plugin://" + plugin_id + "?action=list_related&epgId=" + str(epgId) + "&label=Související / " + encode(programs["name"]) + ")"), 
                ("Vysílání pořadu", "Container.Update(plugin://" + plugin_id + "?action=list_same&epgId=" + str(epgId) + "&label=" + encode(programs["name"]) + ")")]
          if addon.getSetting("download_streams") == "true": 
            menus.append(("Stáhnout", "RunPlugin(plugin://" + plugin_id + "?action=add_to_queue&epgId=" + str(epgId) + ")"))
          list_item.addContextMenuItems(menus)       
          xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
      xbmcplugin.endOfDirectory(_handle)
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Nic nenalezeno", xbmcgui.NOTIFICATION_INFO, 3000)

def save_search_history(query):
    max_history = int(addon.getSetting("search_history"))
    cnt = 0
    history = []
    filename = addon_userdata_dir + "search_history.txt"
    
    try:
      with openfile(filename, "r") as file:
        for line in file:
          item = line[:-1]
          history.append(item)
    except IOError:
      history = []
      
    history.insert(0,query)

    with openfile(filename, "w") as file:
      for item  in history:
        cnt = cnt + 1
        if cnt <= max_history:
            file.write('%s\n' % item)

def load_search_history():
    history = []
    filename = addon_userdata_dir + "search_history.txt"
    try:
      with openfile(filename, "r") as file:
        for line in file:
          item = line[:-1]
          history.append(item)
    except IOError:
      history = []
    return history


def delete_search(query):
    filename = addon_userdata_dir + "search_history.txt"
    history = load_search_history()
    for item in history:
        if item == query:
            history.remove(item)
    try:
        with openfile(filename, "w") as file:
            for item in history:
                file.write('%s\n' % item)
    except IOError:
        pass
    xbmc.executebuiltin('Container.Refresh')

