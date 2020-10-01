#!/usr/bin/env python

#Reads a series of data files  with the (isolated) HSCP momentum information for each event (in the stable limit)
#and extract the efficiencies as a function of the widths.

import sys
from configParserWrapper import ConfigParserExt
import logging
import time
import os
import multiprocessing
import numpy as np
import math,glob,tarfile



FORMAT = '%(levelname)s in %(module)s.%(funcName)s() in %(lineno)s: %(message)s at %(asctime)s'
logging.basicConfig(format=FORMAT,datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)


class Particle(object):

    def __init__(self,**kargs):

        for key,val in kargs.items():
            setattr(self,key,val)

    def GetPdgCode(self):

        return self.pdg

    def fourMom(self):

        return [self.energy] + self.triMomentum

    def triMom(self):

        return self.triMomentum

    def Eta(self):
        pmom = self.P()
        fPz = self.fourMom()[3]
        if pmom != abs(fPz):
            return 0.5*np.log((pmom+fPz)/(pmom-fPz))
        else:
            return 1e30

    def P(self):

        return math.sqrt(self.triMomentum[0]**2 + self.triMomentum[1]**2 + self.triMomentum[2]**2)

    def Energy(self):

        return self.energy

    def GetCalcMass(self):

        if hasattr(self,'mass'):
            return self.mass
        else:
            mass = np.sqrt(np.inner(self.fourMom(),self.fourMom()))
            return mass

def longLivedProbabilityFor(particle,width,detectorLength=None):

    if detectorLength is None:
        #Compute using full detector geometry
        b_detector = 10.8
        h_detector = 7.4
        theta_max_len = math.atan(h_detector/b_detector)
        theta = 2.0*math.atan(math.exp(-abs(particle.Eta())))
        if theta < theta_max_len:
           detectorLength = b_detector/math.cos(theta)
        else:
           detectorLength = h_detector/math.sin(theta)

    gammabeta = particle.P()/particle.mass
    x = detectorLength*width/1.975e-16 #Effective length
    probLongLived = math.exp(-x/gammabeta)

    return probLongLived

def getEffForEvent(event,widths=[0.0],detectorLength=None):
    """
    Compute the efficiency for the event for a given
    list of x-values (xEffs), where x = L/ctau.
    Only uses the maximal signal region/mass reconstruction satisfying m_hscp < mrec/0.6.

    :param event: List with Particle objects containing efficiencies
    :param xEffs: list of float with the effective values for L/ctau to rescale the events for.
                  If None, will return the unrescaled efficiency (zero width).

    :return: numpy array with a
    """


    #Number of particles:
    npart = len(event)
    if npart < 1:
        logger.error("Can not handle events with no particles")
        raise ValueError("%s" %str(event))
    if (npart > 2):
        logger.error("Can not handle more than 2 particles per event")
        raise ValueError("%s" %str(event))

    #Signal region definitions and min reconstructed mass
    SRs = {'c000' : 0,'c100' : 100.0,'c200' : 200.0 ,'c300' :300.0}
    #Trigger probabilities for each signal region/particle:
    ProbTrigger = np.array([0.]*npart)
    #Online probabilities and error for each signal region/particle:
    ProbOnline = dict([[sr,np.array([0.]*npart)] for sr in SRs])
    #Compute zero-width efficiencies:
    for i,hscp in enumerate(event):
        ProbTrigger[i] = hscp.effs['trigger'] #Same trigger eff for all SRs
        for sr,mrec in SRs.items():
            if hscp.mass*0.6 < mrec:
                continue
            ProbOnline[sr][i] = hscp.effs[sr]

    #Create array to store efficiencies for each x (width) value
    effs = np.zeros(len(widths),dtype=[('width',float)]+[(sr,float) for sr in SRs])

    #Loop over x values and compute the probability of reconstructing at least one HSCP:
    for i,w in enumerate(widths):
        effs['width'][i] = w
        probLLP = np.array([longLivedProbabilityFor(hscp,w,detectorLength) for hscp in event])
        for sr in SRs:
            #Compute probability for triggering at least one HSCP  (1 - probability for missing all):
            probTriggerTotal = 1.0 - np.prod(1.0-ProbTrigger*probLLP)
            #Compute probabitlity for reconstructing at least one HSCP  (1 - probability for missing all):
            probTagTotal = 1.0 - np.prod(1.0-ProbOnline[sr])
            #Total probability for triggering and reconstructing at least one HSCP:
            probFinal = probTriggerTotal*probTagTotal
            #Store result:
            effs[sr][i] = probFinal

    return effs

def getEventsFrom(lheFile, effLabels = None):
    """
    Reads a simplified LHE file and returns a list of events.
    Each event is simply a list of TParticle objects.

    :param infile: Path to the input file

    :return: list of events (e.g. [ [ TParticle1, TParticle2,..], [ TParticle1,...]  ])
    """

    if not os.path.isfile(lheFile):
        logger.error("File %s not found" %lheFile)
        return []


    inputFile = lheFile
    if lheFile.endswith(".tar.gz"):
        with tarfile.open(lheFile, "r:gz") as tar:
            inputFile = lheFile.replace('.tar.gz','')
            tar.extract(os.path.basename(inputFile),
                            path=os.path.dirname(lheFile))

    #Define labels for efficiencies is the order appearing in the event file:
    if effLabels is None:
        effLabels = ['trigger','trigger_err','c000','c000_err','c100','c100_err',
                     'c200','c200_err','c300','c300_err']

    f = open(inputFile,'r')
    events = f.read()
    events = events[events.find('<event>'):events.rfind('<\event>')]
    events = events.split('<event>')[1:]
    eventList = []
    f.close()
    for i,event in enumerate(events[:]):
        evLines = [l for l in event.split('\n') if l]
        particles = []
        for l in evLines[2:-1]:
            l = l.replace('\n','').replace('+-','')
            l = l.split()
            l = [float(x) for x in l]
            pData = l[:6]
            triMomentum = [pData[1],pData[2],pData[3]]
            energy =  pData[4]
            pdg = int(pData[0])
            mass = pData[5]
            if pdg > 0:
                name = "hscp"
                charge = 1.
            else:
                name = "~hscp"
                charge = -1.
            particle = Particle(pdg=pdg,triMomentum=triMomentum,energy=energy,mass=mass,name=name,charge=charge)
            particle.effs = dict([[label,l[6+i]] for i,label in enumerate(effLabels)])

            particles.append(particle)

        eventList.append(particles)


    if inputFile != lheFile and os.path.isfile(inputFile):
        os.remove(inputFile)


    return eventList

def getEffsFor(lheFile,selectHSCPs,widths,detectorLength,outFolder):
    """
    Compute the efficiencies for a list of widths
    using the events and efficiencies stored in the lheFile (for zero width).

    :param lheFile: path to the LHE file with efficiencies for zero widths
    :param widths: list of widths (in GeV) to compute the efficiency for
    :param detectorLength: fixed detector length size (in meters)
    :param outFolder: output folder
    :param selectHSCPs: If None will use all HSCPs in the event, otherwise should contain a list with the PDG codes of the HSCPs to be considered.

    :return: True/False
    """

    logger.info("Computing efficiencies for %s" %lheFile)

    if isinstance(selectHSCPs,(int,float)):
        selectHSCPs = [int(selectHSCPs)]

    try:
        events = getEventsFrom(lheFile)
    except:
        logger.error("Error reading events from %s" %lheFile)
        return False

    columns = ['width','c000','c100','c200','c300','c000_err','c100_err','c200_err','c300_err']
    effs = np.zeros(len(widths),dtype=[(c,float) for c in columns])
    effs['width'] = widths
    try:
        for event in events:
            #Filter HSCPs in each event (if required):
            if selectHSCPs is not None:
                event = [hscp for hscp in event if hscp.pdg in selectHSCPs]

            if not event:
                continue  #Skip events without (selected) HSCPs

            #Get rescaled efficiency
            evEffs = getEffForEvent(event,widths,detectorLength)
            for sr in evEffs.dtype.names:
                if sr == 'width': continue
                effs[sr] += evEffs[sr] #Add up efficiencies
                effs[sr+'_err'] += evEffs[sr]**2 #Add up error squared
    except:
        logger.error("Error computing efficiencies for %s" %lheFile)
        return False

    #Compute average efficiency and error
    for label in effs.dtype.names:
        if label == 'width': continue
        if '_err' in label:
            effs[label] = np.sqrt(effs[label])/len(events)
        else:
            effs[label] = effs[label]/len(events)

    res = np.sort(effs,order='width')

    inputFile = lheFile
    if lheFile.endswith(".tar.gz"):
        inputFile = lheFile.replace('.tar.gz','')


    outFile = os.path.join(outFolder,os.path.basename(inputFile).replace('.lhe','')+'.eff')
    if not os.path.isdir(os.path.dirname(outFile)):
        os.makedirs(os.path.dirname(outFile))
    #Save results to file:
    header = '%19s'*len(res.dtype.names) %res.dtype.names
    header = header[3:]
    np.savetxt(outFile,res,header=header,fmt = ['     %1.7e']*len(res.dtype.names))

    return True



if __name__ == "__main__":

    import argparse
    ap = argparse.ArgumentParser( description=
            "Compute efficencies for multiple widths" )
    ap.add_argument('-p', '--parfile', default='eff_parameters.ini',
            help='path to the parameters file.')
    ap.add_argument('-v', '--verbose', default='info',
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

    lheFiles = eval(parser.get("options","lheFiles"))
    effFolder = parser.get("options","effFolder")
    widths = np.array(parser.get("options","widths"))
    detectorLength = parser.get("options","detectorLength")
    ncpus = parser.getint("options","ncpu")
    if parser.has_option("options","selectHSCPs"):
        selectHSCPs = parser.get("options","selectHSCPs")
    else:
        selectHSCPs = None
    if ncpus  < 0:
        ncpus =  multiprocessing.cpu_count()

    ncpus = min(ncpus,len(lheFiles))
    logger.info("Running over %i files with %i cpus" %(len(lheFiles),ncpus))
    pool = multiprocessing.Pool(processes=ncpus)
    children = []
    #Loop over model parameters and submit jobs
    for lheFile in lheFiles:
        p = pool.apply_async(getEffsFor, args=(lheFile,selectHSCPs,widths,detectorLength,effFolder,))
        children.append(p)


    output = [p.get() for p in children]

    print("\n\nDone in %3.2f min" %((time.time()-t0)/60.))
