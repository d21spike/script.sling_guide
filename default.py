import sys, xbmcgui
from resources.lib import guide
from resources.lib.globals import log
from threading import Thread

try:
    window = guide.Guide()
    window.doModal()
    del window
except Exception:
    log("There was a problem launching the modal guide window.")
    xbmcgui.Dialog().ok("Error", "There was a problem launching the modal guide window.", "", "")
    
