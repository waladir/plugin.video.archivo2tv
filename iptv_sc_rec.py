# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

from urllib import urlencode, quote

from datetime import datetime, timedelta 
from datetime import date
import time

path = xbmc.getInfoLabel('ListItem.FileNameAndPath')
channel = xbmc.getInfoLabel('ListItem.ChannelName')
startdatetime = xbmc.getInfoLabel('ListItem.Date')
xbmc.executebuiltin('RunPlugin("plugin://plugin.video.archivo2tv?action=iptv_sc_rec&channel=' + str(channel) + '&startdatetime=' + startdatetime + '")')