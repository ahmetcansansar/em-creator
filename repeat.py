#!/usr/bin/env python3

import subprocess, time

while True:
    o = subprocess.getoutput ( "./bake.py --show" )
    print ( o )
    time.sleep ( 300 )
