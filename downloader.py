# -*- coding: utf-8 -*-

import sys
import xbmc
import xbmcaddon
import xbmcgui
import subprocess
import time
from datetime import datetime
import platform

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from sqlite3 import OperationalError
import sqlite3

from o2tv.utils import plugin_id, check_settings, encode 
from o2tv.epg import get_epg_details
from o2tv.o2api import call_o2_api, get_header, get_header_unity
from o2tv.channels import Channels
from o2tv.session import Session
from o2tv.downloader import check_process

current_version = 2

def open_db():
    global db, version
    addon = xbmcaddon.Addon()
    addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 

    db = sqlite3.connect(addon_userdata_dir + 'downloader.db', timeout = 20)
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

def get_filename(title, startts):
    import unicodedata
    import re
    try:
        unicode('')
    except NameError:
        unicode = str
    starttime = datetime.fromtimestamp(startts).strftime('%Y-%m-%d_%H-%M')
    title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore')
    title = title.decode('utf-8')
    title = unicode(re.sub(r'[^\w\s-]', '', title).strip())
    title = unicode(re.sub(r'[-\s]+', '-', title))
    return title + '_' + starttime + '.ts'

def get_event(epgId, pvrProgramId, title):
    addon = xbmcaddon.Addon()
    err = 0
    url = ''
    post = {}
    channelKey = ''
    stream_type = 'HLS'
    current_ts = int(time.mktime(datetime.now().timetuple()))
    event = get_epg_details([epgId], update_from_api = 1)
    channels = Channels()
    channels_list = channels.get_channels_list('name', visible_filter = False)

    if event != None and current_ts < event['availableTo']:
        if event['startTime'] < current_ts:
            if event['endTime'] < current_ts:
                if pvrProgramId == None:
                    channelKey = channels_list[event['channel']]['channelKey']
                    session = Session()
                    header = get_header(session.get_service(channels_list[channelKey]['serviceid']))
                    subscription = session.get_service(channels_list[channelKey]['serviceid'])['subscription']
                    post = {'serviceType' : 'TIMESHIFT_TV', 'deviceType' : addon.getSetting('devicetype'), 'streamingProtocol' : stream_type,  'subscriptionCode' : subscription, 'channelKey' : encode(channelKey), 'fromTimestamp' : str(event['startTime']*1000), 'toTimestamp' : str(event['endTime']*1000 + (int(addon.getSetting('offset'))*60*1000)), 'id' : epgId, 'encryptionType' : 'NONE'}
                else:
                    session = Session()                    
                    for serviceid in session.services:
                        data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/recordings/', data = None, header = get_header_unity(session.services[serviceid]))
                        if 'err' in data:
                            xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s načtením nahrávek, zkuste to znovu', xbmcgui.NOTIFICATION_ERROR, 6000)
                        if 'result' in data and len(data['result']) > 0:
                            for program in data['result']:
                                if program['pvrProgramId'] == pvrProgramId:
                                    channelKey = program['program']['channelKey']
                    if len(channelKey) > 0:
                        channels_list = channels.get_channels_list(visible_filter = False)
                        header = get_header(session.get_service(channels_list[channelKey]['serviceid']))
                        subscription = session.get_service(channels_list[channelKey]['serviceid'])['subscription']
                        post = {'serviceType' : 'NPVR', 'deviceType' : addon.getSetting('devicetype'), 'streamingProtocol' : stream_type, 'subscriptionCode' : subscription, 'contentId' : pvrProgramId, 'encryptionType' : 'NONE'}                        
            else:
                xbmc.log('live')
                err = 1
        else:
            xbmc.log('future')
            err = 1
    else:
        xbmc.log('neni')
        err = 1

    if err == 1:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s stažením ' + encode(title), xbmcgui.NOTIFICATION_ERROR, 5000)
        current_ts = int(time.mktime(datetime.now().timetuple()))
        db.execute('UPDATE queue SET status = -1, downloadts = ? WHERE epgId = ?', [str(current_ts), str(epgId)])
        db.commit()
        return {}, ''
    else:
        if addon.getSetting('only_sd') == 'true':
            post.update({'resolution' : 'SD'})
        data = call_o2_api(url = 'https://app.o2tv.cz/sws/server/streaming/uris.json', data = post, header = header)
        if 'err' in data:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s stažením streamu', xbmcgui.NOTIFICATION_ERROR, 5000)
        url = ''
        if 'uris' in data and len(data['uris']) > 0 and 'uri' in data['uris'][0] and len(data['uris'][0]['uri']) > 0 :
            for uris in data['uris']:
                if addon.getSetting('only_sd') != 'true' and uris['resolution'] == 'HD':
                    url = uris['uri']
                if addon.getSetting('only_sd') == 'true' and uris['resolution'] == 'SD': 
                    url = uris['uri']
            if url == '':
                url = data['uris'][0]['uri']
        else:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s stažením streamu', xbmcgui.NOTIFICATION_ERROR, 5000)
        return event, url

def download_stream(epgId, url, event):
    addon = xbmcaddon.Addon()
    downloads_dir = addon.getSetting('downloads_dir')
    ffmpeg_bin = addon.getSetting('ffmpeg_bin')       
    xbmcgui.Dialog().notification('Sledování O2TV', 'Stahování ' + encode(event['title']) + ' začalo', xbmcgui.NOTIFICATION_INFO, 5000)       
    filename = get_filename(event['title'], event['startTime'])        
    close_db()
    open_db()
    current_ts = int(time.mktime(datetime.now().timetuple()))
    db.execute('UPDATE queue SET downloadts = ? WHERE epgId = ?', [current_ts, epgId])
    db.commit()
    close_db()
    ffmpeg_params = '-re -y -i ' + url + ' -f mpegts -mpegts_service_type digital_tv -metadata service_provider=SledovaniO2TV -c:v copy -c:a copy -loglevel error ' + downloads_dir + filename
    cmd = ffmpeg_bin + ' ' + ffmpeg_params
    osname = platform.system()
    xbmc.log(cmd)
    if osname == 'Windows':
        subprocess.call(cmd,stdin=None,stdout=None,stderr=None,shell=False,creationflags=0x08000000)
    else:
        subprocess.call(cmd,stdin=None,stdout=None,stderr=None,shell=True)
    xbmcgui.Dialog().notification('Sledování O2TV', 'Stahování ' + encode(event['title']) + ' bylo dokončeno', xbmcgui.NOTIFICATION_INFO, 5000)       
    open_db()
    current_ts = int(time.mktime(datetime.now().timetuple()))
    db.execute('UPDATE queue SET status = 1, downloadts = ? WHERE epgId = ?', [str(current_ts), str(epgId)])
    db.commit()

def read_queue():
    addon = xbmcaddon.Addon()
    while not xbmc.Monitor().abortRequested():
        if addon.getSetting('download_streams') == 'true':
            check_process()
            check_settings()

            xbmc.log('Kontroluji frontu pro stahování')
            open_db()
            try:
                row = None
                epgId = -1
                for row in db.execute('SELECT epgId, pvrProgramId, title FROM queue WHERE status = 0 ORDER BY startts LIMIT 1'):
                    epgId = int(row[0])
                    if row[1] == None or row[1] == 'null':
                        pvrProgramId = None 
                    else:
                        pvrProgramId = int(row[1])
                    title = row[2]
                if epgId > 0:
                    url = ''
                    event = {}
                    event, url = get_event(epgId, pvrProgramId, title)
                    if len(url) > 0:
                        xbmc.log('Začátek stahování: ' + str(epgId))
                        download_stream(epgId = epgId, url = url, event = event)
                        xbmc.log('Konec stahování: ' + str(epgId))
            except OperationalError:
                xbmc.log('DB not ready')
            open_db()
            deletets = int(time.mktime(datetime.now().timetuple()))-7*60*60*24
            try:
                db.execute('DELETE FROM queue WHERE downloadts < ?', [str(deletets)])
            except OperationalError:
                xbmc.log('DB not ready')
            close_db()
        time.sleep(60)
