# -*- coding: utf-8 -*-

import sys
import os
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

try:
    from urllib2 import urlopen, Request, HTTPError
    from urllib import urlencode, quote
    from urlparse import parse_qsl    
except ImportError:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode, quote, parse_qsl
    from urllib.error import HTTPError

import json
import time

from o2tv.utils import plugin_id, encode

addon = xbmcaddon.Addon(id = plugin_id)
addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 

header_unity = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type":"application/json"}
header = {"X-NanguTv-App-Version" : "Android#6.4.1", "User-Agent" : "Dalvik/2.1.0", "Accept-Encoding" : "gzip", "Connection" : "Keep-Alive", "Content-Type" : "application/x-www-form-urlencoded;charset=UTF-8", "X-NanguTv-Device-Id" : addon.getSetting("deviceid"), "X-NanguTv-Device-Name" : addon.getSetting("devicename")}

def call_o2_api(url, data, header):
    if data != None:
      data = data.encode("utf-8")
    request = Request(url = url , data = data, headers = header)
    if addon.getSetting("log_request_url") == "true":
      xbmc.log(str(url))
    if addon.getSetting("log_request_data") == "true" and data != None:
      xbmc.log(str(data))

    try:
      html = urlopen(request).read()
      if addon.getSetting("log_response") == "true":
        xbmc.log(str(html))

      if html and len(html) > 0:
        data = json.loads(html)
        return data
      else:
        return []
    except HTTPError as e:
      return { "err" : e.reason }  

def test_session():
    global header_unity
    services = {}
    post = {"username" : addon.getSetting("username"), "password" : addon.getSetting("password")} 
    data = call_o2_api(url = "https://ottmediator.o2tv.cz/ottmediator-war/login", data = urlencode(post), header = header)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()    

    if "services" in data and "remote_access_token" in data and len(data["remote_access_token"]) > 0 and len(data["services"]) > 0:
      remote_access_token = data["remote_access_token"] 
      for service in data["services"]:
        service_id = service['service_id']

        post = {"service_id" : service_id, "remote_access_token" : remote_access_token}
        data = call_o2_api(url = "https://ottmediator.o2tv.cz/ottmediator-war/loginChoiceService", data = urlencode(post), header = header)
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
          headertmp = header
          headertmp.update({"X-NanguTv-Access-Token" : str(access_token), "X-NanguTv-Device-Id" : addon.getSetting("deviceid")})
          data = call_o2_api(url = "https://app.o2tv.cz/sws/subscription/settings/subscription-configuration.json", data = None, header = headertmp)
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
            data = call_o2_api(url = "https://api.o2tv.cz/unity/api/v1/user/profile/", data = None, header = header_unity)
            if "err" in data:
              xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
              sys.exit()   
            sdata = data["sdata"]
            encodedChannels = data["encodedChannels"]
            channels = data["ottChannels"]["live"]  
            header_unity.update({"x-o2tv-sdata" : str(sdata)})
            services.update({service_id : { "access_token" : access_token, "subscription" : subscription, "isp" : isp, "locality" : locality, "offers" : offers, "tariff" : tariff, "sdata" : sdata, "encodedChannels" : encodedChannels, "channels" : channels}})
          else:
              xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
              sys.exit()            
        else:
            xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
            sys.exit()
      for service_id in services:
        service = services[service_id]
        channelKey = service["channels"][0]
        post = {"serviceType" : "LIVE_TV", "deviceType" : addon.getSetting("devicetype"), "streamingProtocol" : "HLS", "subscriptionCode" : service["subscription"], "channelKey" : channelKey, "encryptionType" : "NONE"}
        headertmp = header
        headertmp.update({"X-NanguTv-Access-Token" : str(service["access_token"]), "X-NanguTv-Device-Id" : addon.getSetting("deviceid")})
        data = call_o2_api(url = "https://app.o2tv.cz/sws/server/streaming/uris.json", data = urlencode(post), header = headertmp)
      for service_id in services:
        service = services[service_id]
        channelKey = service["channels"][0]
        post = {"serviceType" : "LIVE_TV", "deviceType" : addon.getSetting("devicetype"), "streamingProtocol" : "HLS", "subscriptionCode" : service["subscription"], "channelKey" : channelKey, "encryptionType" : "NONE"}
        headertmp = header
        headertmp.update({"X-NanguTv-Access-Token" : str(service["access_token"]), "X-NanguTv-Device-Id" : addon.getSetting("deviceid")})
        data = call_o2_api(url = "https://app.o2tv.cz/sws/server/streaming/uris.json", data = urlencode(post), header = headertmp)
    else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()


def get_auth_token():
    global header_unity
    post = {"username" : addon.getSetting("username"), "password" : addon.getSetting("password")} 
    data = call_o2_api(url = "https://ottmediator.o2tv.cz/ottmediator-war/login", data = urlencode(post), header = header)
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()    
    serviceid_order = int(addon.getSetting("serviceid_order"))  
    if "services" in data and "remote_access_token" in data and len(data["remote_access_token"]) > 0 and serviceid_order + 1 <= len(data["services"]) and "service_id" in data["services"][serviceid_order] and len(data["services"][serviceid_order]["service_id"]) > 0:
        remote_access_token = data["remote_access_token"]
        service_id = data["services"][serviceid_order]['service_id']

        post = {"service_id" : service_id, "remote_access_token" : remote_access_token}
        data = call_o2_api(url = "https://ottmediator.o2tv.cz/ottmediator-war/loginChoiceService", data = urlencode(post), header = header)
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
            data = call_o2_api(url = "https://api.o2tv.cz/unity/api/v1/user/profile/", data = None, header = header_unity)
            if "err" in data:
              xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
              sys.exit()   
            sdata = data["sdata"]
            encodedChannels = data["encodedChannels"]  
            header_unity.update({"x-o2tv-sdata" : str(sdata)})
            return access_token, subscription, isp, locality, offers, tariff, sdata, encodedChannels
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
        data = call_o2_api(url = "https://api.o2tv.cz/unity/api/v1/user/profile/", data = None, header = header_unity)
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()   
        sdata = data["sdata"]
        encodedChannels = data["encodedChannels"]  
        header_unity.update({"x-o2tv-sdata" : str(sdata)})
        return access_token, subscription, isp, locality, offers, tariff, sdata, encodedChannels
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()            
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()

def get_auth_web():
    post = {"username" : addon.getSetting("username"), "password" : addon.getSetting("password")} 
    req = Request("https://api.o2tv.cz/unity/api/v1/services/")
    req.add_header("Content-Type", "application/json")
    resp = urlopen(req, json.dumps(post))
    data = json.loads(resp.read())
    if "err" in data:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()    
    serviceid_order = 0
    if "services" in data and "remoteAccessToken" in data and len(data["remoteAccessToken"]) > 0 and serviceid_order + 1 <= len(data["services"]) and "serviceId" in data["services"][serviceid_order] and len(data["services"][serviceid_order]["serviceId"]) > 0:
      remote_access_token = data["remoteAccessToken"]
      service_id = data["services"][serviceid_order]['serviceId']
      post = {"remoteAccessToken" : remote_access_token} 
      req = Request("https://api.o2tv.cz/unity/api/v1/services/selection/" + service_id + "/")
      req.add_header('Content-Type', 'application/json')
      resp = urlopen(req, json.dumps(post))
      data = json.loads(resp.read())
      if "err" in data:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()    
      if "accessToken" in data and len(data["accessToken"]) > 0:
        access_token = data["accessToken"]
        header_unity = {"User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type" : "application/json", "x-o2tv-access-token" : str(access_token), "x-o2tv-device-id" : addon.getSetting("deviceid"), "x-o2tv-device-name" : addon.getSetting("devicename")}
        data = call_o2_api(url = "https://api.o2tv.cz/unity/api/v1/user/profile/", data = None, header = header_unity)
        if "err" in data:
          xbmcgui.Dialog().notification("Sledování O2TV","Problém při přihlášení", xbmcgui.NOTIFICATION_ERROR, 4000)
          sys.exit()   
        isp = 1
        subscription = data["code"]
        sdata = data["sdata"]
        locality = data["locality"]
        offers = data["subscription"]["offers"]
        tariff = data["tariff"]
        encodedChannels = data["encodedChannels"]
        header_unity.update({"x-o2tv-sdata" : str(sdata)})
        return access_token, subscription, isp, locality, offers, tariff, sdata, encodedChannels
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()            
    else:
      xbmcgui.Dialog().notification("Sledování O2TV","Problém s příhlášením", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()            

def login():
  global access_token, subscription, isp, locality, offers, tariff, sdata, encodedChannels
  global header_unity
  data = {}
  filename = addon_userdata_dir + "session.txt"
  try:
    with open(filename, "r") as file:
      for line in file:
        item = line[:-1]
        data = json.loads(item)
  except IOError:
    data = {}
  if data and len(data) > 0 and "valid_to" in data and data["valid_to"] > int(time.time()):
    access_token = data["access_token"]
    subscription = data["subscription"]
    isp = data["isp"]
    locality = data["locality"]
    offers = data["offers"]
    tariff = data["tariff"]
    sdata = data["sdata"]
    encodedChannels = data["encodedChannels"]
    header.update({"X-NanguTv-Access-Token" : str(access_token), "X-NanguTv-Device-Id" : addon.getSetting("deviceid")})
    header_unity = {"User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type" : "application/json", "x-o2tv-access-token" : str(access_token), "x-o2tv-device-id" : addon.getSetting("deviceid"), "x-o2tv-device-name" : addon.getSetting("devicename"), "x-o2tv-sdata" : str(sdata)}
  else:  
    if "@" in addon.getSetting("username"):
      access_token, subscription, isp, locality, offers, tariff, sdata, encodedChannels = get_auth_token()
#      access_token, subscription, isp, locality, offers, tariff, sdata, encodedChannels = get_auth_web()
    else:
      access_token, subscription, isp, locality, offers, tariff, sdata, encodedChannels = get_auth_password() 
    auth_data = json.dumps({ "access_token" : access_token, "subscription" : subscription, "isp" : isp, "locality" : locality, "offers" : offers, "tariff" : tariff, "sdata" : sdata, "encodedChannels" : encodedChannels, "valid_to" : int(time.time()) + 60*60*24})
    try: 
      with open(filename, "w") as file:
        file.write('%s\n' % auth_data)
    except IOError:
      xbmc.log("Chyba uložení session")

def session_reset():     
    filename = addon_userdata_dir + "session.txt"
    if os.path.exists(filename):
      os.remove(filename) 
    login()
    xbmcgui.Dialog().notification("Sledování O2TV","O2 session byla znovu načtená", xbmcgui.NOTIFICATION_INFO, 4000) 
              