import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import QtWebKitWidgets
import sqlite3
import os
import urllib.parse
from tarfile import TarFile

tree_columns = ('id', 'name', 'size', 'seeds', 'peers', 'hash', 'downloads', 'date')


class NumberSortModel(QSortFilterProxyModel):
    def lessThan(self, left, right):
        lvalue = left.data().toDouble()[0]
        rvalue = right.data().toDouble()[0]
        return lvalue < rvalue


class MainWindow(QMainWindow):
    # noinspection PyUnresolvedReferences
    def __init__(self):
        super(MainWindow, self).__init__()
        frame = QFrame(self)

        self.conn = None
        self.c = None

        self.grid = QGridLayout(frame)
        self.setCentralWidget(frame)

        self.input = QLineEdit()
        self.input2 = QLineEdit()
        self.search = QPushButton()
        self.tree = QTableView()
        self.webview = QtWebKitWidgets.QWebView()
        separator = QSplitter()

        self.model = QStandardItemModel()
        proxy = NumberSortModel()
        proxy.setSourceModel(self.model)
        self.tree.setModel(self.model)
        self.model.setColumnCount(len(tree_columns))
        self.model.setHorizontalHeaderLabels(tree_columns)
        self.tree.verticalHeader().setVisible(False)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setSortingEnabled(True)
        self.tree.verticalHeader().setDefaultSectionSize(24)
        self.webview.setUrl(QUrl("about:blank"))
        self.webview.setZoomFactor(0.85)
        self.search.setText('Search')
        self.input2.setMaximumWidth(300)

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

        self.init_db()

    def do_search(self):
        print('search')
        text = self.input.text()
        category = self.input2.text()
        words = text.split(' ')
        sql = "SELECT * FROM table1 WHERE "
        for w in words:
            if (len(w) > 1) and (w[0]) == '-':
                sql += " (name NOT LIKE '%" + w[1:] + "%') AND"
            else:
                sql += " (name LIKE '%" + w + "%') AND"
        sql = sql[:-3]
        if category != '':
            sql += " AND (category LIKE '%" + category + "%') "
        sql += "ORDER BY seeds LIMIT 100"
        print(sql)  # DEBUG
        items = self.c.execute(sql).fetchall()

        self.model.setRowCount(len(items))
        for i in range(len(items)):
            for j in range(len(tree_columns)):
                item = QStandardItem()
                item.setData(QVariant(items[i][j]), Qt.DisplayRole)
                self.model.setItem(i, j, item)
        self.tree.sortByColumn(tree_columns.index('seeds'), Qt.DescendingOrder)
        self.tree.resizeColumnsToContents()
        if self.tree.columnWidth(tree_columns.index('name')) > 500:
            self.tree.setColumnWidth(tree_columns.index('name'), 500)

    def do_work(self, index=None):
        # print('double click')
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
        archive = TarFile.open('descr/%03i/%05i.tar.bz2' % (id // 100000, id // 1000), 'r:bz2' )
        s = archive.extractfile('%08i' % id).read().decode()
        archive.close()
        self.webview.setHtml(s)

    def init_db(self):
        db_name = 'db.sqlite'
        if os.path.exists(db_name):
            print('db exists')
            self.conn = sqlite3.connect(db_name)
            self.c = self.conn.cursor()
            chksum_old = self.c.execute('SELECT value FROM main WHERE name=\'chksum\'').fetchone()[0]
            size_old = self.c.execute('SELECT value FROM main WHERE name=\'size\'').fetchone()[0]

            # crc32 = None
            archive = TarFile.open('table.tar.bz2', 'r:bz2')
            if 'table.txt' in archive.getnames():
                member = archive.getmember('table.txt')
                chksum = str(member.chksum)
                size = str(member.size)
                if not ((chksum == chksum_old) and (size == size_old)):
                    archive.close()
                    self.c.close()
                    self.conn.close()
                    os.remove(db_name)
            else:
                archive.close()
                self.c.close()
                self.conn.close()
                os.remove(db_name)

        if not os.path.exists(db_name):
            print('db not exists')
            self.conn = sqlite3.connect(db_name)
            archive = TarFile.open('table.tar.bz2', 'r:bz2')
            member = archive.getmember('table.txt')
            chksum = member.chksum
            size = member.size
            f = archive.extractfile('table.txt').read().decode()

            self.c = self.conn.cursor()
            self.c.execute(
                'CREATE TABLE table1 (id INT, name TEXT, size INT, seeds INT, peers INT, hash TEXT, downloads INT, DATE DATE)')
            # self.c.execute('''CREATE VIRTUAL TABLE table1 USING fts4(tokenize=porter, id INT, name TEXT, size INT, seeds INT, peers INT, hash TEXT, downloads INT, DATE DATE)''')

            self.c.execute('CREATE TABLE main (name TEXT, value TEXT)')
            self.c.execute('INSERT INTO main VALUES(\'chksum\', \'' + str(chksum) + '\')')
            self.c.execute('INSERT INTO main VALUES(\'size\', \'' + str(size) + '\')')

            for line in f.splitlines():
                id, name, size, seeds, peers, hash, downloads, date = line.strip().split(sep='\t')
                name = str.replace(name, '\'', '?')
                sql = '''INSERT INTO table1 VALUES (%s, '%s', %s, %s, %s, '%s', %s, '%s')''' % (
                    id, name, size, seeds, peers, hash, downloads, date)
                self.c.execute(sql)

            self.conn.commit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())