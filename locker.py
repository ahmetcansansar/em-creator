#!/usr/bin/env python3

"""
.. module:: mg5Wrapper
        :synopsis: code that wraps around MadGraph5. Produces the data cards,
                   and runs the mg5 executable.

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
    def __init__ ( self, sqrts, topo, ignore_locks ):
        """
        the locking mechanism as a class
        :param sqrts: center of mass energy, e.g. 13
        :param topo: topology, e.g. T2
        :param ignore_locks: ignore all locks? for debugging only
        """
        self.basedir = bakeryHelpers.baseDir()
        self.ignore_locks = ignore_locks
        os.chdir ( self.basedir )
        self.sqrts = sqrts
        self.topo = topo

    def lockfile ( self, masses ):
        ret = "%s/.lock%d_%s_%s" % ( self.basedir, self.sqrts, str(masses).replace(" ","").replace("(","").replace(")","").replace(",","_"), self.topo )
        return ret

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

if __name__ == "__main__":
    l = Locker ( 13, "T2", False )
    l.lock( [120,100] )
