# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
import subprocess

try:
    from urllib import urlencode, quote
    from urllib2 import urlopen, Request
except ImportError:
    from urllib.parse import urlencode, quote
    from urllib.request import urlopen, Request

from datetime import datetime 
import time

from o2tv.o2api import call_o2_api
from o2tv import o2api
from o2tv.epg import get_listitem_epg_details, get_epg_live, get_epg_details
from o2tv.channels import load_channels 
from o2tv.utils import remove_diacritics
from o2tv.downloader import add_to_queue

_url = sys.argv[0]
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

def play_video(type, channelKey, start, end, epgId, title):
    if addon.getSetting("select_resolution") == "true" and addon.getSetting("stream_type") == "HLS" and addon.getSetting("only_sd") != "true":
      resolution = xbmcgui.Dialog().select('Rozlišení', ['HD', 'SD' ], preselect = 0)
    else:
      resolution = -1  

    if addon.getSetting("stream_type") == "MPEG-DASH":
      stream_type = "DASH"
    else:
      stream_type = "HLS"

    if type == "live" or type == "live_iptv" or type == "live_iptv_epg":
      startts = 0
      channels_nums, channels_data, channels_key_mapping = load_channels(channels_groups_filter = 0) # pylint: disable=unused-variable 
      channels_details = get_epg_live(len(channels_nums.keys()))      
      if channelKey.decode("utf-8") in channels_key_mapping:
        data = channels_details[channels_key_mapping[channelKey.decode("utf-8")]]
        start = data["start"]
        startts = int(time.mktime(start.timetuple()))
        end = data["end"]
        epgId = str(data["epgId"])

    if addon.getSetting("stream_type") == "MPEG-DASH-web":
      if type == "archiv" or type == "archiv_iptv":
        data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/programs/" + str(epgId) +"/playlist/", data = None, header = o2api.header_unity)
      if type == "live" or type == "live_iptv" or type == "live_iptv_epg":
        data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/channels/playlist/?channelKey=" + quote(channelKey), data = None, header = o2api.header_unity)
      if type == "recording":
        data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/recordings/" + str(epgId) +"/playlist/", data = None, header = o2api.header_unity)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s přehráním streamu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      if "playlist" in data and len(data["playlist"]) > 0 and "streamUrls" in data["playlist"][0] and "main" in data["playlist"][0]["streamUrls"] and len(data["playlist"][0]["streamUrls"]["main"]) > 0:
        if "timeshift" in data["playlist"][0]["streamUrls"]:
          url = data["playlist"][0]["streamUrls"]["timeshift"]
        else:
          url = data["playlist"][0]["streamUrls"]["main"]
        request = Request(url = url , data = None, headers = o2api.header)
        response = urlopen(request)
        url = response.geturl()
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s přehráním streamu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
    else:
      if type == "archiv" or type == "archiv_iptv":
        start = int(start) * 1000
        end = int(end) * 1000
        post = {"serviceType" : "TIMESHIFT_TV", "deviceType" : addon.getSetting("devicetype"), "streamingProtocol" : stream_type,  "subscriptionCode" : o2api.subscription, "channelKey" : channelKey, "fromTimestamp" : str(start), "toTimestamp" : str(end + (int(addon.getSetting("offset"))*60*1000)), "id" : epgId, "encryptionType" : "NONE"}
      if type == "live" or type == "live_iptv" or type == "live_iptv_epg":
         if addon.getSetting("stream_type") == "MPEG-DASH"  and startts > 0 and addon.getSetting("startover") == "true":
           startts = int(startts) * 1000 - 300000
           post = {"serviceType" : "STARTOVER_TV", "deviceType" : addon.getSetting("devicetype"), "streamingProtocol" : stream_type, "subscriptionCode" : o2api.subscription, "channelKey" : channelKey, "fromTimestamp" : startts, "encryptionType" : "NONE"}
         else:
           post = {"serviceType" : "LIVE_TV", "deviceType" : addon.getSetting("devicetype"), "streamingProtocol" : stream_type, "subscriptionCode" : o2api.subscription, "channelKey" : channelKey, "encryptionType" : "NONE"}
      if type == "recording":
        post = {"serviceType" : "NPVR", "deviceType" : addon.getSetting("devicetype"), "streamingProtocol" : stream_type, "subscriptionCode" : o2api.subscription, "contentId" : epgId, "encryptionType" : "NONE"}
      if addon.getSetting("stream_type") != "MPEG-DASH" and (addon.getSetting("only_sd") == "true" or resolution == 1):
        post.update({"resolution" : "SD"})
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/streaming/uris.json", data = urlencode(post), header = o2api.header)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s přehráním streamu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
      url = ""
      if "uris" in data and len(data["uris"]) > 0 and "uri" in data["uris"][0] and len(data["uris"][0]["uri"]) > 0 :
        for uris in data["uris"]:
          if addon.getSetting("only_sd") != "true" and resolution != 1 and uris["resolution"] == "HD":
            url = uris["uri"]
          if (addon.getSetting("only_sd") == "true" or resolution == 1) and uris["resolution"] == "SD": 
            url = uris["uri"]
        if url == "":
          url = data["uris"][0]["uri"]
        if addon.getSetting("stream_type") == "MPEG-DASH":
          request = Request(url = url , data = None, headers = o2api.header)
          response = urlopen(request)
          url = response.geturl()
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s přehráním streamu", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()
                                                    
    if type == "live_iptv" or type == "live_iptv_epg":
      list_item = xbmcgui.ListItem(path = url)
      list_item = get_listitem_epg_details(list_item, epgId, "")
    elif type == "archiv_iptv":
      list_item = xbmcgui.ListItem(title)
      list_item = get_listitem_epg_details(list_item, str(epgId), "")
    else:
      list_item = xbmcgui.ListItem(path = url)

    if addon.getSetting("stream_type") == "MPEG-DASH" or addon.getSetting("stream_type") == "MPEG-DASH-web":
      list_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
      list_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
      list_item.setMimeType('application/dash+xml')

    if type == "archiv_iptv" or (type == "live_iptv" and addon.getSetting("stream_type") != "HLS" and addon.getSetting("startover") == "true") or type == "live_iptv_epg":
      playlist=xbmc.PlayList(1)
      playlist.clear()
      xbmc.PlayList(1).add(url, list_item)
      xbmc.Player().play(playlist)
    else:
      list_item.setContentLookup(False)       
      xbmcplugin.setResolvedUrl(_handle, True, list_item)

 
