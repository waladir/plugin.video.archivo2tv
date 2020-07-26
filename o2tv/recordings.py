# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

from urllib import urlencode, quote
from datetime import date, datetime, timedelta
import time
import random

from o2tv.o2api import call_o2_api
from o2tv import o2api

from o2tv.channels import load_channels 
from o2tv.utils import get_url
from o2tv import utils

_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

def list_planning_recordings(label):
    xbmcplugin.setPluginCategory(_handle, label)

    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable 
    
    for num in sorted(channels_nums.keys()):  
      list_item = xbmcgui.ListItem(label=channels_nums[num])
      if addon.getSetting("details") == "true" and channels_data[channels_nums[num]] and len(channels_data[channels_nums[num]]["logo"]) > 0:
        list_item.setArt({'thumb': channels_data[channels_nums[num]]["logo"], 'icon': channels_data[channels_nums[num]]["logo"]})
      url = get_url(action='list_rec_days', channelKey = channels_data[channels_nums[num]]["channelKey"].encode("utf-8"), label = label + " / " + channels_nums[num].encode("utf-8"))  
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
        den = utils.day_translation[day.strftime("%w")].decode("utf-8") + " " + day.strftime("%d.%m.%Y")
      list_item = xbmcgui.ListItem(label=den)
      url = get_url(action='future_program', channelKey = channelKey, day = i, label = label + " / " + den_label)  
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def future_program(channelKey, day, label):
    label = label.replace("Nahrávky / Plánování /","")
    xbmcplugin.setPluginCategory(_handle, label)
    if int(day) == 0:
      from_datetime = datetime.now()
      to_datetime = datetime.combine(date.today(), datetime.max.time())
    else:
      from_datetime = datetime.combine(date.today(), datetime.min.time()) + timedelta(days = int(day))
      to_datetime = datetime.combine(from_datetime, datetime.max.time())
    from_ts = int(time.mktime(from_datetime.timetuple()))
    to_ts = int(time.mktime(to_datetime.timetuple()))

    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?channelKey=" + quote(channelKey) + "&from=" + str(from_ts*1000) + "&to=" + str(to_ts*1000) + "&forceLimit=true&limit=500", data = None, header = o2api.header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením programu", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()  

    if "epg" in data and len(data["epg"]) > 0 and len(data["epg"]["items"]) > 0 and len(data["epg"]["items"][0]["programs"]) > 0:
      for programs in data["epg"]["items"][0]["programs"]:
        start = datetime.fromtimestamp(programs["start"]/1000)
        end = datetime.fromtimestamp(programs["end"]/1000)
        epgId = programs["epgId"]

        list_item = xbmcgui.ListItem(label= utils.day_translation_short[start.strftime("%w")].decode("utf-8") + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + " | " + programs["name"])

        if addon.getSetting("details") == "true":  
          list_item = o2api.get_epg_details(list_item, str(epgId), "")
        else:
          list_item.setInfo("video", {"mediatype":"video", "title":programs["name"]})
        list_item.setProperty("IsPlayable", "false")
        list_item.addContextMenuItems([("Přidat nahrávku", "RunPlugin(plugin://plugin.video.archivo2tv?action=add_recording&epgId=" + str(epgId) + ")",)])       
        url = get_url(action='add_recording', channelKey = channelKey, epgId = epgId)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením programu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()    
    
    xbmcplugin.endOfDirectory(_handle)

def list_recordings(label):
    xbmcplugin.setPluginCategory(_handle, label)
    recordings = {}

    list_item = xbmcgui.ListItem(label="Plánování nahrávek")
    url = get_url(action='list_planning_recordings', label = label + " / " + "Plánování")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label="Naplánované nahrávky")
    url = get_url(action='list_future_recordings', label = label + " / " + "Naplánované nahrávky")  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/recordings/", data = None, header = o2api.header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","1Problém s načtením nahrávek, zkuste to znovu", xbmcgui.NOTIFICATION_ERROR, 6000)
    if "result" in data and len(data["result"]) > 0:
      for program in data["result"]:
        if program["state"] == "DONE":
          pvrProgramId = program["pvrProgramId"]
          if "ratings" in program["program"] and len(program["program"]["ratings"]) > 0:
            ratings = program["program"]["ratings"]
          else:
            ratings = {}
          if "longDescription" in program["program"] and len(program["program"]["longDescription"]) > 0:
            plot = program["program"]["longDescription"]
          else:
            plot = ""
          if "images" in program["program"] and len(program["program"]["images"]) > 0 and "cover" in program["program"]["images"][0]:
            img = program["program"]["images"][0]["cover"]
          else:
            img = ""
          recordings.update({program["program"]["start"]+random.randint(0,100) : {"pvrProgramId" : pvrProgramId, "name" : program["program"]["name"], "channelKey" : program["program"]["channelKey"], "start" : utils.day_translation_short[datetime.fromtimestamp(program["program"]["start"]/1000).strftime("%w")].decode("utf-8") + " " + datetime.fromtimestamp(program["program"]["start"]/1000).strftime("%d.%m %H:%M"), "end" : datetime.fromtimestamp(program["program"]["end"]/1000).strftime("%H:%M"), "plot" : plot, "img" : img, "ratings" : ratings}}) 

      for recording in sorted(recordings.keys(), reverse = True):
        list_item = xbmcgui.ListItem(label = recordings[recording]["name"] + " (" + recordings[recording]["channelKey"] + " | " + recordings[recording]["start"] + " - " + recordings[recording]["end"] + ")")
        list_item.setProperty("IsPlayable", "true")
        if addon.getSetting("details") == "true":  
          list_item.setArt({'thumb': "https://www.o2tv.cz/" + recordings[recording]["img"], 'icon': "https://www.o2tv.cz/" + recordings[recording]["img"]})
          list_item.setInfo("video", {"mediatype":"movie", "title":recordings[recording]["name"], "plot":recordings[recording]["plot"]})
          for rating, rating_value in recordings[recording]["ratings"].items():
            list_item.setRating(rating, rating_value/10)
        else:
          list_item.setInfo("video", {"mediatype":"movie", "title":recordings[recording]["name"]})
        list_item.setContentLookup(False)   
        list_item.addContextMenuItems([("Smazat nahrávku", "RunPlugin(plugin://plugin.video.archivo2tv?action=delete_recording&pvrProgramId=" + str(recordings[recording]["pvrProgramId"]) + ")",)])       
        url = get_url(action='play_recording', pvrProgramId = recordings[recording]["pvrProgramId"], title = recordings[recording]["name"].encode("utf-8"))
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
      xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)
    else:
       if "err" not in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Nenalezena žádná nahrávka", xbmcgui.NOTIFICATION_INFO, 4000)
        sys.exit() 

def list_future_recordings(label):
    xbmcplugin.setPluginCategory(_handle, label)
    recordings = {}
    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/recordings/", data = None, header = o2api.header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením nahrávek", xbmcgui.NOTIFICATION_ERROR, 4000)
    
    if "result" in data and len(data["result"]) > 0:
      for program in data["result"]:
        if program["state"] != "DONE":
          pvrProgramId = program["pvrProgramId"]
          if "ratings" in program["program"] and len(program["program"]["ratings"]) > 0:
            ratings = program["program"]["ratings"]
          else:
            ratings = {}
          if "longDescription" in program["program"] and len(program["program"]["longDescription"]) > 0:
            plot = program["program"]["longDescription"]
          else:
            plot = ""
          if "images" in program["program"] and len(program["program"]["images"]) > 0 and "cover" in program["program"]["images"][0]:
            img = program["program"]["images"][0]["cover"]
          else:
            img = ""
          recordings.update({program["program"]["start"]+random.randint(0,100) : {"pvrProgramId" : pvrProgramId, "name" : program["program"]["name"], "channelKey" : program["program"]["channelKey"], "start" : utils.day_translation_short[datetime.fromtimestamp(program["program"]["start"]/1000).strftime("%w")].decode("utf-8") + " " + datetime.fromtimestamp(program["program"]["start"]/1000).strftime("%d.%m %H:%M"), "end" : datetime.fromtimestamp(program["program"]["end"]/1000).strftime("%H:%M"), "plot" : plot, "img" : img, "ratings" : ratings}}) 

      for recording in sorted(recordings.keys(), reverse = True):
        list_item = xbmcgui.ListItem(label = recordings[recording]["name"] + " (" + recordings[recording]["channelKey"] + " | " + recordings[recording]["start"] + " - " + recordings[recording]["end"] + ")")
        list_item.setProperty("IsPlayable", "true")
        if addon.getSetting("details") == "true":  
          list_item.setArt({'thumb': "https://www.o2tv.cz/" + recordings[recording]["img"], 'icon': "https://www.o2tv.cz/" + recordings[recording]["img"]})
          list_item.setInfo("video", {"mediatype":"movie", "title":recordings[recording]["name"], "plot":recordings[recording]["plot"]})
          for rating, rating_value in recordings[recording]["ratings"].items():
            list_item.setRating(rating, rating_value/10)
        else:
          list_item.setInfo("video", {"mediatype":"movie", "title":recordings[recording]["name"]})
        list_item.addContextMenuItems([("Smazat nahrávku", "RunPlugin(plugin://plugin.video.archivo2tv?action=delete_recording&pvrProgramId=" + str(recordings[recording]["pvrProgramId"]) + ")",)])       
        url = get_url(action='list_future_recordings')  
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
      xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)
    else:
        xbmcgui.Dialog().notification("Sledování O2TV","Nenalezena žádná nahrávka", xbmcgui.NOTIFICATION_INFO, 4000)
        sys.exit() 

def delete_recording(pvrProgramId):
    post = {"pvrProgramId" : int(pvrProgramId)}
    data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/vod/pvr-remove-program.json", data = urlencode(post), header = o2api.header)
    if data <> None and "err" in data:
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
