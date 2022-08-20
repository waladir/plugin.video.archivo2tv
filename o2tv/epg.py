# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

try:
    from urllib import quote
    from urllib2 import URLError, urlopen
except ImportError:
    from urllib.parse import quote
    from urllib.request import URLError, urlopen

from sqlite3 import OperationalError
import sqlite3
import json
import gzip
import os

from datetime import date, datetime, timedelta
import time

from o2tv.utils import plugin_id, get_url, encode
from o2tv.o2api import call_o2_api, get_header_unity
from o2tv.channels import Channels 
from o2tv.session import Session

current_version = 7

def open_db(check = 0):
    global db, version
    addon = xbmcaddon.Addon()
    addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 
    if not os.path.isdir(addon_userdata_dir):
        os.mkdir(addon_userdata_dir)
    db = sqlite3.connect(addon_userdata_dir + 'epg.db', timeout = 20)
    if check == 1:
        db.execute('CREATE TABLE IF NOT EXISTS version (version INTEGER PRIMARY KEY)')
        db.execute('CREATE TABLE IF NOT EXISTS epg (epgId INTEGER PRIMARY KEY, startTime INTEGER, endTime INTEGER, channel VARCHAR(255), title VARCHAR(255), availableTo INTEGER)')
        db.execute('CREATE TABLE IF NOT EXISTS epg_details (epgId INTEGER PRIMARY KEY, cover VARCHAR(255), description VARCHAR(255), ratings VARCHAR(255), cast VARCHAR(255), directors VARCHAR(255), year VARCHAR(255), country VARCHAR(255), original VARCHAR(255), genres VARCHAR(255), imdb VARCHAR(255), episodeNumber INTEGER, episodeName VARCHAR(255), seasonNumber INTEGER, episodesInSeason INTEGER, seasonName VARCHAR(255), seriesName VARCHAR(255), contentType VARCHAR(255))')
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
    if version == 4:
        version = 5
        db.execute('ALTER TABLE epg ADD COLUMN startTime INTEGER')
        db.execute('ALTER TABLE epg ADD COLUMN endTime INTEGER')
        db.execute('ALTER TABLE epg ADD COLUMN channel INTEGER')
        db.execute('ALTER TABLE epg ADD COLUMN title INTEGER')
        db.execute('UPDATE version SET version = ?', str(version))
        db.commit()       
    if version == 5:
        version = 6
        db.execute('DELETE FROM epg_details WHERE description=\'\' AND cover=\'\'')
        db.execute('UPDATE version SET version = ?', str(version))
        db.commit()
    if version == 6:
        version = 7
        try:
          db.execute('ALTER TABLE epg ADD COLUMN availableTo INTEGER')
        except OperationalError:
          pass
        try:
          db.execute('ALTER TABLE epg_details ADD COLUMN episodeNumber INTEGER')
        except OperationalError:
          pass
        try:
          db.execute('ALTER TABLE epg_details ADD COLUMN episodeName VARCHAR(255)')
        except OperationalError:
          pass
        try:
          db.execute('ALTER TABLE epg_details ADD COLUMN seasonNumber INTEGER')
        except OperationalError:
          pass
        try:
          db.execute('ALTER TABLE epg_details ADD COLUMN episodesInSeason INTEGER')
        except OperationalError:
          pass
        try:
          db.execute('ALTER TABLE epg_details ADD COLUMN seasonName VARCHAR(255)')
        except OperationalError:
          pass
        try:
          db.execute('ALTER TABLE epg_details ADD COLUMN seriesName VARCHAR(255)')
        except OperationalError:
          pass
        try:
          db.execute('ALTER TABLE epg_details ADD COLUMN contentType VARCHAR(255)')
        except OperationalError:
          pass
        for row in db.execute('SELECT epgId, ratings FROM epg_details'):
          epgId = row[0]
          ratings = json.loads(row[1])
          for rating in ratings:
            ratings[rating] = ratings[rating] * 10
          db.execute('UPDATE epg_details SET ratings = ? WHERE epgId = ? ', [json.dumps(ratings),str(epgId)])
        db.commit()    
        db.execute('UPDATE epg SET availableTo = startTime + (60*60*24*7)')
        db.commit()    
        db.execute('UPDATE version SET version = ?', str(version))
        db.commit()          
    return version

def load_cached_epg():
    global db
    addon = xbmcaddon.Addon()
    addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 

    open_db(check = 1)
    close_db()
    try:
        if addon.getSetting('uncompressed_cached_epg') == 'true':
            cached_epg_db_url = 'http://176.114.248.168:1080/epg_dump.db'
            cached_epg_db = urlopen(cached_epg_db_url, timeout = 10)
            content = cached_epg_db.read()
            with open(addon_userdata_dir + 'cached_epg.db', 'wb') as f:
                f.write(content)
                f.close() 
        else:
            cached_epg_db_url = 'http://176.114.248.168:1080/epg_dump.db.gz'
            cached_epg_db = urlopen(cached_epg_db_url, timeout = 10)
            content = cached_epg_db.read()
            with open(addon_userdata_dir + 'cached_epg.db.gz', 'wb') as f:
                f.write(content)
                f.close() 
            with gzip.open(addon_userdata_dir + 'cached_epg.db.gz', 'rb') as f:
                content = f.read()
                f.close()
            os.remove(addon_userdata_dir + 'cached_epg.db.gz')  
            with open(addon_userdata_dir + 'cached_epg.db', 'wb') as f_out:
                f_out.write(content)
                f_out.close()
        open_db()
        row = None
        for row in db.execute('SELECT version FROM version'):
            db_version = row[0]

        db.execute("ATTACH DATABASE '" + addon_userdata_dir + "cached_epg.db" + "' AS cdb")  
        row = None
        for row in db.execute('SELECT version FROM cdb.version'):
            cdb_version = row[0]

        if db_version == cdb_version:
            xbmc.log('Odstraňování pořadů, které chybí ve staženém EPG')  
            db.execute('DELETE FROM epg WHERE starttime > (SELECT min(starttime) FROM cdb.epg) AND epgId not in (SELECT epgId FROM cdb.epg)')
            db.commit()
            xbmc.log('Odstraňování pořadů s odlišnými daty')  
            db.execute('DELETE FROM epg WHERE epgId in (SELECT a.epgId FROM epg a, cdb.epg b WHERE (a.startTime<>b.startTime OR a.endTime<>b.endTime OR a.channel<>b.channel OR a.title<>b.title OR a.availableTo<>b.availableTo) AND a.epgId=b.epgId)')
            db.commit()
            xbmc.log('Synchronizace nových pořadů')  
            db.execute('INSERT INTO epg SELECT * FROM cdb.epg WHERE epgId NOT IN (SELECT epgId FROM epg)')
            db.commit()
            xbmc.log('Synchronizace nových detailů pořadů')  
            db.execute('INSERT INTO epg_details SELECT * FROM cdb.epg_details WHERE epgId NOT IN (SELECT epgId FROM epg_details)')
            db.commit()
            xbmc.log('Synchronizace dokončená')  
            close_db()  
            os.remove(addon_userdata_dir + 'cached_epg.db')  
            return 1 
        return 0
    except Exception as e:
        close_db()
        xbmc.log('Chyba importu cachovaného EPG: ' + e.__class__.__name__)
        return 0

def load_epg_details():
    global db
    events_detailed_data = {}
    try:
        url = 'https://api.o2tv.cz/unity/api/v1/epg/'
        data = call_o2_api(url = url, data = None, header = get_header_unity())
        if 'err' in data:
            xbmc.log('Chyba API O2 při načítání detailních dat pro EPG!')
            sys.exit()
        if 'result' in data and len(data['result']) > 0 and 'count' in data and data['count'] > 0:
            offset = 0
            step = 50
            cnt = data['count']
            for offset in range(0, cnt + step, step):
                url = 'https://api.o2tv.cz/unity/api/v1/epg/?offset=' + str(offset)
                data = call_o2_api(url = url, data = None, header = get_header_unity())
                if 'err' in data:
                    xbmc.log('Chyba API O2 při načítání detailních dat pro EPG!')
                    sys.exit()
                if 'result' in data and len(data['result']) > 0:
                    for event in data['result']:
                        cover = ''
                        description = ''
                        ratings = {}
                        cast = []
                        directors = []
                        year = ''
                        country = ''
                        original = ''
                        imdb = ''
                        genres = []
                        episodeNumber = -1
                        episodeName = ''
                        seasonNumber = -1
                        episodesInSeason = -1
                        seasonName = ''
                        seriesName = ''    
                        contentType = ''        
                        if 'images' in event and len(event['images']) > 0 and 'cover' in event['images'][0]:
                            cover = event['images'][0]['cover']
                        elif 'picture' in event and len(event['picture']) > 0:
                            cover = event['picture']
                        if 'longDescription' in event and len(event['longDescription']) > 0:
                            description = event['longDescription']
                        elif 'shortDescription' in event and len(event['shortDescription']) > 0:
                            description = event['shortDescription']
                        if 'ratings' in event and len(event['ratings']) > 0:
                            for rating, rating_value in event['ratings'].items():
                                ratings.update({ rating : int(rating_value)})
                        if 'castAndCrew' in event and len(event['castAndCrew']) > 0 and 'cast' in event['castAndCrew'] and len(event['castAndCrew']['cast']) > 0:
                            for person in event['castAndCrew']['cast']:      
                                cast.append(encode(person['name']))
                        if 'castAndCrew' in event and len(event['castAndCrew']) > 0 and 'directors' in event['castAndCrew'] and len(event['castAndCrew']['directors']) > 0:
                            for person in event['castAndCrew']['directors']:      
                                directors.append(encode(person['name']))
                        if 'origin' in event and len(event['origin']) > 0:
                            if 'year' in event['origin'] and len(str(event['origin']['year'])) > 0:
                                year = event['origin']['year']
                            if 'country' in event['origin'] and len(event['origin']['country']) > 0:
                                country = event['origin']['country']['name']
                        if 'origName' in event and len(event['origName']) > 0:
                            original = event['origName']
                        if 'ext' in event and len(event['ext']) > 0 and 'imdbId' in event['ext'] and len(event['ext']['imdbId']) > 0:
                            imdb = event['ext']['imdbId']
                        if 'genreInfo' in event and len(event['genreInfo']) > 0 and 'genres' in event['genreInfo'] and len(event['genreInfo']['genres']) > 0:
                            for genre in event['genreInfo']['genres']:      
                                genres.append(encode(genre['name']))
                        if 'seriesInfo' in event:
                            if 'episodeNumber' in event['seriesInfo'] and len(str(event['seriesInfo']['episodeNumber'])) > 0 and int(event['seriesInfo']['episodeNumber']) > 0:
                                episodeNumber = int(event['seriesInfo']['episodeNumber'])
                            if 'episodeName' in event['seriesInfo'] and len(event['seriesInfo']['episodeName']) > 0:
                                episodeName = event['seriesInfo']['episodeName']
                            if 'seasonNumber' in event['seriesInfo'] and len(str(event['seriesInfo']['seasonNumber'])) > 0 and int(event['seriesInfo']['seasonNumber']) > 0:
                                seasonNumber = int(event['seriesInfo']['seasonNumber'])
                            if 'episodesInSeason' in event['seriesInfo'] and len(str(event['seriesInfo']['episodesInSeason'])) > 0 and int(event['seriesInfo']['episodesInSeason']) > 0:
                                episodesInSeason = int(event['seriesInfo']['episodesInSeason'])
                            if 'seasonName' in event['seriesInfo'] and len(event['seriesInfo']['seasonName']) > 0:
                                seasonName = event['seriesInfo']['seasonName']
                            if 'seriesName' in event['seriesInfo'] and len(event['seriesInfo']['seriesName']) > 0:
                                seriesName = event['seriesInfo']['seriesName']    
                        if 'contentType' in event and len(event['contentType']) > 0:
                            contentType = event['contentType']                           
                        events_detailed_data.update({event['epgId'] : {'cover' : cover, 'description' : description, 'ratings' : ratings, 'cast' : cast, 'directors' : directors, 'year' : year, 'country' : country, 'original' : original, 'genres' : genres, 'imdb' : imdb, 'episodeNumber' : episodeNumber, 'episodeName' : episodeName, 'seasonNumber' : seasonNumber, 'episodesInSeason' : episodesInSeason, 'seasonName' : seasonName, 'seriesName' : seriesName, 'contentType' : contentType}})    
        cnt = 0
        open_db()
        for epgId in events_detailed_data.keys():
            row = None
            for row in db.execute('SELECT * FROM epg WHERE epgId = ?', [epgId]):
                event = row
            if row:
                row = None
                for row in db.execute('SELECT * FROM epg_details WHERE epgId = ?', [epgId]):
                    event = row
                if not row:
                    cnt = cnt + 1
                    db.execute('INSERT INTO epg_details VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (epgId, events_detailed_data[epgId]['cover'], events_detailed_data[epgId]['description'], json.dumps(events_detailed_data[epgId]['ratings']), json.dumps(events_detailed_data[epgId]['cast']), json.dumps(events_detailed_data[epgId]['directors']), events_detailed_data[epgId]['year'], events_detailed_data[epgId]['country'], events_detailed_data[epgId]['original'], json.dumps(events_detailed_data[epgId]['genres']), events_detailed_data[epgId]['imdb'], events_detailed_data[epgId]['episodeNumber'], events_detailed_data[epgId]['episodeName'], events_detailed_data[epgId]['seasonNumber'], events_detailed_data[epgId]['episodesInSeason'], events_detailed_data[epgId]['seasonName'], events_detailed_data[epgId]['seriesName'], events_detailed_data[epgId]['contentType']))      
            db.commit()
        close_db()
        xbmc.log('INSERTED epg_details: ' + str(cnt))
    except URLError:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba API O2 při načítání EPG!', xbmcgui.NOTIFICATION_WARNING, 5000)
        xbmc.log('Error getting EPG data')
        pass

def load_epg_details_inc():
    limit = 250
    limit_ts = int(time.mktime(datetime.now().timetuple()))
    xbmc.log('start incremental loading epg details')
    open_db()
    epgIds = []
    for row in db.execute('SELECT epgId FROM epg WHERE startTime < ? AND epgId not in (SELECT epgId FROM epg_details) LIMIT ' + str(limit),[str(limit_ts),]):    
        epgIds.append(row[0])
    close_db()
    if len(epgIds) > 0:
        get_epg_details(epgIds)
    xbmc.log('total epgIds: ' + str(len(epgIds)))
    xbmc.log('end incremental loading epg details')

def load_epg_ts(channelKeys, from_ts, to_ts):
    global db
    open_db(check = 1)
    close_db()
    events_data = {}
    params = ''
    for channelKey in channelKeys:
        params = params + ('&channelKey=' + quote(encode(channelKey)))
    try: 
        url = 'https://api.o2tv.cz/unity/api/v1/epg/depr/?forceLimit=true&limit=500' + params + '&from=' + str(from_ts*1000) + '&to=' + str(to_ts*1000) 
        print(url)
        data = call_o2_api(url = url, data = None, header = get_header_unity())
        if 'err' in data:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba API O2 při načítání EPG!', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()
        if 'epg' in data and len(data['epg']) > 0 and 'items' in data['epg'] and len(data['epg']['items']) > 0:
            for channel in data['epg']['items']:
                for event in channel['programs']:
                    events_data.update({event['epgId'] : {'startTime' : int(event['start']/1000), 'endTime' : int(event['end']/1000), 'channel' : channel['channel']['name'], 'title' : event['name'], 'availableTo' : int(event['availableTo']/1000)}})
        cnt = 0
        open_db()
        for epgId in events_data.keys():
            row = None
            for row in db.execute('SELECT * FROM epg WHERE epgId = ?', [epgId]):
                event = row
                startTime = int(row[1])
                endTime = int(row[2])
                channel = row[3]
                title = row[4]
                availableTo = int(row[5])
                if startTime != events_data[epgId]['startTime'] or endTime != events_data[epgId]['endTime'] or channel != events_data[epgId]['channel'] or title != events_data[epgId]['title'] or availableTo != events_data[epgId]['availableTo']:
                    db.execute('UPDATE epg SET startTime = ?, endTime = ?, channel = ?, title = ?, availableTo = ? WHERE epgId = ?', (events_data[epgId]['startTime'], events_data[epgId]['endTime'], events_data[epgId]['channel'], events_data[epgId]['title'], events_data[epgId]['availableTo'], epgId))
            if not row:
                cnt = cnt + 1
                db.execute('INSERT INTO epg VALUES(?, ?, ?, ?, ?, ?)', (epgId, events_data[epgId]['startTime'], events_data[epgId]['endTime'], events_data[epgId]['channel'], events_data[epgId]['title'], events_data[epgId]['availableTo']))      
        db.commit()
        close_db()
        xbmc.log('INSERTED epg: ' + str(cnt))
    except URLError:
        xbmc.log('Error getting EPG data')
        xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba API O2 při načítání EPG!', xbmcgui.NOTIFICATION_WARNING, 5000)
        pass

def load_epg_all():
    addon = xbmcaddon.Addon()
    channels = Channels()
    channels_list = channels.get_channels_list('number')
    channelKeys = []
    for number in sorted(channels_list.keys()):
        channelKeys.append(channels_list[number]['channelKey'])
    min_ts = 0
    if addon.getSetting('info_enabled') == 'true':
        xbmcgui.Dialog().notification('Sledování O2TV', 'Začalo stahování dat EPG', xbmcgui.NOTIFICATION_INFO, 5000)  
    cached_epg = 0
    if addon.getSetting('cached_epg') == 'true':
        cached_epg = load_cached_epg()
    if  cached_epg == 0:
        if addon.getSetting('info_enabled') == 'true' and addon.getSetting('cached_epg') == 'true':
            xbmcgui.Dialog().notification('Sledování O2TV', 'Došlo k chybě s EPG keší, stahuji z O2', xbmcgui.NOTIFICATION_INFO, 5000)  
        today_date = datetime.today() 
        today_start_ts = int(time.mktime(datetime(today_date.year, today_date.month, today_date.day) .timetuple()))
        today_end_ts = today_start_ts + 60*60*24 -1
        for day in range(-8,8,1):
            from_ts = today_start_ts + int(day)*60*60*24
            to_ts = from_ts+(24*60*60)-1
            if to_ts > min_ts:
                if from_ts < min_ts:
                    from_ts = min_ts
                load_epg_ts(channelKeys, from_ts, to_ts)

        if addon.getSetting('info_enabled') == 'true':
            xbmcgui.Dialog().notification('Sledování O2TV', 'Začalo stahování detailních dat EPG', xbmcgui.NOTIFICATION_INFO, 5000)  
        load_epg_details()  
    if addon.getSetting('info_enabled') == 'true':
        xbmcgui.Dialog().notification('Sledování O2TV', 'Stahování dat EPG dokončeno', xbmcgui.NOTIFICATION_INFO, 5000)  

    err = 0
    try:
        rec_epgIds = get_recordings_epgIds()
        for epgId in rec_epgIds:
            if epgId == 'err':
                err = 1
        if err == 0:
            in_epgId = ''
            if len(rec_epgIds) > 0:
                in_epgId = 'epgId not in (' + ','.join(rec_epgIds) + ') and '
            now_ts = int(time.mktime(datetime.now().timetuple()))
            open_db()
            db.execute('DELETE FROM epg WHERE ' + in_epgId + 'availableTo < ?', [now_ts])
            db.execute('DELETE FROM epg_details WHERE epgId NOT IN (SELECT epgId FROM epg)')
            db.commit()
            db.execute('VACUUM')
            close_db()
    except URLError:
        pass

def get_epg_details(epgIds, update_from_api = 0):
    global db
    open_db()
    for epgId in epgIds:
        row = None
        epg = 0
        startTime = -1
        endTime = -1
        channel = 'N/A'
        title = 'N/A'
        availableTo = -1
        for row in db.execute('SELECT startTime, endTime, channel, title, availableTo FROM epg WHERE epgId = ?', [epgId]):
            startTime = int(row[0])
            endTime = int(row[1])
            channel = row[2]
            title = row[3]
            availableTo = int(row[4])
            epg = 1
        row = None
        for row in db.execute('SELECT * FROM epg_details WHERE epgId = ?', [epgId]):
            epgId = row[0]
            cover = row[1]
            description = row[2]
            ratings = json.loads(row[3])
            cast = json.loads(row[4])
            directors = json.loads(row[5])
            year = row[6]
            country = row[7]
            original = row[8]
            genres = json.loads(row[9])
            imdb = row[10]
            episodeNumber = row[11]
            episodeName = row[12]
            seasonNumber = row[13]
            episodesInSeason = row[14]
            seasonName = row[15]
            seriesName = row[16] 
            contentType = row[17]
        if not row:
            cover = ''
            description = ''
            ratings = {}
            cast = []
            directors = []
            year = ''
            country = ''
            original = ''
            imdb = ''
            genres = []
            episodeNumber = -1
            episodeName = ''
            seasonNumber = -1
            episodesInSeason = -1
            seasonName = ''
            seriesName = ''
            contentType = ''

            if update_from_api == 1:
                  data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/programs/' + str(epgId) + '/', data = None, header = get_header_unity())
                  if not 'err' in data:
                      if epg == 0:
                          channels = Channels()
                          channels_list = channels.get_channels_list()
                          channel = channels_list[data['channelKey']]
                          startTime = int(data['start'])/1000
                          endTime = int(data['end'])/1000
                          title = data['name']
                          availableTo = data['availableTo']
                          db.execute('INSERT INTO epg VALUES(?, ?, ?, ?, ?, ?)', (epgId, startTime, endTime, channel, title, availableTo))      
                          db.commit
                      if 'images' in data and len(data['images']) > 0 and 'cover' in data['images'][0]:
                          cover = data['images'][0]['cover']
                      elif 'picture' in data and len(data['picture']) > 0:
                          cover = data['picture']
                      if 'longDescription' in data and len(data['longDescription']) > 0:
                          description = data['longDescription']
                      elif 'shortDescription' in data and len(data['shortDescription']) > 0:
                          description = data['shortDescription']
                      if 'ratings' in data and len(data['ratings']) > 0:
                          for rating, rating_value in data['ratings'].items():
                              ratings.update({ rating : int(rating_value)})
                      if 'castAndCrew' in data and len(data['castAndCrew']) > 0 and 'cast' in data['castAndCrew'] and len(data['castAndCrew']['cast']) > 0:
                          for person in data['castAndCrew']['cast']:      
                              cast.append(person['name'])
                      if 'castAndCrew' in data and len(data['castAndCrew']) > 0 and 'directors' in data['castAndCrew'] and len(data['castAndCrew']['directors']) > 0:
                          for person in data['castAndCrew']['directors']:      
                              directors.append(person['name'])
                      if 'origin' in data and len(data['origin']) > 0:
                          if 'year' in data['origin'] and len(str(data['origin']['year'])) > 0:
                              year = data['origin']['year']
                          if 'country' in data['origin'] and len(data['origin']['country']) > 0:
                              country = data['origin']['country']['name']
                      if 'origName' in data and len(data['origName']) > 0:
                          original = data['origName']
                      if 'ext' in data and len(data['ext']) > 0 and 'imdbId' in data['ext'] and len(data['ext']['imdbId']) > 0:
                          imdb = data['ext']['imdbId']
                      if 'genreInfo' in data and len(data['genreInfo']) > 0 and 'genres' in data['genreInfo'] and len(data['genreInfo']['genres']) > 0:
                          for genre in data['genreInfo']['genres']:      
                              genres.append(genre['name'])
                      if 'seriesInfo' in data:
                          if 'episodeNumber' in data['seriesInfo'] and len(str(data['seriesInfo']['episodeNumber'])) > 0 and int(data['seriesInfo']['episodeNumber']) > 0:
                              episodeNumber = int(data['seriesInfo']['episodeNumber'])
                          if 'episodeName' in data['seriesInfo'] and len(data['seriesInfo']['episodeName']) > 0:
                              episodeName = data['seriesInfo']['episodeName']
                          if 'seasonNumber' in data['seriesInfo'] and len(str(data['seriesInfo']['seasonNumber'])) > 0 and int(data['seriesInfo']['seasonNumber']) > 0:
                              seasonNumber = int(data['seriesInfo']['seasonNumber'])
                          if 'episodesInSeason' in data['seriesInfo'] and len(str(data['seriesInfo']['episodesInSeason'])) > 0 and int(data['seriesInfo']['episodesInSeason']) > 0:
                              episodesInSeason = int(data['seriesInfo']['episodesInSeason'])
                          if 'seasonName' in data['seriesInfo'] and len(data['seriesInfo']['seasonName']) > 0:
                              seasonName = data['seriesInfo']['seasonName']
                          if 'seriesName' in data['seriesInfo'] and len(data['seriesInfo']['seriesName']) > 0:
                              seriesName = data['seriesInfo']['seriesName']
                      if 'contentType' in data and len(data['contentType']) > 0:
                          contentType = data['contentType']
                  db.execute('INSERT INTO epg_details VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (epgId, cover, description, json.dumps(ratings), json.dumps(cast), json.dumps(directors), year, country, original, json.dumps(genres), imdb, episodeNumber, episodeName, seasonNumber, episodesInSeason, seasonName, seriesName, contentType))      
    db.commit()
    close_db()
    event = { 'epgId' : epgId, 'startTime' : startTime, 'endTime' : endTime, 'channel' : channel, 'title' : title, 'availableTo' : availableTo, 'cover' : cover, 'description' : description, 'ratings' : ratings, 'cast' : cast, 'directors' : directors, 'year' : year, 'country' : country, 'original' : original, 'genres' : genres, 'imdb' : imdb, 'episodeNumber' : episodeNumber, 'episodeName' : episodeName, 'seasonNumber' : seasonNumber, 'episodesInSeason' : episodesInSeason, 'seasonName' : seasonName, 'seriesName' : seriesName }
    return event

def get_listitem_epg_details(list_item, epgId, img, update_from_api = 0):
    if epgId == None or epgId == 'None':
        list_item.setInfo('video', {'mediatype':'movie'})
        return list_item
    event = get_epg_details([epgId], update_from_api = update_from_api)
    cast = []
    directors = []
    genres = []
    list_item.setInfo('video', {'mediatype':'movie'})
    if 'cover' in event and len(event['cover']) > 0:
        list_item.setArt({'poster': 'https://img1.o2tv.cz/' + event['cover'],'thumb': 'https://img1.o2tv.cz/' + event['cover'], 'icon': 'https://img1.o2tv.cz/' + event['cover']})
    else:
        list_item.setArt({'thumb': img, 'icon': img})    
    if 'description' in event and len(event['description']) > 0:
        list_item.setInfo('video', {'plot': event['description']})
    if 'ratings' in event and len(event['ratings']) > 0:
        for rating, rating_value in event['ratings'].items():
            list_item.setRating(rating, round(float(rating_value)/10,1))
    if 'cast' in event and len(event['cast']) > 0:
        for person in event['cast']:      
            cast.append(encode(person))
        list_item.setInfo('video', {'cast' : cast})  
    if 'directors' in event and len(event['directors']) > 0:
        for person in event['directors']:      
            directors.append(encode(person))
        list_item.setInfo('video', {'director' : directors})  
    if 'year' in event and len(str(event['year'])) > 0:
        list_item.setInfo('video', {'year': int(event['year'])})
    if 'country' in event and len(event['country']) > 0:
        list_item.setInfo('video', {'country': event['country']})
    if 'original' in event and len(event['original']) > 0:
        list_item.setInfo('video', {'originaltitle': event['original']})
    if 'imdb' in event and len(event['imdb']) > 0:
        list_item.setInfo('video', {'imdbnumber': event['imdb']})
    if 'genres' in event and len(event['genres']) > 0:
        for genre in event['genres']:      
          genres.append(encode(genre))
        list_item.setInfo('video', {'genre' : genres})    
    if 'episodeNumber' in event and event['episodeNumber'] != None and int(event['episodeNumber']) > 0:
     # list_item.setInfo('video', {'mediatype': 'episode', 'episode' : int(event['episodeNumber'])}) 
        list_item.setInfo('video', {'mediatype': 'episode'}) 
    if 'episodeName' in event and event['episodeName'] != None and len(event['episodeName']) > 0:
        list_item.setInfo('video', {'title' : event['episodeName']})  
    if 'seriesName' in event and event['seriesName'] != None and len(event['seriesName']) > 0:
        list_item.setInfo('video', {'tvshowtitle' : event['seriesName']})  
    # if 'seasonNumber' in event and event['seasonNumber'] != None and int(event['seasonNumber']) > 0:
    #   list_item.setInfo('video', {'season' : int(event['seasonNumber'])})  
    
    return list_item

def get_epg_all():
    events_data = {}
    events_detailed_data = {}
    
    limit = 8
    limit_ts = int(time.mktime(datetime.now().time.tuple())) - 60*60*24*limit

    open_db()
    row = None
    for row in db.execute('SELECT * FROM epg WHERE startTime >= ? AND availableTo >= ?',[str(limit_ts), int(time.mktime(datetime.now().timetuple()))]):
        epgId = int(row[0])
        startTime = int(row[1])
        endTime = int(row[2])    
        channel = row[3]
        title = row[4]
        if channel not in events_data:
          events_data[channel] = { startTime : {'epgId' : epgId, 'startTime' : startTime, 'endTime' : endTime, 'channel' : channel, 'title' : title }}
        else:  
          events_data[channel].update({ startTime : {'epgId' : epgId, 'startTime' : startTime, 'endTime' : endTime, 'channel' : channel, 'title' : title }})

    for row in db.execute('SELECT * FROM epg_details'):
        epgId = int(row[0])
        cover = row[1]
        description = row[2]
        ratings = json.loads(row[3])
        cast = json.loads(row[4])
        directors = json.loads(row[5])
        year = row[6]
        country = row[7]
        original = row[8]
        genres = json.loads(row[9])
        imdb = row[10]
        episodeNumber = row[11]
        episodeName = row[12]
        seasonNumber = row[13]
        episodesInSeason = row[14]
        seasonName = row[15]
        seriesName = row[16]     
        contentType = row[17]  
        events_detailed_data.update({ epgId : {'name' : title, 'desc' : description, 'icon' : 'https://img1.o2tv.cz' + cover, 'cast' : cast, 'directors' : directors, 'year' : year, 'country' : country, 'genres' : genres, 'ratings' : ratings, 'imdb' : imdb, 'original' : original, 'episodeNumber' : episodeNumber, 'episodeName' : episodeName, 'seasonNumber' : seasonNumber, 'episodesInSeason' : episodesInSeason, 'seasonName' : seasonName, 'seriesName' : seriesName, 'contentType' : contentType }})
    close_db()
    return events_data, events_detailed_data

def get_epg_ts(channelKey, from_ts, to_ts, min_limit):
    events_data = {}
    channels = Channels()
    channels_list = channels.get_channels_list()
    channelName = channels_list[channelKey]['name']

    open_db()
    row = None
    cnt = 0
    for row in db.execute('SELECT count(1) FROM epg WHERE startTime >= ? AND startTime <=? AND channel = ? AND availableTo > ?', [from_ts, to_ts, channelName, int(time.mktime(datetime.now().timetuple()))]):
        cnt = row[0]
    if cnt < min_limit:
        channelKeys = [channelKey]
        load_epg_ts(channelKeys, from_ts, to_ts)  
        open_db()
    for row in db.execute('SELECT epgId, startTime, endTime, title FROM epg WHERE startTime >= ? AND startTime <=? AND channel = ?  AND availableTo > ?', [from_ts, to_ts, channelName, int(time.mktime(datetime.now().timetuple()))]):
        epgId = int(row[0])
        startTime = int(row[1])
        endTime = int(row[2])    
        title = row[3]
        start = datetime.fromtimestamp(startTime)
        end = datetime.fromtimestamp(endTime)
        events_data.update({ startTime : { 'epgId' : epgId, 'startts' : startTime, 'endts' : endTime, 'start' : start , 'end' : end, 'title' : title}})
    close_db()
    return events_data

def get_epg_live(min_limit):
    events_data = {}
    current_ts = int(time.mktime(datetime.now().timetuple()))
    open_db()
    row = None    
    cnt = 0    
    for row in db.execute('SELECT count(1) FROM epg WHERE startTime <= ? AND endTime >=?', [current_ts, current_ts]):
        cnt = row[0]
    if cnt+3 < min_limit:
        channels = Channels()
        channels_list = channels.get_channels_list()
        load_epg_ts(channels_list.keys(), current_ts-60*60*3, current_ts+60*60*3)  
        open_db()
    for row in db.execute('SELECT channel, epgId, startTime, endTime, title FROM epg WHERE startTime <= ? AND endTime >=?', [current_ts, current_ts]):
        channel = row[0]
        epgId = int(row[1])
        startTime = int(row[2])
        endTime = int(row[3])    
        title = row[4]
        start = datetime.fromtimestamp(startTime)
        end = datetime.fromtimestamp(endTime)
        events_data.update({ channel : { 'epgId' : epgId, 'start' : start, 'end' : end, 'title' : title }})
    close_db()
    return events_data

def get_epgId_iptvsc(channelName, channelKey, starttime):
    open_db()
    result = { 'epgId' : -1}    
    for row in db.execute('SELECT epgId, title, startTime, endTime FROM epg WHERE channel = ? AND startTime = ?', [channelName, starttime]):
        epgId = int(row[0])
        title = row[1]
        startts = int(row[2])
        endts = int(row[3])
        result = { 'epgId' : epgId, 'title' : title, 'start' : startts, 'end' : endts}
    close_db()
    if result['epgId'] == -1:
        load_epg_ts([channelKey], int(starttime), int(starttime))
        open_db()
        for row in db.execute('SELECT epgId, title, startTime, endTime FROM epg WHERE channel = ? AND startTime = ?', [channelName, starttime]):
            epgId = int(row[0])
            title = row[1]
            startts = int(row[2])
            endts = int(row[3])
            result = { 'epgId' : epgId, 'title' : title, 'start' : startts, 'end' : endts}
        close_db()
    return result  


def get_recordings_epgIds():
    epgIds = []
    session = Session()
    for serviceid in session.get_services():
        data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/recordings/', data = None, header = get_header_unity(session.services[serviceid]))
        if 'err' in data:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s načtením nahrávek, zkuste to znovu', xbmcgui.NOTIFICATION_ERROR, 5000)
        if 'result' in data and len(data['result']) > 0:
            for program in data['result']:
               epgIds.append(str(program['program']['epgId']))
    return epgIds
