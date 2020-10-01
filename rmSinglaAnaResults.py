#!/usr/bin/env python3

import glob, os, sys, subprocess

def main():
    dirs = glob.glob( "ma5/ANA_TGQ_1*/" )
    for d in dirs:
        fname = "%s/Output/CLs_output_summary.dat" % d
        if not os.path.exists ( fname ):
            print ( "%s does not exist. skip it" % fname )
            continue
        with open ( fname ) as f:
            lines = f.readlines()
        res = set()
        anas = [ "cms_sus_16_033", "atlas_susy_2016_07" ]
        for line in lines:
            for ana in anas:
                if ana in line:
                    res.add ( ana )
        nres = len(res)
        print ( d,":",nres )
        if nres < 2:
            cmd = "rm -rf %s" % d
            print ( cmd )
            subprocess.getoutput ( cmd )

main()
