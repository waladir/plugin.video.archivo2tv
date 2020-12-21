# -*- coding: utf-8 -*-

import sys
import threading
import json
import codecs
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
import xbmcvfs

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

try:
    from urllib2 import urlopen, Request, HTTPError
    from urllib import urlencode, quote
except ImportError:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
    from urllib.parse import urlencode, quote

from datetime import date, datetime, timedelta
import time
import string, random 

from o2tv.o2api import login
from o2tv import o2api
from o2tv.channels import load_channels 
from o2tv.utils import check_settings
from o2tv.epg import load_epg_all, get_epg_all, load_epg_details_inc, open_db, close_db

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')
addon_userdata_dir = translatePath( addon.getAddonInfo('profile') ) 

header_unity = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type":"application/json"}
header = {"X-NanguTv-App-Version" : "Android#6.4.1", "User-Agent" : "Dalvik/2.1.0", "Accept-Encoding" : "gzip", "Connection" : "Keep-Alive", "Content-Type" : "application/x-www-form-urlencoded;charset=UTF-8", "X-NanguTv-Device-Id" : addon.getSetting("deviceid"), "X-NanguTv-Device-Name" : addon.getSetting("devicename")}
tz_offset = int((time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple()))/3600)

class DownloaderThreadClass(threading.Thread):
    def run(self):
      downloader.read_queue()

def save_file_test():
    try:
      content = ""
      test_file = addon.getSetting("output_dir") + "test.fil"
      file = xbmcvfs.File(test_file, "w")
      file.write(bytearray(("test").encode('utf-8')))
      file.close()
      file = xbmcvfs.File(test_file, "r")
      content = file.read()
      if len(content) > 0 and content == "test":
        file.close()
        xbmcvfs.delete(test_file)
        return 1  
      file.close()
      xbmcvfs.delete(test_file)
      return 0
    except Exception:
      file.close()
      xbmcvfs.delete(test_file)
      return 0 

def load_epg_db():
    check_settings() 
    login()

    events_data = {}
    events_detailed_data = {}
    events_data, events_detailed_data = get_epg_all()

    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
   
    if len(channels_data) > 0:
      if save_file_test() == 0:
        xbmcgui.Dialog().notification("Sledování O2TV","Chyba při uložení EPG", xbmcgui.NOTIFICATION_ERROR, 4000)
        return

      try:
        file = xbmcvfs.File(addon.getSetting("output_dir") + "o2_epg.xml", "w")
        if file == None:
          xbmcgui.Dialog().notification("Sledování O2TV","Chyba při uložení EPG", xbmcgui.NOTIFICATION_ERROR, 4000)
        else:
          file.write(bytearray(('<?xml version="1.0" encoding="UTF-8"?>\n').encode('utf-8')))
          file.write(bytearray(('<tv generator-info-name="EPG grabber">\n').encode('utf-8')))
          content = ""
          for num in sorted(channels_nums.keys()):
            channel = channels_nums[num]
            if channel in channels_data:
              content = content + '    <channel id="' + channel.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '">\n'
              content = content + '            <display-name lang="cs">' + channel.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</display-name>\n'
              content = content + '            <icon src="' + channels_data[channel]['logo'] + '" />\n'
              content = content + '    </channel>\n'
          file.write(bytearray((content).encode('utf-8')))
          for num in sorted(channels_nums.keys()):
            channel = channels_nums[num]
            cnt = 0
            content = ""
            if channel in events_data:
              for event in sorted(events_data[channel].keys()):
                starttime = datetime.fromtimestamp(events_data[channel][event]["startTime"]).strftime("%Y%m%d%H%M%S")
                endtime = datetime.fromtimestamp(events_data[channel][event]["endTime"]).strftime("%Y%m%d%H%M%S")
                content = content + '    <programme start="' + starttime + ' +0' + str(tz_offset) + '00" stop="' + endtime + ' +0' + str(tz_offset) + '00" channel="' + events_data[channel][event]["channel"] + '">\n'
                content = content + '       <title lang="cs">' + events_data[channel][event]["title"].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</title>\n'
                if events_data[channel][event]["epgId"] in events_detailed_data:
                  content = content + '       <desc lang="cs">' + events_detailed_data[events_data[channel][event]["epgId"]]["desc"].replace("&","&amp;").replace("<","&lt;").replace("<","&gt;") + '</desc>\n'
                  if events_detailed_data[events_data[channel][event]["epgId"]]["episodeName"] != None and len(events_detailed_data[events_data[channel][event]["epgId"]]["episodeName"]) > 0:
                    content = content + '       <sub-title lang="cs">' + events_detailed_data[events_data[channel][event]["epgId"]]["episodeName"].replace("&","&amp;").replace("<","&lt;").replace("<","&gt;") + '</sub-title>\n'
                  if events_detailed_data[events_data[channel][event]["epgId"]]["episodeNumber"] != None and events_detailed_data[events_data[channel][event]["epgId"]]["seasonNumber"] != None and events_detailed_data[events_data[channel][event]["epgId"]]["episodeNumber"] > 0 and events_detailed_data[events_data[channel][event]["epgId"]]["seasonNumber"] > 0:
                    if events_detailed_data[events_data[channel][event]["epgId"]]["episodesInSeason"] != None and events_detailed_data[events_data[channel][event]["epgId"]]["episodesInSeason"] > 0:
                      content = content + '       <episode-num system="xmltv_ns">' + str(events_detailed_data[events_data[channel][event]["epgId"]]["seasonNumber"]-1) + "." + str(events_detailed_data[events_data[channel][event]["epgId"]]["episodeNumber"]-1) + "/" + str(events_detailed_data[events_data[channel][event]["epgId"]]["episodesInSeason"]) + '.0/0"</episode-num>\n'
                    else:
                      content = content + '       <episode-num system="xmltv_ns">' + str(events_detailed_data[events_data[channel][event]["epgId"]]["seasonNumber"]-1) + "." + str(events_detailed_data[events_data[channel][event]["epgId"]]["episodeNumber"]-1) + '.0/0"</episode-num>\n'
                  content = content + '       <icon src="' + events_detailed_data[events_data[channel][event]["epgId"]]["icon"] + '"/>\n'
                  content = content + '       <credits>\n'
                  for cast in events_detailed_data[events_data[channel][event]["epgId"]]["cast"]: 
                    content = content + '         <actor>' + cast.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</actor>\n'
                  for director in events_detailed_data[events_data[channel][event]["epgId"]]["directors"]: 
                    content = content + '         <director>' + director.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</director>\n'
                  content = content + '       </credits>\n'
                  for category in events_detailed_data[events_data[channel][event]["epgId"]]["genres"]:
                    content = content + '       <category>' + category.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</category>\n'
                  if len(str(events_detailed_data[events_data[channel][event]["epgId"]]["year"])) > 0 and int(events_detailed_data[events_data[channel][event]["epgId"]]["year"]) > 0:
                    content = content + '       <date>' + str(events_detailed_data[events_data[channel][event]["epgId"]]["year"]) + '</date>\n'
                  if len(events_detailed_data[events_data[channel][event]["epgId"]]["country"]) > 0:
                    content = content + '       <country>' + events_detailed_data[events_data[channel][event]["epgId"]]["country"].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</country>\n'
                  for rating_name,rating in events_detailed_data[events_data[channel][event]["epgId"]]["ratings"].items(): 
                    content = content + '       <rating system="' + rating_name.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '"><value>' + str(rating) + '/10</value></rating>\n'
                else:
                  content = content + '       <desc lang="cs"></desc>\n'
                content = content + '    </programme>\n'
                cnt = cnt + 1
                if cnt > 20:
                  file.write(bytearray((content).encode('utf-8')))
                  content = ""
                  cnt = 0
              file.write(bytearray((content).encode('utf-8')))                          
          file.write(bytearray(('</tv>\n').encode('utf-8')))
          file.close()
          xbmcgui.Dialog().notification("Sledování O2TV","EPG bylo uložené", xbmcgui.NOTIFICATION_INFO, 3000)    
      except Exception:
        file.close()
        xbmcgui.Dialog().notification("Sledování O2TV","Nemohu zapsat do " + addon.getSetting("output_dir") + "o2_epg.xml" + "!", xbmcgui.NOTIFICATION_ERROR, 6000)
        sys.exit()
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Nevrácena žádná data!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()

open_db(check = 1)
close_db()

if addon.getSetting("disabled_scheduler") == "true":
  sys.exit()

time.sleep(60)
if not addon.getSetting("epg_interval"):
  interval = 12*60*60
else:
  interval = int(addon.getSetting("epg_interval"))*60*60
next = time.time()

if addon.getSetting("download_streams") == "true":
  import downloader
  dt = DownloaderThreadClass()
  dt.start()

while not xbmc.Monitor().abortRequested():
  if(next < time.time()):
    time.sleep(3)
    if addon.getSetting("username") and len(addon.getSetting("username")) > 0 and addon.getSetting("password") and len(addon.getSetting("password")) > 0:
      login()
      load_epg_all()
      #load_epg_details_inc()
      if addon.getSetting("autogen") == "true":
        load_epg_db()      
    if not addon.getSetting("epg_interval"):
      interval = 12*60*60
    else:
      interval = int(addon.getSetting("epg_interval"))*60*60      
    next = time.time() + float(interval)
  time.sleep(1)
if addon.getSetting("download_streams") == "true":  
  downloader.check_process()  