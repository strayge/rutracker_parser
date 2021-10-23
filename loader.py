#!/usr/bin/env python3

import os
from settings import Settings
import parser
import random
from multiprocessing import Queue, freeze_support, Process, current_process
import queue # for exceptions
import logging
import time
import requests
import signal

def worker(input, output):
    try:
        log = logging.getLogger("thread(%3i)" % random.randrange(1, 999)) # random name
        log.debug('starting thread')

        for new_input in iter(input.get, ('STOP',{})):
            # log.debug('thread iteration')
            new_input[1]['logger'] = log
            if new_input[0] == 'COOKIE':
                status, details = parser.get_cookie(new_input[1])
                output.put((new_input[0], status, details))
            elif new_input[0] == 'GET_PAGE':
                time.sleep(3)
                status, details = parser.get_page(new_input[1])
                output.put((new_input[0], status, details))
            else:
                log.warning('unknown task: %s' % new_input[0])
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    freeze_support()

    format = '%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s'
    logging.basicConfig(level=logging.INFO, format=format, filename='log.txt')
    # logging.basicConfig(level=logging.DEBUG, format=format, filename='log.txt')
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logging.Formatter(format))
    logging.getLogger().addHandler(consoleHandler)
    log = logging.getLogger(__name__)

    # disable debug logging for urllib3 in requests
    urllib3_logger = logging.getLogger('urllib3')
    urllib3_logger.setLevel(logging.CRITICAL)

    log.info("\n\n\n========== Program started ==========")

    try:
        settings = Settings()

        task_queue = Queue()
        done_queue = Queue()

        processes = list()
        log.info("numbers of threads: %i" % settings.threads_num)
        for i in range(settings.threads_num):
            p = Process(target=worker, args=(task_queue, done_queue))
            p.start()
            processes.append(p)

        settings.prepare_lists()
        settings.open_files()

        def stop_threads_and_exit():
            log.debug('Stopping all threads and exitting')
            for i in range(settings.threads_num):
                task_queue.put(('STOP', {}))
            exit()

        if settings.print:
            stop_threads_and_exit()

        if len(settings.ids) == 0:
            log.info('Empty input/left list. Terminated')
            stop_threads_and_exit()

        settings.load_cookies()
        for i in range(len(settings.login_list)):
            if ('cookie' not in settings.login_list[i].keys()) or (settings.login_list[i]['cookie'] == ''):
                proxy = settings.get_free_proxy()
                work = ('COOKIE', {'username': settings.login_list[i]['username'], 'password': settings.login_list[i]['password'],
                                   'proxy_ip': proxy['ip'], 'proxy_port': int(proxy['port'])})
                task_queue.put(work)

        ids_pointer = 0
        # bulk = 30

        nexttime = time.time()
        exit_counter = 0
        status_nexttime = time.time()
        ids_status = {'finished_all':0, 'error_all':0, 'nohash_all':0,'finished_last':0, 'error_last':0, 'nohash_last':0}
        while True:
            if time.time() > status_nexttime:
                status_nexttime = time.time() + 10
                speed = (ids_status['finished_last'] + ids_status['nohash_last']) / 10.0
                if speed != 0:
                    time_remaining = (len(settings.ids) - ids_pointer) / speed
                else:
                    time_remaining = 0
                m, s = divmod(time_remaining, 60)
                h, m = divmod(m, 60)
                print('Last 10 sec: %3d - OK, %3d - NOHASH, %2d - ERROR, Remaining: %ik, %d:%02d"' % (ids_status['finished_last'], ids_status['nohash_last'],
                                                                                                ids_status['error_last'], (len(settings.ids) - ids_pointer)//1000,h,m))
                ids_status['finished_all'] += ids_status['finished_last']
                ids_status['error_all'] += ids_status['error_last']
                ids_status['nohash_all'] += ids_status['nohash_last']
                ids_status['finished_last'] = 0
                ids_status['error_last'] = 0
                ids_status['nohash_last'] = 0
            # adding new tasks
            if (task_queue.qsize() < settings.qsize) and (ids_pointer < len(settings.ids)):
                exit_counter = 0
                id_max = min(ids_pointer + settings.qsize, len(settings.ids))
                for i in range(ids_pointer, id_max):
                    proxy = settings.get_free_proxy()
                    if not proxy:
                        if time.time() > nexttime:
                            log.info('free proxy not available')
                            log.debug('proxies: %s' % str(settings.proxy_list))
                            nexttime = time.time() + 60
                        break
                    cookie = settings.get_free_cookie()
                    if not cookie:
                        if time.time() > nexttime:
                            log.info('free cookie not available')
                            log.debug('cookies: %s' % str(settings.login_list))
                            nexttime = time.time() + 60
                        break
                    work = ('GET_PAGE', {'id': int(settings.ids[i]), 'cookie': cookie, 'headers': settings.headers, 'proxy_ip': proxy['ip'], 'proxy_port': int(proxy['port'])})
                    task_queue.put(work)
                    ids_pointer += 1

            if task_queue.empty() and done_queue.empty():
                # common part
                if exit_counter > 1:
                    log.info('Queues are empty.')
                time.sleep(1)
                exit_counter += 1
                if exit_counter > 5:
                    stop_threads_and_exit()
            else:
                exit_counter = 0

            try:
                task, status, details = done_queue.get(timeout=1)
            except queue.Empty:
                anybody_alive = False
                for j in range(len(processes)):
                    if processes[j].is_alive():
                        anybody_alive = True
                        break
                if anybody_alive:
                    continue
                else:
                    log.info('All threads died, exit.')
                    exit()

            s = signal.signal(signal.SIGINT, signal.SIG_IGN)
            if task == 'COOKIE':
                if status == 'OK':
                    log.debug('processing loop. cookie - ok')
                    settings.set_free_proxy(details['proxy_ip'], details['proxy_port'])
                    settings.set_cookie(details['username'], details['cookie'])
                elif status == 'ERROR':
                    log.error('processing loop. cookie - error: %s' % details['text'])
                    settings.set_free_proxy(details['proxy_ip'], details['proxy_port'])
                    # settings.set_cookie_error(details['username'])
                else:
                    log.warning('processing loop. cookie - unknown status:' + status)
            elif task == 'GET_PAGE':
                if status == 'OK':
                    ids_status['finished_last'] += 1
                    log.debug('processing loop. get page - OK, id: %s' % str(details['id']))
                    settings.set_free_proxy(details['proxy_ip'], details['proxy_port'])
                    settings.set_free_cookie(details['cookie'])
                    id, line, description = details['id'], details['line'], details['description']
                    if not os.path.exists(settings.descr_folder):
                        os.mkdir(settings.descr_folder)
                    path = settings.descr_folder + '/%03i/' % (id // 100000)
                    if not os.path.exists(path):
                        os.mkdir(path)
                    filename = path + ('%08i' % id)
                    handle_description_file = open(filename, 'w', encoding='utf8')
                    handle_description_file.write(description)
                    handle_description_file.close()
                    settings.handle_table_file.write(line + '\n')
                    settings.handle_finished_file.write(str(id) + '\n')
                elif status == 'NO_HASH':
                    ids_status['nohash_last'] += 1
                    log.debug('processing loop. get page - NO HASH, id: %s' % str(details['id']))
                    settings.set_free_proxy(details['proxy_ip'], details['proxy_port'])
                    settings.set_free_cookie(details['cookie'])
                    id = details['id']
                    settings.handle_finished_file.write(str(id) + '\n')
                elif status == 'ERROR':
                    ids_status['error_last'] += 1
                    log.error('processing loop. get page - error: %s' % details['text'])
                    if details['text'] == 'not logined':
                        settings.set_error_cookie(details['cookie'])
                    settings.set_free_cookie(details['cookie'])
                    if ('request exception' in details['text']) or ('request timeout exception' in details['text']):
                        settings.set_error_proxy(details['proxy_ip'], details['proxy_port'])
                    settings.set_free_proxy(details['proxy_ip'], details['proxy_port'])
                    settings.ids.append(int(details['id']))
                else:
                    log.warning('processing loop. get page - unknown status: %s, id: %s' % (status, details['id']))
            else:
                log.warning('processing loop. unknown task:' + task)
            signal.signal(signal.SIGINT, s)

    except KeyboardInterrupt:
        log.info('Ctrl+^C, exitting...')
        exit()
