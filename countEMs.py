#!/usr/bin/env python3

"""
.. module:: countEMs
   :synopsis: count efficiency maps per analysis, so we can give overviews 
              of EM bakery efforts, in papers.

.. moduleauthor:: Wolfgang Waltenberger <wolfgang.waltenberger@gmail.com>

"""

import sys
sys.path.insert(0,"../")
from smodels.experiment.databaseObj import Database

dbpath = "../../smodels-database"

database = Database( dbpath )

if __name__ == "__main__":
    print ( database )
    anaids = ['CMS-SUS-16-033','ATLAS-SUSY-2016-07']
    dTypes = [ "efficiencyMap" ]
    useNonValidated = False
    for anaid in anaids:
        print ( "[countEMs] analysis %s" % anaid )
        er = database.getExpResults ( analysisIDs=[ anaid ], dataTypes=dTypes, \
                                      useNonValidated=useNonValidated )
        ns = {}
        nMaps = set()
        nMapSRs = 0
        for ds in er[0].datasets:
            for txn in ds.txnameList:
                nMapSRs += 1
                stxn=str(txn)
                nMaps.add ( stxn )
                # stxn = stxn.replace("off","")
                n = len(txn.txnameData.y_values) 
                if stxn in ns and ns[stxn]>=n:
                    continue
                ns[stxn]=n
        for t in [ "T1tttt", "T2tt", "T5WW" ]:
            if t in ns and t+"off" in ns:
                ns[t+"*"]=ns[t]+ns[t+"off"]
                ns.pop ( t )
                ns.pop ( t+"off" )
        sns = str(ns).replace("'","").replace("{","").replace("}","")
        print ( "[countEMs] number of grid points per topo %s" % sns )
        print ( "[countEMs] sum of all grid points in all topos", sum ( ns.values() ) )
        print ( "[countEMs] number of maps per analysis/dataset", len(nMaps) )
        print ( "[countEMs] number of maps per analysis/dataset/SR", nMapSRs )

    import IPython
    # IPython.embed()
