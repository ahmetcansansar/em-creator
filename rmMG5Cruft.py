#!/usr/bin/env python3

""" from a MG5 installation at mg5/ remove some cruft """

import subprocess, glob, os

def rm():
    base = "mg5/"
    dirs = [ "HEPTools/boost/boost_1_74_0", "HEPTools/boost/include/" ]
    dirs.append ( "HEPTools/pythia8/include/" )
    dirs.append ( "HEPTools/lhapdf6_py3/include/" )
    dirs.append ( "HEPTools/hepmc/include/" )
    dirs.append ( "HEPTools/zlib/include/" )
    dirs.append ( "MG5_aMC_v3.1.1.tar.gz" )
    dirs.append ( "tests/" )

    for d in dirs:
        if not os.path.exists ( base+d ):
            continue
        cmd = f"rm -rf '{base}{d}'"
        print ( cmd )
        subprocess.getoutput ( cmd )


rm()
