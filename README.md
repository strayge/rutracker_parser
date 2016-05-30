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

### Args

--ids 0000001 0001000 - download specified range of ids  
--ids_file file_with_ids.txt - download ids from specified file  
--ids_ignore old_finish.txt - exclude ids not existed in specified file (as example, skip doesn't existed ids from previous crawling)  
--random - download in random order  
--threads 100 - count of threads for downloading  
--proxy_file proxy.txt - specified file with socks5 proxies (default - proxy.txt)  
--login_file login.txt - specified file with logins and passwords (default - login.txt)  
--resume - resuming previous crawling (skipping downloaded ids from finished.txt)  
--print - with 'resume' closes program after showing finished/left counters  
--folder descriptions - specifying dir for descriptions of (default - descr)  
--qsize 20 - max queue for downloading (default - 30)  

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
  * ...

Screenshot
![Screenshot](viewer_screenshot.png?raw=true)

In search:
* **word** for include word
* **-word** for exclude word
* **limit:5** for set limit of search results (by default - 20)

Double click on hash to copy **magnet-link** into clipboard.

Search is running by seeds count. (if want change - resort table_sorted.txt in table_sorted.tar.bz2 as you want).

