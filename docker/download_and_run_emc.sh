echo "Cloning em-creator repository."
git clone git@github.com:SModelS/em-creator.git
echo "em-creator cloned"

echo "cd em-creator"
cd em-creator

echo "pip3 install -r requirements.txt"
pip3 install -r requirements.txt

# this checks if we mounted a directory containing hepmc example exp.hepmc and if so runs CLA wrapper on it
# to mount the directory add: 
# -v /path/on/host/to/exp.hepmc:/tmp/exp.hepmc
if [ -e /tmp/exp.hepmc ]
then 
  ./cutlangWrapper.py -d ./exp.hepmc -m "(110, 100, 10)" --rerun -a CMS-SUS-16-037
fi

