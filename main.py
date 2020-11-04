# -*- coding: utf-8 -*-
import os                     
import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from urllib import urlencode
    from urlparse import parse_qsl
except ImportError:
    from urllib.parse import urlencode, parse_qsl

from o2tv.o2api import login
from o2tv import o2api
from o2tv.utils import check_settings, get_url, parsedatetime

from o2tv.live import list_live
from o2tv.archive import list_archiv, list_arch_days, list_program
from o2tv.categories import list_categories, list_subcategories, list_category, list_series, list_related, list_same
from o2tv.recordings import list_planning_recordings, list_rec_days, future_program, list_recordings, list_future_recordings, delete_recording, add_recording
from o2tv.stream import play_video
from o2tv.search import list_search, program_search, delete_search
from o2tv.channels import list_channels_list, list_channels_edit, get_o2_channels_lists, load_o2_channel_list, reset_channel_list, edit_channel, delete_channel, list_channels_add, add_channel
from o2tv.channels import list_channels_groups, add_channel_group, delete_channel_group, select_channel_group, edit_channel_group, edit_channel_group_list_channels, edit_channel_group_add_channel, edit_channel_group_delete_channel
from o2tv.iptvsc import generate_playlist, generate_epg, iptv_sc_play, iptv_sc_rec, iptv_sc_download
from o2tv.downloader import list_downloads, add_to_queue, remove_from_queue

_url = sys.argv[0]
_handle = int(sys.argv[1])
addon = xbmcaddon.Addon(id='plugin.video.archivo2tv')

def list_menu():
    icons_dir = os.path.join(addon.getAddonInfo('path'), 'resources','images')
   
    list_item = xbmcgui.ListItem(label="Živé vysílání")
    url = get_url(action='list_live', page = 1, label = "Živé vysílání")  
    list_item.setArt({ "thumb" : os.path.join(icons_dir , 'livetv.png'), "icon" : os.path.join(icons_dir , 'livetv.png') })
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label="Archiv")
    url = get_url(action='list_archiv', label = "Archiv")  
    list_item.setArt({ "thumb" : os.path.join(icons_dir , 'archive.png'), "icon" : os.path.join(icons_dir , 'archive.png') })
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label="Kategorie")
    url = get_url(action='list_categories', label = "Kategorie")  
    list_item.setArt({ "thumb" : os.path.join(icons_dir , 'categories.png'), "icon" : os.path.join(icons_dir , 'categories.png') })
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)    

    list_item = xbmcgui.ListItem(label="Nahrávky")
    url = get_url(action='list_recordings', label = "Nahrávky")  
    list_item.setArt({ "thumb" : os.path.join(icons_dir , 'recordings.png'), "icon" : os.path.join(icons_dir , 'recordings.png') })
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label="Vyhledávání")
    url = get_url(action='list_search', label = "Vyhledávání")  
    list_item.setArt({ "thumb" : os.path.join(icons_dir , 'search.png'), "icon" : os.path.join(icons_dir , 'search.png') })
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    
    if addon.getSetting("download_streams") == "true":
        list_item = xbmcgui.ListItem(label="Stahování")
        url = get_url(action='list_downloads', label = "Stahování")  
        list_item.setArt({ "thumb" : os.path.join(icons_dir , 'downloads.png'), "icon" : os.path.join(icons_dir , 'downloads.png') })
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    if addon.getSetting("hide_channel_list_edit") != "true":
        list_item = xbmcgui.ListItem(label="Seznam kanálů")
        url = get_url(action='list_channels_list', label = "Seznam kanálů")  
        list_item.setArt({ "thumb" : os.path.join(icons_dir , 'settings.png'), "icon" : os.path.join(icons_dir , 'settings.png') })
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def router(paramstring):
    params = dict(parse_qsl(paramstring))

    check_settings() 
    login()
  
    if params:
        if params["action"] == "list_live":
            list_live(params["page"], params["label"])
        elif params['action'] == 'play_live':
            play_video(type = "live", channelKey = params["channelKey"], start = None, end = None, epgId = None, title = params["title"])

        elif params["action"] == "list_archiv":
            list_archiv(params["label"])
        elif params["action"] == "list_arch_days":
            list_arch_days(params["channelKey"], params["label"])
        elif params['action'] == 'list_program':
            list_program(params["channelKey"], params["day_min"], params["label"])
        elif params['action'] == 'play_archiv':
            play_video(type = "archiv", channelKey = params["channelKey"], start = params["start"], end = params["end"], epgId = params["epgId"], title = None)

        elif params["action"] == "list_categories":
            list_categories(params["label"])
        elif params["action"] == "list_subcategories":
            list_subcategories(params["category"], params["label"])           
        elif params["action"] == "list_category":
            if "page" not in params:
              params["page"] = None  
            list_category(params["category"], params["dataSource"], params["filtr"], params["page"], params["label"])
        elif params["action"] == "list_series":
            list_series(params["epgId"], params["season"], params["label"])            
        elif params["action"] == "list_related":
            list_related(params["epgId"], params["label"])            
        elif params["action"] == "list_same":
            list_same(params["epgId"], params["label"])            


        elif params['action'] == 'list_planning_recordings':
            list_planning_recordings(params["label"])
        elif params["action"] == "list_rec_days":
            list_rec_days(params["channelKey"], params["label"])
        elif params['action'] == 'future_program':
            future_program(params["channelKey"], params["day"], params["label"])
        elif params["action"] == "list_recordings":
            list_recordings(params["label"])
        elif params["action"] == "list_future_recordings":
            list_future_recordings(params["label"])
        elif params["action"] == "delete_recording":
            delete_recording(params["pvrProgramId"])
        elif params["action"] == "add_recording":
            add_recording(params["epgId"])
        elif params['action'] == 'play_recording':
            play_video(type = "recording", channelKey = None, start = None, end = None, epgId = params["pvrProgramId"], title = params["title"])

        elif params['action'] == 'list_search':
            list_search(params["label"])
        elif params['action'] == 'program_search':
            program_search(params["query"], params["label"])
        elif params['action'] == 'delete_search':
            delete_search(params["query"])            

        elif params['action'] == 'list_channels_list':
            list_channels_list(params["label"])
        elif params['action'] == 'list_channels_list':
            list_channels_list(params["label"])
        elif params['action'] == 'get_o2_channels_lists':
            get_o2_channels_lists(params["label"])
        elif params['action'] == 'load_o2_channel_list':
            load_o2_channel_list(params["list"])            
        elif params['action'] == 'reset_channel_list':
            reset_channel_list()            
        elif params['action'] == 'list_channels_edit':
            list_channels_edit(params["label"])
        elif params['action'] == 'edit_channel':
            edit_channel(params["channelName"], params["channelNum"])
        elif params['action'] == 'delete_channel':
            delete_channel(params["channelName"], params["channelNum"])
        elif params['action'] == 'list_channels_add':
            list_channels_add(params["label"])
        elif params['action'] == 'add_channel':
            add_channel(params["channelName"], params["channelNum"])

        elif params['action'] == 'list_channels_groups':
            list_channels_groups(params["label"])
        elif params['action'] == 'add_channel_group':
            add_channel_group(params["label"])
        elif params['action'] == 'delete_channel_group':
            delete_channel_group(params["group"])
        elif params['action'] == 'select_channel_group':
            select_channel_group(params["group"])

        elif params['action'] == 'edit_channel_group':
            edit_channel_group(params["group"], params["label"])
        elif params['action'] == 'edit_channel_group_list_channels':
            edit_channel_group_list_channels(params["group"], params["label"])
        elif params['action'] == 'edit_channel_group_add_channel':
            edit_channel_group_add_channel(params["group"], params["channel"])
        elif params['action'] == 'edit_channel_group_delete_channel':
            edit_channel_group_delete_channel(params["group"], params["channel"])
            
        elif params['action'] == 'generate_playlist':
            generate_playlist()
        elif params['action'] == 'generate_epg':
            generate_epg()
        elif params['action'] == 'get_stream_url':
            if addon.getSetting("switch_channel_archiv") == "true" and len(xbmc.getInfoLabel('ListItem.ChannelName')) > 0:
                iptv_sc_play(xbmc.getInfoLabel('ListItem.ChannelName'), parsedatetime(xbmc.getInfoLabel('ListItem.Date'), xbmc.getInfoLabel('ListItem.StartDate')), 0)
            else:
                play_video(type = "live_iptv", channelKey = params["channelKey"], start = None, end = None, epgId = None, title = None)
        elif params['action'] == 'iptv_sc_play':
            iptv_sc_play(params["channel"], params["startdatetime"], 1)
        elif params['action'] == 'iptv_sc_rec':
            iptv_sc_rec(params["channel"], params["startdatetime"])
        elif params['action'] == 'iptv_sc_download':
            iptv_sc_download(params["channel"], params["startdatetime"])            
        elif params['action'] == 'reset_session':
            o2api.session_reset()

        elif params['action'] == 'add_to_queue':
            if "pvrProgramId" in params:
                pvrProgramId = params["pvrProgramId"]
            else:
                pvrProgramId = None
            add_to_queue(epgId = params["epgId"], pvrProgramId = pvrProgramId)            
        elif params['action'] == 'remove_from_queue':
            remove_from_queue(epgId = params["epgId"])            
        elif params['action'] == 'list_downloads':
            list_downloads(params["label"])
        else:
            raise ValueError('Neznámý parametr: {0}!'.format(paramstring))
    else:
        list_menu()

if __name__ == '__main__':
    router(sys.argv[2][1:])

