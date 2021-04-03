# -*- coding: utf-8 -*-

import sys
import xbmcaddon
import xbmc

from datetime import date, datetime, timedelta
import time

from o2tv.epg import load_epg_all, open_db, close_db
from o2tv.iptvsc import load_epg_db

tz_offset = int((time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple()))/3600)

addon = xbmcaddon.Addon()

if addon.getSetting('download_streams') == 'true':
    import threading
    class DownloaderThreadClass(threading.Thread):
        def run(self):
            downloader.read_queue()

open_db(check = 1)
close_db()

if addon.getSetting('disabled_scheduler') == 'true':
    sys.exit()

time.sleep(60)
if not addon.getSetting('epg_interval'):
    interval = 12*60*60
else:
    interval = int(addon.getSetting('epg_interval'))*60*60
next = time.time()

if addon.getSetting('download_streams') == 'true':
    import downloader
    dt = DownloaderThreadClass()
    dt.start()

while not xbmc.Monitor().abortRequested():
    if(next < time.time()):
        time.sleep(3)
        if addon.getSetting('username') and len(addon.getSetting('username')) > 0 and addon.getSetting('password') and len(addon.getSetting('password')) > 0:
            load_epg_all()
            #load_epg_details_inc()
            if addon.getSetting('autogen') == 'true':
                load_epg_db()      
        if not addon.getSetting('epg_interval'):
            interval = 12*60*60
        else:
            interval = int(addon.getSetting('epg_interval'))*60*60      
        next = time.time() + float(interval)
    time.sleep(1)
if addon.getSetting('download_streams') == 'true':  
    downloader.check_process()  

addon = None