#!/usr/bin/python
# -*- coding: cp1251 -*-

from html.parser import unescape
import socks
import requests
import socket
import logging


def get_cookie(params):
    log = params['logger']
    res = {}
    for key in params:
        if key != 'logger': # not serializable object
            res[key] = params[key]
    if params['proxy_port'] != -1:
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, params['proxy_ip'], params['proxy_port'])
        socket.socket = socks.socksocket
    try:
        post_params = {
            'login_username': params['username'],
            'login_password': params['password'],
            'login': b'\xe2\xf5\xee\xe4'  # '%E2%F5%EE%E4'
        }
        print(post_params, params['proxy_ip'], params['proxy_port'])
        r = requests.post('https://rutracker.org/forum/login.php',data=post_params,allow_redirects=False,timeout=20)
        if 'bb_data' in r.cookies.keys():
            cookie = 'bb_data=' + r.cookies['bb_data'] + '; tr_simple=1; spylog_test=1'
            res['cookie'] = cookie
            log.debug('cookie: %s' % cookie)
            return 'OK', res
        else:
            log.debug('no cookies returned')
            res['text'] = 'no cookies returned'
            return 'ERROR', res
    except requests.exceptions.RequestException as e:
        log.debug('request exception')
        res['text'] = 'request exception'
        return 'ERROR', res
    except socket.timeout as e:
        log.debug('request timeout exception')
        res['text'] = 'request timeout exception'
        return 'ERROR', res


def get_page(params):
    log = params['logger']
    res = {}
    for key in params:
        if key != 'logger': # not serializable object
            res[key] = params[key]
    # log.debug('get_page start')
    if params['proxy_port'] != -1:
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, params['proxy_ip'], params['proxy_port'])
        socket.socket = socks.socksocket

    def between(text, p_from, p_to):
        return text.split(p_from)[1].split(p_to)[0]

    try:
        path = '/forum/viewtopic.php?t=%(id)i' % {'id': params['id']}
        url = 'https://rutracker.org%(path)s' % {'path': path}
        params['headers']['Cookie'] = params['cookie']
        req = requests.get(url, headers=params['headers'], timeout=20)
        html = req.text
        if not (('<html>' in html) or ('<HTML>' in html)):
            res['text'] = 'not html in response'
            return 'ERROR', res
        if ('profile.php?mode=register">' in html) or ('action="https://rutracker.org/forum/login.php">' in html):
            res['text'] = 'not logined'
            return 'ERROR', res
        if len(html) < 1000:
            res['text'] = 'too short'
            return 'ERROR', res
        # f = open('html.txt', "w")
        # f.write(html)
        if not ('tor-hash">' in html):
            return 'NO_HASH', res
        else:
            line = list()
            line.append(str(params['id']))
            title = between(html, '<title>', ' :: RuTracker.org')
            title = unescape(title)
            line.append(title)
            size = between(html, '<span id="tor-size-humn" title="', '">') #  '<span id="tor-size-humn"', '</span>')
            if not size.isdigit():
                error_text = 'parser, size, not only numbers, id: %i' % params['id']
                log.warning(error_text)
                res['text'] = error_text
                return 'ERROR', res
            line.append(size)
            # seeds = '0'
            if '<span class="seed">Сиды:&nbsp; <b>' in html:
                seeds = between(html, 'seed">Сиды:&nbsp; <b>', '</b>')
            else:
                seeds = '0'
                # error_text = 'parser, seeds, template not found, id: %i' % params['id']
                # log.debug(error_text)
                # res['text'] = error_text
                # return 'ERROR', res
            line.append(seeds)
            # peers = '0'
            if 'leech">Личи:&nbsp; <b>' in html:
                peers = between(html, 'leech">Личи:&nbsp; <b>', '</b>')
            else:
                peers = '0'
                # error_text = 'parser, peers, template not found, id: %i' % params['id']
                # log.debug(error_text)
                # res['text'] = error_text
                # return 'ERROR', res
            line.append(peers)
            hash = between(html, 'tor-hash">', "</span>")
            line.append(hash)
            if 'torrent скачан:&nbsp; <b>' in html:
                downloads = between(html, 'torrent скачан:&nbsp; <b>', " раз").strip()
            elif '<td>.torrent скачан:</td>\n\t\t<td>' in html:
                downloads = between(html, '<td>.torrent скачан:</td>\n\t\t<td>', " раз").strip()
            elif ('Скачан: ' in html) and ('раза\t\t</td>' in html):
                downloads = between(html, 'Скачан: ', 'раза\t\t</td>').strip()
            elif ('Скачан: ' in html) and ('раз\t\t</td>' in html):
                downloads = between(html, 'Скачан: ', 'раз\t\t</td>').strip()
            else:
                error_text = 'parser, downloads, template not found, id: %i' % params['id']
                log.warning(error_text)
                res['text'] = error_text
                return 'ERROR', res
            if not downloads.isdigit():
                error_text = 'parser, downloads, bad template, id: %i' % params['id']
                log.warning(error_text)
                res['text'] = error_text
                return 'ERROR', res

            line.append(downloads)
            if 'Зарегистрирован &nbsp;[ ' in html:
                date = between(html, 'Зарегистрирован &nbsp;[ ', ' ]')
            elif 'зарегистрирован">[ ' in html:
                date = between(html, 'зарегистрирован">[ ', ' ]<')
            else:
                error_text = 'parser, date, template not found, id: %i' % params['id']
                log.warning(error_text)
                res['text'] = error_text
                return 'ERROR', res

            months = ("Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек")
            for i in range(len(months)):
                date = date.replace(months[i], "%02d" % (i+1))
            line.append(date)

            category_htmlpart = between(html, '<td class="nav w100"', '</td>')
            category_temp = category_htmlpart.replace('">', "</a>").split('</a>')
            category_list = list((i for i in category_temp if
                                  ('<em>' not in i) and ('\t' not in i) and ('style="' not in i) and (
                                  'Список форумов ' not in i)))
            category_string = ''
            for one_category in category_list:
                category_string += one_category + ' | '
            category_string = category_string[:-3]
            line.append(category_string)

            line = '\t'.join(line)
            descr = between(html, '<div class="post_body" id="', '<div class="clear"></div>')
            descr = descr.split('>', 1)[1]
            descr = descr.strip()
            if descr.endswith('</div>'):
                descr = descr[:-6]
            descr = unescape(descr)
            res['line'] = line
            res['description'] = descr
            return 'OK', res
    except requests.exceptions.RequestException as e:
        error_text = 'request exception, id: %i' % params['id']
        log.debug(error_text, exc_info=True)
        res['text'] = error_text
        return 'ERROR', res
    except socket.timeout as e:
        error_text = 'request timeout exception, id: %i' % params['id']
        log.debug(error_text, exc_info=True)
        res['text'] = error_text
        return 'ERROR', res
    except socks.Socks5Error as e:
        error_text = 'request exception (socket error), id: %i' % params['id']
        log.debug(error_text, exc_info=True)
        res['text'] = error_text
        return 'ERROR', res
    except Exception as e:
        error_text = 'unknown error, id: %i' % params['id']
        log.exception(error_text)
        res['text'] = error_text
        return 'ERROR', res
