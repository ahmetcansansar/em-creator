#!/usr/bin/env python3

""" collection of snippets needed in various places """

import glob, time, subprocess, os

def rmLocksOlderThan ( hours=8 ):
    """ remove all locks older than <hours> """
    files = glob.glob ( ".lock*" )
    t = time.time()
    for f in files:
        try:
            ts = os.stat(f).st_mtime
            dt = ( t - ts ) / 60. / 60.
            if dt > hours:
                self.msg ( "removing old lock %s [%d hrs old]" % ( f, int(dt) ) )
                subprocess.getoutput ( "rm -f %s" % f )
        except:
            pass

if __name__ == "__main__":
    rmLocksOlderThan( 8 )
