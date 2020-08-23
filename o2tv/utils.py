# -*- coding: utf-8 -*-

import os
import sys

import xbmcgui
import xbmcaddon
import xbmc

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

import string, random 
import unicodedata

_url = sys.argv[0]
#_handle = int(sys.argv[1])
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

    if addon.getSetting("download_streams") == "true" and (addon.getSetting("ffmpeg_bin") is None or len(addon.getSetting("ffmpeg_bin")) == 0 or not os.path.isfile(addon.getSetting("ffmpeg_bin")) or not os.access(addon.getSetting("ffmpeg_bin"), os.X_OK)):
      test_bin1 = "/usr/bin/ffmpeg"
      test_bin2 = "/storage/.kodi/addons/tools.ffmpeg-tools/bin/ffmpeg"
      if os.path.isfile(test_bin1) and os.access(test_bin1, os.X_OK):
        addon.setSetting("ffmpeg_bin", test_bin1)
      elif os.path.isfile(test_bin2) and os.access(test_bin2, os.X_OK):
        addon.setSetting("ffmpeg_bin", test_bin2)
      else:
        xbmcgui.Dialog().notification("Sledování O2TV","Nastav cestu k ffmpeg!", xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit() 

    if addon.getSetting("download_streams") == "true" and (addon.getSetting("downloads_dir") is None or len(addon.getSetting("downloads_dir")) == 0):
      xbmcgui.Dialog().notification("Sledování O2TV","Nastav adresář pro stahování!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit() 

def get_color(settings_color):
    if len(settings_color) >2 and settings_color.find("]") > 1:
      color = settings_color[1:settings_color.find("]")].replace("COLOR ","")
      return color
    else:
      return ""

def remove_diacritics(text):
  return unicodedata.normalize('NFKD',text).encode('ASCII','ignore')

  

day_translation = {"1" : "Pondělí", "2" : "Úterý", "3" : "Středa", "4" : "Čtvrtek", "5" : "Pátek", "6" : "Sobota", "0" : "Neděle"}  
day_translation_short = {"1" : "Po", "2" : "Út", "3" : "St", "4" : "Čt", "5" : "Pá", "6" : "So", "0" : "Ne"}  
