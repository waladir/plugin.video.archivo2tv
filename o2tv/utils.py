# -*- coding: utf-8 -*-

import os
import sys

import xbmcgui
import xbmcaddon
import xbmc

from urllib import urlencode
import string, random 

_url = sys.argv[0]
_handle = int(sys.argv[1])
addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urlencode(kwargs))

def check_settings():
    if not addon.getSetting("deviceid"):
      addon.setSetting("deviceid",''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(15)))

    if not addon.getSetting("username") or not addon.getSetting("password") or not addon.getSetting("deviceid") or not addon.getSetting("devicename") or  not addon.getSetting("devicetype"):
      xbmcgui.Dialog().notification("Sledování O2TV","V nastavení je nutné mít vyplněné všechny přihlašovací údaje", xbmcgui.NOTIFICATION_ERROR, 10000)
      sys.exit()

    if (addon.getSetting("stream_type") == "MPEG-DASH" or addon.getSetting("stream_type") == "MPEG-DASH-web") and not xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)'):
      xbmcgui.Dialog().notification("Sledování O2TV","Při použítí streamu MPEG-DASH je nutné mít nainstalovaný doplněk InputStream Adaptive", xbmcgui.NOTIFICATION_ERROR, 20000)
      sys.exit()

def get_color(settings_color):
    if len(settings_color) >2 and settings_color.find("]") > 1:
      color = settings_color[1:settings_color.find("]")].replace("COLOR ","")
      return color
    else:
      return ""

day_translation = {"1" : "Pondělí", "2" : "Úterý", "3" : "Středa", "4" : "Čtvrtek", "5" : "Pátek", "6" : "Sobota", "0" : "Neděle"}  
day_translation_short = {"1" : "Po", "2" : "Út", "3" : "St", "4" : "Čt", "5" : "Pá", "6" : "So", "0" : "Ne"}  
