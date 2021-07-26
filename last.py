#!/usr/bin/env python3

import os, subprocess

def run():
    if not os.path.exists ( "baking.log" ):
        return
    f=open("baking.log","rt")
    lines = f.readlines()
    f.close()
    print ( lines[-1] )
    subprocess.getoutput ( lines[-1] )

run()
