#!/usr/bin/env python3

"""
.. module:: cm2Wrapper
        :synopsis: code that wraps around checkmate2. 

.. moduleauthor:: Wolfgang Waltenberger <wolfgang.waltenberger@gmail.com>
"""

import os, sys, colorama, subprocess, shutil, tempfile, time, io, glob
import multiprocessing
import bakeryHelpers
import locker
from os import PathLike

class CM2Wrapper:
    def __init__ ( self, topo, njets, rerun, analyses, keep=False,
                   sqrts = 13, ver="2.0.37", keephepmc=True ):
        """
        :param topo: e.g. T1
        :param keep: keep cruft files, for debugging
        :param sqrts: sqrts, in TeV
        :param ver: version of cm2
        :param keephepmc: keep mg5 hepmc file (typically in mg5results/)
        """
        self.autocompile = False
        self.instanceName = f"{analyses}_{topo}"
        self.topo = topo
        self.sqrts = sqrts
        self.configfile = None
        self.njets = njets
        self.analyses = bakeryHelpers.sModelsName2cm2AnaName ( analyses )
        self.rerun = rerun
        self.keep = keep
        self.keephepmc = keephepmc
        self.basedir = bakeryHelpers.baseDir()
        os.chdir ( self.basedir )
        self.locker = locker.Locker ( sqrts, topo, False )
        self.cm2tempdir = f"{self.basedir}/cm2tempdir/"
        self.cm2results = f"{self.basedir}/cm2results/"
        bakeryHelpers.mkdir ( self.cm2tempdir )
        self.cm2install = f"{self.basedir}/cm2/" 
        self.executable = f"{self.cm2install}/checkmate2/bin/CheckMATE"
        self.tempFiles = []
        if abs ( sqrts - 8 ) < .1:
            self.cm2install = "%s/cm2.8tev/" % self.basedir
        self.ver = ver
        if os.path.isdir ( self.cm2install ) and not os.path.exists ( self.executable ):
            ## some crooked cm2 install, remove it all
            subprocess.getoutput ( f"rm -rf {self.cm2install}" )
            # print ( f"rm -rf {self.cm2install}" )
            # sys.exit()
        if os.path.isdir ( f"{self.basedir}/hepmc2" ) and len ( glob.glob ( f"{self.basedir}/hepmc2/HepMC-*/fio/libHepMCfio.la" ) ) == 0:
            self.exe ( f"rm -r {self.basedir}/hepmc2" )
            
        if not os.path.isdir ( f"{self.basedir}/hepmc2" ):
            self.error ( "hepmc2 install is missing??" )
            if os.path.isdir ( f"{self.basedir}/hepmc2.backup" ):
                self.exe ( f"cp -r {self.basedir}/hepmc2.backup {self.basedir}/hepmc2" )
            else:
                if os.path.isdir ( f"{self.basedir}/hepmc2.template" ):
                    self.exe ( f"cp -r {self.basedir}/hepmc2.template {self.basedir}/hepmc2" )
                    if self.autocompile:
                        self.exe ( "cd hepmc2; ./make.py" )

        bakeryHelpers.checkDelphesInstall( autocompile = self.autocompile )
        if os.path.isdir ( self.cm2install ) and not os.path.exists ( f"{self.executable}" ):
            self.exe ( f"rm -rf {self.cm2install}" )

        if not os.path.isdir ( self.cm2install ):
            self.error ( "cm2 install is missing??" )
            backupdir = "/groups/hephy/pheno/ww/cm2"
            localbackup = f"{self.basedir}/cm2.backup/"
            templatedir = f"{self.basedir}/cm2.template"
            # print ( "localbackup?", os.path.exists ( localbackup ) )
            if os.path.exists ( localbackup ):
                self.exe ( f"cp -r {localbackup} {self.cm2install}" )
            elif os.path.exists ( backupdir ):
                self.exe ( f"cp -r {backupdir} {self.cm2install}" )
            elif os.path.exists ( templatedir ):
                self.exe ( f"cp -r {templatedir} {self.cm2install}" )
        if not os.path.exists ( self.executable ):
            self.info ( f"cannot find cm2 installation at {self.cm2install}" )
            if self.autocompile:
                self.exe ( f"{self.cm2install}/make.py"  )
        self.templateDir = "%s/templates/" % self.basedir
        # self.info ( "initialised" )

    def info ( self, *msg ):
        print ( "%s[cm2Wrapper] %s%s" % ( colorama.Fore.YELLOW, " ".join ( msg ), \
                   colorama.Fore.RESET ) )

    def debug( self, *msg ):
        pass

    def checkInstallation ( self ):
        """ check if installation looks reasonable and complete 
        :raises: Exception, if sth seems missing
        :returns: True, if all good
        """
        exefile = os.path.join ( self.cm2install, self.executable )
        hasExe = os.path.exists ( exefile )
        if not hasExe:
            raise Exception ( f"{exefile} not found" )
        versionFile = os.path.join ( self.cm2install, "checkmate2", "VERSION" )
        if not os.path.exists ( versionFile ):
            raise Exception ( f"version file {versionFile} not found" )
        with open ( versionFile, "rt" ) as f:
            self.ver = f.read().strip()
            f.close()
        return True

    def msg ( self, *msg):
        print ( "[cm2Wrapper] %s" % " ".join ( msg ) )

    def error ( self, *msg ):
        print ( "%s[cm2Wrapper] Error: %s%s" % ( colorama.Fore.RED, " ".join ( msg ), \
                   colorama.Fore.RESET ) )

    def writeRecastingCard ( self ):
        """ this method writes the recasting card, which defines which analyses
        are being recast. """
        return

    def unlink ( self, f ):
        if os.path.exists ( f ) and not self.keep:
            subprocess.getoutput ( "rm -rf %s" % f )

    def writeCommandFile ( self, hepmcfile, process, masses ):
        """ this method writes the commands file for cm2.
        :param hepmcfile: I think thats the input events
        """
        return

    def checkForSummaryFile ( self, masses ):
        """ given the process, and the masses, check summary file
        :returns: True, if there is a usable summary file, with all needed analyses
        """
        return

    def list_analyses ( self ):
        """ list all analyses that are to be found in cm2/ """
        import bakeryHelpers
        bakeryHelpers.listAnalysesCheckMATE()

    def gunzipHepmcFile ( self, hepmcfile : PathLike ) -> PathLike:
        """ given a zipped hepmc file, gunzip it, return path
        to gunzipped file """
        import gzip
        import shutil
        outfile = hepmcfile.replace(".gz","").replace("mg5results","temp")
        if not self.keephepmc:
            self.tempFiles.append ( hepmcfile )
        self.tempFiles.append ( outfile )
        if os.path.exists ( outfile ):
            self.info ( f"skipping gunzip: {outfile} exists" )
            return outfile
        with gzip.open( hepmcfile, 'rb') as f_in:
            with open( outfile, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        self.info ( f"gunzip tarred hepmc file to {outfile}" )
        return outfile
        
    def createConfigFile ( self, masses, hepmcfile ):
        """ create the checkmate.ini configuration file """
        templatefile = os.path.join ( self.basedir, "templates", "checkmate_template.ini" )
        f = open ( templatefile, "rt" )
        lines = f.readlines()
        f.close()
        mass_stripped = str(masses).replace("(", "").replace(")", "")
        mass_stripped = mass_stripped.replace(",", "_").replace(" ", "")

        self.configfile = os.path.join ( self.basedir, "temp", "cm2_" + self.instanceName + "_" + mass_stripped+".ini" )
        f = open ( self.configfile, "wt" )
        outfile = self.gunzipHepmcFile ( hepmcfile )

        for line in lines:
            line = line.replace("@@NAME@@", self.instanceName )
            line = line.replace("@@ANALYSES@@", self.analyses )
            line = line.replace("@@HEPMCFILE@@", outfile )
            line = line.replace("@@OUTPUTDIR@@", self.cm2tempdir )
            f.write ( line )
        f.close()

    def run( self, masses, hepmcfile, pid=None ):
        """ Run cm2 over an hepmcfile, specifying the process
        :param pid: unix process id, for debugging
        :param hepmcfile: the hepcmfile name
        :returns: -1 if problem occured, 0 if all went smoothly,
                   1 if nothing needed to be done.
        """
        mass_stripped = str(masses).replace("(", "").replace(")", "")
        mass_stripped = mass_stripped.replace(",", "_").replace(" ", "")
        self.instanceName = f"{self.analyses}_{self.topo}_{mass_stripped}"
        print ( f"[cm2Wrapper] initialse checkmate {self.ver} for {self.analyses}" )
        self.checkInstallation()
        if not os.path.exists ( self.outputfile() ):
            self.createConfigFile ( masses, hepmcfile )
            self.executeCheckMate()
        effs = self.extractEfficiencies()
        if len(effs)>0:
            ananame = bakeryHelpers.cm2AnaNameToSModelSName ( self.analyses )
            effi_file = bakeryHelpers.getEmbakedName ( ananame, self.topo, "cm2" )
            bakeryHelpers.writeEmbaked ( effs, effi_file, masses, "cm2" )
            self.tempFiles.append ( self.outputfile( final=True ) )
            self.tempFiles.append ( self.cm2tempdir )
            self.tempFiles.append ( self.cm2results )
            self.tempFiles.append ( f"{self.cm2tempdir}/{self.instanceName}" )
        self.clean()
        # self.unlock()
        return 0

    def extractEfficiencies ( self ):
        """ extract the efficiencies from outputfile """
        if not os.path.exists ( self.outputfile( final=True ) ):
            if os.path.exists ( self.outputfile() ): ## need to move
                shutil.copyfile ( self.outputfile(), self.outputfile ( final=True ) )
            else:
                self.error ( f"{self.outputfile( final=True )} not found, cannot extract any efficiencies" )
            return {}
        inSignalRegions = False
        effs = {}
        nevents = -1
        with open ( self.outputfile() ) as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("MCEvents:"):
                    line = line.replace("MCEvents:","").strip()
                    nevents = int ( line )
                if inSignalRegions:
                    tokens = line.split()
                    effs[tokens[0]] = float(tokens[3])
                if inSignalRegions == False and not line.startswith("SR"):
                    continue
                inSignalRegions = True

            f.close()
        effs["__nevents__"]= nevents
        return effs

    def outputfile ( self, final : bool = False ):
        if final:
            ret = f"{self.cm2results}/{self.instanceName}/{self.analyses}.dat"
            bakeryHelpers.mkdir ( f"{self.cm2results}" )
            bakeryHelpers.mkdir ( f"{self.cm2results}/{self.instanceName}" )
        else:
            ret = f"{self.cm2tempdir}/{self.instanceName}/analysis/myprocess_{self.analyses}_signal.dat"
        return ret

    def executeCheckMate ( self ):
        """ run checkmate! """
        run = subprocess.Popen( f'{self.executable} {self.configfile}',
                shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)# ,cwd=checkmateBin)
        output,errorMsg= run.communicate()
        errorMsg = errorMsg.decode("UTF-8")
        if len(errorMsg)>0:
            self.info( f'CheckMATE error: {errorMsg}' )
            output = output.decode("UTF-8")
            self.info( f'CheckMATE output:\n {output}\n' )
        # at this point we move the result from cm2tempdir to cm2results 
        bakeryHelpers.mkdir ( self.cm2results )
        if os.path.exists ( self.outputfile() ):
            # print ( f"@@@ copy {self.outputfile()}, {self.outputfile ( final=True )}" )
            shutil.copyfile ( self.outputfile(), self.outputfile ( final=True ) )
        self.tempFiles.append ( self.outputfile() )


    def exe ( self, cmd, maxLength=100 ):
        """ execute cmd in shell
        :param maxLength: maximum length of output to be printed
        """
        self.msg ( f"exec: [{os.getcwd()}] {cmd}" )
        pipe = subprocess.Popen ( cmd, shell=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE )
        ret=""
        for line in io.TextIOWrapper(pipe.stdout, encoding="latin1"):
            ret+=line
        for line in io.TextIOWrapper(pipe.stderr, encoding="latin1"):
            ret+=line
        ret = ret.strip()
        if len(ret)==0:
            return
        if maxLength == None:
            maxLength = len(ret)+1
        if len(ret)<maxLength:
            self.msg ( " `- %s" % ret )
            return
        self.msg ( " `- %s" % ( ret[-maxLength:] ) )

    def clean ( self ):
        if self.keep:
            return
        if self.configfile != None and os.path.exists ( self.configfile ):
            os.unlink ( self.configfile )
        for t in self.tempFiles:
            self.debug ( f"unlinking {t}" )
            if os.path.exists( t ):
                if os.path.isdir ( t ):
                    shutil.rmtree ( t )
                else:
                    os.unlink ( t )
        return

    def _delete_dir(self, f):
        if os.path.exists(f):
            subprocess.getoutput("rm -rf %s" % f)

    def clean_all ( self ):
        """ clean everything related to checkmate2 """
        self._delete_dir ( "cm2" )
        self._delete_dir ( "hepmc2" )
        return

if __name__ == "__main__":
    import argparse
    argparser = argparse.ArgumentParser(description='checkmate2 runner.')
    argparser.add_argument ( '-a', '--analyses', help='analyses, comma separated [atlas_sus_2016_07]',
                             type=str, default="atlas_susy_2016_07" )
    argparser.add_argument ( '-j', '--njets', help='number of ISR jets [1]',
                             type=int, default=1 )
    argparser.add_argument ( '-s', '--sqrts', help='sqrts [13]',
                             type=int, default=13 )
    argparser.add_argument ( '-t', '--topo', help='topology [T2]',
                             type=str, default="T2" )
    argparser.add_argument ( '-k', '--keep', help='keep temporary files',
                             action="store_true" )
    argparser.add_argument ( '-c', '--clean', help='clean all temporary files, then quit',
                             action="store_true" )
    argparser.add_argument ( '-l', '--list_analyses', help='list all analyses that are found in this cm2 installation',
                             action="store_true" )
    argparser.add_argument ( '-C', '--clean_all', help='clean all temporary files, even results directories, then quit',
                             action="store_true" )
    mdefault = "all"
    argparser.add_argument ( '-m', '--masses', help='mass ranges, comma separated list of tuples. One tuple gives the range for one mass parameter, as (m_first,m_last,delta_m). m_last and delta_m may be ommitted. "all" means: search for mg5 directories, and consider all. [%s]' % mdefault,
                             type=str, default=mdefault )
    argparser.add_argument ( '-p', '--nprocesses', help='number of process to run in parallel. 0 means 1 per CPU [1]',
                             type=int, default=1 )
    argparser.add_argument ( '-r', '--rerun', help='force rerun, even if there is a summary file already',
                             action="store_true" )
    args = argparser.parse_args()
    if args.list_analyses:
        cm2 = CM2Wrapper( args.topo, args.njets, args.rerun, args.analyses )
        cm2.list_analyses()
        sys.exit()
    if args.clean:
        cm2 = cm2Wrapper( args.topo, args.njets, args.rerun, args.analyses )
        cm2.clean()
        sys.exit()
    if args.clean_all:
        cm2 = cm2Wrapper( args.topo, args.njets, args.rerun, args.analyses )
        cm2.clean_all()
        sys.exit()
    if args.masses == "all":
        masses = bakeryHelpers.getListOfMasses ( args.topo )
    else:
        masses = bakeryHelpers.parseMasses ( args.masses )
    nm = len(masses)
    nprocesses = bakeryHelpers.nJobs ( args.nprocesses, nm )
    if nprocesses == 0:
        sys.exit()
    cm2 = CM2Wrapper( args.topo, args.njets, args.rerun, args.analyses, args.keep,
                      args.sqrts )
    # cm2.info( "%d points to produce, in %d processes" % (nm,nprocesses) )
    djobs = int(len(masses)/nprocesses)

    def runChunk ( chunk, pid ):
        for c in chunk:
            hashepmc = cm2.locker.hasHEPMC ( c )
            hepmcfile = cm2.locker.hepmcFileName ( c )
            if hashepmc and not cm2.locker.isLocked ( c ):
                cm2.run ( c, hepmcfile, pid )
            else:
                if not hashepmc:
                    cm2.info ( f"skipping {hepmcfile}: does not exist." )
                else:
                    cm2.info ( f"skipping {hepmcfile}: is locked." )
                    

    jobs=[]
    for i in range(nprocesses):
        chunk = masses[djobs*i:djobs*(i+1)]
        if i == nprocesses-1:
            chunk = masses[djobs*i:]
        p = multiprocessing.Process(target=runChunk, args=(chunk,i))
        jobs.append ( p )
        p.start()
