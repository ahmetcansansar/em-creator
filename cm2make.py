#!/usr/bin/env python3

""" Simple script that handles the installation of checkmate2.
"""

import subprocess, os, sys, shutil
sys.path.insert(0,"../")
from bakeryHelpers import execute, nCPUs
    
ver="2.0.37"

def installHepMC2():
    path = os.path.abspath ( "../hepmc2/" )
    if not os.path.exists ( path ):
        cmd = "cp -r ../hepmc2.template ../hepmc2"
        subprocess.getoutput ( cmd )

def checkForCurl():
    """ check if unix curl is available on the system """
    exe = shutil.which ( "curl" )
    if exe is None:
        print ( "[make.py] not installing cm2: unix tool 'curl' is missing. install with e.g. apt|rpm install curl" )
        sys.exit()
    return True

def install():
    checkForCurl()
    installHepMC2()
    if os.path.exists ( "checkmate2/bin/CheckMATE" ):
        print ( "[make.py] not installing cm2: checkmate2/bin/CheckMATE exists" )
        return
    if os.path.exists ( "checkmate2/" ):
        ## so 'bin' exists, but not 'bin/cm2'. clean!
        clean()
    print ( "installing cm2 ..." )
    # url = "git@github.com:CheckMATE2/checkmate2.git"
    url = "https://github.com/CheckMATE2/checkmate2.git"
    cmd = f"git clone {url}"
    execute ( cmd )
    #cmd = "cd checkmate2 ; mv aclocal.m4 aclocal.old ; aclocal && libtoolize --force && autoreconf"
    autoreconf = shutil.which ( "autoreconf" )
    if autoreconf == None:
        print ( "error: autoreconf not found! maybe you need to install the autoconf package?" )
        sys.exit()
    cmd = "autoreconf"
    execute ( cmd, cwd = "checkmate2" )
    libtool = shutil.which ( "libtool" )
    if libtool == None:
        print ( "error: libtool not found! let me try to continue though." )
    else:
        cmd = f"cp {libtool} ."
        execute ( cmd, cwd = "checkmate2" )
    delphespath = os.path.abspath ( "../delphes/" )
    hepmcpath = os.path.abspath ( "../hepmc2/HepMC-2.06.11/" )
    madgrafpath = os.path.abspath ( "../mg5/" )
    # pythiapath = "../../mg5/HEPTools/pythia8/"
    cmd = f"CPPFLAGS='-I {hepmcpath} -I {delphespath}' ./configure --with-delphes={delphespath} --with-hepmc={hepmcpath} --with-madgraph={madgrafpath}"
    #env = { "CPPFLAGS": f"-I {hepmcpath} -I {delphespath}"}
    # cmd = f"./configure --with-delphes={delphespath} --with-hepmc={hepmcpath} --with-madgraph={madgrafpath}"
    execute ( cmd, cwd = "checkmate2" )
    cmd = "cp /bin/libtool ."
    execute ( cmd, cwd = "checkmate2" )
    ncpus = int ( max ( nCPUs() / 2 - 1, 1 ) )
    cmd = f"make -j {ncpus}" 
    execute ( cmd, cwd = "checkmate2" )

def clean():
    import glob
    for file in glob.glob ( "*" ):
        if file not in [ "make.py", "Makefile" ]:
            cmd = "rm -rf %s" % file
            subprocess.getoutput ( cmd )

if __name__ == "__main__":
    import inspect
    D = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) 
    os.chdir ( D )
    if len(sys.argv)>1 and sys.argv[1]=="clean":
        clean()
        sys.exit()
    install()
