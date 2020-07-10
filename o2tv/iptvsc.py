# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

from urllib import urlencode, quote
from datetime import datetime
import time

from o2tv.o2api import call_o2_api
from o2tv import o2api
from o2tv import utils
from o2tv.stream import play_video
from o2tv.recordings import add_recording
from o2tv.channels import load_channels 

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

def generate_playlist():
    if addon.getSetting("output_dir") is None or len(addon.getSetting("output_dir")) == 0:
      xbmcgui.Dialog().notification("Sledování O2TV","Nastav adresář pro playlist!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit() 
             
    channels_ordered = load_channels()    
    channels = {}
    channel_data = {}
    num = 0
    filename = addon.getSetting("output_dir") + "playlist.m3u"
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
        channel_data.update({channel["channel"]["channelKey"] : "https://www.o2tv.cz/" + channel["channel"]["images"]["color"]["url"]})

    with open(filename, "w") as file:
      file.write('%s\n' % "#EXTM3U")
      for channel in sorted(channels.keys()):  
        if channels[channel]["channelKey"] in channel_data:   
          logo = channel_data[channels[channel]["channelKey"]].encode("utf-8")
        else:
          logo = ""  
        line = "#EXTINF:-1 tvh-epg=\"0\" tvg-logo=\"" + logo + "\"," + channels[channel]["channelName"].encode("utf-8")
        file.write('%s\n' % line)
        line = "plugin://plugin.video.archivo2tv/?action=get_stream_url&channelKey=" + channels[channel]["channelKey"].encode("utf-8")
        file.write('%s\n' % line)
          
    xbmcgui.Dialog().notification("Sledování O2TV","Playlist byl uložený", xbmcgui.NOTIFICATION_INFO, 4000)    

def generate_epg():
    import iptv_sc_epg
    iptv_sc_epg.load_epg()  
    
def iptv_sc_play(channelName, startdatetime, epg):
    print("xxxxxx: " + channelName)
    epgId = -1
    channels_mapping = {}
    if addon.getSetting("remove_hd") == "true":
      channelName = channelName.replace(" HD","").replace("O2 ","")
    if len(startdatetime) > 0:
      from_ts = int(time.mktime(time.strptime(startdatetime, "%d.%m.%Y %H:%M")))
    else:
      from_ts = int(time.mktime(datetime.now().timetuple()))

    if from_ts > int(time.mktime(datetime.now().timetuple())):
        xbmcgui.Dialog().notification("Sledování O2TV","Nelze přehrát budoucí pořad!", xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit()  
    else:
      for offer in o2api.offers:
        post = {"locality" : o2api.locality, "tariff" : o2api.tariff, "isp" : o2api.isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
        data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = o2api.header)                                                               
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()  
        if "channels" in data and len(data["channels"]) > 0:
          for channel in data["channels"]:
            if data["channels"][channel]["channelType"] == "TV":
               if addon.getSetting("remove_hd") == "true":
                 channels_mapping.update({data["channels"][channel]["channelName"].replace(" HD","").encode("utf-8") : data["channels"][channel]["channelKey"].encode("utf-8")})
               else:
                 channels_mapping.update({data["channels"][channel]["channelName"].encode("utf-8") : data["channels"][channel]["channelKey"].encode("utf-8")})

      data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?channelKey=" + quote(channels_mapping[channelName]) + "&from=" + str(from_ts*1000) + "&forceLimit=true&limit=500", data = None, header = o2api.header_unity)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit() 
      if "epg" in data and len(data["epg"]) > 0 and len(data["epg"]["items"]) > 0 and len(data["epg"]["items"][0]["programs"]) > 0:
        for programs in data["epg"]["items"][0]["programs"]:
          if str(programs["start"]) == str(from_ts*1000):
            startts = programs["start"]
            start = datetime.fromtimestamp(programs["start"]/1000)
            endts = programs["end"]
            end = datetime.fromtimestamp(programs["end"]/1000)        
            epgId = programs["epgId"]
            title = utils.day_translation_short[start.strftime("%A")].decode("utf-8") + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + " | " + programs["name"]
      if int(epgId) > 0:
        if int(endts/1000) < int(time.mktime(datetime.now().timetuple())):
          play_video(type = "archiv_iptv", channelKey = channels_mapping[channelName], start = startts, end = endts, epgId = epgId, title = title)
        else:
          if epg == 1:
            play_video(type = "live_iptv_epg", channelKey = channels_mapping[channelName], start = None, end = None, epgId = None, title = None)
          else:
            play_video(type = "live_iptv", channelKey = channels_mapping[channelName], start = None, end = None, epgId = None, title = None)
      else:
        if len(startdatetime) == 0:
          play_video(type = "live_iptv", channelKey = channels_mapping[channelName], start = None, end = None, epgId = None, title = None)
        else:
          xbmcgui.Dialog().notification("Sledování O2TV","Pořad u O2 nenalezen! Používáte EPG z doplňku Sledování O2TV?", xbmcgui.NOTIFICATION_ERROR, 10000)
        sys.exit()  

def iptv_sc_rec(channelName, startdatetime):
    epgId = -1
    channels_mapping = {}

    from_ts = int(time.mktime(time.strptime(startdatetime, "%d.%m.%Y %H:%M")))

    for offer in o2api.offers:
      post = {"locality" : o2api.locality, "tariff" : o2api.tariff, "isp" : o2api.isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post), header = o2api.header)                                                               
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "channels" in data and len(data["channels"]) > 0:
        for channel in data["channels"]:
          if data["channels"][channel]["channelType"] == "TV":
             channels_mapping.update({data["channels"][channel]["channelName"].encode("utf-8") : data["channels"][channel]["channelKey"].encode("utf-8")})

    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?channelKey=" + quote(channels_mapping[channelName]) + "&from=" + str(from_ts*1000) + "&forceLimit=true&limit=500", data = None, header = o2api.header_unity)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit() 
    if "epg" in data and len(data["epg"]) > 0 and len(data["epg"]["items"]) > 0 and len(data["epg"]["items"][0]["programs"]) > 0:
      for programs in data["epg"]["items"][0]["programs"]:
        if str(programs["start"]) == str(from_ts*1000):
          epgId = programs["epgId"]
    if int(epgId) > 0:
      add_recording(epgId)
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Pořad u O2 nenalezen! Používáte EPG z doplňku Sledování O2TV?", xbmcgui.NOTIFICATION_ERROR, 10000)
      sys.exit()  
