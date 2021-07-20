#!/bin/sh

echo "Cloning em-creator repository."
#git clone git@github.com:SModelS/em-creator.git
echo "em-creator cloned"

echo "cd em-creator"
# cd em-creator

echo "pip3 install -r requirements.txt"
# pip3 install --user -r requirements.txt

# this checks if we mounted a directory containing hepmc example exp.hepmc and if so runs CLA wrapper on it
# to mount the directory add: 
# -v /path/on/host/to/exp.hepmc:/tmp/exp.hepmc
if [ -e /src/em-creator/docker/test.hepmc ]
then 
  ../cutlangWrapper.py -d /src/em-creator/docker/test.hepmc -m "(300, 100)" --rerun -a CMS-SUS-16-037
fi

