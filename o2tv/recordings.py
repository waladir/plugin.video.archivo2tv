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
import random

from o2tv.o2api import call_o2_api
from o2tv import o2api

from o2tv.channels import load_channels 
from o2tv.utils import plugin_id, get_url, decode, encode
from o2tv import utils
from o2tv.epg import get_listitem_epg_details, get_epg_ts

_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id = plugin_id)

def list_planning_recordings(label):
    xbmcplugin.setPluginCategory(_handle, label)

    channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter=1) # pylint: disable=unused-variable 
    
    for num in sorted(channels_nums.keys()):  
      list_item = xbmcgui.ListItem(label=channels_nums[num])
      if channels_data[channels_nums[num]] and len(channels_data[channels_nums[num]]["logo"]) > 0:
        list_item.setArt({'thumb': channels_data[channels_nums[num]]["logo"], 'icon': channels_data[channels_nums[num]]["logo"]})
      url = get_url(action='list_rec_days', channelKey = encode(channels_data[channels_nums[num]]["channelKey"]), label = label + " / " + encode(channels_nums[num]))  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)
    
def list_rec_days(channelKey, label):
    xbmcplugin.setPluginCategory(_handle, label)
    for i in range (10):
      day = date.today() + timedelta(days = i)
      if i == 0:
        den_label = "Dnes"
        den = "Dnes"
      elif i == 1:
        den_label = "Zítra"
        den = "Zítra"
      else:
        den_label = utils.day_translation_short[day.strftime("%w")] + " " + day.strftime("%d.%m")
        den = decode(utils.day_translation[day.strftime("%w")]) + " " + day.strftime("%d.%m.%Y")
      list_item = xbmcgui.ListItem(label=den)
      url = get_url(action='future_program', channelKey = channelKey, day = i, label = label + " / " + den_label)  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def future_program(channelKey, day, label):
    label = label.replace("Nahrávky / Plánování /","")
    xbmcplugin.setPluginCategory(_handle, label)
    channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter = 1) # pylint: disable=unused-variable 
    if int(day) == 0:
      from_datetime = datetime.now()
      to_datetime = datetime.combine(date.today(), datetime.max.time())
    else:
      from_datetime = datetime.combine(date.today(), datetime.min.time()) + timedelta(days = int(day))
      to_datetime = datetime.combine(from_datetime, datetime.max.time())
    from_ts = int(time.mktime(from_datetime.timetuple()))
    to_ts = int(time.mktime(to_datetime.timetuple()))

    events = get_epg_ts(decode(channelKey), from_ts, to_ts, 5)
    for key in sorted(events.keys()):
      epgId = events[key]["epgId"]
      start = events[key]["start"]
      end = events[key]["end"]
      list_item = xbmcgui.ListItem(label= decode(utils.day_translation_short[start.strftime("%w")]) + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + " | " + events[key]["title"])
      list_item = get_listitem_epg_details(list_item, str(epgId), channels_data[channels_key_mapping[decode(channelKey)]]["logo"])
      list_item.setProperty("IsPlayable", "false")
      list_item.addContextMenuItems([("Přidat nahrávku", "RunPlugin(plugin://" + plugin_id + "?action=add_recording&epgId=" + str(epgId) + ")",)])       
      url = get_url(action='add_recording', channelKey = channelKey, epgId = epgId)
      xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    xbmcplugin.endOfDirectory(_handle)

def list_recordings(label):
    xbmcplugin.setPluginCategory(_handle, label)
    channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter = 1) # pylint: disable=unused-variable 
    recordings = {}

    list_item = xbmcgui.ListItem(label="Plánování nahrávek")
    url = get_url(action='list_planning_recordings', label = label + " / " + "Plánování")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label="Naplánované nahrávky")
    url = get_url(action='list_future_recordings', label = label + " / " + "Naplánované nahrávky")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/recordings/", data = None, header = o2api.header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením nahrávek, zkuste to znovu", xbmcgui.NOTIFICATION_ERROR, 6000)
    if "result" in data and len(data["result"]) > 0:
      for program in data["result"]:
        if program["state"] == "DONE":
          recordings.update({program["program"]["start"]+random.randint(0,100) : {"pvrProgramId" : program["pvrProgramId"], "name" : program["program"]["name"], "channelKey" : program["program"]["channelKey"], "start" : decode(utils.day_translation_short[datetime.fromtimestamp(program["program"]["start"]/1000).strftime("%w")]) + " " + datetime.fromtimestamp(program["program"]["start"]/1000).strftime("%d.%m %H:%M"), "end" : datetime.fromtimestamp(program["program"]["end"]/1000).strftime("%H:%M"), "epgId" : program["program"]["epgId"]}}) 

      for recording in sorted(recordings.keys(), reverse = True):
        list_item = xbmcgui.ListItem(label = recordings[recording]["name"] + " (" + recordings[recording]["channelKey"] + " | " + recordings[recording]["start"] + " - " + recordings[recording]["end"] + ")")
        list_item.setProperty("IsPlayable", "true")
        list_item = get_listitem_epg_details(list_item, recordings[recording]["epgId"], channels_data[channels_key_mapping[recordings[recording]["channelKey"]]]["logo"])
        list_item.setContentLookup(False) 
        menus = [("Smazat nahrávku", "RunPlugin(plugin://" + plugin_id + "?action=delete_recording&pvrProgramId=" + str(recordings[recording]["pvrProgramId"]) + ")")]
        if addon.getSetting("download_streams") == "true": 
          menus.append(("Stáhnout", "RunPlugin(plugin://" + plugin_id + "?action=add_to_queue&epgId=" + str(recordings[recording]["epgId"]) + "&pvrProgramId=" + str(recordings[recording]["pvrProgramId"]) + ")"))      
        list_item.addContextMenuItems(menus)         
        url = get_url(action='play_recording', pvrProgramId = recordings[recording]["pvrProgramId"], title = encode(recordings[recording]["name"]))
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)

def list_future_recordings(label):
    xbmcplugin.setPluginCategory(_handle, label)
    channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter = 1) # pylint: disable=unused-variable 
    recordings = {}
    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/recordings/", data = None, header = o2api.header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením nahrávek", xbmcgui.NOTIFICATION_ERROR, 4000)
    
    if "result" in data and len(data["result"]) > 0:
      for program in data["result"]:
        if program["state"] != "DONE":
          recordings.update({program["program"]["start"]+random.randint(0,100) : {"pvrProgramId" : program["pvrProgramId"], "name" : program["program"]["name"], "channelKey" : program["program"]["channelKey"], "start" : decode(utils.day_translation_short[datetime.fromtimestamp(program["program"]["start"]/1000).strftime("%w")]) + " " + datetime.fromtimestamp(program["program"]["start"]/1000).strftime("%d.%m %H:%M"), "end" : datetime.fromtimestamp(program["program"]["end"]/1000).strftime("%H:%M"), "epgId" : program["program"]["epgId"]}}) 

      for recording in sorted(recordings.keys(), reverse = True):
        list_item = xbmcgui.ListItem(label = recordings[recording]["name"] + " (" + recordings[recording]["channelKey"] + " | " + recordings[recording]["start"] + " - " + recordings[recording]["end"] + ")")
        list_item.setProperty("IsPlayable", "true")
        list_item = get_listitem_epg_details(list_item, recordings[recording]["epgId"], channels_data[channels_key_mapping[recordings[recording]["channelKey"]]]["logo"])
        list_item.addContextMenuItems([("Smazat nahrávku", "RunPlugin(plugin://" + plugin_id + "?action=delete_recording&pvrProgramId=" + str(recordings[recording]["pvrProgramId"]) + ")",)])       
        url = get_url(action='list_future_recordings')  
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
      xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)
    else:
        xbmcgui.Dialog().notification("Sledování O2TV","Nenalezena žádná nahrávka", xbmcgui.NOTIFICATION_INFO, 4000)
        sys.exit() 

def delete_recording(pvrProgramId):
    post = {"pvrProgramId" : int(pvrProgramId)}
    data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/vod/pvr-remove-program.json", data = urlencode(post), header = o2api.header)
    if data != None and "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s odstraněním nahrávky", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit() 
    else:  
      xbmcgui.Dialog().notification("Sledování O2TV","Nahrávka odstraněna", xbmcgui.NOTIFICATION_INFO, 4000)
    xbmc.executebuiltin('Container.Refresh')

def add_recording(epgId):
    post = {"epgId" : int(epgId)}
    data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/vod/pvr-add-program.json", data = urlencode(post), header = o2api.header)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s přidáním nahrávky", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit() 
    xbmcgui.Dialog().notification("Sledování O2TV","Nahrávka přidána", xbmcgui.NOTIFICATION_INFO, 4000)
