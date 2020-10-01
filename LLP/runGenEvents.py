#!/usr/bin/env python

#Uses an input file to compute the corresponding efficiencies.
#The calculation goes through the following steps
# 1) Run MadGraph using the options set in the input file
# (the proc_card.dat, parameter_card.dat and run_card.dat...).
# Madgraph is used to compute the widths, cross-sections and generate a parton level LHE file.
# 2) Run main_hscp.exe in the input parton level LHE file to generate a simplified hadron-level LHE file
# containing only the HSCPs

#First tell the system where to find the modules:
import sys,os,glob
from configParserWrapper import ConfigParserExt
import logging,shutil
import subprocess
import time,datetime,tempfile,tarfile
import multiprocessing
import numpy as np

FORMAT = '%(levelname)s in %(module)s.%(funcName)s() in %(lineno)s: %(message)s'
logging.basicConfig(format=FORMAT,datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)


def generateProcesses(parser):
    """
    Runs the madgraph process generation.
    This step just need to be performed once for a given
    model and set of processes, since it is independent of the
    numerical values of the model parameters.

    :param parser: ConfigParser object with all the parameters needed

    :return: True if successful. Otherwise False.
    """


    #Get process card:
    pars = parser.toDict(raw=False)["MadGraphPars"]
    processCard = os.path.abspath(pars['proccard'])
    if not os.path.isfile(processCard):
        logger.error("Process card %s not found" %processCard)
        sys.exit()
    with open(processCard,'r') as f:
        lines = f.readlines()
        lines = [l for l in lines[:] if not ('output' in l and 'output' == l.strip()[:6])]
    lines.append('output %s' %pars['processFolder'])

    processCard = tempfile.mkstemp(suffix='.dat', prefix='processCard_',
                               dir=pars['MG5path'])
    os.close(processCard[0])
    processCard = processCard[1]
    with open(processCard,'w') as f:
        for l in lines:
            f.write(l)

    #Generate process
    logger.info('Generating process using %s' %processCard)
    run = subprocess.Popen('./bin/mg5_aMC -f %s' %processCard,shell=True,
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                cwd=pars['MG5path'])

    output,errorMsg = run.communicate()
    logger.debug('MG5 process error:\n %s \n' %errorMsg)
    logger.debug('MG5 process output:\n %s \n' %output)
    logger.info("Finished process generation")

    return True

def generateEvents(parser):

    """
    Runs the madgraph process generation.
    This step just need to be performed once for a given
    model and set of processes, since it is independent of the
    numerical values of the model parameters.

    :param parser: ConfigParser object with all the parameters needed

    :return: True if successful. Otherwise False.
    """

    pars = parser.toDict(raw=False)["MadGraphPars"]
    ncpu = max(1,parser.get("MadGraphPars","ncores"))

    if not 'mg5out' in pars:
        logger.error('MG5 output folder not defined.')
        return False
    else:
        outputFolder = pars['mg5out']
    if not 'processFolder' in pars:
        logger.error('MG5 process folder not defined.')
        return False
    else:
        processFolder = pars['processFolder']


    if not os.path.isdir(processFolder):
        logger.error('Process folder %s not found. Maybe something went wrong with the process generation?' %processFolder)
        return False
    else:
        if os.path.isdir(outputFolder):
            logger.info('outputFolder %s found. It will be replaced' %outputFolder)
            shutil.rmtree(outputFolder)

        shutil.copytree(processFolder,outputFolder)
        if 'runcard' in pars and os.path.isfile(pars['runcard']):
            shutil.copyfile(pars['runcard'],os.path.join(outputFolder,'Cards/run_card.dat'))
        if 'paramcard' in pars and os.path.isfile(pars['paramcard']):
            shutil.copyfile(pars['paramcard'],os.path.join(outputFolder,'Cards/param_card.dat'))

    #Generate commands file:
    commandsFile = tempfile.mkstemp(suffix='.txt', prefix='MG5_commands_', dir=outputFolder)
    os.close(commandsFile[0])
    commandsFileF = open(commandsFile[1],'w')
    commandsFileF.write('done\n')
    comms = parser.toDict(raw=False)["MadGraphSet"]
    #Set a low number of events, since it does not affect the total cross-section value
    #(can be overridden by the user, if the user defines a different number in the input card)
    commandsFileF.write('set nevents 10 \n')
    for key,val in comms.items():
        commandsFileF.write('set %s %s\n' %(key,val))


    if parser.has_option('options','computeWidths'):
        computeWidths = parser.get('options','computeWidths')
        if computeWidths:
            if isinstance(computeWidths,str) or isinstance(computeWidths,unicode):
                commandsFileF.write('compute_widths %s\n' %str(computeWidths))
            else:
                commandsFileF.write('compute_widths all \n')

    #Done setting up options
    commandsFileF.write('done\n')

    commandsFileF.close()
    commandsFile = commandsFile[1]

    logger.info("Generating MG5 events with command file %s" %commandsFile)
    run = subprocess.Popen('./bin/generate_events --multicore --nb_core=%s < %s' %(ncpu,commandsFile),
                           shell=True,stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,cwd=outputFolder)

    output,errorMsg= run.communicate()
    logger.debug('MG5 event error:\n %s \n' %errorMsg)
    logger.debug('MG5 event output:\n %s \n' %output)

    logger.info("Finished event generation")

    return True

def Run_MG5(parser):
    """
    Runs MadGraph5 using the parameters given in parser

    :param parser: ConfigParser object with all the parameters needed
    """

    pars = parser.toDict(raw=False)["MadGraphPars"]

    #Get MG5 output folder
    if not 'mg5out' in pars or not pars['mg5out']:
        mg5out = tempfile.mkdtemp(dir='./',prefix='MG5out_')
        logger.debug('Output MadGraph folder not defined. Results will be saved to %s' %mg5out)
        shutil.rmtree(mg5out)
    else:
        mg5out = pars['mg5out']
    #Expand relative paths:
    parser.set("MadGraphPars",'mg5out',os.path.abspath(os.path.expanduser(mg5out)))
    parser.set("MadGraphPars",'mg5path',os.path.abspath(os.path.expanduser(pars['MG5path'])))
    parser.set("MadGraphPars",'processFolder',os.path.abspath(os.path.expanduser(pars['processFolder'])))

    #Checks
    if not os.path.isdir(pars['MG5path']):
        logger.error("MadGraph folder %s not found" %pars['MG5path'])
        return False
    elif not os.path.isfile(os.path.join(pars['MG5path'],'bin/mg5_aMC')):
        logger.error("MadGraph binary not found in %s/bin" %pars['mg5path'])
        return False

    #Run process generation (if required)
    if os.path.isdir(pars['processFolder']):
        logger.info('Process folder found. Will skip the process generation')
    else:
        generateProcesses(parser)

    #Finally generate events and compute widths:
    generateEvents(parser)
    mg5out = parser.get("MadGraphPars",'mg5out')

    #Save param_card file
    if parser.has_option("MadGraphPars",'slhaout'):
        slhaOut = parser.get("MadGraphPars",'slhaout')
        if slhaOut:
            slhaOut = os.path.abspath(slhaOut)
            if not os.path.isdir(os.path.dirname(slhaOut)):
                os.makedirs(os.path.dirname(slhaOut))
            paramFile = os.path.join(mg5out,'Cards/param_card.dat')
            paramFile = os.path.abspath(paramFile)
            if not os.path.isfile(paramFile):
                logger.warning("Could not find param card %s" %paramFile)
            else:
                shutil.copyfile(paramFile,os.path.abspath(slhaOut))

    #Save banner file
    if parser.has_option("MadGraphPars",'bannerout'):
        bannerOut = parser.get("MadGraphPars",'bannerout')
        if bannerOut:
            bannerOut = os.path.abspath(bannerOut)
            if not os.path.isdir(os.path.dirname(bannerOut)):
                os.makedirs(os.path.dirname(bannerOut))
            bannerDir = os.path.join(mg5out,'Events/run_01/*.txt')
            for f in glob.glob(bannerDir):
                bannerFile = os.path.abspath(f)
                shutil.copyfile(bannerFile,os.path.abspath(bannerOut))

    #Get output file:
    eventFile  = os.path.join(mg5out,'Events/run_01/unweighted_events.lhe.gz')
    eventFile = os.path.abspath(eventFile)
    if not os.path.isfile(eventFile):
        logger.error("Error generating events. Event file not found")
        sys.exit()

    return eventFile

def Run_pythia(parser,inputFile):
    """
    Runs Pythia8 using the parameters given in parser
    and the input LHE or SLHA file generated by MG5

    :param parser: ConfigParser object with all the parameters needed
    :param inputFile: path to the SLHA or LHE parton level file (it can be gzipped)
    """

    pars = parser.toDict(raw=False)["PythiaOptions"]
    if not os.path.isfile(pars['execfile']):
        logger.error('Pythia executable %s not found' %pars['execfile'])
        return False

    if not os.path.isfile(pars['pythiacfg']):
        logger.error('Pythia config file %s not found' %pars['pythiacfg'])
        return False

    #Create output dirs, if do not exist:
    try:
        os.makedirs(os.path.dirname(pars['pythiaout']))
    except:
        pass

    #Run Pythia
    logger.info('Running pythia for %s' %inputFile)
    execFolder = os.path.dirname(pars['execfile'])
    execFile = os.path.basename(pars['execfile'])
    pythiacfg = os.path.abspath(pars['pythiacfg'])
    inputFile = os.path.abspath(inputFile)
    outFile = os.path.abspath(pars['pythiaout'])
    if os.path.splitext(outFile)[1] == '.gz':
        outFile = os.path.splitext(outFile)[0]
    if os.path.splitext(outFile)[1] == '.tar':
        outFile = os.path.splitext(outFile)[0]
    if not os.path.isdir(os.path.dirname(outFile)):
        os.makedirs(os.path.dirname(outFile))

    logger.debug('Excuting: \n./%s -f %s -c %s -o %s -n -1' %(execFile,
                                                          inputFile,pythiacfg,outFile))
    run = subprocess.Popen('./%s -f %s -c %s -o %s -n -1' %(execFile,
                                                          inputFile,pythiacfg,outFile)
                           ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=execFolder)

    output,errorMsg= run.communicate()
    logger.debug('Pythia error:\n %s \n' %errorMsg)
    logger.debug('Pythia output:\n %s \n' %output)

    logger.info("Finished pythia event generation")

    if os.path.isfile(outFile) and ('.gz' in pars['pythiaout']):
        with tarfile.open(outFile+'.tar.gz', "w:gz") as tar:
            tar.add(outFile, arcname=os.path.basename(outFile))
        os.remove(outFile)

    return True

def runAll(parserDict):
    """
    Runs Madgraph, Pythia and the SLHA creator for a given set of options.
    :param parserDict: a dictionary with the parser options.
    """

    t0 = time.time()

    parser = ConfigParserExt()
    parser.read_dict(parserDict)

    #Check if run should be skipped
    skip = False
    if parser.has_option("options","skipDone"):
        skip = parser.get("options","skipDone")
    if skip:
        if parser.get("options","runPythia"):
            pythiaOut = parser.get("PythiaOptions","pythiaout")
            if os.path.isfile(pythiaOut):
                logger.info("File %s found. Skipping run." %pythiaOut)
                now = datetime.datetime.now()
                return "Run skipped at %s" %(now.strftime("%Y-%m-%d %H:%M"))


    #Run MadGraph and create SLHA file (keep MG5 events):
    parserDict["options"]["cleanOutFolders"] = False
    if parser.get("options","runMG"):
        inputFile = Run_MG5(parser)

    #Run Pythia
    if parser.get("options","runPythia"):
        inputFile  = os.path.abspath(parser.get("PythiaOptions","inputFile"))
        if not os.path.isfile(inputFile):
            logger.error("Input file %s for Pythia not found" %inputFile)
        else:
            pFile = Run_pythia(parser, inputFile)
            logger.debug("File %s created" %pFile)

    #Clean output:
    if parser.get("options","cleanOutFolders"):
        if parser.get("options","runMG"):
            logger.info("Cleaning output")
            try:
                shutil.rmtree(parser.getstr("MadGraphPars","mg5out"))
            except:
                pass

    logger.info("Done in %3.2f min" %((time.time()-t0)/60.))
    now = datetime.datetime.now()

    return "Finished run at %s" %(now.strftime("%Y-%m-%d %H:%M"))



if __name__ == "__main__":

    import argparse
    ap = argparse.ArgumentParser( description=
            "Run MadGraph and Pythia in order to compute efficiencies for a given model." )
    ap.add_argument('-p', '--parfile', default='parameters_THSCPM1b.ini',
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

    #Check if a parameter file has been defined:
    parserList = []
    if parser.has_option('MadGraphSet','parametersFile') and parser.get('MadGraphSet','parametersFile'):
        pFile = parser.get('MadGraphSet','parametersFile')
        parser.remove_option('MadGraphSet','parametersFile')
        if not os.path.isfile(pFile):
            logger.error('Parameters file %s not found' %pFile)
            sys.exit()

        values = np.genfromtxt(pFile,names=True)
        xlabels = values.dtype.names
        logger.info('Using values for the parameters: %s from file %s' %(xlabels,pFile))
        for name in xlabels:
            parser.remove_option('MadGraphSet',name)
        for pt in values:
            newParser = ConfigParserExt()
            newParser.read_dict(parser.toDict(raw=True))
            for name in xlabels:
                newParser.set('MadGraphSet',name,str(pt[name]))
            parserList += newParser.expandLoops()
    else:
        #Get a list of parsers (in case loops have been defined)
        parserList = parser.expandLoops()


    ncpus = parser.getint("options","ncpu")
    if ncpus  < 0:
        ncpus =  multiprocessing.cpu_count()
    ncpus = min(ncpus,len(parserList))
    logger.info("Running %i jobs in %i cpus" %(len(parserList),ncpus))
    pool = multiprocessing.Pool(processes=ncpus)
    children = []
    #Loop over model parameters and submit jobs
    firstRun = True
    for newParser in parserList:
        if newParser.get("options","runMG"):
            #Run process generation (if required)
            if not os.path.isdir(newParser.get('MadGraphPars','processFolder')):
                generateProcesses(newParser)

        if firstRun:
            if parser.get("PythiaOptions",'execfile') != 'None':
                os.system("make %s" %parser.get("PythiaOptions",'execfile'))
                time.sleep(5)  #Let first job run for 5s in case it needs to create shared folders
            firstRun = False

        parserDict = newParser.toDict(raw=False) #Must convert to dictionary for pickling
        p = pool.apply_async(runAll, args=(parserDict,))
        children.append(p)


    #Wait for jobs to finish:
    output = [p.get() for p in children]
    for out in output:
        print(out)

    print("\n\nDone in %3.2f min" %((time.time()-t0)/60.))
