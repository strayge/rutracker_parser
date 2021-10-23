#!/usr/bin/env python3

items = []
print('reading...')
f = open('table.txt', 'r', encoding='utf8')
for line in f:
    item = line.strip().split(sep='\t')
    items.append(item)
f.close()

print('sorting...')
items.sort(key=lambda x: int(x[3]), reverse=True)

print('writing...')
f = open('table_sorted.txt', 'w', encoding='utf8')
for item in items:
    line = ''
    for subitem in item:
        line += str(subitem) + '\t'
    f.write(line + '\n')
f.close()

print('compressing...')
import tarfile
tar = tarfile.open("table_sorted.tar.bz2", "w:bz2")
for name in ["table_sorted.txt"]:
    tar.add(name)
tar.close()
print("Done")
