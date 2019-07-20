# -*- coding: utf-8 -*-
import sys
import threading
import re
import xbmc

from mrdini.routines.routines import decrypt_string, request_page

NOT_PLAYING_WAIT_TIME = 0.2
PLAYING_WAIT_TIME = 5 * 60  # wait 5 minutes between each poll event
MAIN_URL = "470098bXNyZXBvIGh0dHBzOi8vZGlnaW9ubGluZS5odQ==" # TODO: better organize this
POLLER_URL_PREFIX = "%s/refresh" % (decrypt_string(MAIN_URL))


class PlaybackMonitorThread(threading.Thread):
    def __init__(self, utils):
        super(PlaybackMonitorThread, self).__init__()

        self._stopped = threading.Event()
        self._ended = (
            threading.Event()
        )  # probably not useful in livestreams' case but who knows
        self.utils = utils
        self.player = xbmc.Player()

        self.daemon = True
        self.start()

    def run(self):
        utils = self.utils
        before_playing_wait = 0.0
        while not self.player.isPlaying():
            xbmc.sleep(int(NOT_PLAYING_WAIT_TIME * 1000))
            if before_playing_wait >= 5:
                self.end()
                return  # couldn't start playing in 5 seconds
            before_playing_wait += NOT_PLAYING_WAIT_TIME
        while self.player.isPlaying():
            xbmc.log("Lejátszás folyamatban...")
            try:
                if not decrypt_string("470098bXNyZXBvIGh0dHBzOi8vb25saW5lLmRpZ2kuaHU=") in self.player.getPlayingFile():
                    xbmc.log("Nem a mienk...")
                    self.stop()
                    break
                try:
                    c_id = self.player.getPlayingFile().split("playlist/", 1)[1].split("/", 1)[0]
                except:
                    xbmc.log("Sikertelen csatornanév kinyerés", xbmc.LOGERROR)
                    self.stop()
                    break
                headers = {
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept": "*/*",
                    "Referer": "%s/player/%s" % (decrypt_string(MAIN_URL), c_id),
                    "X-Requested-With": "XMLHttpRequest",
                    "Connection": "keep-alive",
                }
                cookies = {
                    "XSRF-TOKEN": utils.get_setting("xsrf_token"),
                    "laravel_session": utils.get_setting("laravel_session"),
                    "acc_pp": utils.get_setting("acc_pp"),
                }
                response = request_page(
                    POLLER_URL_PREFIX,
                    params={"id": c_id},
                    cookies=cookies,
                    headers=headers,
                )
                xbmc.log("%s [%s] %s" % (response.url, response.status_code, response.content))
                for k, v in response.cookies.items():
                    if k == "XSRF-TOKEN":
                        utils.set_setting("xsrf_token", v)
                    elif k == "laravel_session":
                        utils.set_setting("laravel_session", v)
                    elif k == "acc_pp":
                        utils.set_setting("acc_pp", v)
                xbmc.log("Kérés elküldve...")
            except RuntimeError:
                pass
            xbmc.sleep(int(PLAYING_WAIT_TIME * 1000))
        self.end()

    def stop(self):
        self._stopped.set()

    def stopped(self):
        return self._stopped.is_set()

    def end(self):
        self._ended.set()

    def ended(self):
        return self._ended.is_set()


class DigiPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        self.utils = kwargs.get("utils")
        self.threads = []

    def stop_threads(self):
        for thread in self.threads:
            if thread.ended():
                continue

            if not thread.stopped():
                thread.stop()

        for thread in self.threads:
            if thread.stopped() and not thread.ended():
                try:
                    thread.join()
                except RuntimeError:
                    pass

    def cleanup_threads(self, only_ended=True):
        active_threads = []
        for thread in self.threads:
            if only_ended and not thread.ended():
                active_threads.append(thread)
                continue

            if not thread.ended() and not thread.stopped():
                thread.stop()
            try:
                thread.join()
            except RuntimeError:
                pass
        self.threads = active_threads

    def onPlayBackStarted(self):
        self.cleanup_threads()
        self.threads.append(
            PlaybackMonitorThread(self.utils)
        )

    def onPlayBackEnded(self):
        self.stop_threads()
        self.cleanup_threads()

    def onPlayBackStopped(self):
        self.onPlayBackEnded()

    def onPlayBackError(self):
        self.onPlayBackEnded()
