#!/usr/bin/env python3

"""
.. module:: ma5Wrapper
        :synopsis: code that wraps around MadAnalysis5. Produces the data cards,
                   and runs the ma5 executable.

.. moduleauthor:: Wolfgang Waltenberger <wolfgang.waltenberger@gmail.com>
"""

import os, sys, colorama, subprocess, shutil, tempfile, time, io
import multiprocessing
import bakeryHelpers

class MA5Wrapper:
    def __init__ ( self, topo, njets, rerun, analyses, keep=False, 
                   sqrts=13, ver="1.9.beta" ):
        """
        :param ver: version of ma5
        """
        self.topo = topo
        self.sqrts = sqrts
        self.njets = njets
        self.analyses = analyses
        self.rerun = rerun
        self.keep = keep
        self.basedir = bakeryHelpers.baseDir()
        os.chdir ( self.basedir )
        self.ma5results = "%s/ma5results/" % self.basedir
        if not os.path.exists ( self.ma5results ):
            subprocess.getoutput ( "mkdir %s" % self.ma5results )
        self.ma5install = "%s/ma5/" % self.basedir
        if abs ( sqrts - 8 ) < .1:
            self.ma5install = "%s/ma5.8tev/" % self.basedir
        self.ver = ver
        if not os.path.isdir ( self.ma5install ):
            self.error ( "ma5 install is missing??" )
            sys.exit()
        self.executable = "bin/ma5"
        if not os.path.exists ( self.ma5install + self.executable ):
            self.info ( "cannot find ma5 installation at %s" % self.ma5install )
            self.exe ( "%s/make.py" % self.ma5install )
        self.templateDir = "%s/templates/" % self.basedir
        # self.info ( "initialised" )

    def info ( self, *msg ):
        print ( "%s[ma5Wrapper] %s%s" % ( colorama.Fore.YELLOW, " ".join ( msg ), \
                   colorama.Fore.RESET ) )

    def debug( self, *msg ):
        pass

    def msg ( self, *msg):
        print ( "[ma5Wrapper] %s" % " ".join ( msg ) )

    def error ( self, *msg ):
        print ( "%s[ma5Wrapper] Error: %s%s" % ( colorama.Fore.RED, " ".join ( msg ), \
                   colorama.Fore.RESET ) )

    def writeRecastingCard ( self ):
        """ this method writes the recasting card, which defines which analyses
        are being recast. """
        self.recastfile = tempfile.mktemp ( dir=self.ma5install, prefix="recast" )
        filename = self.recastfile
        # filename = self.ma5install + "recasting.dat"
        self.debug ( "writing recasting card %s" % filename )
        templatefile = self.templateDir+'/recasting_card.dat'
        if not os.path.exists ( templatefile ):
            self.error ( "cannot find %s" % templatefile )
            sys.exit()
        ## for now simply copy the recasting card
        shutil.copy ( templatefile, filename )
        f = open ( filename, "at" )
        recastcard = { "atlas_susy_2016_07": "delphes_card_atlas_exot_2015_03" }
        recastcard["atlas_susy_2013_02"] = "delphesma5tune_card_atlas_dileptonsusy"
        recastcard["cms_sus_16_033"] = "delphes_card_cms_sus_16_033"
        recastcard["cms_sus_19_006"] = "delphes_card_cms_sus_19_006"
        anas = set(self.analyses.split(","))
        versions = { "atlas_susy_2016_07": "1.2",
                     "atlas_susy_2013_02": "1.1",
                     "cms_sus_19_006": "1.2",
                     "cms_sus_16_033": "1.2" }
        self.info ( "adding %s to recast card %s" % ( self.analyses, filename ) )
        for i in anas:
            if not i in versions or not i in recastcard:
                self.error ( f"{i} is not defined!" )
                sys.exit()
            f.write ( "%s         v%s        on    %s.tcl\n" % ( i, versions[i], recastcard[i] ) )
        f.close()
        self.debug ( "wrote recasting card %s in %s" % ( filename, os.getcwd() ) )

    def unlink ( self, f ):
        if os.path.exists ( f ) and not self.keep:
            subprocess.getoutput ( "rm -rf %s" % f )

    def writeCommandFile ( self, hepmcfile, process, masses ):
        """ this method writes the commands file for ma5.
        :param hepmcfile: I think thats the input events
        """
        self.info ( "writing commandfile %s" % self.commandfile )
        f = open( self.commandfile,'wt')
        #f.write('install delphesMA5tune\n')
        #f.write('install PADForMA5tune\n')
        #f.write('install delphes\n')
        #f.write('install PAD\n')
        f.write('set main.recast = on\n')
        #filename = self.recastfile.replace(self.ma5install,"./")
        #f.write('set main.recast.card_path = %s\n' % filename )
        f.write('set main.recast.card_path = ./recast\n' )
        f.write('set main.recast.global_likelihoods = off\n' )
        f.write('import '+hepmcfile+'\n')
        f.write('submit ANA_%s\n' % bakeryHelpers.dirName( process, masses )  )
        f.close()

    def checkForSummaryFile ( self, masses ):
        """ given the process, and the masses, check summary file
        :returns: True, if there is a usable summary file, with all needed analyses
        """
        process = "%s_%djet" % ( self.topo, self.njets )
        dirname = bakeryHelpers.dirName ( process, masses )
        summaryfile = "%s/ANA_%s/Output/SAF/CLs_output_summary.dat" % \
                       ( self.ma5results, dirname )
        if not os.path.exists ( summaryfile ) or os.stat(summaryfile).st_size<10:
            self.msg ( "No summary file %s found. Run analyses!" % summaryfile )
            return False
        self.msg ( "It seems like there is already a summary file %s" % summaryfile )
        f=open(summaryfile,"rt")
        lines=f.readlines()
        f.close()
        anaIsIn = {}
        analyses = self.analyses.split(",")
        for ana in analyses:
            anaIsIn[ana]=False
        for line in lines:
            for ana in analyses:
                if ana in line:
                    anaIsIn[ana]=True
        allAnasIn = sum ( anaIsIn.values() ) == len(anaIsIn)
        if allAnasIn and (not self.rerun):
            self.msg ( "%s are in the summary file for %s: skip it." % ( self.analyses, str(masses) ) )
            return True
        if not allAnasIn:
            self.msg ( "%s not in summary file: rerun!" % self.analyses )
        return False

    def run( self, masses, hepmcfile, pid=None ):
        """ Run MA5 over an hepmcfile, specifying the process
        :param pid: process id, for debugging
        :param hepmcfile: the hepcmfile name
        :returns: -1 if problem occured, 0 if all went smoothly,
                   1 if nothing needed to be done.
        """
        spid = ""
        if pid != None:
            spid = "[%d]" % pid
        self.commandfile = tempfile.mktemp ( prefix="ma5cmd", dir=self.ma5install )
        self.teefile = tempfile.mktemp ( prefix="ma5", suffix=".run", dir="/tmp" )
        process = "%s_%djet" % ( self.topo, self.njets )
        hasAllInfo = self.checkForSummaryFile ( masses )
        if hasAllInfo:
            return 1
        if not os.path.exists ( hepmcfile ):
            self.error ( "%scannot find hepmc file %s" % ( spid, hepmcfile ) )
            p = hepmcfile.find("Events")
            if not self.keep:
                cmd = "rm -rf %s" % hepmcfile[:p]
                o = subprocess.getoutput ( cmd )
                self.error ( "%sdeleting the folder %s: %s" % ( spid, cmd, o ) )
            return -1
            # sys.exit()
        # now write recasting card
        self.msg ( "%sFound hepmcfile at %s" % ( spid, hepmcfile ) )
        self.writeRecastingCard ()
        self.writeCommandFile( hepmcfile, process, masses )
        Dir = bakeryHelpers.dirName ( process, masses )
        tempdir = "%s/ma5_%s" % ( self.basedir, Dir )
        a = subprocess.getoutput ( "mkdir %s" % tempdir )
        a = subprocess.getoutput ( "cp -r %s/bin %s/madanalysis %s/tools %s" % \
                                   ( self.ma5install, self.ma5install, self.ma5install, tempdir ) )
        a = subprocess.getoutput ( "mv %s %s/recast" % ( self.recastfile, tempdir ) )
        # a = subprocess.getoutput ( "cp -r %s %s" % ( self.recastfile, tempdir ) )
        a = subprocess.getoutput ( "mv %s %s/ma5cmd" % \
                                   ( self.commandfile, tempdir ) )

        # then run MadAnalysis
        os.chdir ( tempdir )
        cmd = "python3 %s -R -s ./ma5cmd 2>&1 | tee %s" % (self.executable, \
                self.teefile )
        self.exe ( cmd, maxLength=None )
        # self.unlink ( self.recastfile )
        # self.unlink ( self.commandfile )
        self.unlink ( self.teefile )
        smass = "_".join ( map ( str, masses ) )
        origsaffile = "%s/ANA_%s_%djet.%s/Output/SAF/defaultset/defaultset.saf" % \
                       ( tempdir, self.topo, self.njets, smass )
        origsaffile = origsaffile.replace("//","/")
        destsaffile = bakeryHelpers.safFile (self.ma5results, self.topo, masses, self.sqrts )
        dirname = bakeryHelpers.dirName ( process, masses )
        origdatfile = "%s/ANA_%s/Output/SAF/CLs_output_summary.dat" % \
                      ( tempdir, dirname )
        origdatfile = origdatfile.replace("//","/")
        errFree=True
        if not os.path.exists ( origdatfile ):
            errFree=False
            self.error ( "dat file %s does not exist!" % origdatfile )
        if not os.path.exists ( origsaffile ):
            errFree=False
            self.error ( "saf file %s does not exist!" % origsaffile )
        destdatfile = bakeryHelpers.datFile (  self.ma5results, self.topo, masses, self.sqrts )
        if errFree: ## only move if we have both
            shutil.move ( origdatfile, destdatfile )
            shutil.move ( origsaffile, destsaffile )
            if not self.keep:
                self.exe ( "rm -rf %s" % hepmcfile )
        if not self.keep:
            self.exe ( "rm -rf %s" % tempdir )
        os.chdir ( self.basedir )
        return 0

    def exe ( self, cmd, maxLength=100 ):
        """ execute cmd in shell
        :param maxLength: maximum length of output to be printed
        """
        self.msg ( "exec: [%s] %s" % (os.getcwd(), cmd ) )
        myenv = dict(os.environ)
        # home = "/scratch-cbe/users/wolfgan.waltenberger/"
        home = os.environ["HOME"]
        home = home.replace("git/em-creator","")
        pylocaldir = "%s/.local/lib/python3.9/" % home
        rootsys="/mnt/hephy/pheno/opt/root6.24-py39-u21.04/"
        import socket
        if socket.gethostname() in [ "two", "wnouc" ]:
            rootsys="/opt/root/"
        myenv["ROOTSYS"]=rootsys
        myenv["PATH"]=".:%s/bin:/usr/bin:/bin:/usr/local/bin" % rootsys
        myenv["LD_LIBRARY_PATH"]="%s/lib:/.singularity.d/libs" % rootsys
        myenv["PYTHONPATH"]="%s:%s/site-packages/:%s/lib:/users/wolfgan.waltenberger/git/smodels-utils" % \
            ( pylocaldir, pylocaldir, rootsys )
        pipe = subprocess.Popen ( cmd, env = myenv, shell=True,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE )
        ret=""
        for line in io.TextIOWrapper(pipe.stdout, encoding="latin1"):
            ret+=line
        for line in io.TextIOWrapper(pipe.stderr, encoding="latin1"):
            ret+=line
        #ret = subprocess.getoutput ( cmd )
        ret = ret.strip()
        if len(ret)==0:
            return
        # maxLength=60
        # maxLength=560
        if maxLength == None:
            maxLength = len(ret)+1
        if len(ret)<maxLength:
            self.msg ( " `- %s" % ret )
            return
        self.msg ( " `- %s" % ( ret[-maxLength:] ) )

    def clean ( self ):
        subprocess.getoutput ( "rm -rf %s/recast*" % self.ma5install )
        subprocess.getoutput ( "rm -rf %s/ma5cmd*" % self.ma5install )
    def clean_all ( self ):
        self.clean()
        subprocess.getoutput ( "rm -rf %s/ANA*" % self.ma5install )

if __name__ == "__main__":
    import argparse
    argparser = argparse.ArgumentParser(description='madanalysis5 runner.')
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
    if args.clean:
        ma5 = MA5Wrapper( args.topo, args.njets, args.rerun, args.analyses )
        ma5.clean()
        sys.exit()
    if args.clean_all:
        ma5 = MA5Wrapper( args.topo, args.njets, args.rerun, args.analyses )
        ma5.clean_all()
        sys.exit()
    if args.masses == "all":
        masses = bakeryHelpers.getListOfMasses ( args.topo )
    else:
        masses = bakeryHelpers.parseMasses ( args.masses )
    nm = len(masses)
    nprocesses = bakeryHelpers.nJobs ( args.nprocesses, nm )
    ma5 = MA5Wrapper( args.topo, args.njets, args.rerun, args.analyses, args.keep,
                      args.sqrts )
    # ma5.info( "%d points to produce, in %d processes" % (nm,nprocesses) )
    djobs = int(len(masses)/nprocesses)

    def runChunk ( chunk, hepmcfile, pid ):
        for c in chunk:
            ma5.run ( c, hepmcfile, pid )

    jobs=[]
    for i in range(nprocesses):
        chunk = masses[djobs*i:djobs*(i+1)]
        if i == nprocesses-1:
            chunk = masses[djobs*i:]
        p = multiprocessing.Process(target=runChunk, args=(chunk,i))
        jobs.append ( p )
        p.start()
