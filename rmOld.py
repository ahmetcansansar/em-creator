#!/usr/bin/env python3

""" remove all Tx_1jet_yyy_zzz folders that are older than n days """

import glob, os, time, pickle, subprocess, argparse

def daysFromNow ( timestamp ):
    """ compute how many days in the past from now """
    t0=time.time()
    return ( t0 - timestamp ) / 60. / 60. / 24.

def hoursFromNow ( timestamp ):
    """ compute how many days in the past from now """
    t0=time.time()
    return ( t0 - timestamp ) / 60. / 60.

def pprint( sdirs ):
    """ print oldest dirs """
    keys = list(sdirs.keys())
    keys.sort()
    for k in keys[:20]:
        #d = daysFromNow(k)
        #print ( "%25s: %.1f days old" % ( sdirs[k], d ) )
        h = hoursFromNow(k)
        print ( "%25s: %.1f hours old" % ( sdirs[k], h ) )

def savePickle ( sdirs ):
    """ write to pickle """
    f=open("stats.pcl","wb" )
    pickle.dump ( sdirs, f )
    f.close()

def createStats():
    """ produce the stats from scratch """
    t0=time.time()
    sdirs = {}
    files = glob.glob("T*")
    for f in files:
        if "TODO" in f:
            continue
        ms = os.stat ( f ).st_mtime
        sdirs[ms]=f
    """
    files = glob.glob("ma5/ANA_T*")
    for f in files:
        ms = os.stat ( f ).st_mtime
        sdirs[ms]=f
    """
    return sdirs

def loadPickle():
    """ load from pickle """
    f=open("stats.pcl","rb" )
    sdirs = pickle.load ( f )
    f.close()
    return sdirs

def rmOlderThan( sdirs, days, dry_run ):
    """ remove all older than <days> days 
    :dry_run: just pretend, if true
    """
    keys = list(sdirs.keys())
    keys.sort()
    for k in keys[:20]:
        d = daysFromNow(k)
        if d > days:
            print ( "removing %s: %.1f days old." % ( sdirs[k], d ) )
            cmd = "rm -rf %s" % sdirs[k]
            o = "dry_run"
            if not dry_run:
                o = subprocess.getoutput ( cmd )
            print ( "   %s: %s" % ( cmd, o ) )
            cmd = "rm -rf ma5/ANA_%s" % sdirs[k] 
            if not dry_run:
                o = subprocess.getoutput ( cmd )
            print ( "   %s: %s" % ( cmd, o ) )

def main():
    argparser = argparse.ArgumentParser(description='remove old directories.')
    argparser.add_argument ( '-t', '--days', help='number of days the dir has to be old [1]',
                             type=int, default=1 )
    argparser.add_argument ( '-f', '--force_rebuild', help='force rebuilding pickle file',
                             action="store_true" )
    argparser.add_argument ( '-d', '--dry_run', help='dry_run, dont remove',
                             action="store_true" )
    args = argparser.parse_args()
    if os.path.exists ( "stats.pcl" ) and not args.force_rebuild:
        sdirs = loadPickle()
    else:
        sdirs = createStats()
        savePickle ( sdirs )
    pprint ( sdirs )
    dry_run = True
    rmOlderThan ( sdirs, args.days, args.dry_run )

main()
