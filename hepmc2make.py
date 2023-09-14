#!/usr/bin/env python3

""" Simple script that handles the installation of hepmc2
"""

import subprocess, os, sys
    
ver="2.06.11"
tarball = f"hepmc{ver}.tgz"
path = "HepMC-{ver}"
libraryname = f"{path}/fio/libHepMCfio.la"

def fetchTarball():
    """ fetch the hepmc2.06.11.tgz tarball """
    if not os.path.exists ( tarball ):
        cmd = "wget https://smodels.github.io/downloads/tarballs/{tarball}"
        subprocess.getoutput ( tarball )

def explodeTarball():
    fetchTarball()
    if os.path.exists ( path ):
        shutil.rmtree ( path )
    cmd = f"tar xzvf {tarball}"
    subprocess.getoutput ( cmd )

def install():
    if os.path.exists ( libraryname ):
        print ( f"[hepmc2make] not installing hepmc2: {libraryname} exists" )
        return
    if os.path.exists ( path ):
        ## so path exists, but not the library. clean!
        clean()
    print ( "[hepmc2make] installing hepmc2 ..." )
    explodeTarball()

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
