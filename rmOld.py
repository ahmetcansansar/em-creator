#!/usr/bin/env python3

""" remove all Tx_1jet_yyy_zzz folders that are older than n days """

import glob, os, time, pickle, subprocess, argparse

def rmOldTempFiles( hours=8 ):
    """ remove temp files older than so and so many hours """
    files = glob.glob ( "temp/*" )
    files += glob.glob ( "cutlang_results/*/ANA_*_*jet/temp/*hepmc" )
    files += glob.glob ( "ma5_T*_*jet.*/" )
    files += glob.glob ( "cutlang_results/*/ANA_*_*jet/temp/CLA*" )
    files += glob.glob ( "cutlang_results/*/ANA_*_*jet/output/delphes_out*root" )
    t = time.time()
    for f in files:
        try:
            ts = os.stat(f).st_mtime
            dt = ( t - ts ) / 60. / 60.
            if dt > hours:
                cmd = "rm -rf %s" % f
                subprocess.getoutput ( cmd )
                print ( cmd )
        except Exception as e:
            pass


def daysFromNow ( timestamp ):
    """ compute how many days in the past from now """
    t0=time.time()
    return hoursFromNow ( timestamp ) / 24.

def hoursFromNow ( timestamp ):
    """ compute how many hours in the past from now """
    t0=time.time()
    return ( t0 - timestamp ) / 60. / 60.

def pprint( sdirs ):
    """ print oldest dirs """
    keys = list(sdirs.keys())
    keys.sort()
    for k in keys: # [:20]:
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
        try:
            ms = os.stat ( f ).st_mtime
            sdirs[ms]=f
        except Exception as e:
            pass
    files = glob.glob("mg5results/T*hepmc.gz")
    for f in files:
        try:
            ms = os.stat ( f ).st_mtime
            sdirs[ms]=f
        except Exception as e:
            pass
    files = glob.glob("../smodels-utils/clip/_B*sh" )
    for f in files:
        try:
            ms = os.stat ( f ).st_mtime
            sdirs[ms]=f
        except Exception as e:
            pass
    files = glob.glob("/users/wolfgan.waltenberger/B*.sh" )
    for f in files:
        try:
            ms = os.stat ( f ).st_mtime
            sdirs[ms]=f
        except Exception as e:
            pass
    files = glob.glob(".lock*" )
    for f in files:
        try:
            ms = os.stat ( f ).st_mtime
            sdirs[ms]=f
        except Exception as e:
            pass
    return sdirs

def loadPickle():
    """ load from pickle """
    f=open("stats.pcl","rb" )
    sdirs = pickle.load ( f )
    f.close()
    return sdirs

def rmOlderThan( sdirs, hours, dry_run ):
    """ remove all older than <hours> hours
    :dry_run: just pretend, if true
    """
    keys = list(sdirs.keys())
    keys.sort()
    for k in keys: # [:20]:
        try:
            h = hoursFromNow(k)
            if h > hours:
                # print ( "removing %s: %.1f hours old." % ( sdirs[k], h ) )
                cmd = "rm -rf %s" % sdirs[k]
                o = "dry_run"
                if not dry_run:
                    o = subprocess.getoutput ( cmd )
                print ( "%s: %s" % ( cmd, o ) )
                #cmd = "rm -rf ma5/ANA_%s" % sdirs[k] 
                #if not dry_run:
                #    o = subprocess.getoutput ( cmd )
                #print ( "   %s: %s" % ( cmd, o ) )
        except Exception as e:
            pass

def main():
    argparser = argparse.ArgumentParser(description='remove old directories.')
    argparser.add_argument ( '-t', '--hours', help='number of hours the dir has to be old [24]',
                             type=int, default=24 )
    #argparser.add_argument ( '-f', '--force_rebuild', help='force rebuilding pickle file',
    #                         action="store_true" )
    argparser.add_argument ( '-d', '--dry_run', help='dry_run, dont remove',
                             action="store_true" )
    args = argparser.parse_args()
    force_rebuild = True
    #if os.path.exists ( "stats.pcl" ) and not force_rebuild:
    #    sdirs = loadPickle()
    #else:
    sdirs = createStats()
    savePickle ( sdirs )
    rmOlderThan ( sdirs, args.hours, args.dry_run )
    rmOldTempFiles ( args.hours )

main()
