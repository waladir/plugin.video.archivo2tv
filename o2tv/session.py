# -*- coding: utf-8 -*-
import sys
import os
import xbmcaddon
import xbmcgui

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

try:
    from urllib2 import urlopen, Request, HTTPError
except ImportError:
    from urllib.request import urlopen, Request

import json
import time 
import codecs
from datetime import datetime
from o2tv.o2api import call_o2_api, get_header, get_header_unity

class Session:
    def __init__(self):
        self.valid_to = -1
        self.load_session()

    def get_services(self, filtered = 1):
        services_order = {}
        services = []
        for serviceid in self.services:
            if self.services[serviceid]['enabled'] == 1 or filtered == 0:
                services_order.update({ self.services[serviceid]['order'] : serviceid})
            
        for order in sorted(services_order.keys()):
            services.append(services_order[order])
        return services

    def enable_service(self, serviceid):
        if serviceid in self.services:
            self.services[serviceid]['enabled'] = 1
            self.save_session()

    def disable_service(self, serviceid):
        if serviceid in self.services:
            self.services[serviceid]['enabled'] = 0
            self.save_session()

    def set_service_order(self, serviceid, order):
        if serviceid in self.services:
            self.services[serviceid]['order'] = order
            self.save_session()

    def get_service(self, serviceid):
        if serviceid in self.services:
            description = self.services[serviceid]['description']
            access_token = self.services[serviceid]['access_token']
            refresh_token = self.services[serviceid]['refresh_token']
            expires_in = self.services[serviceid]['expires_in']
            subscription = self.services[serviceid]['subscription']
            isp = self.services[serviceid]['isp']
            locality = self.services[serviceid]['locality']
            offers = self.services[serviceid]['offers']
            tariff = self.services[serviceid]['tariff']
            sdata = self.services[serviceid]['sdata']
            encodedChannels = self.services[serviceid]['encodedChannels']   
            enabled = self.services[serviceid]['enabled']         
            order = self.services[serviceid]['order']
            return { 'description' : description, 'access_token' : access_token, 'refresh_token' : refresh_token, 'expires_in' : expires_in, 'subscription' : subscription, 'isp' : isp, 'locality' : locality, 'offers' : offers, 'tariff' : tariff, 'sdata' : sdata, 'encodedChannels' : encodedChannels, 'enabled' : enabled, 'order' : order}
        else:
            return None

    def create_session(self, data = None):
        addon = xbmcaddon.Addon()
        if '@' in addon.getSetting('username'):
            self.get_auth_token()
        else:
            self.get_auth_password() 
        order = 1
        if self.services and len(self.services) > 0:
            for service in self.services:
                if data and len(data) > 0 and 'services' in data and service in data['services']:
                    if 'enabled' in data['services'][service]:
                        self.services[service].update({'enabled' : data['services'][service]['enabled']})
                    else:
                        self.services[service].update({'enabled' : 1})
                    if 'order' in data['services'][service]:
                        self.services[service].update({'order' : data['services'][service]['order']})    
                        order = data['services'][service]['order'] + 1                   
                    else:
                        self.services[service].update({'order' : order})
                        order = order + 1
                else:
                    self.services[service].update({'enabled' : 1})
                    self.services[service].update({'order' : order})
                    order = order + 1
        if self.valid_to > 0:
            self.save_session()

    def load_session(self):
        data = None
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
        filename = os.path.join(addon_userdata_dir, 'session.txt')
        try:
            with codecs.open(filename, 'r', encoding='utf-8') as file:
                for row in file:
                    data = row[:-1]
        except IOError as error:
            if error.errno != 2:
                xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba při načtení session', xbmcgui.NOTIFICATION_ERROR, 5000)

        if data is not None:
            data = json.loads(data)
            self.valid_to = int(data['valid_to'])
            reset = 0
            if 'services' in data and self.valid_to and self.valid_to > 0 and self.valid_to > int(time.time()):
                self.services = data['services']
                for serviceid in self.services:
                    service = self.services[serviceid]
                    if 'expires_in' not in service or int(service['expires_in']) < int(time.time()):
                        if 'refresh_token' not in service:
                            service['refresh_token'] = ''
                        access_token, refresh_token, expires_in = self.refresh_token(service['access_token'], service['refresh_token'])
                        if access_token is not None:
                            self.services[serviceid].update({'access_token' : access_token, 'refresh_token' : refresh_token, 'expires_in' : expires_in})
                            self.save_session()
                        else:
                            reset = 1
                    if 'enabled' not in self.services[serviceid]:
                        reset = 1
                if reset == 1:
                    self.valid_to = -1
                    if 'services' in data:
                        self.create_session(data)
                    else:
                        self.create_session()                    
            else:
                self.valid_to = -1
                if 'services' in data:
                    self.create_session(data)
                else:
                    self.create_session()
        else:
            self.valid_to = -1
            self.create_session()

    def save_session(self):
        data = json.dumps({'services' : self.services, 'valid_to' : self.valid_to})
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
        filename = os.path.join(addon_userdata_dir, 'session.txt')
        try:
            with codecs.open(filename, 'w', encoding='utf-8') as file:
                file.write('%s\n' % data)
        except IOError:
            xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba uložení session', xbmcgui.NOTIFICATION_ERROR, 5000)

    def remove_session(self):
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
        filename = os.path.join(addon_userdata_dir, 'session.txt')
        if os.path.exists(filename):
            try:
                data = None
                with codecs.open(filename, 'r', encoding='utf-8') as file:
                    for row in file:
                        data = row[:-1]
                if data is not None:
                    data = json.loads(data)
                    if 'services' not in data:
                        data = None
                os.remove(filename) 
            except IOError:
                xbmcgui.Dialog().notification('Sledování O2TV', 'Chyba při resetu session', xbmcgui.NOTIFICATION_ERROR, 5000)
        self.valid_to = -1
        self.create_session(data)
        xbmcgui.Dialog().notification('Sledování O2TV', 'Byla vytvořená nová session', xbmcgui.NOTIFICATION_INFO, 5000)

    def get_auth_token(self):
        addon = xbmcaddon.Addon()
        self.services = {}
        post = {'username' : addon.getSetting('username'), 'password' : addon.getSetting('password')} 
        data = call_o2_api(url = 'https://ottmediator.o2tv.cz/ottmediator-war/login', data = post, header = get_header())
        if 'err' in data:
            xbmcgui.Dialog().notification('Sledování O2TV','Problém při přihlášení', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()    

        if 'services' in data and 'remote_access_token' in data and len(data['remote_access_token']) > 0 and len(data['services']) > 0:
            remote_access_token = data['remote_access_token'] 
            for service in data['services']:
                service_id = service['service_id']
                service_desc = service['description']

                post = {'service_id' : service_id, 'remote_access_token' : remote_access_token}
                data = call_o2_api(url = 'https://ottmediator.o2tv.cz/ottmediator-war/loginChoiceService', data = post, header = get_header())
                if 'err' in data:
                    pass
                    # xbmcgui.Dialog().notification('Sledování O2TV','Problém při přihlášení', xbmcgui.NOTIFICATION_ERROR, 5000)
                else:
                    post = {'grant_type' : 'remote_access_token', 'client_id' : 'tef-web-portal-etnetera', 'client_secret' : '2b16ac9984cd60dd0154f779ef200679', 'platform_id' : '231a7d6678d00c65f6f3b2aaa699a0d0', 'language' : 'cs', 'remote_access_token' : str(remote_access_token), 'authority' :  'tef-sso', 'isp_id' : '1'}
                    data = call_o2_api(url = 'https://oauth.o2tv.cz/oauth/token', data = post, header = get_header())
                    if 'err' in data:
                        xbmcgui.Dialog().notification('Sledování O2TV','Problém při přihlášení - token', xbmcgui.NOTIFICATION_ERROR, 5000)
                    else:
                        if 'access_token' in data and len(data['access_token']) > 0:
                            access_token = data['access_token']
                            refresh_token = data['refresh_token']
                            expires_in = 0
                            self.get_subscription(access_token, refresh_token, expires_in, service_id, service_desc)
                        else:
                            xbmcgui.Dialog().notification('Sledování O2TV','Problém s příhlášením - token', xbmcgui.NOTIFICATION_ERROR, 5000)
        else:
            xbmcgui.Dialog().notification('Sledování O2TV','Problém s příhlášením', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()
        if len(self.services) < 1:
            xbmcgui.Dialog().notification('Sledování O2TV','Problém s příhlášením - služby', xbmcgui.NOTIFICATION_ERROR, 5000)

    def get_auth_password(self):
        addon = xbmcaddon.Addon()
        self.services = {}        
        post = {'grant_type' : 'password', 'client_id' : 'tef-web-portal-etnetera', 'client_secret' : '2b16ac9984cd60dd0154f779ef200679', 'platform_id' : '231a7d6678d00c65f6f3b2aaa699a0d0', 'language' : 'cs', 'username' : addon.getSetting('username'), 'password' : addon.getSetting('password')}
        data = call_o2_api(url = 'https://oauth.o2tv.cz/oauth/token', data = post, header = get_header())
        if 'err' in data:
            xbmcgui.Dialog().notification('Sledování O2TV','Problém při přihlášení', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()  
        if 'access_token' in data and len(data['access_token']) > 0:
            access_token = data['access_token']
            refresh_token = data['refresh_token']
            expires_in = 0
            self.get_subscription(access_token, refresh_token, expires_in, 'password_authentication', 'password_authentication')
        else:
            xbmcgui.Dialog().notification('Sledování O2TV','Problém s příhlášením - token', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()            

    def get_subscription(self, access_token, refresh_token, expires_in, service_id, service_description):
        addon = xbmcaddon.Addon()
        header = get_header()
        header.update({'X-NanguTv-Access-Token' : str(access_token), 'X-NanguTv-Device-Id' : addon.getSetting('deviceid')})
        data = call_o2_api(url = 'https://app.o2tv.cz/sws/subscription/settings/subscription-configuration.json', data = None, header = header)
        if 'err' in data:
            xbmcgui.Dialog().notification('Sledování O2TV','Problém při přihlášení - subskripce', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()  
        if 'isp' in data and len(data['isp']) > 0 and 'locality' in data and len(data['locality']) > 0 and 'billingParams' in data and len(data['billingParams']) > 0 and 'offers' in data['billingParams'] and len(data['billingParams']['offers']) > 0 and 'tariff' in data['billingParams'] and len(data['billingParams']['tariff']) > 0:
            subscription = data['subscription']
            isp = data['isp']
            locality = data['locality']
            offers = data['billingParams']['offers']
            tariff = data['billingParams']['tariff']
            header_unity = get_header_unity()
            header_unity.update({'x-o2tv-access-token' : str(access_token), 'x-o2tv-device-id' : addon.getSetting('deviceid'), 'x-o2tv-device-name' : addon.getSetting('devicename')})
            data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/user/profile/', data = None, header = header_unity)
            if 'err' in data:
                xbmcgui.Dialog().notification('Sledování O2TV','Problém při přihlášení - profil', xbmcgui.NOTIFICATION_ERROR, 5000)
                sys.exit()   
            sdata = data['sdata']
            encodedChannels = data['encodedChannels']
            channels = data['ottChannels']['live']  
            self.valid_to = int(time.time()) + 60*60*24*7
            self.services.update({service_id : { 'description' : service_description, 'access_token' : access_token, 'refresh_token' : refresh_token, 'expires_in' : expires_in, 'subscription' : subscription, 'isp' : isp, 'locality' : locality, 'offers' : offers, 'tariff' : tariff, 'sdata' : sdata, 'encodedChannels' : encodedChannels, 'channels' : channels}})
        else:
            xbmcgui.Dialog().notification('Sledování O2TV','Problém s příhlášením - subskribce', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()        

    def get_auth_web(self):
        addon = xbmcaddon.Addon()        
        post = {'username' : addon.getSetting('username'), 'password' : addon.getSetting('password')} 
        req = Request('https://api.o2tv.cz/unity/api/v1/services/')
        req.add_header('Content-Type', 'application/json')
        resp = urlopen(req, json.dumps(post))
        data = json.loads(resp.read())
        if 'err' in data:
            xbmcgui.Dialog().notification('Sledování O2TV','Problém při přihlášení', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()    

        if 'services' in data and 'remote_access_token' in data and len(data['remote_access_token']) > 0 and len(data['services']) > 0:
            remote_access_token = data['remote_access_token'] 

            for service in data['services']:
                service_id = service['service_id']
                post = {'remoteAccessToken' : remote_access_token} 
                req = Request('https://api.o2tv.cz/unity/api/v1/services/selection/' + service_id + '/')
                req.add_header('Content-Type', 'application/json')
                resp = urlopen(req, json.dumps(post))
                data = json.loads(resp.read())
                if 'err' in data:
                    xbmcgui.Dialog().notification('Sledování O2TV','Problém při přihlášení - služby', xbmcgui.NOTIFICATION_ERROR, 5000)
                    sys.exit()    

                if 'accessToken' in data and len(data['accessToken']) > 0:
                    access_token = data['accessToken']
                    header_unity = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0', 'Content-Type' : 'application/json', 'x-o2tv-access-token' : str(access_token), 'x-o2tv-device-id' : addon.getSetting('deviceid'), 'x-o2tv-device-name' : addon.getSetting('devicename')}
                    data = call_o2_api(url = 'https://api.o2tv.cz/unity/api/v1/user/profile/', data = None, header = header_unity)
                    if 'err' in data:
                        xbmcgui.Dialog().notification('Sledování O2TV','Problém při přihlášení - profil', xbmcgui.NOTIFICATION_ERROR, 5000)
                        sys.exit()   
                    isp = 1
                    subscription = data['code']
                    sdata = data['sdata']
                    locality = data['locality']
                    offers = data['subscription']['offers']
                    tariff = data['tariff']
                    encodedChannels = data['encodedChannels']
                    channels = data['ottChannels']['live']  
                    self.valid_to = int(time.time()) + 60*60*24*7
                    self.services.update({service_id : { 'access_token' : access_token, 'subscription' : subscription, 'isp' : isp, 'locality' : locality, 'offers' : offers, 'tariff' : tariff, 'sdata' : sdata, 'encodedChannels' : encodedChannels, 'channels' : channels}})

                else:
                    xbmcgui.Dialog().notification('Sledování O2TV','Problém při příhlášení - služby', xbmcgui.NOTIFICATION_ERROR, 5000)
                    sys.exit()            
        else:
            xbmcgui.Dialog().notification('Sledování O2TV','Problém při přihlášení', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()

    def refresh_token(self, access_token, refresh_token):
        post = {'grant_type' : 'refresh_token', 'client_id' : 'tef-web-portal-etnetera', 'client_secret' : '2b16ac9984cd60dd0154f779ef200679', 'platform_id' : '231a7d6678d00c65f6f3b2aaa699a0d0', 'language' : 'cs', 'refresh_token' : str(refresh_token)}
        data = call_o2_api(url = 'https://oauth.o2tv.cz/oauth/token', data = post, header = get_header())
        if 'err' in data:
            return None, None, -1

        if 'access_token' in data and len(data['access_token']) > 0:
            access_token = data['access_token']
            refresh_token = data['refresh_token']
            expires_in = int(time.time()) + int(data['expires_in'])
            return access_token, refresh_token, expires_in
        else:
            return None, None, -1
