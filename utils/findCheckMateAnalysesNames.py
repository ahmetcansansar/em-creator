#!/usr/bin/env python3

"""
.. module:: findCheckMateAnalysesNames
   :synopsis: a tool to find a mapping of checkmate's analysis names
              (that are based on the preprint id) to our names 
              (that are based on the collaborations internal names

.. moduleauthor:: Wolfgang Waltenberger <wolfgang.waltenberger@gmail.com>

"""

import sys
sys.path.insert(0,"../")
from smodels.experiment.databaseObj import Database


def findNames( dbpath ):
    database = Database( dbpath )
    expResults = database.expResultList
    D = {}
    for er in expResults:
        Id = er.globalInfo.id
        collab = "cms" if "CMS" in Id else "atlas"
        arxiv = "none"
        if hasattr ( er.globalInfo, "arxiv" ):
            arxiv = er.globalInfo.arxiv
        if hasattr ( er.globalInfo, "arXiv" ):
            arxiv = er.globalInfo.arXiv
        arxiv = str(arxiv)
        arxiv = arxiv.replace("arXiv:","").replace("arxiv:","")
        arxiv = arxiv.replace("v2","")
        if arxiv.endswith ( ".pdf" ):
            arxiv = arxiv[:-4]
        p1 = arxiv.rfind ( "/" )
        if p1 > 0:
            arxiv = arxiv[p1+1:]
        if arxiv != "none":
            cm2name = f"{collab}_{arxiv.replace('.','_')}"
            D[cm2name]=Id
    for k,v in D.items():
        print ( f"{k} :: {v}" )
    return D

def writeToFile ( D : dict, filename : str = "../cm2names.dict" ):
    f = open ( filename, "wt" )
    f.write ( f"# dictionary for analyses names: checkmate2 <-> SModelS\n" )
    import time
    f.write ( f"# created {time.asctime()}\n" )
    f.write ( "{" )
    for k,v in D.items():
        f.write ( f"'{k}':'{v}',\n" )
    f.write ( "}\n" )
    f.close()

if __name__ == "__main__":
    D = findNames( "../../smodels-database" )
    writeToFile ( D )
