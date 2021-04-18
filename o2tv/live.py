# -*- coding: utf-8 -*-
import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from datetime import datetime 

from o2tv.utils import plugin_id, get_url, get_color, encode
from o2tv.epg import get_epg_live, get_listitem_epg_details
from o2tv.channels import Channels 

_url = sys.argv[0]
if len(sys.argv) > 1:
    _handle = int(sys.argv[1])


def list_live(page, label):
    addon = xbmcaddon.Addon()
    xbmcplugin.setPluginCategory(_handle, label)
    channels = Channels()
    channels_list = channels.get_channels_list('number')
    num = 0
    pagesize = int(addon.getSetting('live_pagesize'))
    channels_details = get_epg_live(len(channels_list.keys()))
    color = get_color(addon.getSetting('label_color_live'))   
    startitem = (int(page)-1) * pagesize
    i = 0

    for num in sorted(channels_list.keys()):  
        if i >= startitem and i < startitem + pagesize: 
            channelName = channels_list[num]['name']
            channelKey = channels_list[num]['channelKey']
            if channelName in channels_details:
                title = channels_details[channelName]['title']
                start = channels_details[channelName]['start']
                end = channels_details[channelName]['end']
                live = '[COLOR ' + str(color) + '] | ' + title + ' | ' + start.strftime('%H:%M') + ' - ' + end.strftime('%H:%M') + '[/COLOR]'
                live_noncolor = ' | ' + title + ' | ' + start.strftime('%H:%M') + ' - ' + end.strftime('%H:%M')
                list_item = xbmcgui.ListItem(label=encode(channelName) + encode(live))
                list_item.setInfo('video', {'mediatype':'movie', 'title': encode(channelName) + ' | ' + encode(title)}) 
                list_item = get_listitem_epg_details(list_item, str(channels_details[channelName]['epgId']), channels_list[num]['logo'])
            else: 
                live = ''
                live_noncolor = ''
                list_item = xbmcgui.ListItem(label=encode(channelName) + encode(live))
                list_item.setInfo('video', {'mediatype':'movie', 'title': encode(channelName) + encode(live)}) 
            list_item.setContentLookup(False)          
            list_item.setProperty('IsPlayable', 'true')
            if channelName in channels_details:
                list_item.addContextMenuItems([('Související pořady', 'Container.Update(plugin://' + plugin_id + '?action=list_related&epgId=' + str(channels_details[channelName]['epgId']) + '&label=Související / ' + encode(channels_details[channelName]['title']) + ')'),
                                             ('Vysílání pořadu', 'Container.Update(plugin://' + plugin_id + '?action=list_same&epgId=' + str(channels_details[channelName]['epgId']) + '&label=' + encode(channels_details[channelName]['title']) + ')')])       
            url = get_url(action='play_live', channelKey = encode(channelKey), title = encode(channelName) + encode(live_noncolor))
            xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
        i = i + 1

    if int(page) * pagesize <= i:
        list_item = xbmcgui.ListItem(label='další strana')
        url = get_url(action='list_live', page = int(page) + 1, label = 'další strana')  
        list_item.setProperty('IsPlayable', 'false')
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)     
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)
