#!/bin/bash
cd "descr"
mkdir "tgz"
for i in {000..052}
do
    echo "$i"
    mkdir "tgz/$i"
    cd "$i"
    for j in {00..99}
    do
        echo "$i$j "
        tar -cjf "$i$j.tar.bz2" $i$j*
        mv "$i$j.tar.bz2" "../tgz/$i/"
    done
cd ..
done
echo "Done"
