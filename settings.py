#!/usr/bin/python
# -*- coding: cp1251 -*-

import argparse
import os
import random
import logging
import json

class Settings:
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.log.debug("start loading settings")

        ap = argparse.ArgumentParser()
        ids_group = ap.add_mutually_exclusive_group(required=True)
        ids_group.add_argument('--ids_file', '-if')
        ids_group.add_argument('--ids', nargs=2, type=int)
        ap.add_argument('--ids_ignore', '-old')
        ap.add_argument('--noproxy', '--direct', '-d', action="store_true")
        ap.add_argument('--port', '-p')
        ap.add_argument('--user', '-u')
        ap.add_argument('--password', '-pw')
        # ap.add_argument('--html')
        ap.add_argument('--folder', '-f')
        # ap.add_argument('--cookie')
        # ap.add_argument('--cookies_list')
        ap.add_argument('--random', action="store_true")
        ap.add_argument('--threads', '-tr', type=int)
        ap.add_argument('--proxy_file', '-pf', '-pr')
        ap.add_argument('--login_file', '-lf')
        ap.add_argument('--restore', '--resume', action="store_true")
        ap.add_argument('--print', action="store_true")
        ap.add_argument('--qsize', '-q', type=int)
        self.options = ap.parse_args()

        self.login = self.options.user if self.options.user else ''
        self.password = self.options.password if self.options.password else ''
        self.ids_file = self.options.ids_file if self.options.ids_file else ''
        self.ids = self.options.ids if self.options.ids else ''
        self.ids_ignore = self.options.ids_ignore if self.options.ids_ignore else ''
        self.restore = True if self.options.restore else False
        self.random = True if self.options.random else False
        self.print = True if self.options.print else False
        self.noproxy = True if self.options.noproxy else False
        # self.html_folder = self.options.html if self.options.html else 'html'
        self.threads_num = int(self.options.threads) if self.options.threads else 1
        self.descr_folder = self.options.folder if self.options.folder else 'descr'
        self.proxy_file = self.options.proxy_file if self.options.proxy_file else 'proxy.txt'
        self.login_file = self.options.login_file if self.options.login_file else 'login.txt'
        self.proxy_port = int(self.options.port) if self.options.port else 9150
        self.qsize = int(self.options.qsize) if self.options.qsize else min((self.threads_num + 2), 30)
        self.table_file = "table.txt"
        self.ids_finished = 'finished.txt'

        useragents = ['Mozilla/5.0 (Android; Mobile; rv:38.0) Gecko/38.0 Firefox/38.0',
              'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/600.6.3 (KHTML, like Gecko) Version/8.0.6 Safari/600.6.3',
              'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0',
              'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43/0/2357/81 Safari/537.36',
              'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0',
              'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
              'Mozilla/5.0 (X11; Ubunru; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0',
              'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.124 Safari/537.36',
              'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/600.6.3 (KHTML, like Gecko) Version/7.1.5 Safari/537.85.15',
              'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:42.0) Gecko/20100101 Firefox/42.0',
              'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:42.0) Gecko/20100101 Firefox/42.0'
              ]

        self.headers = {
            'Accept-Encoding': 'gzip,deflate',
            'Host': 'rutracker.org',
            'Accept-Language': 'ru,en-US;q=0.8,en;q=0.6',
            # 'User-Agent': useragents[random.randrange(0, len(useragents))],
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:42.0) Gecko/20100101 Firefox/42.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Referer': 'http://rutracker.org/forum/index.php',
            #'Cookie': cookie,
            'Connection': 'keep-alive'
        }
        self.proxy_list = list()
        self.login_list = list()
        self.ids = set()

        self.handle_table_file = 0
        self.handle_finished_file = 0

        self.temp_cookies_filename = 'temp_cookies.txt'

        self.log.debug("end loading settings")

        self.threads_per_proxy = 1
        self.threads_per_cookie = 1

    # separate def, because ids lists eats many RAM => each thread eats many RAM
    def prepare_lists(self):
        self.log.debug("start preparing lists")

        if self.options.noproxy:
            self.log.info("no loaded proxy")
            # self.proxy_list.append(options.port)
        elif os.path.exists(self.proxy_file):
            proxies = list(open(self.proxy_file))
            for line in proxies:
                ip, port = line.split()
                self.proxy_list.append({'ip': ip, 'port': int(port), 'in_use': 0, 'fails': 0})
            random.shuffle(self.proxy_list)
            self.log.info("loaded %i proxies from file" % len(self.proxy_list))
        else: #len(self.proxy_list) == 0:
            self.proxy_list = list({'ip': '127.0.0.1', 'port': int(self.proxy_port)})
            self.log.info("loaded single proxy - 127.0.0.1:%s" % str(self.proxy_port))

        if self.login and self.password:
            self.login_list.append({'username': self.login, 'password': self.password, 'in_use': 0, 'fails': 0})
            self.log.info("loaded 1 login")
        elif os.path.exists(self.login_file):
            for line in open(self.login_file):
                if line.strip() == '':
                    continue
                parts = line.strip('\r\n').split()
                if len(parts) != 2:
                    parts =  line.strip('\r\n').split("\t")
                    if len(parts) != 2:
                        self.log.error("Can't split line into user and pass: '%s'." % line)
                        raise "Can't split line into user and pass"
                user, password = parts
                self.login_list.append({'username': user, 'password': password, 'in_use': 0, 'fails': 0})
            random.shuffle(self.login_list)
            self.log.info("loaded %i logins from file" % len(self.login_list))
        if not len(self.login_list):
            self.log.error("Can't load user/pass.")
            raise "Can't load user/pass."
        if self.ids_file:
            self.log.debug("loading ids from file")
            self.ids = set(map(int, open(self.ids_file)))
        else:
            self.ids = set(range(self.options.ids[0], self.options.ids[1]))
        
        if self.ids_ignore and os.path.isfile(self.ids_ignore):
            self.log.debug("ignore part of ids from file")
            max_id = 0
            #ignoring blank lines
            old_ids = set(map(int, filter(lambda s: s != '', map(lambda s: s.strip(), open(self.ids_ignore)))))
            # old_ids = set(map(int, open(options.old)))
            for id in old_ids:
                if id > max_id:
                    max_id = id
            for id in range(1, max_id):
                if (id not in old_ids) and (id in self.ids):
                    self.ids.remove(id)

        if self.restore and os.path.isfile('finished.txt'):
            self.log.debug("ignoring ids from finished file (restore option)")
            ids_finished = set(map(int, open('finished.txt')))
            ids_new = []
            for id in self.ids:
                if id not in ids_finished:
                    ids_new.append(id)
            self.log.info('input:   \t%i' % len(self.ids))
            self.log.info('finished:\t%i' % len(ids_finished))
            self.log.info('left:    \t%i' % len(ids_new))
            self.ids = ids_new

        if self.random:
            self.log.debug("shuffle ids")
            random.shuffle(self.ids)

        self.ids = list(self.ids)

        self.log.debug("end preparing lists")

    def open_files(self):
        self.log.debug("opening files to write results")
        self.handle_table_file = open(self.table_file, 'a', encoding='utf8')
        self.handle_finished_file = open(self.ids_finished, 'a', encoding='utf8')
        # log_file = open('log.txt', 'a', encoding='utf8')

    def close_files(self):
        self.log.debug("closing files with results")
        self.handle_table_file.close()
        # log_file.close()
        self.handle_finished_file.close()

    def load_cookies(self):
        self.log.debug("load_cookies start")
        if os.path.isfile(self.temp_cookies_filename):
            temp_login_list = json.load(open(self.temp_cookies_filename))
            for item in temp_login_list:
                if 'cookie' in item.keys():
                    for i in range(len(self.login_list)):
                        if self.login_list[i]['username'] == item['username']:
                            self.login_list[i]['cookie'] = item['cookie']
                            break
        self.log.debug("load_cookies done")
        self.log.debug("cookies: %s" % str(self.login_list))

    def save_cookies(self):
        self.log.debug("save_cookies")
        json.dump(self.login_list, open(self.temp_cookies_filename, 'w'))

    def set_cookie(self, username, cookie):
        for i in range(len(self.login_list)):
            if self.login_list[i]['username'] == username:
                self.login_list[i]['cookie'] = cookie
                break
        self.save_cookies()

    def get_free_cookie(self):
        not_using_logins = [login for login in self.login_list if (login['in_use'] < self.threads_per_cookie) and ('cookie' in login.keys()) and login['cookie']!='']
        if len(not_using_logins) == 0:
            return None
        random.shuffle(not_using_logins)
        selected_login = min(not_using_logins, key=lambda login: login['fails'])
        # if selected_login['fails'] > 10:
        #     return None
        cookie = selected_login['cookie']
        i = [i for i,login in enumerate(self.login_list) if ('cookie' in login.keys()) and (login['cookie'] == cookie)][0]
        self.login_list[i]['in_use'] += 1
        return cookie

    def set_free_cookie(self, cookie):
        ii = [i for i,login in enumerate(self.login_list) if ('cookie' in login.keys()) and (login['cookie'] == cookie)]
        if len(ii) > 0:
            i = ii[0]
            self.login_list[i]['in_use'] -= 1

    def set_error_cookie(self, cookie):
        self.log.debug('set_error_cookie, cookie: %s' % cookie)
        self.log.debug(self.login_list)
        i = [i for i,login in enumerate(self.login_list) if ('cookie' in login.keys()) and (login['cookie'] == cookie)][0]
        self.login_list[i]['fails'] += 1
        if self.login_list[i]['fails'] > 5:
            self.login_list[i]['cookie'] = ''
            self.save_cookies()
            self.log.warning('cookie removed from pool (too many fails)')

    def get_free_proxy(self):
        if self.noproxy:
            return {'ip':'', 'port': -1}
        not_using_proxies = [proxy for proxy in self.proxy_list if proxy['in_use'] < self.threads_per_proxy]
        random.shuffle(not_using_proxies)
        if len(not_using_proxies) == 0:
            return None
        selected_proxy = min(not_using_proxies, key=lambda p: p['fails'])
        if selected_proxy['fails'] > 1000:
            self.log.debug('none free proxy')
            return None
        i = [i for i,proxy in enumerate(self.proxy_list) if (proxy['ip'] == selected_proxy['ip']) and (proxy['port'] == selected_proxy['port'])][0]
        self.proxy_list[i]['in_use'] += 1
        return selected_proxy

    def set_free_proxy(self, proxy_ip, proxy_port):
        if proxy_port == -1:
            return
        i = [i for i,proxy in enumerate(self.proxy_list) if (proxy['ip'] == proxy_ip) and (proxy['port'] == proxy_port)][0]
        self.proxy_list[i]['in_use'] -= 1

    def set_error_proxy(self, proxy_ip, proxy_port):
        if proxy_port == -1:
            return
        self.log.debug('set_error_proxy, %s: %s' % (proxy_ip, proxy_port))
        i = [i for i,proxy in enumerate(self.proxy_list) if (proxy['ip'] == proxy_ip) and (proxy['port'] == proxy_port)][0]
        self.proxy_list[i]['fails'] += 1