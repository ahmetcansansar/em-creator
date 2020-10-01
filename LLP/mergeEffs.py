#!/usr/bin/env python

#Reads a series of efficiency files  with the efficiency as a function of width and the corresponding SLHA
#files and construct a single efficiency map.

import sys
from configParserWrapper import ConfigParserExt
import logging
import time
import os
import multiprocessing
import numpy as np
import math,glob,tarfile
import pyslha

FORMAT = '%(levelname)s in %(module)s.%(funcName)s() in %(lineno)s: %(message)s at %(asctime)s'
logging.basicConfig(format=FORMAT,datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)



if __name__ == "__main__":

    import argparse
    ap = argparse.ArgumentParser( description=
            "Build efficiency map" )
    ap.add_argument('-p', '--parfile', default='map_parameters.ini',
            help='path to the parameters file.')
    ap.add_argument('-v', '--verbose', default='error',
            help='verbose level (debug, info, warning or error). Default is error')


    t0 = time.time()

    args = ap.parse_args()

    level = args.verbose.lower()
    levels = { "debug": logging.DEBUG, "info": logging.INFO,
               "warn": logging.WARNING,
               "warning": logging.WARNING, "error": logging.ERROR }
    if not level in levels:
        logger.error ( "Unknown log level ``%s'' supplied!" % level )
        sys.exit()
    logger.setLevel(level = levels[level])

    parser = ConfigParserExt()
    ret = parser.read(args.parfile)
    if ret == []:
        logger.error( "No such file or directory: '%s'" % args.parfile)
        sys.exit()

    effFolder = parser.get("options","effFolder")
    slhaFolder = parser.get("options","slhaFolder")
    outputFile =parser.get("options","outputFile")
    massColumns =parser.get("options","massColumns")
    effColumns =parser.get("options","effColumns")
    sortBy =parser.get("options","sortBy")


    #Loop over SLHA files and get efficiencies for each point
    data = []
    for slha in glob.glob(slhaFolder+'/*.slha'):
        effFile = os.path.join(effFolder,os.path.basename(slha).replace('.slha','.eff'))
        if not os.path.isfile(effFile):
            logger.warning('Efficiency file %s not found. Skipping.' %effFile)
            continue

        slhaData = pyslha.readSLHAFile(slha)
        #Open efficiency file
        effs = np.genfromtxt(effFile,names=True)
        if any(not clabel in effs.dtype.names for _,clabel in effColumns):
            logger.error("Missing columns in efficency file. Columns found: %s" %str(effs.dtype.names))
            sys.exit()

        masses = [slhaData.blocks['MASS'][int(massPDG)] for _,massPDG in massColumns]
        for pt in effs:
            row = masses + [pt[column] for _,column in effColumns]
            data.append(row)

    #Create numpy array to store data:
    effs = np.zeros(len(data),dtype=[(c,float) for c,_ in massColumns+effColumns])
    print(len(data))
    for i,pt in enumerate(data):
        effs[i] = tuple(pt)

    effs = np.sort(effs,order=sortBy)
    #Save results to file:
    header = '%19s'*len(effs.dtype.names) %effs.dtype.names
    header = header[3:]
    np.savetxt(outputFile,effs,header=header,fmt = ['     %1.7e']*len(effs.dtype.names))


    print("\n\nDone in %3.2f min" %((time.time()-t0)/60.))
