#!/usr/bin/env python3

""" remove all T* folders that appear wrongly ordered """

import glob, os, sys, subprocess

def correctlyOrdered ( numbers ):
    lastN = 999999
    for n in numbers:
        if n > lastN:
            return False
        lastN = n
    return True

def run():
    files = glob.glob ( "T*_*jet*" )
    files += glob.glob ( "ma5_T*_*jet*" )
    files += glob.glob ( "ma5/ANA_T*_*jet*" )
    for f in files:
        if not "T1" in f and not "T2" in f:
            continue
        if "TGQ" in f or "T3GQ" in f or "T5GQ" in f:
            continue
        p = f.find("jet")
        string = f[p+4:]
        numbers = list ( map ( int, string.split("_") ) )
        cO = correctlyOrdered(numbers)
        if cO == False:
            cmd = "rm -r %s" % f
            print ( cmd )
            subprocess.getoutput ( cmd )

run()
