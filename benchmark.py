#!/usr/bin/env python3

import subprocess

def add ( topo, masses ):
    # destdir = 'lxplus.cern.ch:/eos/project-s/smodels/www/ADL/'
    # destdir = 'saphire:/media/storage/adl/'
    destdir = "/mnt/hephy/pheno/ww/adl"
    f=open("run.sh","at")
    nproc=5
    common = f'./mg5Wrapper.py -n 100000 --cutlang -p {nproc} -a -k --analyses "cms_sus_19_006"'
    line = f'{common} -m "{masses}" -t {topo}\n'
    f.write ( line )
    smasses = "_".join ( map ( str, masses ) )
    line = f'rm -rf {topo}_1jet.{smasses}\n'
    f.write ( line )
    line = f'rm -rf cutlang_results/CMS-SUS-19-006/ANA_{topo}_1jet/temp/{topo}.{smasses}.13.hepmc\n'
    f.write ( line )
    dest = destdir
    source = f'mg5results/{topo}_{smasses}.13.hepmc.gz'
    line = f'scp {source} {dest}\n'
    f.write ( line )
    line = f'rm -rf {source}\n'
    f.write ( line )
    source = f'cutlang_results/CMS-SUS-19-006/ANA_{topo}_1jet/output/delphes_out_{smasses}.root'
    dest = f'{destdir}/delphes_{topo}_{smasses}.root'
    line = f'scp {source} {dest}\n'
    f.write ( line )
    line = f'rm -rf {source}\n'
    f.write ( line )

    f.write ( "\n" )
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
    # points = { "T2tt": [ [950,100],  [600,400] ] }
    for topo, massvecs in points.items():
        for masses in massvecs:
            add ( topo, masses )
    subprocess.getoutput ( "chmod 755 run.sh" )


if __name__ == "__main__":
    run()
