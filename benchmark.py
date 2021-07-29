#!/usr/bin/env python3

def add ( topo, masses ):
    f=open("run.sh","at")
    common = './mg5Wrapper.py -n 100000 --cutlang -p 10 -a -k --analyses "cms_sus_19_006"'
    line = f'{common} -m "{masses}" -t {topo}\n'
    f.write ( line )
    smasses = "_".join ( map ( str, masses ) )
    dest = 'lxplus.cern.ch:/eos/project-s/smodels/www/ADL/'
    source = f'mg5results/{topo}_{smasses}.13.hepmc.gz'
    source += f' cutlang_results/CMS-SUS-19-006/ANA_{topo}_1jet/output/dlphes_out_{smasses}.root'
    line = f'scp {source} {dest}\n\n'
    f.write ( line )
    f.close()

def newShFile ():
    f=open("run.sh","wt")
    f.write ( "#!/bin/sh\n\n" )
    f.close()

def run():
    newShFile()
    points = { "T1tttt": [ [1900,200], [1300,1000] ],
               "T1bbbb": [ [1800,200], [1300,1100] ],
               "T1":     [ [1300,100], [1200,100] ],
               "T5WZh":  [ [1800,100], [1400,1100] ],
               "T2tt":   [ [950,100],  [600,400] ],
               "T2bb":   [ [1000,100], [600,450] ],
               "T2":     [ [1400,200], [1000,800] ] 
    }
    points = { "T2tt": [ [950,100],  [600,400] ] }
    for topo, massvecs in points.items():
        for masses in massvecs:
            add ( topo, masses )


if __name__ == "__main__":
    run()
