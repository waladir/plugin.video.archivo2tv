# -*- coding: utf-8 -*-

import sys
import threading
import json
import codecs
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

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

import downloader

from o2tv.o2api import login
from o2tv import o2api
from o2tv.channels import load_channels 
from o2tv.utils import check_settings

from o2tv.epg import load_epg_all, get_epg_all, load_epg_details_inc

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')
addon_userdata_dir = xbmc.translatePath( addon.getAddonInfo('profile') ) 

header_unity = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type":"application/json"}
header = {"X-NanguTv-App-Version" : "Android#6.4.1", "User-Agent" : "Dalvik/2.1.0", "Accept-Encoding" : "gzip", "Connection" : "Keep-Alive", "Content-Type" : "application/x-www-form-urlencoded;charset=UTF-8", "X-NanguTv-Device-Id" : addon.getSetting("deviceid"), "X-NanguTv-Device-Name" : addon.getSetting("devicename")}
tz_offset = int((time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple()))/3600)

class DownloaderThreadClass(threading.Thread):
    def run(self):
      downloader.read_queue()

def load_epg_db():
    check_settings() 
    login()

    events_data = {}
    events_detailed_data = {}
    events_data, events_detailed_data = get_epg_all()

    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable
   
    if len(channels_data) > 0:
      try:
        with codecs.open(addon.getSetting("output_dir") + "o2_epg.xml", "w", encoding="utf-8") as file:
          file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
          file.write('<tv generator-info-name="EPG grabber">\n')
          for num in sorted(channels_nums.keys()):
            channel = channels_nums[num]
            if channel in channels_data:
              file.write('    <channel id="' + channel.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '">\n')
              file.write('            <display-name lang="cs">' + channel.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</display-name>\n')
              file.write('            <icon src="' + channels_data[channel]['logo'] + '" />\n')
              file.write('    </channel>\n')
          for num in sorted(channels_nums.keys()):
            channel = channels_nums[num]
            if channel in events_data:
              for event in sorted(events_data[channel].keys()):
                starttime = datetime.fromtimestamp(events_data[channel][event]["startTime"]).strftime("%Y%m%d%H%M%S")
                endtime = datetime.fromtimestamp(events_data[channel][event]["endTime"]).strftime("%Y%m%d%H%M%S")
                file.write('    <programme start="' + starttime + ' +0' + str(tz_offset) + '00" stop="' + endtime + ' +0' + str(tz_offset) + '00" channel="' + events_data[channel][event]["channel"] + '">\n')
                file.write('       <title lang="cs">' + events_data[channel][event]["title"].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</title>\n')
                if events_data[channel][event]["epgId"] in events_detailed_data:
                  file.write('       <desc lang="cs">' + events_detailed_data[events_data[channel][event]["epgId"]]["desc"].replace("&","&amp;").replace("<","&lt;").replace("<","&gt;") + '</desc>\n')
                  if events_detailed_data[events_data[channel][event]["epgId"]]["episodeName"] != None and len(events_detailed_data[events_data[channel][event]["epgId"]]["episodeName"]) > 0:
                    file.write('       <sub-title lang="cs">' + events_detailed_data[events_data[channel][event]["epgId"]]["episodeName"].replace("&","&amp;").replace("<","&lt;").replace("<","&gt;") + '</sub-title>\n')
                  if events_detailed_data[events_data[channel][event]["epgId"]]["episodeNumber"] != None and events_detailed_data[events_data[channel][event]["epgId"]]["seasonNumber"] != None and events_detailed_data[events_data[channel][event]["epgId"]]["episodeNumber"] > 0 and events_detailed_data[events_data[channel][event]["epgId"]]["seasonNumber"] > 0:
                    if events_detailed_data[events_data[channel][event]["epgId"]]["episodesInSeason"] != None and events_detailed_data[events_data[channel][event]["epgId"]]["episodesInSeason"] > 0:
                      file.write('       <episode-num system="xmltv_ns">' + str(events_detailed_data[events_data[channel][event]["epgId"]]["seasonNumber"]-1) + "." + str(events_detailed_data[events_data[channel][event]["epgId"]]["episodeNumber"]-1) + "/" + str(events_detailed_data[events_data[channel][event]["epgId"]]["episodesInSeason"]) + '.0/0"</episode-num>\n')
                    else:
                      file.write('       <episode-num system="xmltv_ns">' + str(events_detailed_data[events_data[channel][event]["epgId"]]["seasonNumber"]-1) + "." + str(events_detailed_data[events_data[channel][event]["epgId"]]["episodeNumber"]-1) + '.0/0"</episode-num>\n')
                  file.write('       <icon src="' + events_detailed_data[events_data[channel][event]["epgId"]]["icon"] + '"/>\n')
                  file.write('       <credits>\n')
                  for cast in events_detailed_data[events_data[channel][event]["epgId"]]["cast"]: 
                    file.write('         <actor>' + cast.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</actor>\n')
                  for director in events_detailed_data[events_data[channel][event]["epgId"]]["directors"]: 
                    file.write('         <director>' + director.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</director>\n')
                  file.write('       </credits>\n')
                  for category in events_detailed_data[events_data[channel][event]["epgId"]]["genres"]:
                    file.write('       <category>' + category.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</category>\n')
                  if len(str(events_detailed_data[events_data[channel][event]["epgId"]]["year"])) > 0 and int(events_detailed_data[events_data[channel][event]["epgId"]]["year"]) > 0:
                    file.write('       <date>' + str(events_detailed_data[events_data[channel][event]["epgId"]]["year"]) + '</date>\n')
                  if len(events_detailed_data[events_data[channel][event]["epgId"]]["country"]) > 0:
                    file.write('       <country>' + events_detailed_data[events_data[channel][event]["epgId"]]["country"].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</country>\n')
                  for rating_name,rating in events_detailed_data[events_data[channel][event]["epgId"]]["ratings"].items(): 
                    file.write('       <rating system="' + rating_name.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '"><value>' + str(rating) + '/10</value></rating>\n')
                else:
                  file.write('       <desc lang="cs"></desc>\n')
                file.write('    </programme>\n')
          file.write('</tv>\n')
          if addon.getSetting("info_enabled") == "true":
            xbmcgui.Dialog().notification("Sledování O2TV","EPG bylo uložené", xbmcgui.NOTIFICATION_INFO, 3000)    
          
      except IOError:
        xbmcgui.Dialog().notification("Sledování O2TV","Nemohu zapsat do " + addon.getSetting("output_dir") + "o2_epg.xml" + "!", xbmcgui.NOTIFICATION_ERROR, 6000)
        sys.exit()
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Nevráceny žádná data!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()

if addon.getSetting("disabled_scheduler") == "true":
  sys.exit()

time.sleep(60)
if not addon.getSetting("epg_interval"):
  interval = 12*60*60
else:
  interval = int(addon.getSetting("epg_interval"))*60*60
next = time.time()

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
downloader.check_process()  