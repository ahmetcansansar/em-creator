#!/usr/bin/env python3

import glob, subprocess

def main():
    files = glob.glob("mg5results/*.hepmc.gz" )
    files += glob.glob("results/*.saf" )
    files += glob.glob("results/*.dat" )
    for f in files:
        cmd = "touch %s" % f
        print ( f )
        o = subprocess.getoutput ( cmd )
        print ( o )

main()
