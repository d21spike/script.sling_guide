import calendar, datetime, time, json, os, requests, sys, urllib, sqlite3, string, traceback
from kodi_six import xbmc, xbmcvfs, xbmcplugin, xbmcgui, xbmcaddon

ADDON_NAME = 'Sling Guide'
ADDON_ID = 'script.sling_guide'
SLING_ADDON_ID = 'plugin.video.sling'
SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_URL = 'script://script.sling_guide/'
ADDON_VERSION = SETTINGS.getAddonInfo('version')
ADDON_PATH = SETTINGS.getAddonInfo('path')
IMAGE_PATH = xbmcvfs.translatePath(os.path.join(ADDON_PATH, 'resources', 'skins', 'default', 'media'))
HANDLE_ID = -1
DEBUG = SETTINGS.getSetting('Enable_Debugging') == 'true'
ICON = SETTINGS.getAddonInfo('icon')
FANART = SETTINGS.getAddonInfo('fanart')
UPDATE_LISTING = False
CACHE = False
PRINTABLE = set(string.printable)
SLING = 'plugin://plugin.video.sling/?mode=play&url='
SLING_SETTINGS = xbmcaddon.Addon(id=SLING_ADDON_ID)
SLING_SETTINGS_LOC = SLING_SETTINGS.getAddonInfo('profile')
DB_PATH = xbmcvfs.translatePath(os.path.join(SLING_SETTINGS_LOC, 'sling.db'))

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
             'Chrome/69.0.3497.100 Safari/537.36'
HEADERS = {'Accept': '*/*',
           'Origin': 'https://www.sling.com',
           'User-Agent': USER_AGENT,
           'Content-Type': 'application/json;charset=UTF-8',
           'Referer': 'https://www.sling.com',
           'Accept-Encoding': 'gzip, deflate, br',
           'Accept-Language': 'en-US,en;q=0.9'}
BASE_WEB = 'https://webapp.movetv.com'
WEB_ENDPOINTS = '%s/config/env-list/browser-sling.json' % (BASE_WEB)
VERIFY = True

CONTENT_TYPE = 'Movies'


ACTION_LEFT = 1
ACTION_RIGHT = 2
ACTION_UP = 3
ACTION_DOWN = 4
ACTION_PGUP = 5
ACTION_PGDOWN = 6
ACTION_ENTER = 7
ACTION_BKSPACE = 92
ACTION_ESCAPE = 10
ACTION_LEFTCLICK = 100
ACTION_HOME = 159
ACTION_END = 160


if sys.version_info[0] < 3:
    PY = 2
    import urlparse
    urlLib = urllib
    urlParse = urlparse
else:
    PY = 3
    urlLib = urllib.parse
    urlParse = urlLib


def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR:
        return
    if level == xbmc.LOGERROR:
        msg += ' ,' + traceback.format_exc()
    if PY == 3:
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    else:
        try:
            xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
        except:
            xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + strip(msg), level)


def addDir(name, handleID, url, mode, info=None, art=None, menu=None):
    global CONTENT_TYPE, ADDON_URL
    log('Adding directory %s' % name)
    directory = xbmcgui.ListItem(name)
    directory.setProperty('IsPlayable', 'false')
    if info is None:
        directory.setInfo(type='Video', infoLabels={
                          'mediatype': 'videos', 'title': name})
    else:
        if 'mediatype' in info:
            CONTENT_TYPE = '%ss' % info['mediatype']
        directory.setInfo(type='Video', infoLabels=info)
    if art is None:
        directory.setArt({'thumb': ICON, 'fanart': FANART})
    else:
        directory.setArt(art)

    if menu is not None:
        directory.addContextMenuItems(menu)

    try:
        name = urlLib.quote_plus(name)
    except:
        name = urlLib.quote_plus(strip(name))
    if url != '':
        url = ('%s?url=%s&mode=%s&name=%s' %
               (ADDON_URL, urlLib.quote_plus(url), mode, name))
    else:
        url = ('%s?mode=%s&name=%s' % (ADDON_URL, mode, name))
    log('Directory %s URL: %s' % (name, url))
    xbmcplugin.addDirectoryItem(
        handle=handleID, url=url, listitem=directory, isFolder=True)
    xbmcplugin.addSortMethod(
        handle=handleID, sortMethod=xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)


def addLink(name, handleID,  url, mode, info=None, art=None, total=0, contextMenu=None, properties=None):
    global CONTENT_TYPE, ADDON_URL
    log('Adding link %s' % name)
    link = xbmcgui.ListItem(name)
    if mode == 'info':
        link.setProperty('IsPlayable', 'false')
    else:
        link.setProperty('IsPlayable', 'true')
    if info is None:
        link.setInfo(type='Video', infoLabels={
                     'mediatype': 'video', 'title': name})
    else:
        if 'mediatype' in info:
            CONTENT_TYPE = '%ss' % info['mediatype']
        link.setInfo(type='Video', infoLabels=info)
    if art is None:
        link.setArt({'thumb': ICON, 'fanart': FANART})
    else:
        link.setArt(art)
    if contextMenu is not None:
        link.addContextMenuItems(contextMenu)
    if properties is not None:
        log('Adding Properties: %s' % str(properties))
        for key, value in properties.items():
            link.setProperty(key, str(value))
    try:
        name = urlLib.quote_plus(name)
    except:
        name = urlLib.quote_plus(strip(name))
    if url != '':
        xbmcplugin.addDirectoryItem(handle=handleID, url=url, listitem=link, totalItems=total)
        xbmcplugin.addSortMethod(handle=handleID, sortMethod=xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)


def timeStamp(date):
    return calendar.timegm(date.timetuple())


def stringToDate(string, date_format):
    try:
        return datetime.datetime.strptime(str(string), date_format)
    except TypeError:
        return datetime.datetime(*(time.strptime(str(string), date_format)[0:6]))


def strip(str):
    return "".join(list(filter(lambda x: x in PRINTABLE, str)))
