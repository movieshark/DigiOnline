# -*- coding: utf-8 -*-
"""
    DigiOnline Kodi addon
    Copyright (C) 2019 Mr Dini
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.
    You should have received a copy of the GNU Affero General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>
"""

import sys
from re import findall
from urlparse import parse_qsl
from mrdini.routines import routines, parsedom
from xbmcaddon import Addon
from xbmcplugin import endOfDirectory, setContent

utils = routines.Utils(Addon())

MAIN_URL = "470098bXNyZXBvIGh0dHBzOi8vZGlnaW9ubGluZS5odQ=="
EULA_URL = "470098bXNyZXBvIGh0dHA6Ly9kaWdpLmh1L2luZm9ybWFjaW8vYWRhdHZlZGVsbWktZXMtZmVsaGFzem5hbGFzaS1mZWx0ZXRlbGVr"


def update_cookies(response):
    token = parsedom.parseDOM(
        response.content, name="meta", attrs={"name": "csrf-token"}, ret="content"
    )
    if token:
        utils.set_setting("csrf_token", token[0].encode("utf-8"))
    for k, v in response.cookies.items():
        if k == "XSRF-TOKEN":
            utils.set_setting("xsrf_token", v)
        elif k == "laravel_session":
            utils.set_setting("laravel_session", v)
        elif k == "acc_pp":
            utils.set_setting("acc_pp", v)


def cookie_builder():
    return {
        "XSRF-TOKEN": utils.get_setting("xsrf_token"),
        "laravel_session": utils.get_setting("laravel_session"),
        "acc_pp": utils.get_setting("acc_pp"),
    }


def login():
    headers = {
        "Origin": routines.decrypt_string(MAIN_URL),
        "Accept-Encoding": "gzip, deflate, br",
        "X-CSRF-TOKEN": utils.get_setting("csrf_token"),
        "Accept-Language": "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "*/*",
        "Referer": "%s/csatornak" % (routines.decrypt_string(MAIN_URL)),
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "keep-alive",
    }
    data = {
        "email": utils.get_setting("username"),
        "password": utils.get_setting("password"),
        "accept": "1",  # the privacy rules
    }
    response = routines.request_page(
        "%s/login" % (routines.decrypt_string(MAIN_URL)),
        headers=headers,
        user_agent=utils.get_setting("user_agent"),
        cookies=cookie_builder(),
        data=data,
        allow_redirects=False,
    )
    update_cookies(response)
    if response.status_code != 302:
        utils.create_ok_dialog(
            "Helytelen bejelentkezési adatok! (Kód: %i)" % (response.status_code)
        )
        utils.open_settings()
        exit()
    utils.create_notification("Sikeres bejelentkezés!")


def main_window():
    routines.add_item(
        *sys.argv[:2],
        name="Élő Csatornakínálat",
        action="channels",
        is_directory=True,
        fanart=utils.fanart,
        icon="https://i.imgur.com/n0AbCQn.png"
    )
    routines.add_item(
        *sys.argv[:2],
        name="Mentett sütik törlése",
        action="clear_creds",
        description="A kiegészítő tárolja a sütiket, user-agentet és az azonosításhoz használatos egyedi tokent annak érdekében, hogy egy"
        " böngésző benyomását keltse, illetve spóroljon az adatforgalommal. Ez az opció hasznos lehet, amennyiben a bejelentkezési adatokat"
        " frissítetted, illetve ha szeretnél egy új user-agentet kapni a kiegészítőtől. Az adatok frissítése a legközelebbi csatornalista"
        " megnyitáskor történik.",
        is_directory=False,
        fanart=utils.fanart,
        icon="https://i.imgur.com/1T2DUvG.png"
    )
    routines.add_item(
        *sys.argv[:2],
        name="Beállítások",
        description="Addon beállításai",
        action="settings",
        is_directory=False,
        fanart=utils.fanart,
        icon="https://i.imgur.com/MI42pRz.png"
    )
    routines.add_item(
        *sys.argv[:2],
        name="A kiegészítőről",
        description="Egyéb infók",
        action="about",
        is_directory=False,
        fanart=utils.fanart,
        icon="https://i.imgur.com/bKJK0nc.png"
    )


def live_window():
    if not utils.get_setting("user_agent"):
        utils.set_setting("user_agent", routines.random_uagent())
    headers = {
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    response = routines.request_page(
        "%s/csatornak" % (routines.decrypt_string(MAIN_URL)),
        user_agent=utils.get_setting("user_agent"),
        headers=headers,
    )
    update_cookies(response)
    login()
    for channel in parsedom.parseDOM(
        response.content, name="div", attrs={"class": '[^"]+channel'}
    ):
        try:
            url = "%s/player/%s" % (
                routines.decrypt_string(MAIN_URL),
                parsedom.parseDOM(
                    channel, "a", attrs={"data-id": '[^"]+'}, ret="data-id"
                )[0],
            )
        except:
            continue
            # if we have no way to stream, why would we even bother showing it
        try:
            logo = parsedom.parseDOM(
                parsedom.parseDOM(
                    channel, name="div", attrs={"class": ".+?channels__logo"}
                )[0],
                name="img",
                ret="src",
            )[0]
        except:
            logo = ""
        try:
            program_name = (
                parsedom.replaceHTMLCodes(
                    parsedom.parseDOM(
                        parsedom.parseDOM(
                            channel,
                            name="div",
                            attrs={"class": ".+?channels__program_name"},
                        )[0],
                        name="a",
                    )[0]
                )
                .encode("utf-8")
                .strip()
            )
        except:
            program_name = ""
        try:
            name = (
                parsedom.replaceHTMLCodes(
                    parsedom.parseDOM(
                        channel, name="div", attrs={"class": "channels__name.+?"}
                    )[0]
                )
                .encode("utf-8")
                .strip()
            )
        except:
            name = ""
        description = []
        try:
            timing = parsedom.removeHTMLCodes(
                parsedom.replaceHTMLCodes(
                    parsedom.parseDOM(channel, name="p", attrs={"class": "timing.+?"})[
                        0
                    ]
                ).encode("utf-8")
            ).strip()
        except:
            timing = None
        try:
            progress = parsedom.parseDOM(
                channel,
                name="div",
                attrs={"class": "progress-bar"},
                ret="aria-valuenow",
            )[0].split(".", 1)[0]
        except:
            pass
        if timing and progress:
            description.append(
                "Sugárzási idő: %s (Jelenleg: %s%%)"
                % (timing.encode("utf-8"), progress.encode("utf-8"))
            )
        elif timing:
            description.append("Sugárzási idő: %s" % (timing.encode("utf-8")))
        else:
            description.append("Jelenleg: %s%%" % (progress.encode("utf-8")))
        try:
            description.append(
                parsedom.replaceHTMLCodes(
                    parsedom.parseDOM(
                        channel, name="p", attrs={"class": "description"}
                    )[0]
                )
                .encode("utf-8")
                .strip()
            )
        except:
            pass
        try:
            description.append(
                "[COLOR yellow]Korhatár besorolás: %s[/COLOR]"
                % (
                    parsedom.parseDOM(
                        channel, name="span", attrs={"class": 'age-[^"]+'}, ret="class"
                    )[0]
                    .encode("utf-8")
                    .replace("age-", "")
                )
            )
        except:
            pass
        try:
            description.append(
                "[I]%s[/I]"
                % (
                    parsedom.replaceHTMLCodes(
                        parsedom.parseDOM(
                            channel, name="div", attrs={"class": "next_program"}
                        )[0]
                    )
                    .encode("utf-8")
                    .strip()
                )
            )
        except:
            pass
        if program_name and name:
            final_name = "%s[CR][COLOR gray]%s[/COLOR]" % (name, program_name)
        else:
            final_name = name or program_name
        routines.add_item(
            *sys.argv[:2],
            name=final_name,
            icon=logo,
            action="play",
            extra=url,
            description="[CR][CR]".join(description),
            fanart=utils.fanart,
            is_directory=False,
            refresh=True
        )

    setContent(int(sys.argv[1]), "tvshows")


def resolve_url(name, icon, url, description):
    headers = {
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    response = routines.request_page(
        url,
        headers=headers,
        user_agent=utils.get_setting("user_agent"),
        cookies=cookie_builder(),
        allow_redirects=False,
    )
    update_cookies(response)
    url = findall("createDefaultPlayer\('([^']+)'[^\)]+\);", response.content)
    if response.status_code == 302:
        utils.create_ok_dialog(
            "Nem sikerült a lejátszás. Ez a hiba akkor szokott előfordulni, ha párhuzamosan"
            " történik egy másik bejelentkezés. Kérem frissítse a csatornalistát az újbóli bejelentkezéshez!"
        )
        exit(1)
    elif not url or response.status_code != 200:
        utils.create_ok_dialog(
            "Nem sikerült kinyerni a lejátszási linket. Elképzelhető, hogy magasabb előfizetés szükséges."
        )
        exit()

    routines.play(
        int(sys.argv[1]),
        url[0],
        "video",
        user_agent=utils.get_setting("user_agent"),
        name=name,
        description=description,
        icon=icon,
    )


if __name__ == "__main__":
    params = dict(parse_qsl(sys.argv[2].replace("?", "")))
    action = params.get("action")
    if action is None:
        if utils.get_setting("is_firstrun") == "true":
            from utils.information import text, eula

            utils.create_textbox(text % (utils.addon_name, utils.version))
            if not utils.create_yesno_dialog(
                eula % (routines.decrypt_string(EULA_URL)),
                yes="Elfogadom",
                no="Kilépek",
            ):
                exit()
            utils.set_setting("is_firstrun", "false")
            utils.create_ok_dialog("Kérlek jelentkezz be az addon használatához!")
            utils.open_settings()
            exit()
        main_window()
        endOfDirectory(int(sys.argv[1]))
    if action == "channels":
        live_window()
        endOfDirectory(int(sys.argv[1]))
    if action == "clear_creds":
        utils.set_setting("xsrf_token", "")
        utils.set_setting("csrf_token", "")
        utils.set_setting("laravel_session", "")
        utils.set_setting("acc_pp", "")
        utils.set_setting("user_agent", "")
        utils.create_notification("Adatok sikeresen törölve!")
    if action == "play":
        resolve_url(
            params.get("name"),
            params.get("icon"),
            params.get("extra"),
            params.get("descr"),
        )
    if action == "settings":
        utils.open_settings()
    if action == "about":
        from utils.information import text

        utils.create_textbox(text % (utils.addon_name, utils.version))
