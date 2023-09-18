#!/usr/bin/env python3

"""
.. module:: findCheckMateAnalysesNames
   :synopsis: a tool to find a mapping of checkmate's analysis names
              (that are based on the preprint id) to our names 
              (that are based on the collaborations internal names

.. moduleauthor:: Wolfgang Waltenberger <wolfgang.waltenberger@gmail.com>

"""

import sys, os
ourpath  = os.path.dirname ( __file__ ).replace ( "/utils", "" ).replace("/.","/")
sys.path.insert(0,"../")
from smodels.experiment.databaseObj import Database

def retrieveOldDictionary ( filename : str = "./cm2names.dict" ) -> dict:
    """ see if there is an old dictionary lying around. 
        we would start with it, and overwrite entries """
    filename = standardizePaths ( filename )
    ret = {}
    if not os.path.exists ( filename ):
        return ret
    f = open (  filename, "rt" )
    ret = eval ( f.read() )
    f.close()
    return ret

def standardizePaths ( path ):
    """ make sure relative paths work also """
    if not "." in path:
        return os.path.abspath ( path )
    path = os.path.abspath ( os.path.join ( ourpath, path ) )
    return path

def findNames( dbpath ):
    database = Database( standardizePaths ( dbpath ) )
    expResults = database.expResultList
    D = retrieveOldDictionary ( )
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

def writeToFile ( D : dict, filename : str = "./cm2names.dict" ):
    filename = standardizePaths ( filename )
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
    D = findNames( "../smodels-database" )
    writeToFile ( D )
