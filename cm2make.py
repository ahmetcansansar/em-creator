#!/usr/bin/env python3

""" Simple script that handles the installation of checkmate2.
    and its plugins.
"""

import subprocess, os, sys
    
ver="2.0.37"

def install_plugins():
    print ( "[make.py] installing plugins (tail -f /tmp/cm2.install to monitor) ... " )
    f=open("install.script","r")
    lines=f.readlines()
    f.close()
    for line in lines:
        if line[0]=="#":
            continue
        print ( " - %s" % line.strip() )
        ## installing.txt is what is being installed right now
        f=open("installing.txt","w")
        f.write(line)
        f.close()
        cmd = "python3 bin/cm2 -s -f installing.txt 2>&1 | tee /tmp/cm2.install"
        a = subprocess.getoutput ( cmd )
        print ( a )
    os.unlink ( "installing.txt" )

def install():
    # checkDependencies()
    if os.path.exists ( "bin/cm2" ):
        print ( "[make.py] not installing cm2: bin/cm2 exists" )
        return
    if os.path.exists ( "bin" ):
        ## so 'bin' exists, but not 'bin/cm2'. clean!
        clean()
    print ( "installing cm2 ..." )
    url = "git@github.com:CheckMATE2/checkmate2.git"
    cmd = f"git clone {url}"
    o = subprocess.getoutput ( cmd )
    print ( f"git clone: {o}" )
    cmd = "cd checkmate2 ; autoreconf"
    o = subprocess.getoutput ( cmd )
    print ( f"autoreconf: {o}" )
    delphespath = "../../delphes/"
    hepmcpath = "../../hepmc2/hepmc/HepMC-2.06.11/"
    madgrafpath = "../../mg5/"
    # pythiapath = "../../mg5/HEPTools/pythia8/"
    cmd = f"cd checkmate2 ; CPPFLAGS='-I {hepmcpath}'; ./configure --with-delphes={delphespath} --with-hepmc={hepmcpath} --with-madgraph={madgrafpath}"
    o = subprocess.getoutput ( cmd )
    print ( f"configure: {cmd} {o}" )

def isInstalled ( library ):
    """ is library installed (deb) """
    cmd = "dpkg -l %s | tail -n 1" % library
    o = subprocess.getoutput ( cmd )
    if o.startswith ( "ii" ):
        return True
    if o.startswith ( "un" ):
        return False
    print ( "cannot decipher dpkg output %s" % o )
    return False

def checkDependencies():
    """ check the dependencies on deb packages """
    fj = isInstalled ( "libfastjet-dev" )
    if not fj:
        print ( "libfastjet-dev not installed" )
        sys.exit()

def clean():
    import glob
    for file in glob.glob ( "*" ):
        if file not in [ "make.py", "install.script", "Makefile" ]:
            cmd = "rm -rf %s" % file
            subprocess.getoutput ( cmd )

if __name__ == "__main__":
    import inspect
    D = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) 
    os.chdir ( D )
    if len(sys.argv)>1 and sys.argv[1]=="clean":
        clean()
        sys.exit()
    if len(sys.argv)>1 and sys.argv[1]=="plugins":
        install_plugins()
        sys.exit()
    install()
    install_plugins()
