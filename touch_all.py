#!/usr/bin/env python3

import glob, subprocess, os

def touch ( Dir, level=0 ):
    """ touch file or directory. if Directory recursively touch
        everything beneath """
    cmd = f"touch {Dir}"
    subprocess.getoutput ( cmd )
    nfiles = 1
    if os.path.isdir ( Dir ):
        files = glob.glob ( Dir+"/*" )
        for f in files:
            nfiles += touch ( f, level+1 )
    if level<2:
        print ( f"{cmd}: {nfiles}" )
    return nfiles


def main():
    touch ( "CutLang/" )
    touch ( "delphes/" )
    touch ( "embaked/" )
    touch ( "mg5/" )
#    touch ( "cutlang_results/" )

main()
