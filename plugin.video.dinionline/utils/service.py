import time
import xbmc
from xbmcaddon import Addon

from mrdini.routines import routines
from poller import DigiPlayer


class BackgroundMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        self.addon_id = "plugin.video.dinionline"


if __name__ == "__main__":
    xbmc.log("DINIONLINE Monitor started")
    monitor = BackgroundMonitor()
    playback_checker = DigiPlayer(utils=routines.Utils(Addon(id=monitor.addon_id)))

    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break
        # dummy keepalive thing
