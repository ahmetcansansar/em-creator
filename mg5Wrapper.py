#!/usr/bin/env python3

"""
.. module:: mg5Wrapper
        :synopsis: code that wraps around MadGraph5. Produces the data cards,
                   and runs the mg5 executable.

.. moduleauthor:: Wolfgang Waltenberger <wolfgang.waltenberger@gmail.com>
"""

import os, sys, colorama, subprocess, shutil, tempfile, time, socket, random, ast
import multiprocessing, glob, io
import bakeryHelpers
from bakeryHelpers import rmLocksOlderThan
import locker
from typing import Dict, List

class MG5Wrapper:
    def __init__ ( self, args : Dict, recaster : List ):
        """
        :param args: the command line args, as a dictionary
        :param recaster: perform recasting (ma5 or cutlang)
        """
        self.args = args
        self.nevents = args["nevents"]
        self.checkHost()
        self.basedir = bakeryHelpers.baseDir()
        os.chdir ( self.basedir )
        self.tempdir = bakeryHelpers.tempDir()
        self.resultsdir = os.path.join(self.basedir, "mg5results")
        self.recast = args["recast"]
        self.adl_file = args["adl_file"]
        self.event_condition = args["event_condition"]
        self.mkdir ( self.resultsdir )
        self.locker = locker.Locker ( args["sqrts"], args["topo"],
                                      args["ignore_locks"] )
        self.topo = args["topo"]
        self.keep = args["keep"]
        self.keephepmc = args["keephepmc"]
        self.rerun = args["rerun"]
        self.njets = args["njets"]
        self.mg5install = os.path.join(self.basedir, "mg5")
        self.logfile = None
        self.logfile2 = None
        self.tempf = None
        self.sqrts = args["sqrts"]
        self.recaster = recaster
        self.pyver = 3 ## python version
        self.setMG5Version()
        if "py3" in self.ver:
            self.pyver = 3
        if not os.path.isdir ( self.mg5install ):
            self.error ( "mg5 install is missing??" )
        self.executable = os.path.join(self.mg5install, "bin/mg5_aMC")
        if not os.path.exists ( self.executable ):
            self.info ( "cannot find mg5 installation at %s" % self.mg5install )
            if os.path.exists ( self.mg5install ):
                subprocess.getoutput ( f"rm -rf {self.mg5install}" )
            self.info ( "cannot even find mg5/ directory." )
            localbackup = f"{self.basedir}/mg5.backup/"
            backupdir = "/groups/hephy/pheno/ww/mg5"
            templatedir = f"{self.basedir}/mg5.template"
            destdir = f"{self.basedir}/mg5"
            if os.path.exists ( localbackup ):
                self.info ( f"local backup found at {localbackup}" )
                self.exe ( f"cp -r {localbackup} {destdir}" )
            elif os.path.exists ( backupdir ):
                self.info ( f"NO local backup found at {localbackup}" )
                self.exe ( f"cp -r {backupdir} {destdir}" )
                self.info ( f"clip backup found at {backupdir}" )
            elif os.path.exists ( templatedir ):
                self.info ( f"NO clip backup found at {backupdir}" )
                self.exe ( f"cp -r {templatedir} {destdir}" )
                self.info ( f"template backup found at {templatedir}" )
                self.exe ( "mg5/make.py" )
        if not os.path.exists ( f"{self.mg5install}/idm" ):
            subprocess.getoutput ( f"cp -r idm {self.mg5install}" )
        self.determineMG5Version()
        self.templateDir = os.path.join(self.basedir, "templates/")
        ebeam = str(int(self.sqrts*1000/2))
        ptlund = "-1"
        ptlund = "2."
        ktdurham = "-1."
        self.mgParams = { 'EBEAM': ebeam, # Single Beam Energy expressed in GeV
                          'NEVENTS': str(self.nevents), 'MAXJETFLAVOR': '5',
            #              'PDFLABEL': "'lhapdf'", 'XQCUT': '20', 'QCUT': '10',
                          'PDFLABEL': "'nn23lo1'", 'XQCUT': 'M[0]/4',
                          'PTLUND': ptlund, 'KTDURHAM': ktdurham,
                          ## xqcut for gluino-gluino production: mgluino/4
        }#,'qcut': '90'}
        if "TChi" in self.topo or "THig" in self.topo:
            # for electroweakinos go lower in xqcut
            self.mgParams["XQCUT"]="M[0]/6"
       
        self.correctPythia8CfgFile()
        self.msg ( "remove potential old cruft" )
        rmLocksOlderThan ( 3 ) ## remove locks older than 3 hours
        from utils import rmOld
        stats = rmOld.createStats()
        # rmOld.rmOlderThan ( stats, 8, False )
        self.info ( f"initialised MG5 {self.ver}" )

    def setMG5Version ( self ):
        self.ver = "???"
        versionfile = f"{self.mg5install}/VERSION"
        if os.path.exists ( versionfile ):
            with open ( versionfile, "rt" ) as f:
                lines = f.readlines()
                f.close()
                for line in lines:
                    if "version =" in line:
                        self.ver = line.replace("version =","").strip()

    def checkHost ( self ):
        """ check which host and environment we are in. Warn against running
            outside of singularity container, on clip """
        import socket
        hostname = socket.gethostname()
        if "clip-login-1" in hostname:
            self.msg ( "WARNING: running on the login node!" )
            if self.nevents > 200:
                sys.exit()
        if "clip" in hostname:
            try:
                singularity = os.environ["SINGULARITY_NAME"]
            except KeyError as e:
                pass
                #self.error ( "we seem to not be inside of a singularity container!" )
                #sys.exit(-1)

    def determineMG5Version ( self ):
        """ find out version of mg5, by peeking into mg5 directory """
        files = glob.glob ( "mg5/MG5_aMC_v*.tar.gz" )
        if len(files) != 1:
            self.msg ( "I dont understand, I see %d MG5 tarballs" % len(files) )
            return
        ver = files[0].replace(".tar.gz","").replace("mg5/","")
        ver = ver.replace ( "MG5_aMC_", "" ).replace(".","_")
        if not ver.startswith ( "v" ):
            self.msg ( "I dont understand the version id %s" % ver )
            return
        self.debug ( f"this is MG5 {ver}" )
        if ver.startswith ( "v" ):
            self.ver = ver
        if "py3" in ver:
            self.pyver = 3

    def correctPythia8CfgFile ( self ):
        """ a simple method intended to check if we have to add SysCalc:qCutList=90
            to the pythia8 configuration """
        ## qcut: SysCalc:qCutList in mg5/Template/LO/Cards/pythia8_card_default.dat
        #self.msg ( "FIXME we shouldnt be using this!" )
        return
        self.msg ( "now checking if pythia8 config needs correction" )
        needsCorrection = True
        cfgFile = "mg5/Template/LO/Cards/pythia8_card_default.dat"
        f = open ( cfgFile, "rt" )
        lines = f.readlines()
        f.close()
        for line in lines:
            p = line.find("!")
            if p > -1:
                line = line[:p]
            line = line.strip()
            if line == "":
                continue
            if "SysCalc:qCutList" in line:
                needsCorrection = False
        if "2_6" in self.ver: # only needed for 2_7 i think
            needsCorrection = False
        if not needsCorrection:
            self.msg ( "%s does not need correction" % cfgFile )
            return
        self.msg ( "seems like %s needs qCutList added" % cfgFile )
        f = open ( cfgFile, "at" )
        f.write ( "SysCalc:qCutList = 90.\n" )
        f.close()

    def info ( self, *msg ):
        print ( "%s[mg5Wrapper] %s%s" % ( colorama.Fore.YELLOW, " ".join ( msg ), \
                   colorama.Fore.RESET ) )

    def announce ( self, *msg ):
        print ( "%s[mg5Wrapper] %s%s" % ( colorama.Fore.GREEN, " ".join ( msg ), \
                   colorama.Fore.RESET ) )

    def debug( self, *msg ):
        pass

    def msg ( self, *msg):
        print ( "[mg5Wrapper] %s" % " ".join ( msg ) )

    def error ( self, *msg ):
        print ( "%s[mg5Wrapper] %s%s" % ( colorama.Fore.RED, " ".join ( msg ), \
                   colorama.Fore.RESET ) )

    def writePythiaCard ( self, process="", masses="" ):
        """ this method writes the pythia card for within mg5.
        :param process: fixme (eg T2_1jet)
        """
        self.runcard = tempfile.mktemp ( prefix="run", suffix=".card",
                                         dir=self.tempdir )
        self.debug ( f"writing pythia run card {self.runcard}" )
        templatefile = f"{self.templateDir}/template_run_card.dat"
        if not os.path.exists ( templatefile ):
            self.error ( f"cannot find {templatefile}" )
            sys.exit()
        tfile = open( templatefile,'r')
        lines = tfile.readlines()
        tfile.close()
        g = open ( self.runcard, "w" )
        for line in lines:
            for k,v in self.mgParams.items():
                if k in line:
                    vold = v
                    if type(v)==str and "M[0]" in v:
                        m0 = masses[0]
                        if bakeryHelpers.isAssociateProduction ( self.topo ):
                            m0 = ( masses[0] + masses[1] ) / 2. ## mean!
                            # m0 = min( masses[0], masses[1] )
                        v = v.replace("M[0]",str(m0))
                        v = str(eval (v ))
                    line = line.replace( f"@@{k}@@",v)
            g.write ( line )
        if False and self.topo in [ "TChiQ" ]:
            self.info( f"topo is {self.topo}: switch to new sde strategy (2)" )
            g.write ( f"# for topos like {self.topo} we use the new sde strategy\n" )
            g.write ( f"# see: https://indico.cern.ch/event/1041378/contributions/4374468/attachments/2258140/3832110/21_06_04_VBFSCAN_new_ps.pdf" )
            g.write ( "\n" )
            g.write ( " 2 = sde_strategy ! the new integration strategy\n" )
            # g.write ( " 2 = hard_survey ! not sure if this is needed, nor what it does\n" )
        g.close()
        self.info(f"wrote run card {self.runcard} for {str(masses)}[{self.topo}]")

    def writeCommandFile ( self, process = "", masses = None ):
        """ this method writes the commands file for mg5.
        :param process: fixme (eg T2tt_1jet)
        """
        self.commandfile = tempfile.mktemp ( prefix="mg5cmd", dir=self.tempdir )
        f = open(self.commandfile,'w')
        f.write('set automatic_html_opening False\n' )
        f.write('launch %s\n' % bakeryHelpers.dirName(process,masses))
        f.write('shower=Pythia8\n')
        f.write('detector=OFF\n')
        #f.write('detector=Delphes\n')
        #f.write('pythia=ON\n')
        #f.write('madspin=OFF\n')
        # f.write('order=LO\n')
        # f.write('reweight=ON\n')
        f.write('0\n')
        f.write('0\n')
        f.close()

    def pluginMasses( self, slhaTemplate, masses ):
        """ take the template slha file and plug in
            masses """
        f=open( self.templateDir+"/"+slhaTemplate,"r")
        lines=f.readlines()
        f.close()
        self.slhafile = tempfile.mktemp(suffix=".slha",dir=self.tempdir )
        f=open( self.slhafile,"w")
        n=len(masses)
        for line in lines:
            tokens = line.split()
            for i in range(n):
                repl = str(masses[i])
                prev = f"M{n-i-1}"
                if len(tokens)>1:
                    mt = tokens[1]
                    if "+" in mt and not "+" in repl:
                        mt = mt.replace ( prev, str(masses[i]) )
                        try:
                            mt=str(eval(mt))
                            repl=mt
                        except Exception as e:
                            pass
                if "+2" in line and False:
                    print ( "mt", mt )
                    print ( f"replacing with {repl}" )
                    print ( f"line is {line}" )
                p1 = line.find("+")
                p2 = line.find(" ",p1)
                addOn = line[p1:p2]
                if addOn in [ "+00", "+" ]:
                    addOn = ""
                line = line.replace ( prev+addOn, repl )
            f.write ( line )
        f.close()

    def sleep ( self ):
        """ if a file called sleep exists with an integer number in it,
        then sleep that long before starting the next point.
        meant to be used to control the production on an HPC cluster """
        sleepFile = f"{self.basedir}/sleep"
        s = 0
        if os.path.exists ( sleepFile ):
            f = open(sleepFile,"rt")
            txt = f.read()
            f.close()
            try:
                s = int ( txt )
            except Exception as e:
                pass
        if s > 0:
            self.info ( f"sleeping for {s} seconds before next point" )
            time.sleep ( s )

    def run( self, masses, analyses, pid=None ):
        """ Run MG5 for topo, with njets additional ISR jets, giving
        also the masses as a list.
        """
        self.sleep()
        self.checkInstallation()
        import emCreator
        isIn = emCreator.massesInEmbakedFile ( masses, analyses, self.topo, self.recaster )
        # print ( f"is the point {masses} for {analyses} in embakedfile? {isIn} rerun: {self.rerun}" )
        # sys.exit()
        if isIn and not self.rerun:
            return
        if not "adl" in self.recaster and self.locker.hasMA5Files ( masses ) and not self.rerun:
            return
        if "adl" in self.recaster and self.locker.hasCutlangFiles ( masses ) and not self.rerun:
            return
        locked = self.locker.lock ( masses )
        if locked:
            self.info ( "%s[%s] is locked. Skip it" % ( masses, self.topo ) )
            self.info ( f"If you wish to remove it:\nrm {self.locker.lockfile(masses)}" )
            return
        self.process = "%s_%djet" % ( self.topo, self.njets )
        if self.locker.hasHEPMC ( masses ):
            if not self.rerun:
                which  = self.recaster[0]
                self.info ( "hepmc file for %s[%s] exists. go directly to %s." % \
                            ( str(masses), self.topo, which ) )
                self.runRecasting ( masses, analyses, pid )
                self.locker.unlock ( masses )
                return
            else:
                self.info ( "hepmc file for %s exists, but rerun requested." % str(masses) )

        if "TRV1" in self.topo and float(masses[0]) >= 450. :
            self.mgParams["XQCUT"]="M[0]/15"
        if "TRV1" in self.topo and float(masses[0]) < 450. :
            self.mgParams["XQCUT"]="30"
        if "TRS1" in self.topo and float(masses[0]) >= 525. :
            self.mgParams["XQCUT"]="M[0]/15"
        if "TRS1" in self.topo and float(masses[0]) < 525. :
            self.mgParams["XQCUT"]="35"
       
        self.announce ( "starting MG5 on %s[%s] at %s in job #%s" % (masses, self.topo, time.asctime(), pid ) )
        slhaTemplate = f"slha/{self.topo}_template.slha"
        self.pluginMasses( slhaTemplate, masses )
        # first write pythia card
        self.writePythiaCard ( process=self.process, masses=masses )
        # then write command file
        self.writeCommandFile( process=self.process, masses=masses )
        # then run madgraph5
        r=self.execute ( self.slhafile, masses )
        self.unlink ( self.slhafile )
        if r:
            self.runRecasting ( masses, analyses, pid )
        self.locker.unlock ( masses )

    def runRecasting ( self, masses, analyses, pid ):
        """ run the recasting. cutlang or ma5 """
        try:
            if not self.recast:
                return
            if "adl" in self.recaster:
                self.runCutlang ( masses, analyses, pid )
            if "cm2" in self.recaster:
                self.runCheckmate ( masses, analyses, pid )
            if "MA5" in self.recaster:
                self.runMA5 ( masses, analyses, pid )
        except Exception as e:
            if self.keep: # if keep is on, we remove the lock. seems like were debugging
                self.locker.unlock ( masses )
            raise e

    def runMA5 ( self, masses, analyses, pid ):
        """ run ma5, if desired """
        spid=""
        if pid != None:
            spid = " in job #%d" % pid
        self.announce ( "starting MA5 on %s[%s] at %s%s" % ( str(masses), self.topo, time.asctime(), spid ) )
        from ma5Wrapper import MA5Wrapper
        ma5 = MA5Wrapper ( self.topo, self.njets, self.rerun, analyses, self.keep,
                           self.sqrts, keephepmc = self.keephepmc )
        self.debug ( "now call ma5Wrapper" )
        hepmcfile = self.locker.hepmcFileName ( masses )
        ret = ma5.run ( masses, hepmcfile, pid )
        msg = "finished MG5+MA5"
        if ret > 0:
            msg = "nothing needed to be done"
        if ret < 0:
            msg = "error encountered"
        self.announce ( "%s for %s[%s] at %s%s" % ( msg, str(masses), self.topo, time.asctime(), spid ) )

    def runCutlang ( self, masses, analyses, pid ):
        """ run cutlang, if desired """
        spid=""
        if pid != None:
            spid = " in job #%d" % pid
        self.announce ( "starting cutlang on %s[%s] at %s%s" % ( str(masses), self.topo, time.asctime(), spid ) )
        from cutlangWrapper import CutLangWrapper
        rerun = self.rerun
        # rerun = True
        analist = analyses.split(",")
        for ana in analist:
            ana = ana.strip()
            cl = CutLangWrapper ( self.topo, self.njets, rerun, ana,
                    auto_confirm = True, keep = self.keep, adl_file = self.adl_file,
                    event_condition = self.event_condition )
            #                   self.sqrts )
            self.debug ( f"now call cutlangWrapper for {ana}" )
            hepmcfile = self.locker.hepmcFileName ( masses )
            ret = cl.run ( masses, hepmcfile, pid )
            msg = "finished MG5+Cutlang: "
            if ret > 0:
                msg += "nothing needed to be done"
            if ret < 0:
                msg += "error encountered"
            self.announce ( "%s for %s[%s] at %s%s" % ( msg, str(masses), self.topo, time.asctime(), spid ) )

    def runCheckmate ( self, masses, analyses, pid ):
        """ run checkmate, if desired """
        spid=""
        if pid != None:
            spid = " in job #%d" % pid
        self.announce ( "starting checkmate on %s[%s] at %s%s" % ( str(masses), self.topo, time.asctime(), spid ) )
        from cm2Wrapper import CM2Wrapper
        rerun = self.rerun
        # rerun = True
        analist = analyses.split(",")
        for ana in analist:
            ana = ana.strip()
            cl = CM2Wrapper ( self.topo, self.njets, rerun, ana, keep = self.keep )
            #                   self.sqrts )
            self.debug ( f"now call cutlangWrapper for {ana}" )
            hepmcfile = self.locker.hepmcFileName ( masses )
            ret = cl.run ( masses, hepmcfile, pid )
            msg = "finished MG5+Checkmate: "
            if ret > 0:
                msg += "nothing needed to be done"
            if ret < 0:
                msg += "error encountered"
            self.announce ( "%s for %s[%s] at %s%s" % ( msg, str(masses), self.topo, time.asctime(), spid ) )


    def unlink ( self, f ):
        """ remove a file, if keep is not true """
        if self.keep:
            return
        if f == None:
            return
        if os.path.exists ( f ):
            subprocess.getoutput ( "rm -rf %s" % f )

    def exe ( self, cmd, masses="" ):
        sm = ""
        if masses != "":
            sm="[%s]" % str(masses)
        self.msg ( "exec %s%s:: %s" % (self.topo, sm, cmd[:] ) )
        pipe = subprocess.Popen ( cmd, shell=True,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE )
        ret=""
        for line in io.TextIOWrapper(pipe.stdout, encoding="latin1"):
            ret+=line
        for line in io.TextIOWrapper(pipe.stderr, encoding="latin1"):
            ret+=line
        if len(ret)==0:
            return
        maxLength=200
        # maxLength=100000
        if len(ret)<maxLength:
            self.msg ( " `- %s" % ret )
            return
        offset = 200
        self.msg ( " `- %s ..." % ( ret[-maxLength-offset:-offset] ) )

    def addJet ( self, lines, njets, f ):
        """ if 'generate' or 'add process' line, then append n jets to file f """
        for line in lines:
            if "generate" in line or "add process" in line:
                line = line.strip()
                line = line.replace ( "generate ", "add process " )
                if "$" in line and not " $" in line:
                   self.error ( "found a line with dollar and no space %s" % line )
                   self.error ( "please add a space before the dollar" )
                   sys.exit()
                if " $" in line:
                    line = line.replace(" $"," j"*njets+" $" )
                # Check if '/' exists in the line
                if '/' in line:
                    parts = line.split('/')
                    if len(parts) == 2:
                        line = parts[0] + " j"*njets + " /" + parts[1]
                    else:
                        self.error("Invalid line format, found multiple backslashes: %s" % line)
                        sys.exit()
                else:
                    line = line + " j"*njets
                line = line + "\n"
                f.write ( line )

    def mkdir ( self, dirname ):
        if not os.path.exists ( dirname ):
            try:
                os.mkdir ( dirname )
            except FileExistsError as e:
                # can happen if many processses start at once
                pass
    def checkInstallation ( self ):
        """ check the mg5 installation, including plugins
        :raises: Exception, if anything is wrong
        :returns: True, if all is ok
        """
        path = os.path.join ( self.mg5install, "HEPTools", "bin" )
        pythiaconfig = os.path.join ( path, "pythia8-config" )
        # print ( f"[mg5Wrapper] checking in {path}" )
        if not os.path.exists ( pythiaconfig ):
            raise Exception ( f"cannot find pythia8-config: {pythiaconfig}" )
        cmd = f"{pythiaconfig} --with-hepmc2"
        o = subprocess.getoutput ( cmd )
        if o == "false":
            raise Exception ( f"pythia8 has no hepmc2 support" )
        if False:
            cmd = f"{pythiaconfig} --with-lhapdf6"
            o = subprocess.getoutput ( cmd )
            if o == "false":
                raise Exception ( f"pythia8 has no lhapdf6 support" )
        return True

    def execute ( self, slhaFile, masses ):
        templatefile = self.templateDir + '/MG5_Process_Cards/'+self.topo+'.txt'
        if not os.path.isfile( templatefile ):
            self.error ( "The process card %s does not exist." % templatefile )
            sys.exit()
        f=open(templatefile,"r")
        lines=f.readlines()
        f.close()
        self.tempf = tempfile.mktemp(prefix="mg5proc",dir=self.tempdir )
        f=open(self.tempf,"w")
        if self.topo == "TChiQ":
            f.write ( "import model MSSM_SLHA2-full --modelname\n" )
        else:
            if "Hig" in self.topo:
                f.write ( "import model idm\n" )
            else:
                f.write ( "import model MSSM_SLHA2\n" )
        if False:
            # for SLHA1
            self.info ( f"do we need to port {self.topo} to slha2?" )
            f.write ( "import model_v4 mssm\n" )
        for line in lines:
            f.write ( line )
        for i in [ 1, 2, 3 ]:
            if self.njets >= i:
                self.addJet ( lines, i, f )

        Dir = bakeryHelpers.dirName ( self.process, masses )
        f.write ( "output %s\n" % Dir )
        f.close()
        self.info ( "run mg5 for %s[%s]: %s" % ( masses, self.topo, self.tempf ) )
        self.logfile = tempfile.mktemp ()
        if os.path.exists ( Dir ):
            subprocess.getoutput ( f"rm -rf {Dir}" )
        os.mkdir ( Dir )

        if self.keep:
            self.mkdir ( "keep/" )
            shutil.copy ( self.tempf, "keep/" + Dir + "mg5proc" )
        shutil.move ( self.tempf, Dir + "/mg5proc" )
        cmd = "python%d %s %s/mg5proc 2>&1 | tee %s" % \
              ( self.pyver, self.executable, Dir, self.logfile )
        self.exe ( cmd, masses )
        ## copy slha file
        if not os.path.exists ( Dir+"/Cards" ):
            cmd = f"rm -rf {Dir}"
            o = subprocess.getoutput ( cmd )
            o = subprocess.getoutput ( f"cat {self.logfile}" )
            self.error ( f"{Dir}/Cards does not exist! Skipping! {o}" )
            self.exe ( cmd, masses )
            return False
        with open ( f"{Dir}/analysis", "wt" ) as f:
            # pen down the analysis name
            ana = self.args["analyses"].upper().replace("_","-")
            f.write ( ana+"\n" )
            f.close()
        if "bias" in self.topo:
            shutil.copy("templates/pythia8_card_match.dat", Dir+'/Cards/pythia8_card.dat')
        shutil.move(slhaFile, Dir+'/Cards/param_card.dat' )
        shutil.move(self.runcard, Dir+'/Cards/run_card.dat' )
        shutil.move(self.commandfile, Dir+"/mg5cmd" )
        if (os.path.isdir(Dir+'/Events/run_01')):
            shutil.rmtree(Dir+'/Events/run_01')
        self.logfile2 = tempfile.mktemp ()
        cmd = f"python{self.pyver} {self.executable} {Dir}/mg5cmd 2>&1 | tee {self.logfile2}"
        self.exe ( cmd, masses )
        hepmcfile = self.orighepmcFileName( masses )
        if self.hasorigHEPMC ( masses ):
            dest = self.locker.hepmcFileName ( masses )
            self.msg ( "moving", hepmcfile, "to", dest )
            shutil.move ( hepmcfile, dest )
        else:
            self.error ( f"could not find orig hepmc file {self.orighepmcFileName( masses )}! maybe there is something wrong with the mg5 installation?" )
        self.clean( Dir )
        return True

    def clean ( self, Dir=None ):
        """ clean up temporary files
        :param Dir: if given, then assume its the runtime directory, and remove "Source", "lib", "SubProcesses" and other subdirs
        """
        if self.keep:
            return
        self.info ( "cleaning up %s, %s, %s, %s" % \
                ( self.commandfile, self.tempf, self.logfile, self.logfile2 ) )
        self.unlink ( ".lock*" )
        #self.unlink ( self.commandfile )
        #self.unlink ( self.tempf )
        self.unlink ( self.logfile )
        self.unlink ( self.logfile2 )
        if Dir != None:
            cmd = "rm -rf %s" % Dir
            o = subprocess.getoutput ( cmd )
            self.info ( "clean up %s: %s" % ( cmd, o ) )

    def orighepmcFileName ( self, masses ):
        """ return the hepmc file name *before* moving """
        hepmcfile = bakeryHelpers.dirName( self.process,masses)+\
                            "/Events/run_01/tag_1_pythia8_events.hepmc.gz"
        return hepmcfile

    def hasorigHEPMC ( self, masses ):
        """ does it have a valid HEPMC file? if yes, then skip the point """
        hepmcfile = self.orighepmcFileName( masses )
        if not os.path.exists ( hepmcfile ):
            return False
        if os.stat ( hepmcfile ).st_size < 100:
            ## too small to be real
            return False
        return True


def main():
    import argparse
    argparser = argparse.ArgumentParser(description='madgraph5 runner.')
    argparser.add_argument ( '-n', '--nevents', help='number of events to generate [10000]',
                             type=int, default=10000 )
    argparser.add_argument ( '-j', '--njets', help='number of ISR jets [1]',
                             type=int, default=1 )
    argparser.add_argument ( '--sqrts', help='sqrts [13]',
                             type=int, default=13 )
    argparser.add_argument ( '-p', '--nprocesses', help='number of process to run in parallel. 0 means 1 per CPU [1]',
                             type=int, default=1 )
    argparser.add_argument ( '-T', '--topo', help='topology [T2]',
                             type=str, default="T2" )
    argparser.add_argument ( '-k', '--keep', help='keep temporary files',
                             action="store_true" )
    argparser.add_argument ( '-K', '--keephepmc', help='keep hepmc files',
                             action="store_true" )
    argparser.add_argument ( '--show', help='show production stats',
                             action="store_true" )
    argparser.add_argument ( '-a', '--recast', help='run also recasting after producing the events',
                             action="store_true" )
    argparser.add_argument ( '-c', '--clean', help='clean all temporary files, then quit',
                             action="store_true" )
    argparser.add_argument ( '-b', '--bake', help='call emCreator, bake .embaked files',
                             action="store_true" )
    argparser.add_argument ( '-C', '--clean_all', help='clean all temporary files, even Tx directories, then quit',
                             action="store_true" )
    argparser.add_argument ( '--cutlang', help='use cutlang instead of MA5',
                             action="store_true" )
    argparser.add_argument ( '--checkmate', help='use checkmate instead of MA5',
                             action="store_true" )
    argparser.add_argument ( '--adl_file', help='specify the name of the adl description to be used [if not specified, try to guess]',
                             type=str, default=None )
    argparser.add_argument ( '--event_condition', help='specify conditions on the events, filter out the rest, e.g. {"higgs":1}: one and only one higgs [None]',
                             type=str, default=None )
    argparser.add_argument ( '--copy', help='copy embaked file to smodels-database',
                             action="store_true" )
    argparser.add_argument ( '-l', '--list_analyses', help='print a list of MA5 analyses, then quit',
                             action="store_true" )
    anadef = "atlas_susy_2016_07"
    anadef = "cms_sus_19_006"
    argparser.add_argument ( '--analyses', help='analyses, comma separated [%s]' % anadef,
                             type=str, default=anadef )
    argparser.add_argument ( '--maxgap2', help='maximum mass gap between second and third, to force offshell [None]',
                             type=float, default=None )
    argparser.add_argument ( '--mingap1', help='minimum mass gap between first and second, to force onshell or a mass hierarchy [None]',
                             type=float, default=None )
    argparser.add_argument ( '--mingap2', help='minimum mass gap between second and third, to force onshell or a mass hierarchy [None]',
                             type=float, default=None )
    argparser.add_argument ( '--mingap13', help='minimum mass gap between first and third, to force onshell or a mass hierarchy [None]',
                             type=float, default=None )
    argparser.add_argument ( '--maxgap13', help='maximum mass gap between first and third, to force offshell [None]',
                             type=float, default=None )
    argparser.add_argument ( '--maxgap1', help='maximum mass gap between first and second, to force offshell [None]',
                             type=float, default=None )
    argparser.add_argument ( '-r', '--rerun', help='force rerun, even if there is a summary file already',
                             action="store_true" )
    argparser.add_argument ( '--dry_run', help='dry run, just print out the mass points',
                             action="store_true" )
    argparser.add_argument ( '--ignore_locks', help='ignore any locks. for debugging only.',
                             action="store_true" )
    #mdefault = "(2000,1000,10),(2000,1000,10)"
    mdefault = "(1000,2000,50),'half',(1000,2000,50)"
    argparser.add_argument ( '-m', '--masses', help='mass ranges, comma separated list of tuples. One tuple gives the range for one mass parameter, as (m_lowest, m_highest, delta_m). m_highest and delta_m may be omitted. Keywords "half" and "same" (add quotes) are accepted for intermediate masses. [%s]' % mdefault,
                             type=str, default=mdefault )
    args = argparser.parse_args()
    if args.topo in [ "T1", "T2", "T1bbbb", "T2bb", "T2ttoff", "T1ttttoff" ] and args.mingap1 == None and not args.list_analyses and not args.clean and not args.clean_all:
        if "(" in args.masses:
            print ( f"[mg5Wrapper] for topo {args.topo} we set mingap1 to 1." )
        args.mingap1 = 1.
    if args.topo in [ "T1tttt", "T2tt" ] and args.mingap1 == None and not args.list_analyses and not args.clean and not args.clean_all:
        if "(" in args.masses:
            print ( f"[mg5Wrapper] for topo {args.topo} we set mingap1 to 1." )
        ## also for these we set to 1. because usually this is also used for offshell
            print ( f"[mg5Wrapper] for topo {args.topo} we set mingap1 to 1." )
        args.mingap1 = 1. # 170.
    if args.topo in [ "T1ttttoff", "T2ttoff" ] and args.maxgap1 == None and not args.list_analyses and not args.clean and not args.clean_all:
        if "(" in args.masses:
            print ( f"[mg5Wrapper] for topo {args.topo} we set maxgap1 to 180." )
        args.maxgap1 = 180.
    if args.list_analyses:
        bakeryHelpers.listAnalyses( args.cutlang, args.checkmate )
        sys.exit()
    if args.show:
        import printProdStats
        anas = args.analyses.split(",")
        for ana in anas:
            ana = bakeryHelpers.ma5AnaNameToSModelSName ( ana )
            printProdStats.main( ana )
        sys.exit()

    if args.clean_all:
        bakeryHelpers.cleanAll()
        sys.exit()

    if args.clean:
        bakeryHelpers.clean()
        sys.exit()

    hname = socket.gethostname()
    if hname.find(".")>0:
        hname=hname[:hname.find(".")]
    logfile = "baking.log"
    lastline = None
    if os.path.exists ( logfile ):
        f=open( logfile,"rt")
        lines = f.readlines()
        f.close()
        if len(lines)>0:
            lastline = lines[-1].strip()
    cmd = ""
    for i,a in enumerate(sys.argv):
        if i>0 and sys.argv[i-1] in [ "-m", "--masses" ]:
            a='"%s"' % a
        if i>0 and sys.argv[i-1] in [ "--analyses" ]:
            a='"%s"' % a
        cmd += a + " "
    cmd = cmd[:-1]
    if lastline == None or lastline != cmd:
        with open(logfile,"a") as f:
            f.write ( f"[{hname}] {time.asctime()}:\n{cmd}\n" )
    nReqM = bakeryHelpers.nRequiredMasses ( args.topo )
    keepOrder=True
    if args.topo == "TGQ":
        keepOrder=False
    masses = bakeryHelpers.parseMasses ( args.masses,
                                         mingap1=args.mingap1, maxgap1=args.maxgap1,
                                         mingap2=args.mingap2, maxgap2=args.maxgap2,
                                         mingap13=args.mingap13, maxgap13=args.maxgap13 )
    if args.dry_run:
        print ( f"[mg5Wrapper] masses: {masses}" )
        sys.exit()
    import random
    random.shuffle ( masses )
    nm = len(masses)
    if nm == 0:
        line = "[mg5Wrapper] no masses found within the constraints:"
        if args.mingap1 != None or args.maxgap1 != None:
            line += f" gap(1,2) not in [{args.mingap1},{args.maxgap1 if args.maxgap1 is not None else '+inf'}];"
        if args.mingap13 != None or args.maxgap13 != None:
            line += f" gap(1,3) not in [{args.mingap13},{args.maxgap13 if args.maxgap13 is not None else '+inf'}];"
        if args.mingap2 != None or args.maxgap2 != None:
            line += f" gap(2,3) not in [{args.mingap2},{args.maxgap2 if args.maxgap2 is not None else '+inf'}];"
        print ( f"{line}" )
        locker.Locker( args.sqrts, args.topo, args.ignore_locks ).unlock ( masses )
        sys.exit()
    if nReqM != len(masses[0]):
        print ( "[mg5Wrapper] you gave %d masses, but %d are required for %s." % \
                ( len(masses[0]), nReqM, args.topo ) )
        sys.exit()
    nprocesses = bakeryHelpers.nJobs ( args.nprocesses, nm )
    recaster = [ "MA5" ]
    if args.cutlang or args.checkmate:
        recaster = [ "adl" ]
        if args.checkmate:
            recaster = [ "cm2" ]
        args.recast = True
    if args.checkmate and args.cutlang:
        print ( "[mg5Wrapper] both checkmate and cutlang have been asked for. please choose!" )
        sys.exit()

    mg5 = MG5Wrapper( vars(args), recaster )
    # mg5.info( "%d points to produce, in %d processes" % (nm,nprocesses) )
    djobs = int(len(masses)/nprocesses)

    def runChunk ( chunk, pid ):
        for c in chunk:
            mg5.run ( c, args.analyses, pid )
        print ( "%s[runChunk] finished chunk #%d%s" % \
                ( colorama.Fore.GREEN, pid, colorama.Fore.RESET ) )

    jobs=[]
    for i in range(nprocesses):
        chunk = masses[djobs*i:djobs*(i+1)]
        if i == nprocesses-1:
            chunk = masses[djobs*i:]
        p = multiprocessing.Process(target=runChunk, args=(chunk,i))
        jobs.append ( p )
        p.start()
    for j in jobs:
        j.join()
    if args.bake:
        import emCreator
        from types import SimpleNamespace
        # analyses = "atlas_susy_2016_07"
        analyses = args.analyses
        args = SimpleNamespace ( masses="all", topo=args.topo, njets=args.njets, \
                analyses = analyses, copy=args.copy, keep=args.keep, sqrts=args.sqrts,
                verbose=False, ma5=not args.cutlang, cutlang=args.cutlang, stats=True,
                cleanup = False, checkmate=args.checkmate )
        emCreator.run ( args )
    """
    with open(logfile,"a") as f:
        cmd = ""
        for i,a in enumerate(sys.argv):
            if i>0 and sys.argv[i-1] in [ "-m", "--masses" ]:
                a='"%s"' % a
            cmd += a + " "
        cmd = cmd[:-1]
        # f.write ( "[%s] %s: ended: %s\n" % ( hname, time.asctime(), cmd ) )
    """

if __name__ == "__main__":
    main()
