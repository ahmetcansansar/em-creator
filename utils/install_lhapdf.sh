#!/bin/sh

VER="6.3.0"

wget https://lhapdf.hepforge.org/downloads/?f=LHAPDF-${VER}.tar.gz -O LHAPDF-${VER}.tar.gz
# ^ or use a web browser to download, which will get the filename correct
tar xf LHAPDF-${VER}.tar.gz
cd LHAPDF-${VER}
./configure --prefix=~/.local/
make
make install
