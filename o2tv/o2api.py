# -*- coding: utf-8 -*-

import sys
import os
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

try:
    from urllib2 import urlopen, Request, HTTPError
    from urllib import urlencode, quote
    from urlparse import parse_qsl    
except ImportError:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode, quote, parse_qsl
    from urllib.error import HTTPError

import json
import time

from o2tv.utils import encode

def get_header_unity(service = None):
    addon = xbmcaddon.Addon()
    header = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0', 'Content-Type' : 'application/json'}
    if service != None:
        header.update({'x-o2tv-access-token' : str(service['access_token']), 'x-o2tv-sdata' : str(service['sdata']), 'x-o2tv-device-id' : addon.getSetting('deviceid'), 'x-o2tv-device-name' : addon.getSetting('devicename')})
        return header
    else:
        return header

def get_header(service = None):
    addon = xbmcaddon.Addon()
    header = {'X-NanguTv-App-Version' : 'Android#6.4.1', 'User-Agent' : 'Dalvik/2.1.0', 'Accept-Encoding' : 'gzip', 'Connection' : 'Keep-Alive', 'Content-Type' : 'application/x-www-form-urlencoded;charset=UTF-8', 'X-NanguTv-Device-Id' : addon.getSetting('deviceid'), 'X-NanguTv-Device-Name' : addon.getSetting('devicename')}
    if service != None:
         header.update({'X-NanguTv-Access-Token' : str(service['access_token']), 'X-NanguTv-Device-Id' : addon.getSetting('deviceid')})
    return header

def call_o2_api(url, data, header):
    addon = xbmcaddon.Addon()
    if data != None:
        data = urlencode(data)
        data = data.encode('utf-8')
    request = Request(url = url , data = data, headers = header)
    if addon.getSetting('log_request_url') == 'true':
        xbmc.log(str(url))
    try:
        html = urlopen(request).read()
        if addon.getSetting('log_response') == 'true':
            xbmc.log(str(html))
        if html and len(html) > 0:
            data = json.loads(html)
            return data
        else:
            return []
    except HTTPError as e:
        return { 'err' : e.reason }  

