# -*- coding: utf-8 -*-

import sys
import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui
import platform
import subprocess

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

import time
from datetime import datetime

from sqlite3 import OperationalError
import sqlite3

from o2tv.utils import get_url, encode
from o2tv.epg import get_epg_details

addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')
addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 
current_version = 2

def open_db():
    global db, version
    db = sqlite3.connect(addon_userdata_dir + "downloader.db", timeout = 20)
    db.execute('CREATE TABLE IF NOT EXISTS version (version INTEGER PRIMARY KEY)')
    db.execute('CREATE TABLE IF NOT EXISTS queue (epgId INTEGER PRIMARY KEY,title VARCHAR(255), startts INTEGER, endts INTEGER, status INTEGER, downloadts INTEGER, pvrProgramId INTEGER)')
    
    row = None
    for row in db.execute('SELECT version FROM version'):
      version = row[0]
    if not row:
        db.execute('INSERT INTO version VALUES (?)', [current_version])
        db.commit()     
        version = current_version
    if version != current_version:
      version = migrate_db(version)
    db.commit()     

def close_db():
    global db
    db.close()    

def migrate_db(version):
    global db
    if version == 0:
      version = 1
      db.execute('UPDATE version SET version = ?', str(version))
      db.commit()   
    if version == 1:
      version = 2
      try:
        db.execute('ALTER TABLE queue ADD COLUMN pvrProgramId INTEGER')
      except OperationalError:
        pass
      db.execute('UPDATE version SET version = ?', str(version))
      db.commit()           

    return version

def check_process():
    import os
    import signal
    osname = platform.system()
    if osname == "Linux":
      cmd = 'pgrep -f "ffmpeg.*SledovaniO2TV"'
      procs = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
      pids = procs.communicate()[0].split()
      for pid in pids:
        try:
          os.kill(int(pid),signal.SIGTERM)
        except OSError:
          pass
    if osname == "Windows":
      cmd = 'taskkill /f /im ffmpeg.exe'
      subprocess.call(cmd,stdin=None,stdout=None,stderr=None,shell=False,creationflags=0x08000000) 

def add_to_queue(epgId, pvrProgramId):
    open_db()
    event = get_epg_details([epgId], update_from_api = 1)
    row = None
    for row in db.execute('SELECT epgId FROM queue WHERE epgId = ?', [str(epgId)]):
      xbmcgui.Dialog().notification("Sledování O2TV","Pořad už je ve frontě ke stažení!", xbmcgui.NOTIFICATION_ERROR, 4000)
      close_db() 
      sys.exit()
    if row == None:
        db.execute('INSERT INTO queue VALUES (?, ?, ?, ?, ?, ?, ?)', [epgId, event["title"], event["startTime"], event["endTime"], 0, "null", pvrProgramId])
        db.commit()
        xbmcgui.Dialog().notification("Sledování O2TV","Pořad " + encode(event["title"]) + " byl přidaný do fronty ke stažení", xbmcgui.NOTIFICATION_INFO, 4000)           
    close_db() 

def remove_from_queue(epgId):
    open_db()
    row = None
    for row in db.execute('SELECT status, downloadts FROM queue WHERE epgId = ?', [str(epgId)]):
      if int(row[0]) == 0 and row[1] != "null":
        check_process()
      db.execute('DELETE FROM queue WHERE epgId = ?', [str(epgId)])
      db.commit()
      xbmcgui.Dialog().notification("Sledování O2TV","Pořad byl z fronty smazaný", xbmcgui.NOTIFICATION_INFO, 5000)           
    close_db()
    if row == None:
      xbmcgui.Dialog().notification("Sledování O2TV","Pořad nebyl ve frontě nalezený!", xbmcgui.NOTIFICATION_ERROR, 4000)
      sys.exit()
    xbmc.executebuiltin('Container.Refresh')

def list_downloads(label):
    _handle = int(sys.argv[1])
    xbmcplugin.setPluginCategory(_handle, label)
    open_db()
    for row in db.execute('SELECT epgId, title, startts, endts, status, downloadts FROM queue ORDER BY downloadts DESC'):
      epgId = int(row[0])
      title = row[1]
      startts = int(row[2])
      endts = int(row[3])
      status = int(row[4])
      if row[5] != "null":
        downloadts = int(row[5])
      else:
        downloadts = None  
      currentts = int(time.mktime(datetime.now().timetuple()))
      if status == 1:
        title = encode(title) + " (100%)"
      elif status == -1:  
        title = encode(title) + " (CHYBA)"
      elif downloadts == None:
        title = encode(title) + " (ČEKÁ)"
      else:
        pct = float(currentts-downloadts)/(endts-startts)*100
        title = encode(title) + " (" + str(int(pct)) + "%)"
      list_item = xbmcgui.ListItem(label=title)
      list_item.setProperty("IsPlayable", "false")
      list_item.setContentLookup(False)   
      list_item.addContextMenuItems([("Smazat z fronty", "RunPlugin(plugin://plugin.video.archivo2tv?action=remove_from_queue&epgId=" + str(epgId) + ")")])  
      url = get_url(action='list_downloads', label=label)
      xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)
    close_db()



