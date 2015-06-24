#!/usr/bin/python
# -*- coding: cp1251 -*-

import os
import argparse
import random
import socket
from html.parser import unescape
from multiprocessing import Queue, freeze_support, Process, current_process
import queue

import socks
import requests



# ############# SETTINGS ###############
# Rutracker.org login & pass
import time

default_login = 'LOGIN'
default_password = 'PASSWORD'
default_proxy_port = 9150
default_threads_num = 1
######################################
default_ids_file = 'ids.txt'
table_file = "table.txt"
default_html_folder = 'html'
default_descr_folder = 'descr'
default_proxy_file = 'proxy.txt'
default_login_file = 'login.txt'
domain, path_tmpl = 'rutracker.org', '/forum/viewtopic.php?t=%(id)i'


class SomeError(Exception):
    def __init__(self, value, fatal=True):
        self.value = value
        self.fatal = fatal

    def __str__(self):
        return repr(self.value)


def get_rutracker_cookie(login, password):
    post_params = {
        'login_username': login,
        'login_password': password,
        'login': b'\xc2\xf5\xee\xe4'  # '%C2%F5%EE%E4'
    }
    # time.sleep(random.randrange(2, 5))  # DEBUG
    r = requests.post('http://login.rutracker.org/forum/login.php', data=post_params)
    if 'bb_data' in r.cookies.keys():
        cookie = 'bb_data=' + r.cookies['bb_data'] + '; tr_simple=1; spylog_test=1'
        # print('DEBUG', 'cookie =', cookie)  # DEBUG
        return cookie
    else:
        raise SomeError('no cookies, get_rutracker_cookie')


def is_logined(html):
    if "action=\"http://login.rutracker.org/forum/login.php\">" in html:
        return False
    else:
        return True


def parse_rutracker(id, html):
    def between(text, p_from, p_to):
        return text.split(p_from)[1].split(p_to)[0]

    def fix_date(date):
        date = date.replace("Янв", "Jan")
        date = date.replace("Фев", "Feb")
        date = date.replace("Мар", "Mar")
        date = date.replace("Апр", "Apr")
        date = date.replace("Май", "May")
        date = date.replace("Июн", "Jun")
        date = date.replace("Июл", "Jul")
        date = date.replace("Авг", "Aug")
        date = date.replace("Сен", "Sep")
        date = date.replace("Окт", "Oct")
        date = date.replace("Ноя", "Nov")
        date = date.replace("Дек", "Dec")
        return date

    def do_with(id, text):
        if not ('tor-hash' in text):
            raise SomeError('no hash', fatal=False)
            # return id, 'ERROR', 'NO HASH'
        else:
            line = list()
            line.append(str(id))
            title = between(text, '<title>', ' :: RuTracker.org')
            title = unescape(title)
            line.append(title)
            size_parts = between(text, '<td id="tor-size-humn">', '</td>')
            size_parts = size_parts.split('&nbsp;')
            # size_parts = between(text, 'Размер:&nbsp; <b>', '</b>').split('&nbsp;')
            size = float(size_parts[0])
            if size_parts[1] == 'KB':
                size *= 1024
            if size_parts[1] == 'MB':
                size *= 1024 ** 2
            if size_parts[1] == 'GB':
                size *= 1024 ** 3
            if size_parts[1] == 'TB':
                size *= 1024 ** 4
            size = str(int(size))
            line.append(size)
            seeds = '0'
            if '<span class="seed">Сиды:&nbsp; <b>' in text:
                seeds = between(text, 'seed">Сиды:&nbsp; <b>', '</b>')
            line.append(seeds)
            peers = '0'
            if 'leech">Личи:&nbsp; <b>' in text:
                peers = between(text, 'leech">Личи:&nbsp; <b>', '</b>')
            line.append(peers)
            hash = between(text, 'tor-hash">', "</span>")
            line.append(hash)
            if 'torrent скачан:&nbsp; <b>' in text:
                downloads = between(text, 'torrent скачан:&nbsp; <b>', " раз")
            else:
                downloads = between(text, '<td>.torrent скачан:</td>\n\t\t<td>', " раз")
            line.append(downloads)
            if 'Зарегистрирован &nbsp;[ ' in text:
                date = between(text, 'Зарегистрирован &nbsp;[ ', ' ]')
            else:
                date = between(text, 'зарегистрирован">[ ', ' ]<')
            # date = between(text, 'зарегистрирован">[ ', ' ]<')
            date = fix_date(date)
            line.append(date)

            category_htmlpart = between(text, '<td class="nav w100"', '</td>')
            category_temp = category_htmlpart.replace('">', "</a>").split('</a>')
            category_list = list((i for i in category_temp if ('<em>' not in i) and ('\t' not in i) and ('style="' not in i) and ('Список форумов ' not in i)))
            category_string = ''
            for one_category in category_list:
                category_string += one_category + ' | '
            category_string = category_string[:-3]
            # print(category_string)
            line.append(category_string)

            line = '\t'.join(line)
            descr = between(text, '<div class="post_body" id="', '<div class="clear"></div>')
            descr = descr.split('>', 1)[1]
            descr = descr.strip()
            if descr.endswith('</div>'):
                descr = descr[:-6]
            descr = unescape(descr)
            return id, line, descr

    text = html
    if 'profile.php?mode=register">' in text:
        raise SomeError('no login', fatal=False)
    if len(text) < 1000:
        raise SomeError('too short', fatal=False)
    return do_with(id, text)


def process_rutracker_page(id, headers):
    path = path_tmpl % {'id': id}
    url = 'http://%(domain)s%(path)s' % {'domain': domain, 'path': path}
    req = requests.get(url, headers=headers)
    html = req.text
    if not (('<html>' in html) or ('<HTML>' in html)):
        raise SomeError('not html in response', fatal=False)
    if not is_logined(html):
        raise SomeError('not logined')
    return parse_rutracker(id, html)


def worker(input, output, cookie, proxy, options):
    if options.noproxy:
        print('no using proxy')
    else:
        print(('using proxy, port ' + str(proxy)))
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", proxy)
        socket.socket = socks.socksocket

    # try:
    #     cookie = get_rutracker_cookie(login, password)
    # except requests.exceptions.RequestException:
    #     output.put((current_process().name, 'ERROR', 'RequestException in get_rutracker_cookie'))
    #     exit()
    # except SomeError as e:
    #     output.put((current_process().name, 'ERROR', e.value))
    #     exit()

    useragents = ['Mozilla/5.0 (Android; Mobile; rv:38.0) Gecko/38.0 Firefox/38.0',
                  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/600.6.3 (KHTML, like Gecko) Version/8.0.6 Safari/600.6.3',
                  'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0',
                  'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0',
                  'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0',
                  'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43/0/2357/81 Safari/537.36',
                  'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0',
                  'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
                  'Mozilla/5.0 (X11; Ubunru; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0',
                  'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.124 Safari/537.36',
                  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/600.6.3 (KHTML, like Gecko) Version/7.1.5 Safari/537.85.15'
                  ]

    headers = {
        'Accept-Encoding': 'gzip,deflate,sdch',
        'Host': domain,
        'Accept-Language': 'ru,en-US;q=0.8,en;q=0.6',
        'User-Agent': useragents[random.randrange(0, len(useragents))],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'http://%s/' % domain,
        'Cookie': cookie,
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0'
    }

    for id in iter(input.get, 'STOP'):
        try:
            result = process_rutracker_page(id, headers)
            output.put(result)
        except requests.exceptions.RequestException:
            output.put(id, 'ERROR', 'Connection error')
        except SomeError as e:
            output.put((id, 'ERROR', e.value))
            if e.fatal:
                output.put(current_process().name, 'ERROR', 'Thread terminated.')
                exit()
        time.sleep(3)


if __name__ == '__main__':
    freeze_support()

    ap = argparse.ArgumentParser()
    ids_group = ap.add_mutually_exclusive_group(required=True)
    ids_group.add_argument('--ids_file', '-if')
    ids_group.add_argument('--ids', nargs=2, type=int)
    ap.add_argument('--noproxy', '--direct', '-d', action="store_true")
    ap.add_argument('--port', '-p')
    ap.add_argument('--user', '-u')
    ap.add_argument('--password', '-pw')
    ap.add_argument('--html')
    ap.add_argument('--folder', '-f')
    ap.add_argument('--cookie')
    ap.add_argument('--random', action="store_true")
    ap.add_argument('--threads', '-tr', type=int)
    ap.add_argument('--proxy_file', '-pf', '-pr')
    ap.add_argument('--login_file', '-lf')
    ap.add_argument('--restore', action="store_true")
    ap.add_argument('--print', action="store_true")
    options = ap.parse_args()

    LOGIN = options.user if options.user else default_login
    PASSWORD = options.password if options.password else default_password
    ids_file = options.ids_file if options.ids_file else default_ids_file
    html_folder = options.html if options.html else default_html_folder
    threads_num = int(options.threads) if options.threads else default_threads_num
    descr_folder = options.folder if options.folder else default_descr_folder
    proxy_file = options.proxy_file if options.proxy_file else default_proxy_file
    login_file = options.login_file if options.login_file else default_login_file
    proxy_port = int(options.port) if options.port else default_proxy_port

    if options.html:
        html_folder = options.html

    task_queue = Queue()
    done_queue = Queue()

    proxy_list = list()
    if options.port:
        proxy_list.append(options.port)
    elif os.path.exists(proxy_file):
        proxy_list = list(map(str.strip, open(proxy_file)))  # read file, remove \n
    if len(proxy_list) == 0:
        proxy_list = list({proxy_port})
    random.shuffle(proxy_list)

    login_list = {}
    if os.path.exists(login_file):
        login_list = list(map(str.split, open(login_file)))  # read file, split user pass
    if len(login_list) == 0:
        login_list = list({(LOGIN, PASSWORD)})
    random.shuffle(login_list)

    cookie_proxy_list = []

    last_i = 0
    for i in range(len(login_list)):
        last_i = i
        l, p = login_list[i]
        proxy = int(proxy_list[i % len(proxy_list)])
        if options.noproxy:
            # print('no using proxy')
            pass
        else:
            # print(('using proxy, port ' + str(proxy)))
            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", proxy)
            socket.socket = socks.socksocket

        try:
            cookie = get_rutracker_cookie(l, p)
            cookie_proxy_list.append([cookie, proxy])
            print('OK, proxy: ' + str(proxy) + ', login: ' + l)
        except:
            print('ERROR, proxy: ' + str(proxy) + ', login: ' + l)
        time.sleep(0.7)

        if len(cookie_proxy_list) >= threads_num:
            print('stop cookies, break')
            break
        print('cookie_proxy_list length: ' + str(len(cookie_proxy_list)))

    max_threads = min(len(cookie_proxy_list) * 2, threads_num)
    print('max threads =', max_threads)
    for j in range(max_threads - len(cookie_proxy_list)):
        proxy = int(proxy_list[(last_i + j) % len(proxy_list)])
        cookie_proxy_list.append([cookie_proxy_list[j][0], proxy])

    print(cookie_proxy_list)
    processes = list()
    for i in range(len(cookie_proxy_list)):
        login, password = login_list[i % len(login_list)]
        cookie, proxy = cookie_proxy_list[i % len(cookie_proxy_list)]
        # proxy = int(proxy_list[i % len(proxy_list)])
        time.sleep(1)
        p = Process(target=worker, args=(task_queue, done_queue, cookie, proxy, options))
        p.start()
        processes.append(p)

    # ==============================================
    if options.ids_file:
        ids = set(map(int, open(ids_file)))
    else:
        ids = set(range(options.ids[0], options.ids[1]))

    if options.restore:
        ids_finished = set(map(int, open('finished.txt')))
        ids_new = []
        for id in ids:
            if id not in ids_finished:
                ids_new.append(id)
        print('input:   \t', len(ids))
        print('finished:\t', len(ids_finished))
        print('left:    \t', len(ids_new))
        ids = ids_new

    print(len(ids))
    if options.print:
        exit()

    if len(ids) == 0:
        print('Empty input/left list. Terminated.')
        exit()

    # print('DEBUG', ids)  # DEBUG

    if options.random:
        random.shuffle(ids)
    # ==============================================

    for number, id in enumerate(ids):
        id = int(id)
        task_queue.put(id)

    for i in range(len(cookie_proxy_list)):
        task_queue.put('STOP')

    handle_table_file = open(table_file, 'a', encoding='utf8')

    # if not os.path.exists(html_folder):
    #     os.mkdir(html_folder)

    finished_file = open('finished.txt', 'a', encoding='utf8')
    log_file = open('log.txt', 'a', encoding='utf8')

    # for i in range(len(ids)):
    while True:
        if task_queue.empty():
            print('Task queue is empty.')

        try:
            res = done_queue.get(timeout=2)
        except queue.Empty:
            anybody_alive = False
            for j in range(len(processes)):
                if processes[j].is_alive():
                    anybody_alive = True
                    break
            if anybody_alive:
                continue
            else:
                print('All processes died, terminated.')
                exit()

        # noinspection PyUnboundLocalVariable
        id, arg1, arg2 = res
        if arg1 == 'ERROR':
            if arg2 == 'no hash':
                arg1 = 'OK'
                finished_file.write(str(id) + '\n')
            print(id, arg1, arg2)
            log_file.write(str(id) + ' ' + str(arg1) + ' ' + str(arg2) + '\n')
            continue

        line = arg1
        descr = arg2

        print(id, 'OK')
        finished_file.write(str(id) + '\n')
        log_file.write(str(id) + ' ' + 'ok' + '\n')

        handle_table_file.write(line + '\n')

        if not os.path.exists(descr_folder):
            os.mkdir(descr_folder)
        path = descr_folder + '/%03i/' % (id // 100000)
        if not os.path.exists(path):
            os.mkdir(path)

        filename = path + ('%08i' % id)
        descr_file = open(filename, 'w', encoding='utf8')
        descr_file.write(descr)
        descr_file.close()

    handle_table_file.close()
    log_file.close()
    finished_file.close()
