# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
import json

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

try:
    from urllib import urlencode, quote_plus
except ImportError:
    from urllib.parse import urlencode, quote_plus

from datetime import datetime 
import time
import codecs

from o2tv.o2api import call_o2_api, get_header_unity
from o2tv.session import Session
from o2tv import o2api
from o2tv.utils import plugin_id, get_url, remove_diacritics, decode, encode
from o2tv import utils
from o2tv.channels import Channels 
from o2tv.epg import get_listitem_epg_details

_url = sys.argv[0]
_handle = int(sys.argv[1])

def load_categories():
    addon = xbmcaddon.Addon()
    addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 

    filename = addon_userdata_dir + 'categories.txt'
    not_found = 0
    try:
        with codecs.open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                data = json.loads(line[:-1])
    except IOError:
        not_found = 1          
  
    if not_found == 1 or (data and 'valid_to' in data and data['valid_to'] < int(time.time())):
        slugs = []
        invalid_slugs = []
        categories = {}
        subcategories = {}
        data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/lists/?name=catalogue', data = None, header = get_header_unity())
        if 'err' in data:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s načtením kategorií', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()  
        if 'result' in data and len(data['result']) > 0:
            for category in data['result']:
                if 'slug' in category and len(category['slug']) > 0:
                    slugs.append(category['slug'])

        for slug in slugs:
            data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/lists/slug/?slug=' + slug, data = None, header = get_header_unity())
            if 'err' in data:
              invalid_slugs.append(slug)
            else:   
              if 'name' in data and len(data['name']) > 0:
                categories.update({ slug : { 'name' : data['name'], 'type' : data['type'], 'filter' : data['filter'], 'dataSource' : data['dataSource'] }})
      
        for slug in invalid_slugs:
            slugs.remove(slug)

        for slug in slugs:
            if categories[slug]['type'] == 'list':
                data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/lists/?name=' + encode(categories[slug]['filter']['name']), data = None, header = get_header_unity())  
                if 'err' in data:
                    xbmcgui.Dialog().notification('Sledování O2TV','Problém s načtením kategorií', xbmcgui.NOTIFICATION_ERROR, 4000)
                    sys.exit()  
                if 'result' in data and len(data['result']) > 0:
                    cnt = 0
                    subcategory = {}
                    for category in data['result']:
                        subcategory.update({ cnt : {  'name' : category['name'], 'type' : category['type'], 'filter' : category['filter'], 'dataSource' : category['dataSource'] }})  
                        cnt = cnt + 1    
                subcategories.update({ categories[slug]['filter']['name'] : subcategory })    
        try:
            with codecs.open(filename, 'w', encoding='utf-8') as file:
                data = json.dumps({'categories' : categories, 'subcategories' : subcategories, 'slugs' : slugs, 'valid_to' : int(time.time()) + 60*60*24})
                file.write('%s\n' % data)
        except IOError:
            xbmc.log('Chyba uložení kategorií') 
    else:
        categories = data['categories']  
        subcategories = data['subcategories']  
        slugs = data['slugs']
    return categories, subcategories, slugs

def list_categories(label):
    xbmcplugin.setPluginCategory(_handle, label)
    categories, subcategories, slugs = load_categories() # pylint: disable=unused-variable 
    for slug in slugs:
        if categories[slug]['type'] == 'programs' and 'filter' in categories[slug]:
            filtr = encode(json.dumps({'genres' : categories[slug]['filter']['genres'], 'notGenres' : categories[slug]['filter']['notGenres'], 'containsAllGenres' : categories[slug]['filter']['containsAllGenres'], 'contentType' : categories[slug]['filter']['contentType']}))
            list_item = xbmcgui.ListItem(label=encode(categories[slug]['name']))
            url = get_url(action='list_category', category = encode(categories[slug]['filter']['contentType']), dataSource = categories[slug]['dataSource'], filtr = filtr, label = label + ' / ' + encode(categories[slug]['name']))  
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
        if categories[slug]['type'] == 'list' and 'filter' in categories[slug]:
            list_item = xbmcgui.ListItem(label=encode(categories[slug]['name']))
            url = get_url(action='list_subcategories', category = encode(categories[slug]['filter']['name']), dataSource = categories[slug]['dataSource'], label = label + ' / ' + encode(categories[slug]['name']))  
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)              

def list_subcategories(category, label):
    xbmcplugin.setPluginCategory(_handle, label)
    categories, subcategories, slugs = load_categories() # pylint: disable=unused-variable 
    subcategory_keys = {}
    for num in subcategories[category].keys():
        subcategory_keys.update({int(num) : num})
    for num in sorted(subcategory_keys.keys()):
        subcategory =subcategory_keys[num]
        if subcategories[category][subcategory]['type'] == 'programs' and encode(subcategories[category][subcategory]['filter']['contentType']) != 'živý přenos':
            filtr = encode(json.dumps({'genres' : subcategories[category][subcategory]['filter']['genres'], 'notGenres' : subcategories[category][subcategory]['filter']['notGenres'], 'containsAllGenres' : subcategories[category][subcategory]['filter']['containsAllGenres'], 'contentType' : subcategories[category][subcategory]['filter']['contentType']}))
            list_item = xbmcgui.ListItem(label=encode(subcategories[category][subcategory]['name']))
            url = get_url(action='list_category', category = encode(subcategories[category][subcategory]['name']), dataSource = subcategories[category][subcategory]['dataSource'], filtr = filtr, label = label + ' / ' + encode(subcategories[category][subcategory]['name']))  
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)              

def list_category(category, dataSource, filtr, page, label):
    xbmcplugin.setPluginCategory(_handle, label)
    addon = xbmcaddon.Addon()
    page_limit = int(addon.getSetting('category_pagesize'))
    filtr = json.loads(filtr)
    params = ''
    genres = []
    nongenres = []
    for genre in filtr['genres']:
        if len(genre) > 0:
            params = params + '&genres=' + quote_plus(encode(genre))
            genres.append(genre)
    for nongenre in filtr['notGenres']:
        if len(nongenre) > 0:
            params = params + '&notGenres=' + quote_plus(encode(nongenre))
            nongenres.append(nongenre)
    contentType = filtr['contentType']

    channels = Channels()
    channels_list = channels.get_channels_list()

    events = {}
    data = call_o2_api(url = 'https://api.o2tv.cz' + dataSource + '?containsAllGenres=' + str(filtr['containsAllGenres']).lower() + '&contentType=' + contentType + params + '&encodedChannels=' + channels.get_encoded_channels() + '&sort=-o2rating&grouped=true&isFuture=false&limit=500&offset=0', data = None, header = get_header_unity())
    if 'err' in data:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s načtením kategorie', xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit()        
    if 'result' in data and len(data['result']) > 0:
        num = 0
        cnt = 0
        characters = []
        for event in data['result']:
            cnt = cnt + 1
            if addon.getSetting('categories_sorting') == 'ratingu':
                events.update({ num : event})
                num = num + 1
            else:
                events.update({ remove_diacritics(event['name']) : event})
                if remove_diacritics(event['name'][:1].upper()) not in characters:
                    characters.append(remove_diacritics(event['name'][:1].upper()))
        if addon.getSetting('categories_sorting') == 'názvu' and page is None and page_limit > 0 and len(events) > page_limit:
            characters.sort()
            for character in characters:
                list_item = xbmcgui.ListItem(label=character)
                url = get_url(action='list_category', category = contentType, dataSource = dataSource, filtr = json.dumps(filtr), page = encode(character), label =  label + ' / ' + encode(character.decode('utf-8')))  
                xbmcplugin.addDirectoryItem(_handle, url, list_item, True)        
        else:  
            if addon.getSetting('categories_sorting') == 'ratingu' and page_limit > 0:
                if page is None:
                    page = 1
                startitem = (int(page)-1) * page_limit
            cnt = 0
            for key in sorted(events.keys()):
                if page is None or page_limit == 0 or (page is not None and addon.getSetting('categories_sorting') == 'názvu' and remove_diacritics(events[key]['name'][:1].upper()) == page.encode('utf-8')) or (page is not None and addon.getSetting('categories_sorting') == 'ratingu' and cnt >= startitem and cnt < startitem + page_limit):
                    event = events[key]
                    startts = event['start']/1000
                    start = datetime.fromtimestamp(event['start']/1000)
                    endts = event['end']/1000
                    end = datetime.fromtimestamp(event['end']/1000)
                    epgId = event['epgId']
                    isSeries = 0
                    if event['channelKey'] in channels_list: 
                        if 'seriesInfo' in event and 'seriesName' in event['seriesInfo'] and len(event['seriesInfo']['seriesName']) > 0:
                            isSeries = 1
                            event['name'] = event['seriesInfo']['seriesName']
                            if 'seasonNumber' in event['seriesInfo']:
                                event['name'] = event['name'] # + ' ['+ str(event['seriesInfo']['seasonNumber']) + ']'
                            list_item = xbmcgui.ListItem(label = event['name'] + ' (' + channels_list[event['channelKey']]['name'] + ')')
                        else:
                            list_item = xbmcgui.ListItem(label = event['name'] + ' (' + channels_list[event['channelKey']]['name'] + ' | ' + decode(utils.day_translation_short[start.strftime('%w')]) + ' ' + start.strftime('%d.%m %H:%M') + ' - ' + end.strftime('%H:%M') + ')')
                        cast = []
                        directors = []
                        genres = []
                        list_item.setInfo('video', {'mediatype':'movie'})
                        if 'images' in event and len(event['images']) > 0:
                            list_item.setArt({'poster': 'https://img1.o2tv.cz/' + event['images'][0]['cover'],'thumb': 'https://img1.o2tv.cz/' + event['images'][0]['cover'], 'icon': 'https://img1.o2tv.cz/' + event['images'][0]['cover']})
                        if 'longDescription' in event and len(event['longDescription']) > 0:
                            list_item.setInfo('video', {'plot': event['longDescription']})
                        if 'ratings' in event and len(event['ratings']) > 0:
                            for rating, rating_value in event['ratings'].items():
                                list_item.setRating(rating, int(rating_value)/10)
                        if 'castAndCrew' in event and len(event['castAndCrew']) > 0 and 'cast' in event['castAndCrew'] and len(event['castAndCrew']['cast']) > 0:
                            for person in event['castAndCrew']['cast']:      
                                cast.append(encode(person['name']))
                            list_item.setInfo('video', {'cast' : cast})  
                        if 'castAndCrew' in event and len(event['castAndCrew']) > 0 and 'directors' in event['castAndCrew'] and len(event['castAndCrew']['directors']) > 0:
                            for person in event['castAndCrew']['directors']:      
                                directors.append(encode(person['name']))
                            list_item.setInfo('video', {'director' : directors})  
                        if 'origin' in event and len(event['origin']) > 0:
                            if 'year' in event['origin'] and len(str(event['origin']['year'])) > 0:
                                list_item.setInfo('video', {'year': event['origin']['year']})
                            if 'country' in event['origin'] and len(event['origin']['country']) > 0:
                                list_item.setInfo('video', {'country': event['origin']['country']['name']})
                        if 'origName' in event and len(event['origName']) > 0:
                            list_item.setInfo('video', {'originaltitle': event['origName']})
                        if 'ext' in event and len(event['ext']) > 0 and 'imdbId' in event['ext'] and len(event['ext']['imdbId']) > 0:
                            list_item.setInfo('video', {'imdbnumber': event['ext']['imdbId']})
                        if 'genreInfo' in event and len(event['genreInfo']) > 0 and 'genres' in event['genreInfo'] and len(event['genreInfo']['genres']) > 0:
                            for genre in event['genreInfo']['genres']:      
                                genres.append(encode(genre['name']))
                            list_item.setInfo('video', {'genre' : genres})    
                        menus = [('Související pořady', 'Container.Update(plugin://' + plugin_id + '?action=list_related&epgId=' + str(epgId) + '&label=Související / ' + encode(event['name']) + ')'), 
                                ('Vysílání pořadu', 'Container.Update(plugin://' + plugin_id + '?action=list_same&epgId=' + str(epgId) + '&label=' + encode(event['name']) + ')')]
                        if addon.getSetting('download_streams') == 'true': 
                            menus.append(('Stáhnout', 'RunPlugin(plugin://' + plugin_id + '?action=add_to_queue&epgId=' + str(epgId) + ')'))      
                        list_item.addContextMenuItems(menus)       
                        if isSeries == 0:
                            list_item.setProperty('IsPlayable', 'true')
                            list_item.setContentLookup(False)          
                            url = get_url(action='play_archiv', channelKey = encode(event['channelKey']), start = startts, end = endts, epgId = epgId)
                            xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
                        else:
                            if 'seasonNumber' in event['seriesInfo'] and int(event['seriesInfo']['seasonNumber']) > 0:
                                season = int(event['seriesInfo']['seasonNumber'])
                            else:
                                season = -1  
                            list_item.setProperty('IsPlayable', 'false')
                            url = get_url(action='list_series', epgId = epgId, season = season, label = encode(event['name']))
                            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
                cnt = cnt + 1

            if page is not None and addon.getSetting('categories_sorting') == 'ratingu' and int(page) * page_limit <= cnt:
                list_item = xbmcgui.ListItem(label='další strana')
                url = get_url(action='list_category', category = contentType, dataSource = dataSource, filtr = json.dumps(filtr), page = int(page) + 1, label = label)  
                list_item.setProperty('IsPlayable', 'false')
                xbmcplugin.addDirectoryItem(_handle, url, list_item, True)     
    xbmcplugin.endOfDirectory(_handle)


def list_series(epgId, season, label):
    xbmcplugin.setPluginCategory(_handle, label)
    params = ''
    channels = Channels()
    channels_list = channels.get_channels_list()
    if int(season) > 0:
        params = params + '&seasonNumber=' + str(season)
    data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/programs/' + str(epgId) + '/episodes/?containsAllGenres=false&encodedChannels=' + channels.get_encoded_channels() + '&isFuture=false' + params, data = None, header = get_header_unity())
    if 'err' in data:
        xbmcgui.Dialog().notification('Sledování O2TV','Problém s načtením kategorie', xbmcgui.NOTIFICATION_ERROR, 4000)
        sys.exit()        
    if 'result' in data and len(data['result']) > 0:
        for event in data['result']:
            print(event['channelKey'])
            if event['channelKey'] in channels_list:
                startts = event['start']/1000
                start = datetime.fromtimestamp(event['start']/1000)
                endts = event['end']/1000
                end = datetime.fromtimestamp(event['end']/1000)
                epgId = event['epgId']
                list_item = xbmcgui.ListItem(label = event['name'] + ' (' + channels_list[event['channelKey']]['name'] + ' | ' + decode(utils.day_translation_short[start.strftime('%w')]) + ' ' + start.strftime('%d.%m %H:%M') + ' - ' + end.strftime('%H:%M') + ')')
                list_item.setInfo('video', {'mediatype':'movie'})
                list_item = get_listitem_epg_details(list_item, str(event['epgId']), channels_list[event['channelKey']]['logo'])
                list_item.setProperty('IsPlayable', 'true')
                list_item.setContentLookup(False)          
                url = get_url(action='play_archiv', channelKey = encode(event['channelKey']), start = startts, end = endts, epgId = epgId)
                xbmcplugin.addDirectoryItem(_handle, url, list_item, False)      
        xbmcplugin.endOfDirectory(_handle)
    
def list_related(epgId, label):
    xbmcplugin.setPluginCategory(_handle, label)
    addon = xbmcaddon.Addon(id = plugin_id)

    channels = Channels()
    channels_list = channels.get_channels_list()

    data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/programs/' + str(epgId) + '/related/?encodedChannels=' + channels.get_encoded_channels() + '&isFuture=false', data = None, header = get_header_unity())
    if 'err' in data:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s načtením kategorie', xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit()        
    if 'result' in data and len(data['result']) > 0:
        for event in data['result']:
            if event['channelKey'] in channels_list:
                startts = event['start']/1000
                start = datetime.fromtimestamp(event['start']/1000)
                endts = event['end']/1000
                end = datetime.fromtimestamp(event['end']/1000)
                epgId = event['epgId']
                list_item = xbmcgui.ListItem(label = event['name'] + ' (' + channels_list[event['channelKey']]['name'] + ' | ' + decode(utils.day_translation_short[start.strftime('%w')]) + ' ' + start.strftime('%d.%m %H:%M') + ' - ' + end.strftime('%H:%M') + ')')
                list_item.setInfo('video', {'mediatype':'movie'})
                list_item = get_listitem_epg_details(list_item, str(event['epgId']), channels_list[event['channelKey']]['logo'])
                list_item.setProperty('IsPlayable', 'true')
                list_item.setContentLookup(False)  
                if addon.getSetting('download_streams') == 'true': 
                    list_item.addContextMenuItems([('Stáhnout', 'RunPlugin(plugin://' + plugin_id + '?action=add_to_queue&epgId=' + str(epgId) + ')')])         
                url = get_url(action='play_archiv', channelKey = encode(event['channelKey']), start = startts, end = endts, epgId = epgId)
                xbmcplugin.addDirectoryItem(_handle, url, list_item, False)      
            xbmcplugin.endOfDirectory(_handle)
    else:  
        xbmcgui.Dialog().notification('Sledování O2TV','Žádné pořady nenalezeny', xbmcgui.NOTIFICATION_INFO, 4000)

def list_same(epgId, label):
    xbmcplugin.setPluginCategory(_handle, label)
    addon = xbmcaddon.Addon()

    data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/programs/' + str(epgId) + '/grouped/', data = None, header = get_header_unity())
    if 'err' in data:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s načtením kategorie', xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit()

    if 'result' in data and len(data['result']) > 0:
        channels = Channels()
        channels_list = channels.get_channels_list()
        cnt = 0
        for event in data['result']:
            if event['channel']['channelKey'] in channels_list:
                startts = event['program']['start']/1000
                start = datetime.fromtimestamp(event['program']['start']/1000)
                endts = event['program']['end']/1000
                end = datetime.fromtimestamp(event['program']['end']/1000)
                if endts < int(time.mktime(datetime.now().timetuple())):
                    cnt = cnt + 1
                    epgId = event['program']['epgId']
                    list_item = xbmcgui.ListItem(label = event['program']['name'] + ' (' + channels_list[event['channel']['channelKey']]['name'] + ' | ' + decode(utils.day_translation_short[start.strftime('%w')]) + ' ' + start.strftime('%d.%m %H:%M') + ' - ' + end.strftime('%H:%M') + ')')
                    list_item.setInfo('video', {'mediatype':'movie'})
                    list_item = get_listitem_epg_details(list_item, event['program']['epgId'], channels_list[event['channel']['channelKey']]['logo'])
                    list_item.setProperty('IsPlayable', 'true')
                    list_item.setContentLookup(False)      
                    if addon.getSetting('download_streams') == 'true': 
                        list_item.addContextMenuItems([('Stáhnout', 'RunPlugin(plugin://' + plugin_id + '?action=add_to_queue&epgId=' + str(epgId) + ')')])         
                    url = get_url(action='play_archiv', channelKey = encode(event['channel']['channelKey']), start = startts, end = endts, epgId = epgId)
                    xbmcplugin.addDirectoryItem(_handle, url, list_item, False)      
        if cnt == 0:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Žádné pořady nenalezeny', xbmcgui.NOTIFICATION_INFO, 5000)
        else:
            xbmcplugin.endOfDirectory(_handle)  
    else:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Žádné pořady nenalezeny', xbmcgui.NOTIFICATION_INFO, 5000)
