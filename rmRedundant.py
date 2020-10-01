#!/usr/bin/python3

import bakeryHelpers, subprocess

def getGoodMasses():
    """ get list of masses we actually want """
    masses=bakeryHelpers.parseMasses ( "[(200,2101,50),(0,2001,50)]", mingap1=1. )
    masses+=bakeryHelpers.parseMasses ( "[(200,2101,50),(0,1501,10)]", maxgap1=31. )
    return masses

def getExistingMasses(topo="T2"):
    """ get list of masses we actually have """
    masses = bakeryHelpers.getListOfMasses ( topo, True, 13 )
    return masses

def massInGood ( mass, good ):
    """ is mass vector in list of good mass vectors? """
    for g in good:
        if mass == g:
            return True
    return False

def existingNotInGood ( existing, good ):
    """ get list of masses we do not want """
    ret=[]
    nRemoved = 0
    for mass in existing:
        isInGood = massInGood ( mass, good )
        if not isInGood:
            # T2_600_460.13.saf
            nRemoved += 1
            cmd = "rm -r results/T2_%d_%d.13.saf" % mass
            subprocess.getoutput  ( cmd )
            cmd = "rm -r results/T2_%d_%d.13.dat" % mass
            subprocess.getoutput  ( cmd )
    print ( "removed %d files" % nRemoved )

def main():
    good = getGoodMasses()
    existing = getExistingMasses ()
    remove = existingNotInGood ( existing, good )

main()
