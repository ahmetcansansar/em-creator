#!/usr/bin/env python3

"""
.. module:: locker
   :synopsis: code to lock and unlock certain mass points,
              for given topologies and sqrts. used to make sure,
              we dont run the same point in parallel

.. moduleauthor:: Wolfgang Waltenberger <wolfgang.waltenberger@gmail.com>
"""

import os, sys, subprocess, time, socket, random
import signal
import bakeryHelpers

__locks__ = set()

def signal_handler(sig, frame):
    print('You pressed Ctrl+C, remove all locks!')
    for l in __locks__:
        cmd = "rm -f %s" % l
        subprocess.getoutput ( cmd )
        print ( cmd )
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

class Locker:
    def __init__ ( self, sqrts, topo, ignore_locks, prefix=".lock" ):
        """
        the locking mechanism as a class
        :param sqrts: center of mass energy, e.g. 13
        :param topo: topology, e.g. T2
        :param ignore_locks: ignore all locks? for debugging only
        :param prefix: prefix for lock files
        """
        self.basedir = bakeryHelpers.baseDir()
        self.ignore_locks = ignore_locks
        os.chdir ( self.basedir )
        self.sqrts = sqrts
        self.topo = topo
        self.prefix = prefix

    def lockfile ( self, masses ):
        m = str(masses).replace(" ","").replace("(","").replace(")","")
        m = m.replace(",","_")
        ret = f"{self.basedir}/{self.prefix}{self.sqrts}_{m}_{self.topo}"
        return ret

    def isLocked ( self, masses ):
        """ a simple query if a point is locked, 
            but does not lock itself. """
        filename = self.lockfile( masses )
        return os.path.exists ( filename )

    def lock ( self, masses ):
        """ lock for topo and masses, to make sure processes dont
            overwrite each other
        :returns: True if there is already a lock on it
        """
        if self.ignore_locks:
            return False
        filename = self.lockfile( masses )
        __locks__.add ( filename )
        if os.path.exists ( filename ):
            return True
        for i in range(5):
            try:
                with open ( filename, "wt" ) as f:
                    f.write ( time.asctime()+","+socket.gethostname()+"\n" )
                    f.close()
                return False
            except FileNotFoundError as e:
                t0 = random.uniform(2.,4.*i)
                self.msg ( "FileNotFoundError #%d %s. Sleep for %.1fs" % ( i, e, t0 ) )
                time.sleep( t0 )
        return True ## pretend there is a lock

    def unlock ( self, masses ):
        """ unlock for topo and masses, to make sure processes dont
            overwrite each other """
        if self.ignore_locks:
            return
        filename = self.lockfile( masses )
        if filename in __locks__:
            __locks__.remove ( filename )
        if os.path.exists ( filename ):
            cmd = "rm -f %s" % filename
            subprocess.getoutput ( cmd )

    def hepmcFileName ( self, masses ):
        """ return the hepmc file name at final destination.
            admittedly has not much to do with locking, but it's a nice
            way to share this method between ma5Wrapper and mg5Wrapper """
        smasses = "_".join(map(str,masses))
        resultsdir = os.path.join(self.basedir, "mg5results")
        dest = "%s/%s_%s.%d.hepmc.gz" % \
               ( resultsdir, self.topo, smasses, self.sqrts )
        return dest

    def hasHEPMC ( self, masses ):
        """ does it have a valid HEPMC file? if yes, then skip the point """
        hepmcfile = self.hepmcFileName( masses )
        if not os.path.exists ( hepmcfile ):
            return False
        if os.stat ( hepmcfile ).st_size < 100:
            ## too small to be real
            return False
        return True

if __name__ == "__main__":
    l = Locker ( 13, "T2", False )
    masses=(120,100)
    l.lock( masses )
    il = l.isLocked ( masses )
    print ( f"after locking: {masses} is locked? {il}" )
    l.unlock( masses )
    il = l.isLocked ( masses )
    print ( f"after unlocking: {masses} is locked {il}" )
