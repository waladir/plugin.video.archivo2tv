# -*- coding: utf-8 -*-

import sys
import json
import codecs
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

if sys.version_info.major<3:
  from urllib2 import Request, urlopen, HTTPError, URLError
  from urllib import urlencode, quote
else:
  from urllib.request import Request, urlopen
  from urllib.error import URLError, HTTPError
  from urllib.parse import urlencode, quote

from datetime import date, datetime, timedelta
import time

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')
addon_userdata_dir = xbmc.translatePath( addon.getAddonInfo('profile') ) 

header_unity = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type":"application/json"}
header = {"X-NanguTv-App-Version" : "Android#6.4.1", "User-Agent" : "Dalvik/2.1.0", "Accept-Encoding" : "gzip", "Connection" : "Keep-Alive", "Content-Type" : "application/x-www-form-urlencoded;charset=UTF-8", "X-NanguTv-Device-Name" : addon.getSetting("deviceid"), "X-NanguTv-Device-Name" : addon.getSetting("devicename")}
tz_offset = int((time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple()))/3600)

def call_o2_api(url, data, header):
    request = Request(url = url , data = data, headers = header)
    if addon.getSetting("log_request_url") == "true":
      xbmc.log(url)
    if addon.getSetting("log_request_data") == "true" and data <> None:
      xbmc.log(data)

    try:
      html = urlopen(request).read()
      if addon.getSetting("log_response") == "true":
        xbmc.log(html)

      if html and len(html) > 0:
        data = json.loads(html)
        return data
      else:
        return []
    except HTTPError as e:
      return { "err" : e.reason }   
    except URLError:
      return { "err" : "connection error" }      
      
def check_settings():
    if not addon.getSetting("deviceid"):
      addon.setSetting("deviceid",''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(15)))

    if addon.getSetting("output_dir") is None or len(addon.getSetting("output_dir")) == 0:
      xbmcgui.Dialog().notification("Sledování O2TV","Nastav adresář pro EPG!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit() 

    if not addon.getSetting("username") or not addon.getSetting("password") or not addon.getSetting("deviceid") or not addon.getSetting("devicename") or  not addon.getSetting("devicetype"):
      xbmcgui.Dialog().notification("Sledování O2TV","V nastavení je nutné mít vyplněné všechny přihlašovací údaje", xbmcgui.NOTIFICATION_ERROR, 10000)
      sys.exit()

    if (addon.getSetting("stream_type") == "MPEG-DASH" or addon.getSetting("stream_type") == "MPEG-DASH-web") and not xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)'):
      xbmcgui.Dialog().notification("Sledování O2TV","Při použítí streamu MPEG-DASH je nutné mít nainstalovaný doplněk InputStream Adaptive", xbmcgui.NOTIFICATION_ERROR, 20000)
      sys.exit()

def get_auth_token():
    global header_unity
    post = {"username" : addon.getSetting("username"), "password" : addon.getSetting("password")} 
    data = call_o2_api(url = "https://ottmediator.o2tv.cz:4443/ottmediator-war/login", data = urlencode(post), header = header)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
      return None, None, None, None, None, None, None          

    if "services" in data and "remote_access_token" in data and len(data["remote_access_token"]) > 0 and "service_id" in data["services"][0] and len(data["services"][0]["service_id"]) > 0:
        remote_access_token = data["remote_access_token"]
        service_id = data["services"][0]['service_id']

        post = {"service_id" : service_id, "remote_access_token" : remote_access_token}
        data = call_o2_api(url = "https://ottmediator.o2tv.cz:4443/ottmediator-war/loginChoiceService", data = urlencode(post), header = header)
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()  

        post = {"grant_type" : "remote_access_token", "client_id" : "tef-web-portal-etnetera", "client_secret" : "2b16ac9984cd60dd0154f779ef200679", "platform_id" : "231a7d6678d00c65f6f3b2aaa699a0d0", "language" : "cs", "remote_access_token" : str(remote_access_token), "authority" :  "tef-sso", "isp_id" : "1"}
        data = call_o2_api(url = "https://oauth.o2tv.cz/oauth/token", data = urlencode(post), header = header)
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()  

        if "access_token" in data and len(data["access_token"]) > 0:
          access_token = data["access_token"]
          header.update({"X-NanguTv-Access-Token" : str(access_token), "X-NanguTv-Device-Id" : addon.getSetting("deviceid")})
          data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/settings/subscription-configuration.json", data = None, header = header)
          if "err" in data:
            xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
            sys.exit()  
          if "isp" in data and len(data["isp"]) > 0 and "locality" in data and len(data["locality"]) > 0 and "billingParams" in data and len(data["billingParams"]) > 0 and "offers" in data["billingParams"] and len(data["billingParams"]["offers"]) > 0 and "tariff" in data["billingParams"] and len(data["billingParams"]["tariff"]) > 0:
            subscription = data["subscription"]
            isp = data["isp"]
            locality = data["locality"]
            offers = data["billingParams"]["offers"]
            tariff = data["billingParams"]["tariff"]
            header_unity = {"User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type" : "application/json", "x-o2tv-access-token" : str(access_token), "x-o2tv-device-id" : addon.getSetting("deviceid"), "x-o2tv-device-name" : addon.getSetting("devicename")}
            data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/user/profile/", data = None, header = header_unity)
            if "err" in data:
              xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
              sys.exit()   
            sdata = data["sdata"]
            header_unity.update({"x-o2tv-sdata" : str(sdata)})
            return access_token, subscription, isp, locality, offers, tariff, sdata
          else:
              xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
              sys.exit()            
        else:
            xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
            sys.exit()
    else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()

def get_auth_password():
    global header_unity
    post = {"grant_type" : "password", "client_id" : "tef-web-portal-etnetera", "client_secret" : "2b16ac9984cd60dd0154f779ef200679", "platform_id" : "231a7d6678d00c65f6f3b2aaa699a0d0", "language" : "cs", "username" : addon.getSetting("username"), "password" : addon.getSetting("password")}
    data = call_o2_api(url = "https://oauth.o2tv.cz/oauth/token", data = urlencode(post), header = header)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
      return None, None, None, None, None, None, None   
      
    if "access_token" in data and len(data["access_token"]) > 0:
      access_token = data["access_token"]
      header.update({"X-NanguTv-Access-Token" : str(access_token), "X-NanguTv-Device-Id" : addon.getSetting("deviceid")})
      data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/settings/subscription-configuration.json", data = None, header = header)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()  
         
      if "isp" in data and len(data["isp"]) > 0 and "locality" in data and len(data["locality"]) > 0 and "billingParams" in data and len(data["billingParams"]) > 0 and "offers" in data["billingParams"] and len(data["billingParams"]["offers"]) > 0 and "tariff" in data["billingParams"] and len(data["billingParams"]["tariff"]) > 0:
        subscription = data["subscription"]
        isp = data["isp"]
        locality = data["locality"]
        offers = data["billingParams"]["offers"]
        tariff = data["billingParams"]["tariff"]
        header_unity = {"User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type" : "application/json", "x-o2tv-access-token" : str(access_token), "x-o2tv-device-id" : addon.getSetting("deviceid"), "x-o2tv-device-name" : addon.getSetting("devicename")}
        data = call_o2_api(url = "https://www.o2tv.cz/unity/api/v1/user/profile/", data = None, header = header_unity)
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()   
        sdata = data["sdata"]
        header_unity.update({"x-o2tv-sdata" : str(sdata)})
        return access_token, subscription, isp, locality, offers, tariff, sdata
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()            
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()
      
def load_channels():
    channels = {}
    channels_ordered = {}
    for offer in offers:
      post = {"locality" : locality, "tariff" : tariff, "isp" : isp, "language" : "ces", "deviceType" : addon.getSetting("devicetype"), "liveTvStreamingProtocol" : "HLS", "offer" : offer}
      data = call_o2_api(url = "https://app.o2tv.cz/sws/server/tv/channels.json", data = urlencode(post).encode("utf-8"), header = header)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Chyba API O2 při načítání kanálů!", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()
      if "channels" in data and len(data["channels"]) > 0:
        for channel in data["channels"]:
          if data["channels"][channel]["channelType"] == "TV":
            channels_ordered.update({data["channels"][channel]["channelNumber"] : data["channels"][channel]["channelKey"]})
            channels.update({data["channels"][channel]["channelKey"] : {"channelKey" : data["channels"][channel]["channelKey"], "channelName" : data["channels"][channel]["channelName"]}})
    if len(channels) == 0:
      xbmcgui.Dialog().notification("Sledování O2TV","Chyba API O2 při načítání kanálů!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()
    return channels_ordered, channels      
    
def load_epg(): 
    global access_token, subscription, isp, locality, offers, tariff, sdata
    check_settings() 
    
    if "@" in addon.getSetting("username"):
      access_token, subscription, isp, locality, offers, tariff, sdata = get_auth_token()
    else:
      access_token, subscription, isp, locality, offers, tariff, sdata = get_auth_password()
    if not access_token or len(access_token) == 0:
      return
      
    channels_ordered, channels = load_channels()
  
    if addon.getSetting("epg_min") < 1 and addon.getSetting("epg_min") > 7:
      xbmcgui.Dialog().notification("Sledování O2TV","Počet dnů pro EPG musí být v intervalu 1 až 7!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()
    if addon.getSetting("epg_fut") < 1 and addon.getSetting("epg_fut") > 7:
      xbmcgui.Dialog().notification("Sledování O2TV","Počet dnů pro EPG musí být v intervalu 1 až 7!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()

    channels_data = {}
    events_data = {}
    events_detailed_data = {}
    params = ""

    for channelKey in channels.keys():
      params = params + ("&channelKey=" + quote(channelKey.encode("utf-8")))

    for day in range(int(addon.getSetting("epg_min"))*-1,int(addon.getSetting("epg_fut")),1):
      from_datetime = datetime.combine(date.today(), datetime.min.time()) - timedelta(days = -1*int(day))
      from_ts = int(time.mktime(from_datetime.timetuple()))
      to_ts = from_ts+(24*60*60)-1

      url = "https://www.o2tv.cz/unity/api/v1/epg/depr/?forceLimit=true&limit=500" + params + "&from=" + str(from_ts*1000) + "&from=" + str(from_ts*1000) 
      data = call_o2_api(url = url, data = None, header = header_unity)
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Chyba API O2 při načítání EPG!", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()
      if "epg" in data and len(data["epg"]) > 0 and "items" in data["epg"] and len(data["epg"]["items"]) > 0:
        for channel in data["epg"]["items"]:
          channels_data.update({channel["channel"]["channelKey"] : {"name" : channel["channel"]["name"], "logo" : "https://www.o2tv.cz" + channel["channel"]["logoUrl"]}})
          for event in channel["programs"]:
            if channel["channel"]["channelKey"] not in events_data:
              events_data[channel["channel"]["channelKey"]] = {event["start"] : {"epgId" : event["epgId"], "startTime" : int(event["start"]/1000), "endTime" : int(event["end"]/1000), "channel" : channel["channel"]["name"], "title" : event["name"]}}
            else:  
              events_data[channel["channel"]["channelKey"]].update({event["start"] : {"epgId" : event["epgId"], "startTime" : int(event["start"]/1000), "endTime" : int(event["end"]/1000), "channel" : channel["channel"]["name"], "title" : event["name"]}})

    if len(channels_data) > 0:
      try:
        with codecs.open(addon.getSetting("output_dir") + "o2_epg.xml", "w", encoding="utf-8") as file:
          file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
          file.write('<tv generator-info-name="EPG grabber">\n')
          for channel_num in sorted(channels_ordered.keys()):
            channel = channels_ordered[channel_num]
            if channel in channels_data:
              file.write('    <channel id="' + channels_data[channel]["name"].replace("&","&amp;") + '">\n')
              file.write('            <display-name lang="cs">' + channels_data[channel]["name"].replace("&","&amp;") + '</display-name>\n')
              file.write('            <icon src="' + channels_data[channel]['logo'] + '" />\n')
              file.write('    </channel>\n')
          for channel_num in sorted(channels_ordered.keys()):
            channel = channels_ordered[channel_num]
            if channel in events_data:
              for event in sorted(events_data[channel].keys()):
                starttime = datetime.fromtimestamp(events_data[channel][event]["startTime"]).strftime("%Y%m%d%H%M%S")
                endtime = datetime.fromtimestamp(events_data[channel][event]["endTime"]).strftime("%Y%m%d%H%M%S")
                file.write('    <programme start="' + starttime + ' +0' + str(tz_offset) + '00" stop="' + endtime + ' +0' + str(tz_offset) + '00" channel="' + events_data[channel][event]["channel"] + '">\n')
                file.write('       <title lang="cs">' + events_data[channel][event]["title"].replace("&","&amp;") + '</title>\n')
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


if addon.getSetting("autogen") == "true":
  load_epg()  
  if not addon.getSetting("epg_interval"):
    interval = 12*60*60
  else:
    interval = int(addon.getSetting("epg_interval"))*60*60
  next = time.time() + float(interval) 
  while True:
    if(next < time.time()):
      time.sleep(30)
      load_epg()
      next = time.time() + float(interval)
    time.sleep(1)
  