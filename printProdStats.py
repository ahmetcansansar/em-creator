#!/usr/bin/env python3

import glob, time, subprocess, os, colorama

def pprint ( text ):
    if not os.path.exists ( "logs/" ):
        subprocess.getoutput ( "mkdir logs" )
    print ( text )
    f=open("logs/prod_%s.txt" % time.asctime().replace(" ","_"), "a" )
    f.write ( text +"\n" )
    f.close()

def ma5():
    dirname = "results/"
    ma5Files = glob.glob ( "%s/*.dat" % dirname )
    ma5Stats={}
    for f in ma5Files:
        f = f.replace(dirname,"")
        process = f.split("_")[0]
        if not process in ma5Stats:
            ma5Stats[process]=0
        ma5Stats[process]+=1
    pprint ( "ma5 production:" )
    keys = list ( ma5Stats.keys() )
    keys.sort()
    for k in keys:
        v=ma5Stats[k]
        pprint ( " - %s: %s summary.dat files" % ( k, v ) )
    goodkeys = {}
    for k in keys:
        p=k.find("_")
        goodkeys[ k[:p] ]=ma5Stats[k]
    return goodkeys

def mg5():
    dirname="mg5results/"
    mg5Files = glob.glob ( "%s/*.hepmc.gz" % dirname )
    mg5Stats={}
    for f in mg5Files:
        f = f.replace(dirname,"")
        p1 = f.find("_")
        process = f[:p1]
        if not process in mg5Stats:
            mg5Stats[process]=0
        mg5Stats[process]+=1
    pprint ( "mg5 production:" )
    keys = list ( mg5Stats.keys() )
    keys.sort()
    for k in keys:
        v=mg5Stats[k]
        pprint ( " - %s: %s hepmc files" % ( k, v ) )
    goodkeys = []
    for k in keys:
        p=k.find("_")
        goodkeys.append ( k[:p] )
    return goodkeys

def inDatabase( topos_c, analysis ):
    """ whats in the database, but print only topos_c topologies 
    :param analysis: print only for analysis
    """
    if type ( analysis ) in [ tuple, list ]:
        for x in analysis:
            inDatabase ( topos_c, x )
        return
    collab = "ATLAS"
    if "CMS" in analysis:
        collab = "CMS"
    dbpath = "../../smodels-database/13TeV/%s/%s-eff/orig" % ( collab, analysis )
    print ("[printProdStats] in database [...%s...]" % dbpath.replace("orig/","")[-40:] )
    # print ( topos_c )
    dbFiles=glob.glob ("%s/T*embaked" % dbpath )
    stats={}
    for i in dbFiles:
        f=open(i)
        g=eval(f.read())
        f.close()
        topo = os.path.basename ( i ).replace(".embaked","")
        stats[topo]=len(g.keys())
    ks = list ( stats.keys() )
    ks.sort()
    for k in ks:
        if not k in topos_c.keys():
            continue
        beg,end="",""
        if stats[k] < topos_c[k]:
            beg,end=colorama.Fore.GREEN,colorama.Fore.RESET
        pprint ( "%s - %s: %d points --> now %d %s" % ( beg, k, stats[k], topos_c[k], end ) )


def main( analysis ):
    mg5()
    topos = ma5()
    inDatabase( topos, analysis )

if __name__ == "__main__":
    main( "cms_sus_16_033" )
