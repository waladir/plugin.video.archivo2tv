# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

from urllib import urlencode, quote
from datetime import date, datetime, timedelta
import time
import codecs

from o2tv.o2api import call_o2_api
from o2tv import o2api
from o2tv import utils
from o2tv.stream import play_video
from o2tv.recordings import add_recording
from o2tv.channels import load_channels 

from o2tv.epg import load_epg_all, get_epg_all

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

addon_userdata_dir = xbmc.translatePath( addon.getAddonInfo('profile') ) 
header_unity = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type":"application/json"}
header = {"X-NanguTv-App-Version" : "Android#6.4.1", "User-Agent" : "Dalvik/2.1.0", "Accept-Encoding" : "gzip", "Connection" : "Keep-Alive", "Content-Type" : "application/x-www-form-urlencoded;charset=UTF-8", "X-NanguTv-Device-Id" : addon.getSetting("deviceid"), "X-NanguTv-Device-Name" : addon.getSetting("devicename")}
tz_offset = int((time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple()))/3600)

def load_epg_db():
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
          xbmcgui.Dialog().notification("Sledování O2TV","EPG bylo uložené", xbmcgui.NOTIFICATION_INFO, 3000)    
          
      except IOError:
        xbmcgui.Dialog().notification("Sledování O2TV","Nemohu zapsat do " + addon.getSetting("output_dir") + "o2_epg.xml" + "!", xbmcgui.NOTIFICATION_ERROR, 6000)
        sys.exit()
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Nevráceny žádná data!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()

def load_epg():
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable

    events_data = {}
    events_detailed_data = {}
    params = ""

    for num in sorted(channels_nums.keys()):
      params = params + ("&channelKey=" + quote(channels_data[channels_nums[num]]["channelKey"].encode("utf-8")))

    for day in range(-8,8,1):
      from_datetime = datetime.combine(date.today(), datetime.min.time()) - timedelta(days = -1*int(day))
      from_ts = int(time.mktime(from_datetime.timetuple()))
      to_ts = from_ts+(24*60*60)-1

      url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?forceLimit=true&limit=500" + params + "&from=" + str(from_ts*1000) + "&to=" + str(to_ts*1000) 
      data = o2api.call_o2_api(url = url, data = None, header = header_unity)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Chyba API O2 při načítání EPG!", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()
      if "epg" in data and len(data["epg"]) > 0 and "items" in data["epg"] and len(data["epg"]["items"]) > 0:
        for channel in data["epg"]["items"]:
          for event in channel["programs"]:
            if channel["channel"]["name"] not in events_data:
              events_data[channel["channel"]["name"]] = {event["start"] : {"epgId" : event["epgId"], "startTime" : int(event["start"]/1000), "endTime" : int(event["end"]/1000), "channel" : channel["channel"]["name"], "title" : event["name"]}}
            else:  
              events_data[channel["channel"]["name"]].update({event["start"] : {"epgId" : event["epgId"], "startTime" : int(event["start"]/1000), "endTime" : int(event["end"]/1000), "channel" : channel["channel"]["name"], "title" : event["name"]}})

    url = "https://www.o2tv.cz/unity/api/v1/epg/"
    data = o2api.call_o2_api(url = url, data = None, header = header_unity)
    if "err" in data:
      print("Chyba API O2 při načítání detailních dat pro EPG!")
      sys.exit()
    if "result" in data and len(data["result"]) > 0 and "count" in data and data["count"] > 0:
      offset = 0
      step = 50
      cnt = data["count"]
      for offset in range(0, cnt + step, step):
        url = "https://www.o2tv.cz/unity/api/v1/epg/?offset=" + str(offset)
        data = o2api.call_o2_api(url = url, data = None, header = header_unity)
        if "err" in data:
          print("Chyba API O2 při načítání detailních dat pro EPG!")
          sys.exit()
        if "result" in data and len(data["result"]) > 0:
          for event in data["result"]:
            desc = ""
            img = ""
            cast = []
            year = -1
            country = ""
            directors = []
            genres = []
            ratings = {}
            if "shortDescription" in event:
              desc = event["shortDescription"]
            if "images" in event and "cover" in event["images"][0]:
              img = event["images"][0]["cover"]
            if "castAndCrew" in event and len(event["castAndCrew"]) > 0 and "cast" in event["castAndCrew"] and len(event["castAndCrew"]["cast"]) > 0:
              for person in event["castAndCrew"]["cast"]:      
                cast.append(person["name"])
            if "castAndCrew" in event and len(event["castAndCrew"]) > 0 and "directors" in event["castAndCrew"] and len(event["castAndCrew"]["directors"]) > 0:
              for person in event["castAndCrew"]["directors"]:      
                directors.append(person["name"])
            if "origin" in event and len(event["origin"]) > 0:
              if "year" in event["origin"] and len(str(event["origin"]["year"])) > 0:
                year =  event["origin"]["year"]
              if "country" in event["origin"] and len(event["origin"]["country"]) > 0:
                country = event["origin"]["country"]["name"]
            if "ratings" in event and len(event["ratings"]) > 0:
              for rating, rating_value in event["ratings"].items():
                ratings.update({rating : int(rating_value)/10})
            if "genreInfo" in event and len(event["genreInfo"]) > 0 and "genres" in event["genreInfo"] and len(event["genreInfo"]["genres"]) > 0:
              for genre in event["genreInfo"]["genres"]:      
                genres.append(genre["name"])
            events_detailed_data.update({event["epgId"] : {"name" : event["name"], "desc" : desc, "icon" : "https://www.o2tv.cz" + img, "cast" : cast, "directors" : directors, "year" : year, "country" : country, "genres" : genres, "ratings" : ratings }})
    else:
      print("Chyba při načítání detailních dat pro EPG!")
      sys.exit()

   
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
                  file.write('       <icon src="' + events_detailed_data[events_data[channel][event]["epgId"]]["icon"] + '"/>\n')
                  file.write('       <credits>\n')
                  for cast in events_detailed_data[events_data[channel][event]["epgId"]]["cast"]: 
                    file.write('         <actor>' + cast.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</actor>\n')
                  for director in events_detailed_data[events_data[channel][event]["epgId"]]["directors"]: 
                    file.write('         <director>' + director.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</director>\n')
                  file.write('       </credits>\n')
                  for category in events_detailed_data[events_data[channel][event]["epgId"]]["genres"]:
                    file.write('       <category>' + category.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</category>\n')
                  if len(str(events_detailed_data[events_data[channel][event]["epgId"]]["year"])) > 0 and int(year) > 0:
                    file.write('       <date>' + str(events_detailed_data[events_data[channel][event]["epgId"]]["year"]) + '</date>\n')
                  if len(events_detailed_data[events_data[channel][event]["epgId"]]["country"]) > 0:
                    file.write('       <country>' + events_detailed_data[events_data[channel][event]["epgId"]]["country"].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</country>\n')
                  for rating_name,rating in events_detailed_data[events_data[channel][event]["epgId"]]["ratings"].items(): 
                    file.write('       <rating system="' + rating_name.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '"><value>' + str(rating) + '/10</value></rating>\n')
                else:
                  file.write('       <desc lang="cs"></desc>\n')
                file.write('    </programme>\n')
          file.write('</tv>\n')
          xbmcgui.Dialog().notification("Sledování O2TV","EPG bylo uložené", xbmcgui.NOTIFICATION_INFO, 3000)    
          
      except IOError:
        xbmcgui.Dialog().notification("Sledování O2TV","Nemohu zapsat do " + addon.getSetting("output_dir") + "o2_epg.xml" + "!", xbmcgui.NOTIFICATION_ERROR, 6000)
        sys.exit()
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Nevráceny žádná data!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()

def generate_playlist():
    if addon.getSetting("output_dir") is None or len(addon.getSetting("output_dir")) == 0:
      xbmcgui.Dialog().notification("Sledování O2TV","Nastav adresář pro playlist!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit() 
             
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable 
    filename = addon.getSetting("output_dir") + "playlist.m3u"

    with codecs.open(filename, "w", encoding = "utf-8") as file:
      file.write('%s\n' % "#EXTM3U")
      for num in sorted(channels_nums.keys()):  
        if channels_data[channels_nums[num]] and len(channels_data[channels_nums[num]]["logo"]) > 0:   
          logo = channels_data[channels_nums[num]]["logo"]
        else:
          logo = ""  
        if addon.getSetting("add_channel_numbers") == "true":
          line = "#EXTINF:-1 tvg-chno=\"" + str(num) + "\" tvh-epg=\"0\" tvg-logo=\"" + logo + "\"," + channels_nums[num]
        else:
          line = "#EXTINF:-1 tvh-epg=\"0\" tvg-logo=\"" + logo + "\"," + channels_nums[num]
        file.write('%s\n' % line)
        line = "plugin://plugin.video.archivo2tv/?action=get_stream_url&channelKey=" + quote(channels_data[channels_nums[num]]["channelKey"].encode("utf-8"))
        file.write('%s\n' % line)
          
    xbmcgui.Dialog().notification("Sledování O2TV","Playlist byl uložený", xbmcgui.NOTIFICATION_INFO, 4000)    

def generate_epg():
    if addon.getSetting("use_epg_db") == "true":
      load_epg_all()
      load_epg_db()      
    else:
      load_epg()
    
def iptv_sc_play(channelName, startdatetime, epg):
    epgId = -1
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
      channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable       
      channelKey = channels_data[channelName.decode("utf-8")]["channelKey"].encode("utf-8")
      param =  "channelKey=" + quote(channelKey)
      data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?" + param + "&from=" + str(from_ts*1000) + "&forceLimit=true&limit=500", data = None, header = o2api.header_unity)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s načtením kanálů", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit() 
      if "epg" in data and len(data["epg"]) > 0 and len(data["epg"]["items"]) > 0 and len(data["epg"]["items"][0]["programs"]) > 0:
        for programs in data["epg"]["items"][0]["programs"]:
          if str(programs["start"]) == str(from_ts*1000):
            startts = programs["start"]/1000
            start = datetime.fromtimestamp(programs["start"]/1000)
            endts = programs["end"]/1000
            end = datetime.fromtimestamp(programs["end"]/1000)        
            epgId = programs["epgId"]
            title = utils.day_translation_short[start.strftime("%w")].decode("utf-8") + " " + start.strftime("%d.%m %H:%M") + " - " + end.strftime("%H:%M") + " | " + programs["name"]
      if int(epgId) > 0:
        if int(endts) < int(time.mktime(datetime.now().timetuple())):
          play_video(type = "archiv_iptv", channelKey = channelKey, start = startts, end = endts, epgId = epgId, title = title)
        else:
          if epg == 1:
            play_video(type = "live_iptv_epg", channelKey = channelKey, start = None, end = None, epgId = None, title = None)
          else:
            play_video(type = "live_iptv", channelKey = channelKey, start = None, end = None, epgId = None, title = None)
      else:
        if len(startdatetime) == 0:
          play_video(type = "live_iptv", channelKey = channelKey, start = None, end = None, epgId = None, title = None)
        else:
          xbmcgui.Dialog().notification("Sledování O2TV","Pořad u O2 nenalezen! Používáte EPG z doplňku Sledování O2TV?", xbmcgui.NOTIFICATION_ERROR, 10000)
        sys.exit()  

def iptv_sc_rec(channelName, startdatetime):
    channelName = channelName.decode("utf-8")
    epgId = -1

    from_ts = int(time.mktime(time.strptime(startdatetime, "%d.%m.%Y %H:%M")))
    channels_nums, channels_data, channels_key_mapping = load_channels() # pylint: disable=unused-variable 
    channelKey = channels_data[channelName]["channelKey"].encode("utf-8")
    param =  "channelKey=" + quote(channelKey)

    data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?" + param + "&from=" + str(from_ts*1000) + "&forceLimit=true&limit=500", data = None, header = o2api.header_unity)
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
