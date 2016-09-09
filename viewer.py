#!/usr/bin/python3
# -*- coding: utf8 -*-

import sys
import urllib.parse
from tarfile import TarFile
import io
from datetime import datetime

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import QtWebKitWidgets

tree_columns = ('id', 'name', 'size', 'seeds', 'peers', 'hash', 'downloads', 'date', 'category')
tree_columns_visible = ('ID', 'Название', 'Размер', 'Сиды', 'Пиры', 'Hash', 'Скачиваний', 'Дата', 'Раздел')


class NumberSortModel(QSortFilterProxyModel):
    def lessThan(self, left, right):
        if not left.data():
            return True
        if not right.data():
            return False

        if left.column() in [tree_columns.index('id'), tree_columns.index('seeds'), tree_columns.index('peers'),
                             tree_columns.index('downloads')]:
            lvalue = int(left.data())
            rvalue = int(right.data())
        elif left.column() == tree_columns.index('date'):
            lvalue = datetime.strptime(left.data(), '%d-%b-%y %H:%M')
            rvalue = datetime.strptime(right.data(), '%d-%b-%y %H:%M')
        elif left.column() == tree_columns.index('size'):
            lvalue = left.data()
            rvalue = right.data()
            if lvalue[-2:] == ' B':
                lvalue = float(lvalue[:-2])
            elif lvalue[-3:] == ' KB':
                lvalue = float(lvalue[:-3]) * 1024
            elif lvalue[-3:] == ' MB':
                lvalue = float(lvalue[:-3]) * 1024 * 1024
            elif lvalue[-3:] == ' GB':
                lvalue = float(lvalue[:-3]) * 1024 * 1024 * 1024
            if rvalue[-2:] == ' B':
                rvalue = float(rvalue[:-2])
            elif rvalue[-3:] == ' KB':
                rvalue = float(rvalue[:-3]) * 1024
            elif rvalue[-3:] == ' MB':
                rvalue = float(rvalue[:-3]) * 1024 * 1024
            elif rvalue[-3:] == ' GB':
                rvalue = float(rvalue[:-3]) * 1024 * 1024 * 1024
        else:
            lvalue = left.data()
            rvalue = right.data()
        return lvalue < rvalue


class MainWindow(QMainWindow):
    # noinspection PyUnresolvedReferences
    def __init__(self):
        super(MainWindow, self).__init__()
        frame = QFrame(self)

        self.result_count = 0
        self.founded_items = []

        self.grid = QGridLayout(frame)
        self.setCentralWidget(frame)

        self.input = QLineEdit()
        self.input2 = QLineEdit()
        self.search = QPushButton()
        self.tree = QTableView()
        self.webview = QtWebKitWidgets.QWebView()
        separator = QSplitter()
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.do_update_table)

        self.model = QStandardItemModel()
        proxy = NumberSortModel()
        proxy.setSourceModel(self.model)
        self.tree.setModel(proxy)
        self.model.setColumnCount(len(tree_columns))
        self.model.setHorizontalHeaderLabels(tree_columns_visible)
        self.tree.verticalHeader().setVisible(False)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setSortingEnabled(True)
        self.tree.verticalHeader().setDefaultSectionSize(24)
        self.webview.setUrl(QUrl("about:blank"))
        self.webview.setZoomFactor(0.85)
        self.search.setText('Искать')
        self.input2.setMaximumWidth(300)
        self.setWindowTitle('RuTracker database   |   by Strayge')
        self.input.setPlaceholderText('Строка для поиска в названии')
        self.input2.setPlaceholderText('Строка для поиска в категории')

        self.grid.addWidget(self.input, 0, 0)
        self.grid.addWidget(self.input2, 0, 1)

        self.grid.addWidget(self.search, 0, 2)
        self.grid.addWidget(separator, 1, 0, 2, 0)
        separator.addWidget(self.tree)
        separator.addWidget(self.webview)

        self.resize(1500, 800)
        self.tree.resize(2800, 0)

        self.search.clicked.connect(self.do_search)
        self.input.returnPressed.connect(self.do_search)
        self.input2.returnPressed.connect(self.do_search)
        self.tree.clicked.connect(self.do_select)
        self.tree.doubleClicked.connect(self.do_work)

        self.searcher = None
        self.first_result = False

    def do_update_table(self, finish=False):
        if finish:
            self.timer.stop()
        self.model.setRowCount(len(self.founded_items))
        for i in range(self.result_count, len(self.founded_items)):
            for j in range(len(tree_columns)):
                item = self.founded_items[i]
                qitem = QStandardItem()
                qitem.setData(QVariant(item[j]), Qt.DisplayRole)
                self.model.setItem(i, j, qitem)
            self.result_count += 1

        # self.tree.sortByColumn(tree_columns.index('seeds'), Qt.DescendingOrder)
        self.tree.resizeColumnsToContents()
        if self.tree.columnWidth(tree_columns.index('name')) > 500:
            self.tree.setColumnWidth(tree_columns.index('name'), 500)
        if finish:
            self.timer.stop()
            self.statusbar.showMessage('Поиск закончен. Найдено %i записей' % len(self.founded_items))
            self.search.setText('Поиск')
        else:
            self.statusbar.showMessage('Идет поиск... Найдено %i записей' % self.result_count)

    def do_add_founded_item(self, item):
        for j in range(len(tree_columns)):
            if j == tree_columns.index('size'):
                size = int(item[j])
                if size < 1024:
                    item[j] = '%.0f B' % (float(item[j]))
                elif size < 1024 * 1024:
                    item[j] = '%.0f KB' % (float(item[j]) / 1024)
                elif size < 1024 * 1024 * 1024:
                    item[j] = '%.0f MB' % (float(item[j]) / (1024 * 1024))
                else:
                    item[j] = '%.2f GB' % (float(item[j]) / (1024 * 1024 * 1024))
        self.founded_items.append(item)

    def do_show_status(self, text):
        if text == 'Поиск закончен.':
            self.do_update_table(True)
        else:
            self.statusbar.showMessage(text + ' Найдено %i записей.' % len(self.founded_items))

    def do_search(self):
        if self.search.text() == 'Отмена':
            if self.searcher and self.searcher.isRunning():
                self.search.setText('Поиск')
                self.searcher.stop()
                self.timer.stop()
                return

        self.first_result = True
        self.search.setText('Отмена')
        self.result_count = 0
        self.founded_items = []
        self.model.setRowCount(0)
        self.searcher = SearchThread(self.input.text(), self.input2.text())
        self.searcher.add_founded_item.connect(self.do_add_founded_item)
        self.searcher.status.connect(self.do_show_status)
        self.searcher.start(QThread.LowestPriority)
        self.timer.start()

    def do_work(self, index=None):
        index = self.tree.model().mapToSource( index )
        
        name = self.model.item(index.row(), tree_columns.index('name')).text()
        hash = self.model.item(index.row(), tree_columns.index('hash')).text()
        args = (
            ('magnet:?xt=urn:btih:', name),
            ('dn=', hash),
            ('tr=', 'udp://tracker.publicbt.com:80'),
            ('tr=', 'udp://tracker.openbittorrent.com:80'),
            ('tr=', 'tracker.ccc.de:80'),
            ('tr=', 'tracker.istole.it:80'),
            ('tr=', 'udp://tracker.publicbt.com:80')
        )
        link = ''
        for i, j in args:
            link += i + urllib.parse.quote_plus(j).replace('+', '%20')
        # noinspection PyArgumentList
        QApplication.clipboard().setText(link)
        print('magnet link copied to clipboard.')

    def do_select(self, index=None):
        id = int(self.model.item(index.row(), tree_columns.index('id')).text())
        try:
            archive = TarFile.open('descr/%03i/%05i.tar.bz2' % (id // 100000, id // 1000), 'r:bz2')
            s = archive.extractfile('%08i' % id).read().decode()
            archive.close()
            self.webview.setHtml(s)
        except FileNotFoundError:
            self.webview.setHtml('Нет описания')


class SearchThread(QThread):
    add_founded_item = pyqtSignal(object)
    status = pyqtSignal(object)

    def __init__(self, text, category):
        QThread.__init__(self)
        self.text = text
        self.category = category

    def stop(self):
        self.status.emit('Поиск остановлен.')
        self.terminate()

    def run(self):
        limit = 20
        text = self.text
        category = self.category

        words_contains = []
        words_not_contains = []
        words_category = []

        for w in text.split(' '):
            if (len(w) > 1) and (w[0]) == '-':
                words_not_contains.append(w[1:])
            elif (len(w) > len('limit:')) and (w[:6] == 'limit:'):
                limit = int(w[6:])
            else:
                words_contains.append(w)
        for w in category.split(' '):
            words_category.append(w)

        archive = TarFile.open('table_sorted.tar.bz2', 'r:bz2')
        member = archive.members[0]
        buffered_reader = archive.extractfile(member)
        buffered_text_reader = io.TextIOWrapper(buffered_reader, encoding='utf8')

        founded_items = 0

        for line in buffered_text_reader:
            item = line.strip().split(sep='\t')
            next = False
            for w in words_contains:
                if w.lower() in item[tree_columns.index('name')].lower():
                    pass
                else:
                    next = True
                    break
            if next:
                continue
            for w in words_not_contains:
                if w.lower() in item[tree_columns.index('name')].lower():
                    next = True
                    break
            if next:
                continue
            for w in words_category:
                if w.lower() in item[tree_columns.index('category')].lower():
                    pass
                else:
                    next = True
                    break
            if next:
                continue

            founded_items += 1
            self.add_founded_item.emit(item)

            if founded_items >= limit:
                self.status.emit('Поиск закончен.')
                break


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())
