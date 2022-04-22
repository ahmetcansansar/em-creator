#!/usr/bin/env python3

import glob, shutil, os, subprocess

def backup():
    backup = "/groups/hephy/pheno/ww/embaked.backup/"
    backup2 = "/groups/hephy/pheno/ww/embaked.backup2/"
    if not os.path.exists ( backup2 ):
        os.mkdir ( backup2 )
    if not os.path.exists ( backup ):
        os.mkdir ( backup )
    cmd = f"cp {backup}/* {backup2}"
    o = subprocess.getoutput ( cmd )
    print ( f"[backupEmbaked] {cmd}: {o}" )
    cmd = f"cp embaked/* {backup}"
    o = subprocess.getoutput ( cmd )
    print ( f"[backupEmbaked] {cmd}: {o}" )

backup()
