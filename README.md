Rutracker parser
================
This scripts creates local copy of rutracker and allow to view/search throught this copy.

Parser
------------
parser.py - creates local copy of all torrents at rutracker.org.

Its saves line for each torrent in **table.txt** with (separator - /t):
* id
* title
* size (in bytes)
* seeds
* peers
* hash
* downloads
* date
* category

Description for each torrent saves to **./descr/012/0123456** where id = 0123456

For using script needs files **login.txt** with username/passwords and **proxy.txt** with proxies.

Example of login.txt:
```
username1 password1
username2 password2
```

Example of proxy.txt:
```
127.0.0.1 8080
127.0.0.1 8081
```

Example of use
```
python3 ./loader.py --ids 0000001 5160000 --threads 200 --qsize 25 --resume
```

Converting
------------
pack.sh - pack descriptions for viewer

sort.py - sort and pack descriptions for viewer

Viewer
------------
viewer.py - allow search throught local copy.

For work needs:
* **table_sorted.tar.bz2** with table_sorted.txt
* **descr** with dirs 000, 001, 002, ... which contains:
  * 00000.tar.bz2, 00001.tar.bz2, ..., 00099.tar.bz2 for 000
  * 00100.tar.bz2, 00101.tar.bz2, ..., 00199.tar.bz2 for 001

Screenshot
[Screenshot](viewer_screenshot.png)

In search:
* **word** for include word
* **-word** for exclude word
* **limit:5** for set limit of search results (by default - 20)

Search is running by seeds count. (if want change - resort table_sorted.txt in table_sorted.tar.bz2 as you want).

