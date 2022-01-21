#!/usr/bin/env python3

""" Simple script that handles the installation of MadAnalysis5.
    and its plugins.
"""

import subprocess, os, sys
    
# ver="1.9.beta"
ver="1.9.60"

def install_plugins():
    print ( "[make.py] installing plugins (tail -f /tmp/ma5.install to monitor) ... " )
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
        cmd = "python3 bin/ma5 -s -f installing.txt 2>&1 | tee /tmp/ma5.install"
        a = subprocess.getoutput ( cmd )
        print ( a )
    os.unlink ( "installing.txt" )

def install():
    # checkDependencies()
    if os.path.exists ( "bin/ma5" ):
        print ( "[make.py] not installing ma5: bin/ma5 exists" )
        return
    print ( "installing ma5 ..." )
    url="https://smodels.github.io/downloads/tarballs/"
    sv = ver.split(".")
    tarball = "ma5_v%s.tgz" % ver
    if sv[2]=="60":
        tarball = f"MadAnalysis5_v{ver}.tgz"
    if not os.path.exists ( tarball ):
        cmd = "wget %s/%s" % ( url, tarball )
        o = subprocess.getoutput ( cmd )
        print ( f"[make.py] wget: {o}" )
    cmd = "tar xzvf %s" % tarball
    subprocess.getoutput ( cmd )
    cmd = "mv madanalysis5/* ."
    subprocess.getoutput ( cmd )
    cmd = "rmdir madanalysis5"
    subprocess.getoutput ( cmd )
    cmd = "rm %s" % tarball
    subprocess.getoutput ( cmd )
    if not os.path.exists ( "bin/ma5" ):
        print ( "something went wrong with the install. please check manually" )
        sys.exit()
    # install_plugins()

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
