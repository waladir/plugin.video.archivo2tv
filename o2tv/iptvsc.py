# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
import xbmcvfs

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

try:
    from urllib import urlencode, quote
except ImportError:
    from urllib.parse import urlencode, quote
    
from datetime import date, datetime, timedelta
import time
import codecs

from o2tv import o2api
from o2tv import utils
from o2tv.utils import plugin_id, encode, decode
from o2tv.stream import play_video
from o2tv.recordings import add_recording
from o2tv.channels import Channels 
from o2tv.epg import load_epg_all, get_epg_all, get_epgId_iptvsc, get_epg_details

tz_offset = int((time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple()))/3600)

def save_file_test(epg = 0):
    addon = xbmcaddon.Addon()  
    try:
        content = ''
        if len(addon.getSetting('output_epg_dir')) > 0 and epg == 1:
            output_dir = addon.getSetting('output_epg_dir')
        else:
            output_dir = addon.getSetting('output_dir')      
        test_file = output_dir + 'test.fil'
        file = xbmcvfs.File(test_file, 'w')
        file.write(bytearray(('test').encode('utf-8')))
        file.close()
        file = xbmcvfs.File(test_file, 'r')
        content = file.read()
        if len(content) > 0 and content == 'test':
            file.close()
            xbmcvfs.delete(test_file)
            return 1  
        file.close()
        xbmcvfs.delete(test_file)
        return 0
    except Exception:
        file.close()
        xbmcvfs.delete(test_file)
        return 0 
      
def load_epg_db(output_file = ''):
    addon = xbmcaddon.Addon()
    events_data = {}
    events_detailed_data = {}
    events_data, events_detailed_data = get_epg_all()

    channels = Channels()
    if addon.getSetting('epg_for_all_channels') == 'true':
        channels_list = channels.get_channels_list('number', available_filter = False, visible_filter = False)
    else:
        channels_list = channels.get_channels_list('number', visible_filter = True)
    
    if len(channels_list) > 0:
        if save_file_test(epg = 1) == 0:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba při uložení EPG', xbmcgui.NOTIFICATION_ERROR, 5000)
            return

        if len(addon.getSetting('output_epg_dir')) > 0:
            output_dir = addon.getSetting('output_epg_dir')
        else:
            output_dir = addon.getSetting('output_dir') 

        try:
            if len(output_file) > 0:
                file = xbmcvfs.File(output_file, 'w')
            else:
                file = xbmcvfs.File(output_dir + 'o2_epg.xml', 'w')

            if file == None:
                xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba při uložení EPG', xbmcgui.NOTIFICATION_ERROR, 5000)
            else:
                file.write(bytearray(('<?xml version="1.0" encoding="UTF-8"?>\n').encode('utf-8')))
                file.write(bytearray(('<tv generator-info-name="EPG grabber">\n').encode('utf-8')))
                content = ''
                for number in sorted(channels_list.keys()):
                    channel = channels_list[number]['name']
                    content = content + '    <channel id="' + channel.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '">\n'
                    content = content + '            <display-name lang="cs">' + channel.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</display-name>\n'
                    content = content + '            <icon src="' + channels_list[number]['logo'] + '" />\n'
                    content = content + '    </channel>\n'
                file.write(bytearray((content).encode('utf-8')))
                for number in sorted(channels_list.keys()):
                    channel = channels_list[number]['name']
                    cnt = 0
                    content = ''
                    if channel in events_data:
                        for event in sorted(events_data[channel].keys()):
                            starttime = datetime.fromtimestamp(events_data[channel][event]['startTime']).strftime('%Y%m%d%H%M%S')
                            endtime = datetime.fromtimestamp(events_data[channel][event]['endTime']).strftime('%Y%m%d%H%M%S')
                            content = content + '    <programme start="' + starttime + ' +0' + str(tz_offset) + '00" stop="' + endtime + ' +0' + str(tz_offset) + '00" channel="' + events_data[channel][event]['channel'] + '">\n'
                            content = content + '       <title lang="cs">' + events_data[channel][event]['title'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</title>\n'
                            if events_data[channel][event]['epgId'] in events_detailed_data:
                                if events_detailed_data[events_data[channel][event]['epgId']]['original'] != None and len(events_detailed_data[events_data[channel][event]['epgId']]['original']) > 0:
                                    content = content + '       <title>' + events_detailed_data[events_data[channel][event]['epgId']]['original'].replace('&','&amp;').replace('<','&lt;').replace('<','&gt;') + '</title>\n'
                                content = content + '       <desc lang="cs">' + events_detailed_data[events_data[channel][event]['epgId']]['desc'].replace('&','&amp;').replace('<','&lt;').replace('<','&gt;') + '</desc>\n'
                                if events_detailed_data[events_data[channel][event]['epgId']]['episodeName'] != None and len(events_detailed_data[events_data[channel][event]['epgId']]['episodeName']) > 0:
                                    content = content + '       <sub-title lang="cs">' + events_detailed_data[events_data[channel][event]['epgId']]['episodeName'].replace('&','&amp;').replace('<','&lt;').replace('<','&gt;') + '</sub-title>\n'
                                if events_detailed_data[events_data[channel][event]['epgId']]['episodeNumber'] != None and events_detailed_data[events_data[channel][event]['epgId']]['seasonNumber'] != None and events_detailed_data[events_data[channel][event]['epgId']]['episodeNumber'] > 0 and events_detailed_data[events_data[channel][event]['epgId']]['seasonNumber'] > 0:
                                    if events_detailed_data[events_data[channel][event]['epgId']]['episodesInSeason'] != None and events_detailed_data[events_data[channel][event]['epgId']]['episodesInSeason'] > 0:
                                        content = content + '       <episode-num system="xmltv_ns">' + str(events_detailed_data[events_data[channel][event]['epgId']]['seasonNumber']-1) + '.' + str(events_detailed_data[events_data[channel][event]['epgId']]['episodeNumber']-1) + '/' + str(events_detailed_data[events_data[channel][event]['epgId']]['episodesInSeason']) + '.0/0"</episode-num>\n'
                                    else:
                                        content = content + '       <episode-num system="xmltv_ns">' + str(events_detailed_data[events_data[channel][event]['epgId']]['seasonNumber']-1) + '.' + str(events_detailed_data[events_data[channel][event]['epgId']]['episodeNumber']-1) + '.0/0"</episode-num>\n'
                                content = content + '       <icon src="' + events_detailed_data[events_data[channel][event]['epgId']]['icon'] + '"/>\n'
                                content = content + '       <credits>\n'
                                for cast in events_detailed_data[events_data[channel][event]['epgId']]['cast']: 
                                    content = content + '         <actor>' + cast.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</actor>\n'
                                for director in events_detailed_data[events_data[channel][event]['epgId']]['directors']: 
                                    content = content + '         <director>' + director.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</director>\n'
                                content = content + '       </credits>\n'
                                for category in events_detailed_data[events_data[channel][event]['epgId']]['genres']:
                                    content = content + '       <category>' + category.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</category>\n'
                                if len(str(events_detailed_data[events_data[channel][event]['epgId']]['year'])) > 0 and int(events_detailed_data[events_data[channel][event]['epgId']]['year']) > 0:
                                    content = content + '       <date>' + str(events_detailed_data[events_data[channel][event]['epgId']]['year']) + '</date>\n'
                                if len(events_detailed_data[events_data[channel][event]['epgId']]['country']) > 0:
                                    content = content + '       <country>' + events_detailed_data[events_data[channel][event]['epgId']]['country'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</country>\n'
                                for rating_name,rating in events_detailed_data[events_data[channel][event]['epgId']]['ratings'].items(): 
                                    content = content + '       <rating system="' + rating_name.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '"><value>' + str(rating) + '/10</value></rating>\n'
                            else:
                                content = content + '       <desc lang="cs"></desc>\n'
                            content = content + '    </programme>\n'
                            cnt = cnt + 1
                            if cnt > 20:
                                file.write(bytearray((content).encode('utf-8')))
                                content = ''
                                cnt = 0
                        file.write(bytearray((content).encode('utf-8')))                          
                file.write(bytearray(('</tv>\n').encode('utf-8')))
                file.close()
                if addon.getSetting('info_enabled') == 'true':
                  xbmcgui.Dialog().notification('Sledování O2TV', 'EPG bylo uložené', xbmcgui.NOTIFICATION_INFO, 5000)    
        except Exception:
            file.close()
            xbmcgui.Dialog().notification('Sledování O2TV', 'Nemohu zapsat do ' + output_dir + 'o2_epg.xml' + '!', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()
    else:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Nevrácena žádná data!', xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit()

def generate_playlist(output_file = ''):
    addon = xbmcaddon.Addon()
    if addon.getSetting('output_dir') is None or len(addon.getSetting('output_dir')) == 0:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Nastav adresář pro playlist!', xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit() 
             
    channels = Channels()
    channels_list = channels.get_channels_list('number')

    if len(output_file) > 0:
        filename = output_file
    else:
        filename = addon.getSetting('output_dir') + 'playlist.m3u'

    if save_file_test(epg = 0) == 0:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba při uložení playlistu', xbmcgui.NOTIFICATION_ERROR, 5000)
        return

    try:
        file = xbmcvfs.File(filename, 'w')
        if file == None:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba při uložení playlistu', xbmcgui.NOTIFICATION_ERROR, 5000)
        else:
            file.write(bytearray(('#EXTM3U\n').encode('utf-8')))
            for number in sorted(channels_list.keys()):  
                logo = channels_list[number]['logo']
                if addon.getSetting('add_channel_numbers') == 'true':
                    if addon.getSetting('catchup_mode') == 'default':
                        line = '#EXTINF:-1 catchup="default" catchup-days="7" catchup-source="plugin://plugin.video.archivo2tv/?action=get_stream_url&channelKey=' + quote(encode(channels_list[number]['channelKey'])) + '&catchup_start_ts={utc}&catchup_end_ts={utcend}" tvg-chno="' + str(number) + '" tvg-id="' + channels_list[number]['name'] + '" tvh-epg="0" tvg-logo="' + logo + '",' + channels_list[number]['name']
                    else:
                        line = '#EXTINF:-1 catchup="append" catchup-days="7" catchup-source="&catchup_start_ts={utc}&catchup_end_ts={utcend}" tvg-chno="' + str(number) + '" tvg-id="' + channels_list[number]['name'] + '" tvh-epg="0" tvg-logo="' + logo + '",' + channels_list[number]['name']
                else:
                    if addon.getSetting('catchup_mode') == 'default':
                        line = '#EXTINF:-1 catchup="default" catchup-days="7" catchup-source="plugin://plugin.video.archivo2tv/?action=get_stream_url&channelKey=' + quote(encode(channels_list[number]['channelKey'])) + '&catchup_start_ts={utc}&catchup_end_ts={utcend}" tvg-id="' + channels_list[number]['name'] + '" tvh-epg="0" tvg-logo="' + logo + '",' + channels_list[number]['name']
                    else:
                        line = '#EXTINF:-1 catchup="append" catchup-days="7" catchup-source="&catchup_start_ts={utc}&catchup_end_ts={utcend}" tvg-id="' + channels_list[number]['name'] + '" tvh-epg="0" tvg-logo="' + logo + '",' + channels_list[number]['name']
                file.write(bytearray((line + '\n').encode('utf-8')))
                line = 'plugin://' + plugin_id + '/?action=get_stream_url&channelKey=' + quote(encode(channels_list[number]['channelKey']))
                if addon.getSetting('iptvsc_timeshift') == 'true':
                    file.write(bytearray(('#KODIPROP:inputstream=inputstream.ffmpegdirect\n').encode('utf-8')))
                    file.write(bytearray(('#KODIPROP:inputstream.ffmpegdirect.stream_mode=timeshift\n').encode('utf-8')))
                    file.write(bytearray(('#KODIPROP:inputstream.ffmpegdirect.is_realtime_stream=true\n').encode('utf-8')))
                    file.write(bytearray(('#KODIPROP:mimetype=video/mp2t\n').encode('utf-8')))
                file.write(bytearray((line + '\n').encode('utf-8')))
            file.close()
            xbmcgui.Dialog().notification('Sledování O2TV', 'Playlist byl uložený', xbmcgui.NOTIFICATION_INFO, 5000)    
    except Exception:
        file.close()
        xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba při uložení playlistu', xbmcgui.NOTIFICATION_ERROR, 5000)

def generate_epg(output_file = ''):
    addon = xbmcaddon.Addon()
    if addon.getSetting('disabled_scheduler') != 'true':
        load_epg_all()
    load_epg_db(output_file)      
    
def iptv_sc_play(channelName, startdatetime, epg):
    epgId = -1
    addon = xbmcaddon.Addon()
    channelName = decode(channelName)
    if len(startdatetime) > 0:
        from_ts = int(time.mktime(time.strptime(startdatetime, '%d.%m.%Y %H:%M')))
    else:
        from_ts = int(time.mktime(datetime.now().timetuple()))

    channels = Channels()
    channels_list = channels.get_channels_list('name')
    if channelName not in  channels_list:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Kanál přehrávaný z IPTV SC nebyl nalezený!', xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit()          
    channelKey = channels_list[channelName]['channelKey']
 
    if from_ts > int(time.mktime(datetime.now().timetuple())):
        xbmcgui.Dialog().notification('Sledování O2TV', 'Nelze přehrát budoucí pořad!', xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit()  
    else:
        event = get_epgId_iptvsc(channelName, channelKey, from_ts)
        epgId = event['epgId']
        if epgId > 0:
            startts = event['start']
            start = datetime.fromtimestamp(event['start'])
            endts = event['end']
            end = datetime.fromtimestamp(event['end'])        
            epgId = event['epgId']
            title = decode(utils.day_translation_short[start.strftime('%w')]) + ' ' + start.strftime('%d.%m %H:%M') + ' - ' + end.strftime('%H:%M') + ' | ' + event['title']

        if int(epgId) > 0:
            if int(endts) < int(time.mktime(datetime.now().timetuple())):
              play_video(type = 'archiv_iptv', channelKey = encode(channelKey), start = startts, end = endts, epgId = epgId, title = title)
            else:
                if epg == 1:
                    play_video(type = 'live_iptv_epg', channelKey = encode(channelKey), start = None, end = None, epgId = None, title = None)
                else:
                    play_video(type = 'live_iptv', channelKey = encode(channelKey), start = None, end = None, epgId = None, title = None)
        else:
            if len(startdatetime) == 0:
                play_video(type = 'live_iptv', channelKey = encode(channelKey), start = None, end = None, epgId = None, title = None)
            else:
                xbmcgui.Dialog().notification('Sledování O2TV', 'Pořad u O2 nenalezen! Používáte EPG z doplňku Sledování O2TV?', xbmcgui.NOTIFICATION_ERROR, 10000)
            sys.exit()  

def iptv_sc_rec(channelName, startdatetime):
    epgId = -1
    channels = Channels()
    channels_list = channels.get_channels_list('name')
    channelName = decode(channelName)
    from_ts = int(time.mktime(time.strptime(startdatetime, '%d.%m.%Y %H:%M')))
    event = get_epgId_iptvsc(channelName, channels_list[channelName]['channelKey'], from_ts)
    epgId = event['epgId']
    if epgId > 0:
        add_recording(channels_list[channelName]['channelKey'], epgId)
    else:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Pořad u O2 nenalezen! Používáte EPG z doplňku Sledování O2TV?', xbmcgui.NOTIFICATION_ERROR, 10000)
        sys.exit()  

def iptv_sc_download(channelName, startdatetime):
    addon = xbmcaddon.Addon()
    if addon.getSetting('download_streams') == 'true':  
        from o2tv.downloader import add_to_queue
    epgId = -1
    from_ts = int(time.mktime(time.strptime(startdatetime, '%d.%m.%Y %H:%M')))
    channels = Channels()
    channels_list = channels.get_channels_list('name')
    channelName = decode(channelName)
    event = get_epgId_iptvsc(channelName, channels_list[channelName]['channelKey'], from_ts)
    epgId = event['epgId']
    if epgId > 0:
        event = get_epg_details([epgId], update_from_api = 1)
        if event['startTime'] > int(time.mktime(datetime.now().timetuple())) or event['endTime'] > int(time.mktime(datetime.now().timetuple())):
            xbmcgui.Dialog().notification('Sledování O2TV', 'Lze stáhnout jen už odvysílaný pořad!', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()  
        if event['availableTo'] < int(time.mktime(datetime.now().timetuple())):
            xbmcgui.Dialog().notification('Sledování O2TV', 'Pořad u O2 už není k dispozici!', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()         
        add_to_queue(epgId, None)
    else:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Pořad u O2 nenalezen! Používáte EPG z doplňku Sledování O2TV?', xbmcgui.NOTIFICATION_ERROR, 10000)
        sys.exit()  