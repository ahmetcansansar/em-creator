#!/usr/bin/env python3

""" remove all Tx_1jet.yyy_zzz folders that come without a lockfile """

import os, glob, subprocess
from bakeryHelpers import rmLocksOlderThan

def rm():
    rmLocksOlderThan ( 8. )
    files = glob.glob ( "T*_*jet.*" )
    for f in files:
        tokens = f.split("_")
        topo = tokens[0]
        mmother = tokens[1].replace("1jet.","")
        mlsp = tokens[2]
        lockfile = f".lock13_{mmother}_{mlsp}_{topo}"
        if os.path.exists ( lockfile ):
            print ( "keeping", f )
        else:
            print ( "removing", f )
            cmd = f"rm -rf {f}"
            subprocess.getoutput ( cmd )


rm()
