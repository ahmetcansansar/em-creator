#!/usr/bin/env python3

""" code to remove old temp files """

import glob, os, sys, subprocess, time

def main( hours=8 ):
    """ remove temp files older than so and so many hours """
    files = glob.glob ( "temp/*" )
    files += glob.glob ( "cutlang_results/*/ANA_*_*jet/temp/*hepmc" )
    files += glob.glob ( "cutlang_results/*/ANA_*_*jet/output/delphes_out*root" )
    t = time.time()
    for f in files:
        ts = os.stat(f).st_mtime
        dt = ( t - ts ) / 60. / 60.
        if dt > hours:
            cmd = "rm -f %s" % f
            subprocess.getoutput ( cmd )
            print ( cmd )
main()
