# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from urllib2 import urlopen, Request
    from urllib import urlencode, quote
except ImportError:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode, quote    

from datetime import datetime 
import time

from o2tv.o2api import call_o2_api, get_header, get_header_unity
from o2tv import o2api
from o2tv.session import Session
from o2tv.epg import get_listitem_epg_details, get_epg_live, get_epg_details, get_epgId_iptvsc
from o2tv.channels import Channels 
from o2tv.utils import remove_diacritics, decode, encode

_url = sys.argv[0]
if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def play_catchup(channelKey, start_ts):
    event = get_epgId_iptvsc(channelKey, start_ts)
    if event['epgId'] == -1 or event['end'] > int(time.mktime(datetime.now().timetuple()))-10:
        if event['epgId'] == -1:
            play_video(type = 'live_iptv', channelKey = channelKey, start = None, end = None, epgId = event['epgId'], title = None)
        else:
            play_video(type = 'live_iptv', channelKey = channelKey, start = event['start'], end = None, epgId = event['epgId'], title = None)
    else:
        play_video(type = 'archiv', channelKey = channelKey, start = event['start'], end = event['end'], epgId = event['epgId'], title = None)

def play_video(type, channelKey, start, end, epgId, title):
    addon = xbmcaddon.Addon()
    session = Session()
    channelKey = decode(channelKey)
    channels = Channels()
    channels_list = channels.get_channels_list(visible_filter = False)
    header_unity = get_header_unity(session.get_service(channels_list[channelKey]['serviceid']))
    header = get_header(session.get_service(channels_list[channelKey]['serviceid']))

    if 'serviceid' not in channels_list[channelKey] or len(channels_list[channelKey]['serviceid']) == 0:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Pravděpodobně neaktivní kanál. Zkuste reset kanálů.', xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit()  

    subscription = session.get_service(channels_list[channelKey]['serviceid'])['subscription']

    if addon.getSetting('select_resolution') == 'true' and addon.getSetting('stream_type') == 'HLS' and addon.getSetting('only_sd') != 'true':
        resolution = xbmcgui.Dialog().select('Rozlišení', ['HD', 'SD' ], preselect = 0)
    else:
        resolution = -1  

    if addon.getSetting('stream_type') == 'MPEG-DASH':
        stream_type = 'DASH'
    else:
        stream_type = 'HLS'

    force_mpeg_dash = 0
    if addon.getSetting('stream_type') == 'HLS' and xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)') and (type == 'live_iptv' or type == 'live_iptv_epg') and addon.getSetting('force_mpeg_dash') == 'true': 
        stream_type = 'DASH'
        force_mpeg_dash = 1

    if type == 'live' or type == 'live_iptv' or type == 'live_iptv_epg':
        startts = 0
        channels_details = get_epg_live(len(channels_list.keys()))      
        if channels_list[channelKey]['name'] in channels_details:
            without_details = 0
        else:
            without_details = 1  

        if channelKey in channels_list and without_details == 0:
            data = channels_details[channels_list[channelKey]['name']]
            start = data['start']
            startts = int(time.mktime(start.timetuple()))
            end = data['end']
            epgId = str(data['epgId'])

    if addon.getSetting('stream_type') == 'MPEG-DASH-web':
        if type == 'archiv' or type == 'archiv_iptv':
            data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/programs/' + str(epgId) +'/playlist/', data = None, header = header_unity)
        if type == 'live' or type == 'live_iptv' or type == 'live_iptv_epg':
            data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/channels/playlist/?channelKey=' + quote(channelKey), data = None, header = header_unity)
        if type == 'recording':
            data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/recordings/' + str(epgId) +'/playlist/', data = None, header = header_unity)
        if 'err' in data:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s přehráním streamu', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()  
        if 'playlist' in data and len(data['playlist']) > 0 and 'streamUrls' in data['playlist'][0] and 'main' in data['playlist'][0]['streamUrls'] and len(data['playlist'][0]['streamUrls']['main']) > 0:
            if 'timeshift' in data['playlist'][0]['streamUrls']:
                url = data['playlist'][0]['streamUrls']['timeshift']
            else:
                url = data['playlist'][0]['streamUrls']['main']
            request = Request(url = url , data = None, headers = header)
            response = urlopen(request)
            url = response.geturl()
        else:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s přehráním streamu', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()  
    else:
        if type == 'archiv' or type == 'archiv_iptv':
            start = int(float(start) * 1000)
            end = int(float(end) * 1000)
            post = {'serviceType' : 'TIMESHIFT_TV', 'deviceType' : addon.getSetting('devicetype'), 'streamingProtocol' : stream_type,  'subscriptionCode' : subscription, 'channelKey' : encode(channelKey), 'fromTimestamp' : str(start), 'toTimestamp' : str(end + (int(addon.getSetting('offset'))*60*1000)), 'id' : epgId, 'encryptionType' : 'NONE'}
        if type == 'live' or type == 'live_iptv' or type == 'live_iptv_epg':
            if (addon.getSetting('stream_type') == 'MPEG-DASH' or force_mpeg_dash == 1) and startts > 0 and addon.getSetting('startover') == 'true':
                startts = int(float(startts) * 1000 - 300000)
                post = {'serviceType' : 'STARTOVER_TV', 'deviceType' : addon.getSetting('devicetype'), 'streamingProtocol' : stream_type, 'subscriptionCode' : subscription, 'channelKey' : encode(channelKey), 'fromTimestamp' : startts, 'encryptionType' : 'NONE'}
            else:
                post = {'serviceType' : 'LIVE_TV', 'deviceType' : addon.getSetting('devicetype'), 'streamingProtocol' : stream_type, 'subscriptionCode' : subscription, 'channelKey' : encode(channelKey), 'encryptionType' : 'NONE'}
        if type == 'recording':
            post = {'serviceType' : 'NPVR', 'deviceType' : addon.getSetting('devicetype'), 'streamingProtocol' : stream_type, 'subscriptionCode' : subscription, 'contentId' : epgId, 'encryptionType' : 'NONE'}
        if addon.getSetting('stream_type') != 'MPEG-DASH' and force_mpeg_dash == 0 and (addon.getSetting('only_sd') == 'true' or resolution == 1):
            post.update({'resolution' : 'SD'})
        data = call_o2_api(url = 'https://app.o2tv.cz/sws/server/streaming/uris.json', data = post, header = header)
        if 'err' in data:
            if data['err'] == 'Not Found':
                post = {'serviceType' : 'LIVE_TV', 'deviceType' : addon.getSetting('devicetype'), 'streamingProtocol' : stream_type, 'subscriptionCode' : subscription, 'channelKey' : encode(channelKey), 'encryptionType' : 'NONE'}
                data = call_o2_api(url = 'https://app.o2tv.cz/sws/server/streaming/uris.json', data = post, header = header)
                if 'err' in data:
                    xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s přehráním streamu', xbmcgui.NOTIFICATION_ERROR, 5000)
                    sys.exit()
            else:
                xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s přehráním streamu', xbmcgui.NOTIFICATION_ERROR, 5000)
                sys.exit()
        url = ''
        if 'uris' in data and len(data['uris']) > 0 and 'uri' in data['uris'][0] and len(data['uris'][0]['uri']) > 0 :
            for uris in data['uris']:
                print(uris)
                if addon.getSetting('only_sd') != 'true' and resolution != 1 and uris['resolution'] == 'HD':
                    url = uris['uri']
                if (addon.getSetting('only_sd') == 'true' or resolution == 1) and uris['resolution'] == 'SD': 
                    url = uris['uri']
            if url == '':
                url = data['uris'][0]['uri']
            if addon.getSetting('stream_type') == 'MPEG-DASH' or force_mpeg_dash == 1:
                request = Request(url = url , data = None, headers = header)
                response = urlopen(request)
                url = response.geturl().replace('http:','https:').replace(':80/',':443/')
        else:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s přehráním streamu', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()
                                                    
    if type == 'live_iptv' or type == 'live_iptv_epg':
        list_item = xbmcgui.ListItem(path = url)
        list_item = get_listitem_epg_details(list_item, str(epgId), '', update_from_api = 1)
    elif type == 'archiv_iptv':
        list_item = xbmcgui.ListItem(title)
        list_item = get_listitem_epg_details(list_item, str(epgId), '', update_from_api = 1)
    else:
        list_item = xbmcgui.ListItem(path = url)

    if addon.getSetting('stream_type') == 'MPEG-DASH' or addon.getSetting('stream_type') == 'MPEG-DASH-web' or force_mpeg_dash == 1:
        list_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
        list_item.setProperty('inputstream', 'inputstream.adaptive')
        list_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        list_item.setMimeType('application/dash+xml')
    if type == 'archiv_iptv' or (type == 'live_iptv' and (addon.getSetting('stream_type') != 'HLS' or force_mpeg_dash == 1) and addon.getSetting('startover') == 'true') or type == 'live_iptv_epg':
        playlist=xbmc.PlayList(1)
        playlist.clear()
        if epgId is not None:
            event = get_epg_details([str(epgId)], update_from_api = 1)
            list_item.setInfo('video', {'title' : event['title']}) 
        else:
            list_item.setInfo('video', {'title' : channels_list[channelKey]['name']}) 
        xbmc.PlayList(1).add(url, list_item)
        xbmc.Player().play(playlist)
    else:
        list_item.setContentLookup(False)       
        xbmcplugin.setResolvedUrl(_handle, True, list_item)

 
