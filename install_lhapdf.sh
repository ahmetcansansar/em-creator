#!/bin/sh

wget https://lhapdf.hepforge.org/downloads/?f=LHAPDF-6.3.0.tar.gz -O LHAPDF-6.3.0.tar.gz
# ^ or use a web browser to download, which will get the filename correct
tar xf LHAPDF-6.3.0.tar.gz
cd LHAPDF-6.3.0
./configure --prefix=~/.local/bin/
make
make install
