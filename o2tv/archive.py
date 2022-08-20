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
    
from datetime import date, datetime, timedelta
import time

from o2tv.utils import plugin_id, get_url, get_color, decode, encode
from o2tv import utils
from o2tv.epg import get_epg_ts, get_listitem_epg_details
from o2tv.channels import Channels 

_url = sys.argv[0]
if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def list_archiv(label):
    xbmcplugin.setPluginCategory(_handle, label)
    channels = Channels()
    channels_list = channels.get_channels_list('number')
    for number in sorted(channels_list.keys()):  
        list_item = xbmcgui.ListItem(label=channels_list[number]['name'])
        if len(channels_list[number]['logo']) > 0:
            list_item.setArt({'thumb': channels_list[number]['logo'], 'icon': channels_list[number]['logo']})
        url = get_url(action='list_arch_days', channelKey = encode(channels_list[number]['channelKey']), label = encode(label + ' / ' + channels_list[number]['name']))  
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)

def list_arch_days(channelKey, label):
    xbmcplugin.setPluginCategory(_handle, label)
    for i in range (8):
        day = date.today() - timedelta(days = i)
        if i == 0:
            den_label = 'Dnes'
            den = 'Dnes'
        elif i == 1:
            den_label = 'Včera'
            den = 'Včera'
        else:
            den_label = utils.day_translation_short[day.strftime('%w')] + ' ' + day.strftime('%d.%m')
            den = decode(utils.day_translation[day.strftime('%w')]) + ' ' + day.strftime('%d.%m.%Y')
        list_item = xbmcgui.ListItem(label=den)
        url = get_url(action='list_program', channelKey = channelKey, day_min = i, label = label + ' / ' + den_label)  
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)

def list_program(channelKey, day_min, label):
    label = label.replace('Archiv /','')
    xbmcplugin.setPluginCategory(_handle, label)
    addon = xbmcaddon.Addon()
    channelKey = decode(channelKey)
    channels = Channels()
    channels_list = channels.get_channels_list()
    today_date = datetime.today() 
    today_start_ts = int(time.mktime(datetime(today_date.year, today_date.month, today_date.day) .timetuple()))
    today_end_ts = today_start_ts + 60*60*24 -1
    if int(day_min) == 0:
        from_ts = today_start_ts - int(day_min)*60*60*24
        to_ts = int(time.mktime(datetime.now().timetuple()))
    
    else:
        from_ts = today_start_ts - int(day_min)*60*60*24
        to_ts = today_end_ts - int(day_min)*60*60*24

    events = {}
    events = get_epg_ts(channelKey, from_ts, to_ts, 8)

    if addon.getSetting('archive_reverse_sort') == "true":
        archive_reverse = True
    else:
        archive_reverse = False

    for key in sorted(events.keys(), reverse = archive_reverse):
        if int(events[key]['endts']) > int(time.mktime(datetime.now().timetuple()))-60*60*24*7:
            list_item = xbmcgui.ListItem(label = decode(utils.day_translation_short[events[key]['start'].strftime('%w')]) + ' ' + events[key]['start'].strftime('%d.%m %H:%M') + ' - ' + events[key]['end'].strftime('%H:%M') + ' | ' + events[key]['title'])
            list_item.setInfo('video', {'mediatype':'movie', 'title': events[key]['title']}) 
            list_item = get_listitem_epg_details(list_item, str(events[key]['epgId']), channels_list[channelKey]['logo'])
            list_item.setProperty('IsPlayable', 'true')
            list_item.setContentLookup(False)          
            menus = [('Přidat nahrávku', 'RunPlugin(plugin://' + plugin_id + '?action=add_recording&channelKey=' + channelKey + '&epgId=' + str(events[key]['epgId']) + ')'), 
                    ('Související pořady', 'Container.Update(plugin://' + plugin_id + '?action=list_related&epgId=' + str(events[key]['epgId']) + '&label=Související / ' + encode(events[key]['title']) + ')'), 
                    ('Vysílání pořadu', 'Container.Update(plugin://' + plugin_id + '?action=list_same&epgId=' + str(events[key]['epgId']) + '&label=' + encode(events[key]['title']) + ')')]
            if addon.getSetting('download_streams') == 'true': 
                menus.append(('Stáhnout', 'RunPlugin(plugin://' + plugin_id + '?action=add_to_queue&epgId=' + str(events[key]['epgId']) + ')'))
            list_item.addContextMenuItems(menus)       
            url = get_url(action='play_archiv', channelKey = encode(channelKey), start = events[key]['startts'], end = events[key]['endts'], epgId = events[key]['epgId'])
            xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)