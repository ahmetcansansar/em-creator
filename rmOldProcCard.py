#!/usr/bin/env python3

import glob, os, sys, subprocess, time

def main():
    topo = "TGQ"
    # topo = "T3GQ"
    dirs = glob.glob( "%s_1jet.*" % topo )
    for i,d in enumerate(dirs):
        print ( "%d/%d: %s" % ( i, len(dirs), d ) )
        fname = "%s/Cards/proc_card_mg5.dat" % d
        if not os.path.exists ( fname ):
            print ( "%s does not exist. skip it" % fname )
            continue
        with open ( fname ) as f:
            lines = f.readlines()
        hasDollar = False
        procline = ""
        for line in lines:
            if "generate" in line:
                procline = line.strip()
            if "generate" in line and "$" in line:
                hasDollar=True
        print ( "procline", procline )
        print ( "dates to", time.ctime( os.stat ( fname ).st_mtime ) )
        if not hasDollar:
            cmd = "rm -rf %s" % d
            o=""
            o=subprocess.getoutput ( cmd )
            print ( cmd, o )
            cmd = "rm -rf ma5/ANA_%s" % d 
            o=""
            o=subprocess.getoutput ( cmd )
            print ( cmd, o )

main()
