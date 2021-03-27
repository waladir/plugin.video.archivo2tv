# -*- coding: utf-8 -*-
import os
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
    from urllib import urlencode, quote
except ImportError:
    from urllib.parse import urlencode, quote
    
import json
import time
import codecs

from o2tv.session import Session
from o2tv.o2api import call_o2_api, get_header, get_header_unity
from o2tv.utils import plugin_id, get_url, decode, encode

_url = sys.argv[0]
if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def list_channels_list(label):
    xbmcplugin.setPluginCategory(_handle, label)
    list_item = xbmcgui.ListItem(label='Ruční editace')
    url = get_url(action='list_channels_edit', label = label + ' / Ruční editace')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label='Načtení uživatelského seznamu z O2')
    url = get_url(action='get_o2_channels_lists', label = label + '/ Načtení z O2')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label='Vlastní skupiny kanálů')
    url = get_url(action='list_channels_groups', label = label + ' / Skupiny kanálů')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label='Resetovat seznam kanálů')
    url = get_url(action='reset_channels_list')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def edit_channel(channelKey):
    channelKey = decode(channelKey)
    channels = Channels()
    channels_list = channels.get_channels_list(visible_filter = False)
    new_num = xbmcgui.Dialog().numeric(0, 'Číslo kanálu', str(channels_list[channelKey]['number']))
    if len(new_num) > 0 and int(new_num) > 0:
        channels_nums = channels.get_channels_list('number', visible_filter = False)
        if int(new_num) in channels_nums:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Číslo kanálu ' + new_num +  ' je použité u kanálu ' + encode(channels_nums[int(new_num)]['name']), xbmcgui.NOTIFICATION_ERROR, 5000)
        else:  
            channels.set_number(channelKey, new_num)

def list_channels_edit(label):
    xbmcplugin.setPluginCategory(_handle, label)
    channels = Channels()
    channels_list = channels.get_channels_list('number', visible_filter = False)
    if len(channels_list) > 0:
        for number in sorted(channels_list.keys()):
            if channels_list[number]['visible'] == True:
                list_item = xbmcgui.ListItem(label=str(number) + ' ' + channels_list[number]['name'])
            else:
                list_item = xbmcgui.ListItem(label='[COLOR=gray]' + str(number) + ' ' + channels_list[number]['name'] + '[/COLOR]')
            url = get_url(action='edit_channel', channelKey = encode(channels_list[number]['channelKey']))
            list_item.addContextMenuItems([('Zvýšit čísla kanálů', encode('RunPlugin(plugin://' + plugin_id + '?action=change_channels_numbers&from_number=' + str(number) + '&direction=increase)')),       
                                            ('Snížit čísla kanálů', encode('RunPlugin(plugin://' + plugin_id + '?action=change_channels_numbers&from_number=' + str(number) + '&direction=decrease)'))])       
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
        xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)

def change_channels_numbers(from_number, direction):
    channels = Channels()
    if direction == 'increase':
        change = xbmcgui.Dialog().numeric(0, 'Zvětšit čísla kanálů počínaje kanálem číslo ' + str(from_number) + ' o: ', str(1))
    else:
        change = xbmcgui.Dialog().numeric(0, 'Zmenšit čísla kanálů počínaje kanálem číslo ' + str(from_number) + ' o: ', str(1))
    
    if len(change) > 0:
        change = int(change)
        if change > 0:
            if direction == 'decrease':
                change = change * -1
            channels.change_channels_numbers(from_number, change)
            xbmc.executebuiltin('Container.Refresh')
        else:  
            xbmcgui.Dialog().notification('Sledování O2TV', 'Je potřeba zadat číslo větší než jedna', xbmcgui.NOTIFICATION_ERROR, 5000)
    else:  
        xbmcgui.Dialog().notification('Sledování O2TV', 'Je potřeba zadat číslo větší než jedna!', xbmcgui.NOTIFICATION_ERROR, 5000)


def get_o2_channels_lists(label):
    xbmcplugin.setPluginCategory(_handle, label)
    session = Session()
    for serviceid in session.services:
        data = call_o2_api(url = 'https://app.o2tv.cz/sws/subscription/settings/get-user-pref.json?name=nangu.channelListUserChannelNumbers', data = None, header = get_header(session.services[serviceid]))
        if 'err' in data:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s načtením seznamu kanálů', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()  
        if 'listUserChannelNumbers' in data and len(data['listUserChannelNumbers']) > 0:
            for list in data['listUserChannelNumbers']:
                list_item = xbmcgui.ListItem(label= list.replace('user::',''))
                url = get_url(action='load_o2_channels_list', serviceid = serviceid, list = encode(list))  
                xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
            xbmcplugin.endOfDirectory(_handle)

def load_o2_channels_list(serviceid, list):
    session = Session()
    channels = Channels()
    data = call_o2_api(url = 'https://app.o2tv.cz/sws/subscription/settings/get-user-pref.json?name=nangu.channelListUserChannelNumbers', data = None, header = get_header(session.services[serviceid]))
    if 'err' in data:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s načtením seznamu kanálů', xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit() 
    if 'listUserChannelNumbers' in data and len(data['listUserChannelNumbers']) > 0:
        for list_name in data['listUserChannelNumbers']:
            if list == encode(list_name):
                channels_list = channels.get_channels_list(visible_filter = False)
                for channel in channels_list:
                    if channel in data['listUserChannelNumbers'][decode(list)]:
                        channels.set_visibility(channel, True)
                    else:
                        channels.set_visibility(channel, False)
        xbmcgui.Dialog().notification('Sledování O2TV', 'Seznam kanálů byl načtený', xbmcgui.NOTIFICATION_INFO, 5000)          
    else:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s načtením seznamu kanálů', xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit()  

def list_channels_groups(label):
    xbmcplugin.setPluginCategory(_handle, label)    
    channels_groups = Channels_groups()

    list_item = xbmcgui.ListItem(label='Nová skupina')
    url = get_url(action='add_channel_group', label = 'Nová skupina')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    if channels_groups.selected == None:
        list_item = xbmcgui.ListItem(label='[B]Všechny kanály[/B]')
    else:  
        list_item = xbmcgui.ListItem(label='Všechny kanály')
    url = get_url(action='list_channels_groups', label = 'Seznam kanálů / Skupiny kanálů')  
    list_item.addContextMenuItems([('Vybrat skupinu', 'RunPlugin(plugin://' + plugin_id + '?action=select_channel_group&group=all)' ,)])       
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)    
    for channels_group in channels_groups.groups:
        if channels_groups.selected == channels_group:
            list_item = xbmcgui.ListItem(label='[B]' + channels_group + '[/B]')                
        else:
            list_item = xbmcgui.ListItem(label=channels_group)
        url = get_url(action='edit_channel_group', group = encode(channels_group), label = 'Skupiny kanálů / ' + encode(channels_group)) 
        list_item.addContextMenuItems([('Vybrat skupinu', 'RunPlugin(plugin://' + plugin_id + '?action=select_channel_group&group=' + quote(encode(channels_group)) + ')'), 
                                      ('Smazat skupinu', 'RunPlugin(plugin://' + plugin_id + '?action=delete_channel_group&group=' + quote(encode(channels_group)) + ')')])       
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)

def select_channel_group(group):
    group = decode(group)
    channels_groups = Channels_groups()
    channels_groups.select_group(group)
    xbmc.executebuiltin('Container.Refresh')
    if (not group in channels_groups.channels or len(channels_groups.channels[group]) == 0) and group != 'all':
        xbmcgui.Dialog().notification('Sledování O2TV', 'Vybraná skupina je prázdná', xbmcgui.NOTIFICATION_WARNING, 5000)    

def add_channel_group(label):
    input = xbmc.Keyboard('', 'Název skupiny')
    input.doModal()
    if not input.isConfirmed(): 
        return
    group = input.getText()
    if len(group) == 0:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Je nutné zadat název skupiny', xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit()          
    group = decode(group)
    channels_groups = Channels_groups()
    if group in channels_groups.groups:
        xbmcgui.Dialog().notification('Sledování O2TV', 'Název skupiny je už použitý', xbmcgui.NOTIFICATION_ERROR, 5000)
        sys.exit()          
    channels_groups.add_channels_group(group)    
    xbmc.executebuiltin('Container.Refresh')


def delete_channel_group(group):
    response = xbmcgui.Dialog().yesno('Smazání skupiny kanálů', 'Opravdu smazat skupinu kanálů ' + group + '?', nolabel = 'Ne', yeslabel = 'Ano')
    if response:
        group = decode(group)
        channels_groups = Channels_groups()
        channels_groups.delete_channels_group(group)
        xbmc.executebuiltin('Container.Refresh')

def edit_channel_group(group, label):
    group = decode(group)
    xbmcplugin.setPluginCategory(_handle, label)    
    channels_groups = Channels_groups()
    channels = Channels()
    channels_list = channels.get_channels_list(visible_filter = False)
   
    list_item = xbmcgui.ListItem(label='Přidat kanál')
    url = get_url(action='edit_channel_group_list_channels', group = encode(group), label = encode(group) + ' / Přidat kanál')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    list_item = xbmcgui.ListItem(label='Přidat všechny kanály')
    url = get_url(action='edit_channel_group_add_all_channels', group = encode(group), label = encode(group) + ' / Přidat kanál')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    if group in channels_groups.channels:
        for channel in channels_groups.channels[group]:
            if channel in channels_list:
                list_item = xbmcgui.ListItem(label = channels_list[channel]['name'])
                url = get_url(action='edit_channel_group', group = encode(group), label = label)  
                list_item.addContextMenuItems([('Smazat kanál', 'RunPlugin(plugin://' + plugin_id + '?action=edit_channel_group_delete_channel&group=' + quote(encode(group)) + '&channel='  + quote(encode(channel)) + ')',)])       
                xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)

def edit_channel_group_list_channels(group, label):
    group = decode(group)
    xbmcplugin.setPluginCategory(_handle, label)  
    channels_groups = Channels_groups()
    channels = Channels()
    channels_list = channels.get_channels_list('number', visible_filter = False)
    for number in sorted(channels_list.keys()):
        if not group in channels_groups.groups or not group in channels_groups.channels or not channels_list[number]['channelKey'] in channels_groups.channels[group]:
            list_item = xbmcgui.ListItem(label=str(number) + ' ' + channels_list[number]['name'])
            url = get_url(action='edit_channel_group_add_channel', group = encode(group), channel = encode(channels_list[number]['channelKey']))  
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)

def edit_channel_group_add_channel(group, channel):
    group = decode(group)
    channel = decode(channel)
    channels_groups = Channels_groups()
    channels_groups.add_channel_to_group(channel, group)
    xbmc.executebuiltin('Container.Refresh')

def edit_channel_group_add_all_channels(group):
    group = decode(group)
    channels_groups = Channels_groups()
    channels_groups.add_all_channels_to_group(group)
    xbmc.executebuiltin('Container.Refresh')

def edit_channel_group_delete_channel(group, channel):
    group = decode(group)
    channel = decode(channel)
    channels_groups = Channels_groups()
    channels_groups.delete_channel_from_group(channel, group)
    xbmc.executebuiltin('Container.Refresh')

class Channels:
    def __init__(self):
        self.load_channels()

    def set_visibility(self, channelKey, visibility):
        self.channels[channelKey].update({'visible' : visibility})
        self.save_channels()

    def set_number(self, channelKey, number):
        self.channels[channelKey].update({'number' : int(number)})
        self.save_channels()

    def change_channels_numbers(self, from_number, change):
        from_number = int(from_number)
        change = int(change)
        channels_list = self.get_channels_list('number', visible_filter = False)
        for number in sorted(channels_list.keys(), reverse = True):
            if number >= from_number:
                self.channels[channels_list[number]['channelKey']].update({'number' : int(number)+int(change)})
        self.save_channels()                

    def get_channels_list(self, bykey = None, visible_filter = True, available_filter = True):
        channels = {}
        if bykey == None:
            channels = self.channels
        else:
            for channel in self.channels:
                channels.update({self.channels[channel][bykey] : self.channels[channel]})
        for channel in list(channels):
            if available_filter == True and channels[channel]['available'] == False:
                del channels[channel]
            elif visible_filter == True and channels[channel]['visible'] == False:
                del channels[channel]
        return channels

    def get_encoded_channels(self):
        encoded_channels = ''
        channels_list = self.get_channels_list('number')
        for number in sorted(channels_list.keys()):
            encoded_channels = encoded_channels + str(channels_list[number]['key'])
        return encoded_channels

    def load_channels(self):
        data = None
        self.channels = {}
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
        filename = os.path.join(addon_userdata_dir, 'channels.txt')
        try:
            with codecs.open(filename, 'r', encoding='utf-8') as file:
                for row in file:
                    data = row[:-1]
        except IOError as error:
            if error.errno != 2:
                xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba při načtení seznamu kanálů', xbmcgui.NOTIFICATION_ERROR, 5000)
        if data is not None:
            try:            
                data = json.loads(data)
            except:
                data = {'valid_to' : -1}
                filename = os.path.join(addon_userdata_dir, 'channels_data.txt')
                if os.path.exists(filename):
                    os.remove(filename) 
                    self.valid_to = -1
                    channels_nums = self.migrate_channels()
                    self.merge_channels(self.get_o2_channels(), channels_nums)
                    
    
            self.valid_to = int(data['valid_to'])
            if 'channels' in data and self.valid_to and self.valid_to > 0 and self.valid_to > int(time.time()):
                self.channels = data['channels']
            else:
                self.valid_to = -1
                self.merge_channels(self.get_o2_channels())
                self.save_channels()
        else:
            self.valid_to = -1
            self.merge_channels(self.get_o2_channels())
            self.save_channels()

    def save_channels(self):
        self.valid_to = int(time.time()) + 60*60*24
        data = json.dumps({'channels' : self.channels, 'valid_to' : self.valid_to})
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
        filename = os.path.join(addon_userdata_dir, 'channels.txt')
        try:
            with codecs.open(filename, 'w', encoding='utf-8') as file:
                file.write('%s\n' % data)
        except IOError:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba uložení kanálů', xbmcgui.NOTIFICATION_ERROR, 5000)      

    def reset_channels(self):
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 
        filename = os.path.join(addon_userdata_dir, 'channels.txt')
        if os.path.exists(filename):
            os.remove(filename) 
        self.load_channels()
        xbmcgui.Dialog().notification('Sledování O2TV', 'Seznam kanálů byl resetovaný', xbmcgui.NOTIFICATION_INFO, 5000) 

    def get_o2_channels(self):
        addon = xbmcaddon.Addon()
        channels = {}
        data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/channels/', data = None, header = get_header_unity())
        if 'err' in data:
            xbmcgui.Dialog().notification('O2TV','Problém při načtení kanálů z O2', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()           
        if 'result' in data and len(data['result']) > 0:
            for channel in data['result']:        
                channels.update({channel['channel']['channelKey'] : { 'name' : channel['channel']['name'], 'number' : int(channel['channel']['weight']), 'logo' : 'https://assets.o2tv.cz' + channel['channel']['images']['color']['url'], 'key' : channel['channel']['keyForCache'], 'available' : False, 'serviceid' : ''}})

        session = Session()
        for serviceid in session.services:
            for offer in session.services[serviceid]['offers']:
                post = {'locality' : session.services[serviceid]['locality'], 'tariff' : session.services[serviceid]['tariff'], 'isp' : session.services[serviceid]['isp'], 'language' : 'ces', 'deviceType' : addon.getSetting('devicetype'), 'liveTvStreamingProtocol' : 'HLS', 'offer' : offer}
                data = call_o2_api(url = 'https://app.o2tv.cz/sws/server/tv/channels.json', data = post, header = get_header(session.services[serviceid]))
                if 'err' in data:
                    xbmcgui.Dialog().notification('Sledování O2TV', 'Problém s načtením kanálů', xbmcgui.NOTIFICATION_ERROR, 5000)
                    sys.exit()  
                if 'channels' in data and len(data['channels']) > 0:
                    for channel in data['channels']:
                        if data['channels'][channel]['channelType'] == 'TV' and data['channels'][channel]['channelKey'] not in channels:
                            channels.update({data['channels'][channel]['channelKey'] : { 'name' : data['channels'][channel]['channelName'], 'number' : int(data['channels'][channel]['channelNumber']), 'key' : '', 'logo' : ''}})
                        if data['channels'][channel]['channelKey'] in channels:
                            channels[data['channels'][channel]['channelKey']].update({'available' : True})                        
                            if 'serviceid' not in channels[data['channels'][channel]['channelKey']] or len(channels[data['channels'][channel]['channelKey']]['serviceid']) == 0 or (channels[data['channels'][channel]['channelKey']]['serviceid'] != serviceid and len(session.services[serviceid]['offers']) > len(session.services[channels[data['channels'][channel]['channelKey']]['serviceid']]['offers'])):
                                channels[data['channels'][channel]['channelKey']].update({'serviceid' : serviceid})
        return channels

    def merge_channels(self, o2channels, channels_nums = {}):
        if len(channels_nums) > 0:
            for number in sorted(channels_nums.keys()):
                max_number = number
        else:
            max_number = 0
        if len(self.channels):
            max_number = self.channels[max(self.channels, key = lambda channel: self.channels[channel]['number'])]['number']
        for channel in sorted(o2channels, key = lambda channel: o2channels[channel]['number']):
            if channel in self.channels:
                if self.channels[channel]['name'] != o2channels[channel]['name']:
                    self.channels[channel].update({'name' : o2channels[channel]['name']})
                if self.channels[channel]['o2number'] != o2channels[channel]['number']:
                    self.channels[channel].update({'o2number' : o2channels[channel]['number']})
                if self.channels[channel]['logo'] != o2channels[channel]['logo']:
                    self.channels[channel].update({'logo' : o2channels[channel]['logo']})
                if self.channels[channel]['key'] != o2channels[channel]['key']:
                    self.channels[channel].update({'key' : o2channels[channel]['key']})
                if self.channels[channel]['available'] != o2channels[channel]['available']:
                    self.channels[channel].update({'available' : o2channels[channel]['available']})
                # if self.channels[channel]['serviceid'] != o2channels[channel]['serviceid']:
                #     self.channels[channel].update({'serviceid' : o2channels[channel]['serviceid']})
            else:
                channelKey = channel
                name = o2channels[channel]['name']
                available = o2channels[channel]['available']
                o2number = o2channels[channel]['number']
                key = o2channels[channel]['key']
                if available == True:
                    if len(channels_nums) > 0:
                        number = -1
                        for num in sorted(channels_nums.keys()):
                            if channels_nums[num] == name:
                                number = num
                        if number == -1:
                            max_number = max_number + 1
                            number = max_number
                    else:
                        max_number = max_number + 1
                        number = max_number
                else:
                    number = -1
                logo = o2channels[channel]['logo']
                visible = True
                serviceid = o2channels[channel]['serviceid']
                self.channels.update({channel : {'channelKey' : channelKey, 'name' : name, 'available' : available, 'o2number' : o2number, 'number' : number, 'key' : key, 'logo' : logo, 'visible' : visible, 'serviceid' : serviceid}})
        for channel in self.channels.keys():
            if channel not in o2channels:
                del self.channels[channel]
    
    def migrate_channels(self):
        channels_nums = {}
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
        filename = os.path.join(addon_userdata_dir, 'channels.txt')
        try:
            with codecs.open(filename, 'r', encoding='utf-8') as file:
                for line in file:
                    channel = line[:-1].split(";")
                    channels_nums.update({ int(channel[1]) : channel[0]})
        except IOError:
            pass        
        return channels_nums

class Channels_groups:
    def __init__(self):
        self.groups = []
        self.channels = {}
        self.selected = None
        self.load_channels_groups()

    def add_channel_to_group(self, channel, group):
        channel_group = []
        channels = Channels()
        channels_list = channels.get_channels_list('number', visible_filter = False)
    
        for number in sorted(channels_list.keys()):
            if (group in self.channels and channels_list[number]['channelKey'] in self.channels[group]) or channels_list[number]['channelKey'] == channel:
                channel_group.append(channels_list[number]['channelKey'])
        if group in self.channels:
            del self.channels[group]
        self.channels.update({group : channel_group})
        self.save_channels_groups()
        if group == self.selected:
            self.select_group(group) 

    def add_all_channels_to_group(self, group):
        channel_group = []
        channels = Channels()
        channels_list = channels.get_channels_list('number', visible_filter = False)
        if group in self.channels:
            del self.channels[group]
        for number in sorted(channels_list.keys()):
            channel_group.append(channels_list[number]['channelKey'])
        self.channels.update({group : channel_group})
        self.save_channels_groups()
        if group == self.selected:
            self.select_group(group) 

    def delete_channel_from_group(self, channel, group):
        self.channels[group].remove(channel)
        self.save_channels_groups()
        if group == self.selected:
            self.select_group(group) 

    def add_channels_group(self, group):
        self.groups.append(group)
        self.save_channels_groups()

    def delete_channels_group(self, group):
        self.groups.remove(group)
        if group in self.channels:
            del self.channels[group]
        if self.selected == group:
            self.selected = None
            self.save_channels_groups()
            self.select_group('all')
        self.save_channels_groups()

    def select_group(self, group):
        channels = Channels()
        if group == 'all':
            self.selected = None
            channels_list = channels.get_channels_list(visible_filter = False)
            for channel in channels_list:
                channels.set_visibility(channel, True)
        else:
            self.selected = group
            if group in self.channels and len(self.channels[group]):
                channels_list = channels.get_channels_list(visible_filter = False)
                for channel in channels_list:
                    if channel in self.channels[group]:
                        channels.set_visibility(channel, True)
                    else:
                        channels.set_visibility(channel, False)
        self.save_channels_groups()      

    def load_channels_groups(self):
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 
        filename = os.path.join(addon_userdata_dir, 'channels_groups.txt')
        try:
            with codecs.open(filename, 'r', encoding='utf-8') as file:
                for line in file:
                    if line[:-1].find(';') != -1:
                        channel_group = line[:-1].split(';')
                        if channel_group[0] in self.channels:
                            groups = self.channels[channel_group[0]]
                            groups.append(channel_group[1])
                            self.channels.update({channel_group[0] : groups})
                        else:
                            self.channels.update({channel_group[0] : [channel_group[1]]})
                    else:
                        group = line[:-1]
                        if group[0] == '*':
                            self.selected = group[1:]
                            self.groups.append(group[1:])
                        else:
                            self.groups.append(group)
        except IOError:
            self.groups = []
            self.channels = {}
            self.selected = None

    def save_channels_groups(self):
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 
        filename = os.path.join(addon_userdata_dir, 'channels_groups.txt')
        if(len(self.groups)) > 0:
            try:
                with codecs.open(filename, 'w', encoding='utf-8') as file:
                    for group in self.groups:
                        if group == self.selected:
                            line = '*' + group
                        else:
                            line = group
                        file.write('%s\n' % line)
                    for group in self.groups:
                        if group in self.channels:
                            for channel in self.channels[group]:
                                line = group + ';' + channel
                                file.write('%s\n' % line)
            except IOError:
                xbmc.log('Chyba uložení skupiny')   
        else:
            if os.path.exists(filename):
                os.remove(filename) 
