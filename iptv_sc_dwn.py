# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from urllib import urlencode, quote
except ImportError:
    from urllib.parse import urlencode, quote

from datetime import datetime, timedelta 
from datetime import date
import time

from o2tv.utils import parsedatetime

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

if addon.getSetting("download_streams") == "true":  
    path = xbmc.getInfoLabel('ListItem.FileNameAndPath')
    channel = xbmc.getInfoLabel('ListItem.ChannelName')
    startdatetime = parsedatetime(xbmc.getInfoLabel('ListItem.Date'), xbmc.getInfoLabel('ListItem.StartDate'))

    xbmc.executebuiltin('RunPlugin("plugin://plugin.video.archivo2tv?action=iptv_sc_download&channel=' + str(channel) + '&startdatetime=' + startdatetime + '")')
else:
    xbmcgui.Dialog().notification("Sledování O2TV","Stahování je v doplňku Sledování O2TV vypnuté!", xbmcgui.NOTIFICATION_ERROR, 4000)