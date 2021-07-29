#!/usr/bin/env python3

""" code to remove old temp files """

import glob, os, sys, subprocess, time, argparse

def main( hours=8 ):
    """ remove temp files older than so and so many hours """
    files = glob.glob ( "temp/*" )
    files += glob.glob ( "cutlang_results/*/ANA_*_*jet/temp/*hepmc" )
    files += glob.glob ( "cutlang_results/*/ANA_*_*jet/output/delphes_out*root" )
    t = time.time()
    for f in files:
        try:
            ts = os.stat(f).st_mtime
            dt = ( t - ts ) / 60. / 60.
            if dt > hours:
                cmd = "rm -f %s" % f
                subprocess.getoutput ( cmd )
                print ( cmd )
        except Exception as e:
            pass

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description='remove old temp files.')
    argparser.add_argument ( '-t', '--hours', help='number of hours the temp file has to be old [8]',
                             type=int, default=8 )
    args = argparser.parse_args()
    main( args.hours )
