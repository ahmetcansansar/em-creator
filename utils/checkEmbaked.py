#!/usr/bin/env python3

""" check .embaked files, look at double entries, etc """

import sys
import time
import numpy
import subprocess

def discussStatistics ( saved ):
    nzero=0
    nevs = []
    for k,v in saved.items():
        if "__nevents__" in v.keys():
            nevs.append ( v["__nevents__"] )
        else:
            nzero+=1
    print ( "%d with no nevents record" % nzero )
    if len(nevs)==0:
        print ( "no entries with nevents record" )
    else:
        print ( "%d nevents between %d and %d" % \
                ( len(nevs), min(nevs), max(nevs) ) )


def isAnOffshellGuy ( masses, values ):
    """ find out if this is such an offshell guy """
    if "__nevents__" in values:
        return False
    if masses[1]<(masses[2]+80.) and abs(masses[2]-60.)>.1:
        return True
    return False

def check ( topo, overwrite, stats, remove_offshell  ):
    """
    :param topo: e.g. T5WW
    :param overwrite: overwrite embaked file with cleaned version
    :param stats: print some stats about nevents
    :param remove_offshell: remove guys with no __nevents__ that have an
       offhsell second decay and an LSP mass != 60. This is a hack 
       to attempt to fix T6WWoffleft 
    """
    f=open("embaked/%s.embaked" % topo, "rt" )
    lines=f.readlines()
    f.close()
    allms = set()
    saved = {}
    comments = set()
    for ctr,line in enumerate(lines):
        if "#" in line:
            p = line.find("#" )
            comments.add ( line[p:] )
            line=line[:p]
        if line=="":
            continue
        if line[0]=="{":
            line = line[1:]
        line = line.strip()
        if line == "}":
            continue
        kv = line.split(":",1)
        masses = eval(kv[0])
        svs = kv[1]
        if svs.endswith(","):
            svs = svs[:-1]
        values = eval(svs)
        isOldOffshell = isAnOffshellGuy ( masses, values )
        if isOldOffshell and remove_offshell:
            print ( "[checkEmbaked] I have an offshell guy but without nevents: %s. You asked for removal." % str(masses  ))
            continue
        if masses in allms:
            print ( "[checkEmbaked] mass vector %s appears twice!" % str(masses) )
            if not "__nevents__" in saved[masses]:
                print ( "[checkEmbaked] old version has no nevents. overwrite!" )
                saved[masses]=values
                continue
            if not "__nevents__" in values:
                print ( "[checkEmbaked] new version has no nevents. keep old!" )
                continue
            nold = saved[masses]["__nevents__"]
            nnew = values["__nevents__"]
            if nnew > nold:
                print ( "[checkEmbaked] newer version has more events. overwrite!" )
                saved[masses]=values
                continue
        else:
            saved[masses]=values
        allms.add ( masses )
    newFile = "new%s.embaked" % topo
    if overwrite:
        newFile = "%s.embaked" % topo
    print ( "[checkEmbaked] storing cleaned embaked file as %s" % newFile )
    f=open( newFile, "wt" )
    for c in comments:
        f.write ( c )
    f.write ( "# rewritten %s\n" % time.asctime() )
    f.write ( "{" )
    for k,v in saved.items():
        f.write ( "%s: %s,\n" % ( str(k), str(v) ) )
    f.write ( "}\n" )
    f.close()
    if stats:
        discussStatistics ( saved )

if __name__ == "__main__":
    import argparse
    argparser = argparse.ArgumentParser(description =
        'check embaked files, remove dupes')
    argparser.add_argument ('-t', '--topo',
        help = 'topo to look at [T6WWleft]',\
        default = "T6WWleft", type = str )
    argparser.add_argument ('-w', '--overwrite',
        help = 'overwrite old embaked file',\
        action = 'store_true' )
    argparser.add_argument ('-c', '--copy',
        help = 'copy yourself to em-creator',\
        action = 'store_true' )
    argparser.add_argument ('-r', '--remove_offshell',
        help = 'remove offshell guys that have no __nevents__ and have mSLP!=60',\
        action = 'store_true' )
    argparser.add_argument ('-s', '--stats',
        help = 'show some stats',\
        action = 'store_true' )
    args = argparser.parse_args()
    if args.copy:
        cmd = "cp ./checkEmbaked.py ../../../../../em-creator"
        out = subprocess.getoutput ( cmd )
        if out != "":
            print ( "[checkEmbaked] %s" % out )
        sys.exit()
    check ( args.topo, args.overwrite, args.stats, args.remove_offshell )
