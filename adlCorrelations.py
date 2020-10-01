#!/usr/bin/env python3

""" code for the determination of correlations from ADL described 
    analyses """

import ROOT
import pickle, os
import numpy as np

def getAnalysisName ( filename ):
    """given filename, get the name of the analysis """
    ret = filename.replace("_histograms.root","")
    ret = ret.replace("cmssus","")
    ret = ret.replace("cmssus","cms-sus-")
    ret = ret.replace("160","16-0")
    ret = ret.upper()
    return ret

def getEventList( files, nmax = None ):
    """ get a compiled event list for all files all signal regions 
    :param nmax: get no more than nmax events, if None ignore.
    """
    evlist = {}
    for f in files:
        anaName = getAnalysisName ( f )
        rf = ROOT.TFile ( f )
        n = rf.regions.GetEntries()
        if nmax != None and nmax < n:
            n = nmax
        for sr in rf.regions.GetListOfBranches():
            tmp = []
            for i in range( n ):
                rf.regions.GetEntry(i)
                inorout = rf.regions.GetLeaf(sr.GetName()).GetValue()
                tmp.append ( int(inorout) )
            evlist["%s:%s" % ( anaName, sr.GetName() ) ] = tmp
    print ( "[adlCorrelations] event list", evlist )
    return evlist

def getCorrelationMatrix ( files ):
    """ get the correlation matrix between all signal regions in file """
    matrix = loadMatrix()
    if matrix:
        return matrix
    nmax = None # 10
    evlist = getEventList ( files, nmax )
    matrix = {}
    for anaName in evlist.keys():
        n = len(evlist[anaName])
        matrix[anaName]={}
        for name2 in evlist.keys():
            matrix[anaName][name2]=False
    for i in range(n):
        anas = []
        for anaName,events in evlist.items():
            if events[i]==1:
                anas.append ( anaName )
        for n1 in anas:
            for n2 in anas:
                matrix[n1][n2]=True
                matrix[n2][n1]=True
    print ( "[adlCorrelations] matrix", matrix )
    return matrix

def storeMatrix ( matrix ):
    """ store matrix in pickle file """
    f=open("matrix.pcl","wb")
    pickle.dump ( matrix, f )
    f.close()

def loadMatrix ( ):
    """ retrieve matrix from pickle file """
    if not os.path.exists ( "matrix.pcl" ):
        return False
    f=open("matrix.pcl","rb")
    matrix = pickle.load ( f )
    f.close()
    return matrix

def plotMatrix ( matrix ):
    npArray = np.array([list(val.values()) for val in matrix.values()])
    from matplotlib import pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    cm = LinearSegmentedColormap.from_list(
                    "mine", [ "g", "r" ], N=2 )
    plt.imshow ( npArray, cmap = cm )
    plt.subplots_adjust(left=0.05, right=0.97, top=0.97, bottom=0.2)
    ax = plt.axes()
    ax.set_xticks(np.arange(len(matrix.keys())))
    ax.set_yticks(np.arange(len(matrix.keys())))
    ax.set_xticklabels ( matrix.keys() )
    ax.set_yticklabels ( matrix.keys() )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
                     rotation_mode="anchor")
    plt.setp(ax.get_yticklabels(), rotation=45, ha="right",
                     rotation_mode="anchor")
    plt.savefig ( "matrix.png" )

if __name__ == "__main__":
    analyses = [ "cmssus16033_histograms.root", "cmssus16042_histograms.root" ]
    matrix = getCorrelationMatrix ( analyses )
    plotMatrix ( matrix )
    storeMatrix ( matrix )
