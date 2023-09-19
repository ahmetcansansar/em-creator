#!/usr/bin/env python3
"""
.. module:: CutLangWrapper
        :synopsis: code that wraps around cutlang. Produces the data cards,
                   and runs the cutlang executable.

.. moduleauthor:: Wolfgang Waltenberger <wolfgang.waltenberger@gmail.com>
.. moduleauthor:: Jan Mrozek <jmrozek@protonmail.ch>

..directory structure::
    em-creator --┬-CutLang---------┬-runs ~ dir with running script (CLA.sh)
                 |                 +-CLA  ~ dir with executable (CLA.exe)
                 |                 + ADLLHCAnalysis ~ contains adl files for analyses
                 +-cutlang_results-┬-ANA_*-┬-output-┬-efficiencies.embaked ~ after running join_embaked
                 |                         |        +-<analysis>_<topo>_mass_<mass>.embaked
                 |                         |        +-CL_output_summary.dat
                 |                         |        +-delphes_out_*.root
                 |                         |        +-log_<time>.txt
                 |                         +-temp---┬-hepmcfile.hepmc ~ if it was gzipped
                 |                                  +-log_<time>.txt
                 +-Delphes---------┬-DelphesHepMC ~ delphes executable
                                   +-cards ~ dir with delphes configuration cards
"""
# TODO: Adapt for paralelisation.
# TODO: Add exception mechanism to exe.
# TODO: Debug levels? Or adapt logging package?
# TODO: Maybe add some time to logs and embaked?
# FIXME: Refactor postprocessing
# FIXME: Remove the directory if makefile not present
# FIXME: Print only last n lines of exe output.
# FIXME: Instead of exiting, raise exceptions?
# FIXME: Adapt the getmasses scheme to CLA wrapper
# FIXME: Delphes & Cutlang return codes.
# FIXME: Output partial efficiencies into .part.embaked files
# FIXME: analyses or analysis in __main__ and in run and __init__?
# TODO: Add a filter complement function

# Standard library imports
import os                      # For path, unlink
import sys                     # For exit()
import colorama                # For output colors (in msg, error, ...)
import subprocess              # For Popen in exe method
import shutil                  # For move(), rmtree(), FIXME remove?
import re                      # For delphes card picker
import multiprocessing         # Used when run as __main__
import gzip                    # For decompression of hepmc file
import time                    # Used for waiting after blocking io error
import glob                    # for finding adl files
import random                  # Used to randomize waiting time after blocking io error
from datetime import datetime  # For timestamp of embaked files
from typing import List, Union, Text # For type hinting

from colorama import Fore

# 3 party imports

# local imports
import bakeryHelpers       # For dirnames
from bakeryHelpers import execute


class CutLangWrapper:

    GZIP_BLOCK = 1 << 24  # Block to decompress gzipped file, ~ 16 MB

    def __init__(self, topo: str, njets: int, rerun: bool, analysis: str,
                 auto_confirm: bool = True, filterString: str = "",
                 keep: bool = False, adl_file : Union[Text,None] = None,
                 event_condition : Union[Text,None] = None ) -> None:
        """
        If not already present, clones and builds Delphes, CutLang and ADLLHC Analyses.
        Prepares output directories.

        :param topo:    SMS topology
                        (see https://smodels.github.io/docs/SmsDictionary )
        :param njets:   Number of jets
        :param rerun:   True for rerunning the analyses already done
        :param analysis: Analysis to be done
                        (see https://smodels.github.io/docs/ListOfAnalyses )
        :param auto_confirm: Proceed with downloads without prompting
        :param keep: keep temporary files for debugging?
        """
        # General vars
        self.njets = njets
        self.adl_file = adl_file
        self.getEventCondition ( event_condition )
        self.keep = keep ## keep temporary files?
        self.topo = topo
        if "," in analysis:
            self._error ( "Multiple analyses supplied. This should be handled by mg5Wrapper!" )
            sys.exit(-1)
        self.analysis = self._standardise_analysis(analysis)
        self.rerun = rerun
        self.auto_confirm = auto_confirm
        if len(filterString) > 0:
            self.filterRegions, self.filterBins =\
                             CutLangWrapper.process_filter_string(filterString)
        else:
            self.filterRegions, self.filterBins = set(), {}

        # make auxiliary directories
        self.base_dir = Directory(f"cutlang_results/{self.analysis}", make=True)
        dirname = f"{self.topo}_{self.njets}jet"
        self.ana_dir = Directory(os.path.join(self.base_dir.get(), f"ANA_{dirname}"), make=True)
        self.out_dir = Directory(os.path.join(self.ana_dir.get(), "output"), make=True)
        self.tmp_dir = Directory(os.path.join(self.ana_dir.get(), "temp"), make=True)
        time = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        self.initlog = os.path.join(self.tmp_dir.get(), "log_" + time + ".txt")
        self.tempFiles = [] ## way to keep track of tempFiles
        self._delete_dir(self.initlog)

        # Cutlang vars
        self.cutlanginstall = "./CutLang/"
        self.cutlang_executable = "./CutLang/CLA/CLA.exe"
        self.cutlang_run_dir = "./runs"  # Directory where the CutLang will run
        self.cutlang_script = "./CLA.sh"
        self.summaryfile = os.path.join("./", f"clsum_{topo}_{self.analysis}.dat")

        # ADLLHCAnalysis vars
        self.adllhcanalyses = "./CutLang/ADLLHCanalyses"

        # Delphes vars
        self.delphesinstall = "./delphes/"

        # ====================
        #      Delphes Init
        # ====================
        # Check if Delphes dir is present and if not, attempt to clone it from github
        self.delphes_exe = bakeryHelpers.checkDelphesInstall ( self.delphesinstall )

        # =====================
        #      Cutlang Init
        # =====================
        # Check if Cutlang dir is present and if not, attempt to clone it from github
        if not os.path.isdir(self.cutlanginstall):
            self._info("cutlang directory missing, download from github?")
            if self._confirmation("Download from github?"):
                args = ['git', 'clone', 'https://github.com/unelg/CutLang']
                #v = 'v.2.9.0'
                #v = 'v2.9.10'
                #args = ['git', 'clone', '-b', v, 'https://github.com/unelg/CutLang']
                # args = ['git', 'clone', 'https://github.com/unelg/CutLang']
                execute(args, exit_on_fail=True, logfile=self.initlog)
            else:
                self._error("No CutLang dir. Exiting.")
                sys.exit()

        # if there is no executable, compile it
        if not os.path.exists(self.cutlang_executable):
            self._info("cannot find cutlang installation at %s" % self.cutlanginstall)
            compile_path = os.path.abspath(self.cutlanginstall + "CLA/")
            # Check for existence of makefile, if not present exit
            makefile_path = os.path.join(compile_path, "Makefile")
            if not os.path.isfile(makefile_path):
                self._error("No executable and no Makefile. Bailin' it.")
                sys.exit()
            # disable warnings for compilation to declutter output
            compile_path = os.path.abspath(self.cutlanginstall + "CLA/")
            args = ['sed', '-i', 's/ -Wall//g', os.path.join(compile_path, "Makefile")]
            execute(args)

            self._info("Compiling CutLang...")
            ncpus = 4
            try:
                from smodels.tools.runtime import nCPUs
                ncpus = nCPUs()
            except ImportError:
                pass
            args = [ 'make', '-j', str(ncpus) ]
            execute(args, cwd=compile_path, exit_on_fail=True, logfile=self.initlog)
        self._info("CutLang initialisation finished.")

        # ==============================
        #      ADL LHC Analyses Init
        # ==============================
        # Check if ADLLHCAnalyses dir is present and if not, attempt to clone it from github
        if not os.path.exists(self.adllhcanalyses):
            os.makedirs(self.adllhcanalyses)
        if not os.path.isdir(self.adllhcanalyses):
            self._error("ADL LHC Analyses path is not a direcotry, exiting.")
            sys.exit()
        dirname = os.path.dirname(self.adllhcanalyses)
        if len(os.listdir(self.adllhcanalyses)) == 0:
            args = ["rm", "-rf", self.adllhcanalyses]
            execute(args)
            args = ["git", "clone", "https://github.com/ADL4HEP/ADLLHCanalyses"]
            execute( args, cwd=dirname, exit_on_fail=True, 
                      logfile=self.initlog)
        allowDraftAnas = True
        if allowDraftAnas:
            draftname = "ADLAnalysisDrafts"
            fulldraft = os.path.join ( dirname, draftname )
            if os.path.exists ( fulldraft ):
                pass
            #    args = ["rm", "-rf", fulldraft ]
            #    execute(args)
            else:
                args = ["git", "clone", f"https://github.com/ADL4HEP/{draftname}"]
                execute(args, cwd=dirname,
                         exit_on_fail=True, logfile=self.initlog)
            import shutil
            for x in glob.glob ( f"{dirname}/ADLAnalysisDrafts/*" ):
                if not "CMS-" in x and not "ATLAS-" in x:
                    continue
                fname = os.path.basename ( x )
                if not os.path.exists ( os.path.join ( dirname, "ADLLHCanalyses", fname ) ):
                    shutil.copytree ( f"{dirname}/ADLAnalysisDrafts/{fname}", f"{dirname}/ADLLHCanalyses/{fname}" )

        self._info("ADLLHC Analyses initialisation finished.")

    def getEventCondition ( self, event_condition ):
        pids = { "gamma": 22, "Z": 23, "higgs": 25 }
        self.event_condition = event_condition
        if event_condition == None:
            return
        self.event_condition = {}
        for k,v in pids.items():
            event_condition = event_condition.replace(k,str(v))
        self.event_condition = eval ( event_condition )

    def list_analyses ( self ):
        """ list all analyses that are to be found in CutLang/ADLLHCanalyses/ """
        files = glob.glob ( f"{self.adllhcanalyses}/CMS*" )
        files += glob.glob ( f"{self.adllhcanalyses}/ATLAS*" )
        for f in files:
            t = f.replace( self.adllhcanalyses + "/", "" )
            print ( t )

    def getMassesFromHEPMCFile ( self, hepmcfile: str ) -> str:
        """ try to obtain the masses from the hepmc file name """
        ret = hepmcfile.replace(".hepmc.gz","").replace(".hepmc","")
        if ret.endswith(".13"):
            ret = ret[:-3]
        if ret.endswith(".8"):
            ret = ret[:-2]
        p1 = ret.find("_")
        ret = ret[ p1+1: ]
        ret = ret.replace("_",",")
        ret = "(" + ret + ")"
        return ret
        
    def filterDelphesUproot ( self, delph_out : str ):
        """ lets now go through the delphes file, and keep only events
            that contains Z bosons AND gammas FIXME doesnt work yet """
        import uproot
        f = uproot.open ( delph_out )
        delphes = f["Delphes"]
        allpids = delphes["Particle/Particle.PID"].array()
        print ( "pids of entry 0", list(allpids[0][:10]) )
        print ( "pids of entry 1", list(allpids[1][:10]) )
        askfor = ( 22, 25 ) # 22: gamma, 23: Z, 25: higgs
        bitmask = []
        for i,pids in enumerate ( allpids ):
            addMe = True
            for ask in askfor:
                if not ask in pids and not -ask in pids:
                    addMe = False
            bitmask.append ( addMe )
        self._msg ( f"@@@@ bitmask is {bitmask}" )
        """
        g = uproot.recreate ( "new.root", compression=uproot.ZLIB(4) )
        g["ProcessID0"]=f["ProcessID0"]
        g["Delphes"]=delphes
        g.close()
        """

    def readRootArray ( self, arr ):
        """ arr is ROOT.TLeafElement, read all entries """
        ret = []
        for i in range(arr.GetNdata()):
            tmp = arr.GetValue(i)
            if tmp == int(tmp):
                tmp = int(tmp)
            ret.append ( tmp )
        return ret

    def filterDelphes ( self, delph_out : str ):
        """ lets now go through the delphes file, and keep only events
            that contains Z bosons AND gammas """
        if self.event_condition is None:
            return
        bitmask = []
        self._msg ( f"filtering {delph_out}" )
        import ROOT
        f = ROOT.TFile ( delph_out, "read" )
        g = ROOT.TFile ( "new.root", "recreate" )
        d = f.Delphes
        # d = f.Get("Delphes") does the same as above
        # branch = d.GetBranch("Particle")
        leaf = d.GetLeaf("Particle.PID")
        n = d.GetEntries()
        cloned = d.CopyTree("0")
        # 22: gamma, 23: Z, 25: higgs
        # print ( "event condition is", self.event_condition )
        for event in range(n):
            d.GetEntry(event) # start with event #0
            pids = self.readRootArray(leaf)
            counts = {}
            for k in self.event_condition.keys():
                counts[k] = pids.count(k)
            passes = True
            for k,v in self.event_condition.items():
                if k in counts and v == counts[k]:
                    continue
                passes = False
            # print ( "counts for event", event, "are", counts, "passes", passes )
            if passes:
                cloned.Fill()
        g.Write()
        g.Close()
        f.Close()
        cmd = f"mv new.root {delph_out}"
        subprocess.getoutput ( cmd )

    def run(self, mass: str, hepmcfile: str, pid: int = None) -> int:
        """ Gives efficiency values for the given hepmc file.

            input.hepmc --> Delphes --> output.root --┬-> CutLang --> eff.embaked
                                        CutLang.edl --┘
            error values:
                -1:   Cannot find hepmc file
                -2:   The analysis has already been done and rerun flag is False
                -3:   Could not copy CutLang to temporary directory
                -4    There were no efficiencies found
        :param mass: string that describes the mass vector, e.g. "(1000,100)".
                     If "Masses not specified", then try to extract masses from
                     hepmcfile name. FIXME what now, mass range or tuple of masses?
        """
        if mass == "Masses not specified":
            # try to extract mass from hepmc file name
            mass = self.getMassesFromHEPMCFile ( hepmcfile )

        time = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        smass=str(mass)
        logfile = os.path.join(self.tmp_dir.get(), "_".join(["log", smass, time]) + ".txt")
        self._delete_dir(logfile)
        mass_stripped = str(mass).replace("(", "").replace(")", "")
        mass_stripped = mass_stripped.replace(",", "_").replace(" ", "")

        self._info(f"Writing output into directory {self.ana_dir.get()} .")
        self._info(f"Masses are {mass}")

        if self._check_summary_file(mass):
            return -2

        # Decompress hepmcfile if necessary
        if not os.path.isfile(hepmcfile):
            self._error(f"cannot find hepmc file {hepmcfile}.")
            return -1
        if ".gz" in hepmcfile:
            hepmcfile = self._decompress(hepmcfile, self.tmp_dir.get())


        # ======================
        #        Delphes
        # ======================
        # set input/output paths
        self._msg("Found hepmcfile at", hepmcfile)
        delphes_card = self._pick_delphes_card()
        delph_out = os.path.join(self.out_dir.get(), f"delphes_out_{mass_stripped}.root")

        # Remove output file if already exists
        if os.path.exists(delph_out):
            self._info(f"Removing {delph_out}.")
            args = ["rm", delph_out]
            execute(args, logfile=logfile)


        # run delphes
        self._debug("Running delphes.")
        args = [self.delphes_exe, delphes_card, delph_out, hepmcfile]
        execute(args, logfile=logfile)
        self._debug("Delphes finished.")

        ## possibly we need to filter the delphes output
        # self.filterDelphesUproot ( delph_out )
        self.filterDelphes ( delph_out )

        # ======================
        #        CutLang
        # ======================
        # Prepare input paths
        cla_input = os.path.abspath(delph_out)
        cutlangfile = self.pickCutLangFile(self.analysis)

        # copy cutlang to a temporary directory
        cla_temp_name = os.path.join(self.tmp_dir.get(), f"CLA_{mass_stripped}")
        # to prevent errors from copy during reruns delete and remake
        if os.path.exists(cla_temp_name):
            self._delete_dir(cla_temp_name)
        cla_temp = Directory(cla_temp_name, make=True)
        if not self._copy_cla(cla_temp.get(), logfile):
            self.removeTempFiles()
            return -3
        cla_run_dir = os.path.join(cla_temp.get(), self.cutlang_run_dir)

        # run CutLang
        cmd = [self.cutlang_script, cla_input, "DELPHES", "-i", cutlangfile]
        self._debug("Running CLA")
        execute(cmd, cwd=cla_run_dir, logfile=logfile)
        self._debug("CLA finished.")

        ## now that we ran cutlang, mark the delphes root file as to-be-deleted
        self.tempFiles.append ( delph_out )

        # ====================
        #  Postprocessing
        # ====================
        # efficiency file name
        effi_file = os.path.join(self.out_dir.get(),
                                 self._get_embaked_name(self.analysis,
                                                        self.topo,
                                                        mass_stripped))
        self._info(f"Writing partial efficiencies into file: {os.getcwd()}/{effi_file}")
        # to store intermediate results
        nevents = []
        entries = ""
        filecount = 0
        # go over all the .root files made by CLA
        for filename in os.listdir(cla_run_dir):
            if filename.startswith("histoOut") and filename.endswith(".root"):
                filecount += 1
                filename = os.path.join(cla_run_dir, filename)
                # get partial efficiencies from each file
                self._info(f"processing #{filecount}: {filename}" )
                tmp_entries, tmp_nevents = self.extract_efficiencies(filename,
                                                                     cutlangfile)
                nevents += tmp_nevents
                entries += tmp_entries
                destdir = os.path.join(self.tmp_dir.get(), os.path.basename(filename))
                self._info(f"found {len(nevents)}/{len(entries)}, move to {destdir}" )
                shutil.move(filename, destdir)
        self._info(f"Nevents: {nevents[:3]}")
        # check that the number of events was the same for all regions
        if len(set(nevents)) > 1:
            self._error("Number of events before selection is not constant in all regions:")
            self._error(f"Numbers of events: {set(nevents)}")
            self._error(f"Using the value: {nevents[0]}")
        if len(nevents) > 0:
            # write efficiencies to .embaked file
            self._add_output_summary ( mass )
            self._msg(f"Writing efficiency values for masses {mass} to file:\n {effi_file}")
            with open(effi_file, "wt") as f:
                f.write(str(mass) + ": {")
                f.write(entries)
                f.write(f"'__t__':'{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}', ")
                nev = nevents[0]
                if nev == int(nev):
                    nev = int(nev)
                f.write(f"'__nevents__':{nev}")
                f.write("}")
            self._msg(f"done writing into {effi_file}")
            ## now that we have an embaked file, mark also the CLA dir as removable
            self.tempFiles.append ( f"{cla_temp_name}" )
            self.removeTempFiles()
            return 0
        else:
            self.error(f"Did not find any events: {nevents}. Filecount {filecount}. Entries: '{entries}'. CLAdir {cla_run_dir}")
            # self.error(f"directory reads {os.listdir(cla_run_dir)}" )
            self.removeTempFiles()
            return -4
    def error ( self, *args ):
        print ( "[cutlangWrapper]", " ".join(map(str,args)) )

    def get_cla_out_filename(self, cla_run_dir, inputname):
        """ Returns the name of CLA output file"""
        outfile = os.path.join(cla_run_dir,
                               "histoOut-" + os.path.basename(inputname).split(".")[0] + ".root")
        self._info(f"Searching for CLA output at:\n{outfile}")
        if os.path.isfile(outfile):
            return outfile
        else:
            self._error("Could not find CLA output file. Aborting.")
            # sys.exit()

    def extract_efficiencies(self, cla_out, cla_file):
        """ Extracts the efficiencies from CutLang output, via uproot or ROOT
            returns:
                entries, nevents tuple:
                        entries -- String containing efficiencies extracted from the cla_out file
                        nevents -- Tuple of numbers of events for each entry.
            :param cla_out:  .root file output of CLA
            :param cla_file:  .adl file specifying CutLang regions
        """
        # first try via ROOT, then uproot
        try:
            tmp_entries, tmp_nevents = self.extract_efficiencies_ROOT(
                                            cla_out, cla_file )
        except Exception as e:
            self._info ( f"ROOT-based extractor failed {e}, using uproot-based extractor!" )
            tmp_entries, tmp_nevents = self.extract_efficiencies_uproot(
                                            cla_out, cla_file )
        # if we wish to compare
        #for i,(x,y) in enumerate ( zip ( tmp_entries, Rtmp_entries ) ):
        #    if x!=y:
        #        print ( f"difference in #{i}/{len(tmp_entries)}:\n" )
        #        print ( f">>{tmp_entries[i-20:i+20]}<<\n >>{Rtmp_entries[i-20:i+20]}<<" )
        #        break
        #with open('/dev/pts/5') as user_tty:
        #    import sys
        #    sys.stdin=user_tty
        #    import IPython
        #    IPython.embed( )
        #print ( tmp_entries == Rtmp_entries )
        #sys.exit()
        return tmp_entries, tmp_nevents

    def extract_efficiencies_ROOT(self, cla_out, cla_file):
        """ Extracts the efficiencies from CutLang output.
            returns:
                entries, nevents tuple:
                        entries -- String containing efficiencies extracted from the cla_out file
                        nevents -- Tuple of numbers of events for each entry.
            :param cla_out:  .root file output of CLA
            :param cla_file:  .adl file specifying CutLang regions
        """
        import ROOT # To parse CutLang output

        # open the ROOT file
        rootFile = ROOT.TFile(cla_out)
        if rootFile is None:
            self._error( f"ROOT Cannot find CutLang results at {cla_out}.")
            return None

        # temporary TH1D structure to write results in
        rootTmp = ROOT.TH1D()
        nevents = []  # list of starting numbers of events
        entries = ""  # efficiency entries for output
        contains_eff = False  # Whether this root file yielded an efficiencies
        ignorelist = {'baseline', 'presel'} & self.filterRegions

        self._debug("ROOT Objects found in CutLang results:")
        self._debug(str([x.ReadObj().GetName() for x in rootFile.GetListOfKeys()]))

        # Traverse all keys in ROOT file
        for x in rootFile.GetListOfKeys():

            x = x.ReadObj()
            if isinstance(x, ROOT.TDirectoryFile):
                # if the region is in ignorelist, move onto another one
                regionName = x.GetName()
                if regionName in ignorelist:
                    continue

                # if there is no cutflow defined in region, move onto another one
                keys = [y.ReadObj().GetName() for y in x.GetListOfKeys()]
                # cutflow ~ the event number histogram
                if "cutflow" not in keys:
                    self._info(f"Cutflow not in objects in {x.GetName()} in {cla_out}")
                    continue

                # copy cutflow object into temp root object and process it
                rootTmp = x.cutflow
                entry = "".join(["'", regionName, "': "])
                s = rootTmp.GetNbinsX()
                if rootTmp[2] == 0:
                    entries += "NaN"
                    nevents.append(0)
                    continue
                # rootTmp[2] == number of all events
                entry += str(rootTmp[(s-1)]/rootTmp[2]) + ', '
                self._debug("ROOT "+entry)
                nevents.append(rootTmp[2])
                entries += entry
                contains_eff = True
                # if the region contains bins, process them
                if "bincounts" in keys:
                    rootTmp = x.bincounts
                    nbins = rootTmp.GetNbinsX()
                    self._info(f"ROOT Found {nbins} bins in {regionName} section.")
                    # set the bins to be excluded from printout
                    if regionName in self.filterBins:
                        filterBinNums = self.filterBins[regionName]
                    else:
                        filterBinNums = []

                    for i in range(nbins+1):
                        # if bin number i is filtered out, skip it
                        if i in filterBinNums:
                            continue
                        bin_name = rootTmp.GetXaxis().GetBinLabel(i)
                        bin_name = "_".join([regionName, bin_name.replace(" ", "_")])
                        bin_name = self._shorten_bin_name(bin_name)
                        entry = "".join(["'", bin_name, "': "])
                        self._debug(f"ROOT bin {bin_name} nevents: {nevents[-1]}.")
                        entry += str(rootTmp[i]/nevents[-1]) + ', '
                        entries += entry
            else:
                self._debug(f"ROOT {x.GetName()} is not a Directory File.")
                self._debug(f"ROOT {x.GetName()} is of type {type(x)}")
            # entry ~ data point to write into efficiency map
        if contains_eff is False:
            self._error(f"ROOT No efficiencies found in file {cla_out}.")
        # print ( f"returning {entries} {nevents}" )
        return entries, nevents

    def extract_efficiencies_uproot(self, cla_out, cla_file):
        """ Extracts the efficiencies from CutLang output, via uproot
            returns:
                entries, nevents tuple:
                        entries -- String containing efficiencies extracted from the cla_out file
                        nevents -- Tuple of numbers of events for each entry.
            :param cla_out:  .root file output of CLA
            :param cla_file:  .adl file specifying CutLang regions
        """
        if not os.path.exists ( cla_out ):
            self._error( f"Cannot find CutLang results at {cla_out}.")
            return None
        import uproot

        rootFile = None
        try:
            # open the ROOT file
            rootFile = uproot.open(cla_out)
        except Exception as e:
            self._error(f"Exception {e}")
            rootFile = None

        if rootFile is None:
            self._error( f"Cannot find CutLang results at {cla_out}." )
            return None

        # temporary TH1D structure to write results in
        # rootTmp = ROOT.TH1D()
        rootTmp = []
        nevents = []  # list of starting numbers of events
        entries = ""  # efficiency entries for output
        contains_eff = False  # Whether this root file yielded an efficiencies
        ignorelist = {'baseline', 'presel'} & self.filterRegions

        self._debug("uproot: Objects found in CutLang results:")
        # self._debug(str([x.ReadObj().GetName() for x in rootFile.GetListOfKeys()]))
        self._debug(str([x for x in rootFile] ) )

        # Traverse all keys in ROOT file
        # for x in rootFile.GetListOfKeys():
        self._info ( f"uproot filterBins {self.filterBins} filterRegions {self.filterRegions}" )
        for name,obj in rootFile.items():
                if name.endswith ( "/bincounts;1" ):
                    self._info(f"Found bins in {name} section.")
                    objname = objname.replace("/bincounts;1","")
                    labels = obj.axes[0].labels()
                    if objname in self.filterBins:
                        filterBinNums = self.filterBins[objname]
                    else:
                        filterBinNums = []
                    v = obj.values()
                    entries += f"'{objname}_': {v[-1]}, "
                    for i,v in enumerate ( v ):
                        if i in filterBinNums:
                            continue
                        bin_name = labels[i]
                        bin_name = "_".join([objname, bin_name.replace(" ", "_")])
                        bin_name = self._shorten_bin_name(bin_name)
                        entry = "".join(["'", bin_name, "': "])
                        self._debug(f"uproot bin no {v} nevents: {nevents[-1]}.")
                        entry += str(v/nevents[-1]) + ', '
                        entries += entry
                    continue
                if not "/cutflow;1" in name:
                    continue
                objname = name.replace("/cutflow;1","")
                if objname in ignorelist:
                    continue
                # copy cutflow object into temp root object and process it
                entry = "".join(["'", objname , "': "])
                v = obj.values()
                s = len ( v )
                entry += str(v[(s-2)]/v[1]) + ', '
                self._debug( f"uproot {entry}" )
                nevents.append(v[1])
                entries += entry
                contains_eff = True
        return entries, nevents

    def pickCutLangFile(self, a_name):
        """ Returns absolute path to ADLLHC Analysis file. If not available raises error.
            :param a_name string Analysis name in standard format (see _standardise_analysis)
                                 e.g. 'CMS_SUS_012_32'
        """
        a_name = a_name.replace("_", "-")
        if self.adl_file != None:
            if "/" in self.adl_file:
                cla_path = os.path.abspath ( self.adl_file )
                #self._msg ( f"for the adl file name, please supply only the file name, not a path like {self.adl_file}" )
                #p = self.adl_file.rfind("/")
                #self.adl_file = self.adl_file[p+1:]
            else:
                cla_path = os.path.join(self.adllhcanalyses, a_name.upper(), self.adl_file )
            if os.path.exists ( cla_path ):
                return os.path.abspath ( cla_path )
            self._error ( f"you specified an adl file {self.adl_file} but I could not find it at {cla_path}. Aborting." )
            sys.exit()
        cla_path = os.path.join(self.adllhcanalyses, a_name.upper(), a_name.upper() + "*.adl")
        files = glob.glob ( cla_path )
        if len(files)>1:
             self._msg ( f"Found several adl files for analysis {a_name}: {files}" )
             self._msg ( f"Please implement a way to deal with this" )
             raise Exception ( f"Found several adl files for analysis {a_name}: {files}" )
        if len(files)==0:
            line = f"found no adl file for analysis {a_name}"
            raise Exception ( line )
        return os.path.abspath ( files[0] )

    @classmethod
    def get_effi_name(cls, mass):
        mass_stripped = str(mass).replace("(", "").replace(")", "")
        return os.path.join(cls.out_dir.get(), cls._get_embaked_name(cls.analyses, cls.topo, mass_stripped))

    def clean(self):
        """ Deletes the output directory
        """
        self._delete_dir(self.base_dir.get())

    def clean_all(self):
        """ Deletes all the directories that might have been made by CutLangWrapper
            Use with care.
        """

        if self._confirmation("This will delete all directories created by running CutLangWrapper.\n"
                              "Proceed?"):
            self.clean()
            self._delete_dir("./CutLang")
            self._delete_dir("./delphes")

    # =========================================================================
    # Private methods
    # =========================================================================

    def _copy_cla(self, where, logfile=None):
        """
        Copy CutLang to temporary directory.
        :param where    copy destination
        :param logfile  file where output of all commands is written
        """
        partlist = ["analysis_core", "BP", "CLA", "runs", "scripts"]
        partlist = map(lambda x: os.path.join(self.cutlanginstall, x), partlist)
        for part in partlist:
            cmd = ['cp', '-r', part, where]
            if execute(cmd, logfile=logfile) != 0:
                return False
        # To prevent redefinitions we have to replace all the shared libraries
        # in the tmp directory with links to the original ones
        core_dir = os.path.join(self.cutlanginstall, 'analysis_core')
        self._msg( f"Linking {core_dir}" )
        for filename in os.listdir(core_dir):
            if filename.endswith(".so"):
                link_name = os.path.join(where, 'analysis_core', filename)
                origin_name = os.path.abspath(os.path.join(core_dir, filename))
                cmd = ['ln', '-sf', origin_name, link_name]
                if execute(cmd, logfile=logfile) != 0:
                    return False
        return True

    def _read_output_summary ( self ):
        """ read the output summary """
        f = open(self.summaryfile, "r+")
        txt = f.read()
        f.close()
        mymasses=eval( txt )
        return mymasses

    def _add_output_summary ( self, mass ):
        """ append to the output summary """
        emass = mass
        try:
            emass = eval(mass)
        except TypeError as e:
            pass
        mymasses = set()
        if os.path.exists(self.summaryfile) and os.stat(self.summaryfile).st_size > 0:
            f = open(self.summaryfile, "r+")
            txt = f.read()
            f.close()
            mymasses = eval ( txt )
        if mass in mymasses:
            return mymasses ## nothing needs to be done
        mymasses.add ( emass )
        mymasses = list(mymasses)
        mymasses.sort()
        mymasses = set(mymasses)
        # we have a lot of processes running at the same time ....
        self.lockSummaryFile()
        f = open(self.summaryfile, "w")
        f.write ( str(mymasses)+"\n" )
        f.close()
        self.unlockSummaryFile()
        return mymasses

    def lockSummaryFile ( self ):
        ctr = 0
        while os.path.exists ( self.summaryfile+".lock" ) and ctr < 5:
            ctr += 1
            time.sleep ( .1 * ctr )
        g = open(self.summaryfile+".lock","wt")
        g.write ( time.asctime()+"\n" )
        g.close()

    def unlockSummaryFile ( self ):
        if os.path.exists( self.summaryfile+".lock"):
            os.unlink ( self.summaryfile+".lock" )

    def _check_summary_file(self, mass):
        """
        Check if the analysis had already been done.
        returns True if the analysis has been run for that mass tuple and rerun == False
                False in all other cases
        """
        if self.rerun:
            self._msg( f"was asked to rerun, not checking CL_output_summary.dat" )
            return False
        emass = mass
        try:
            emass = eval(mass)
        except TypeError as e:
            pass
        # Check if the analysis has been done already
        result = False
        if os.path.exists(self.summaryfile) and os.stat(self.summaryfile).st_size > 0:
            self._msg(f"It seems like there is already a summary file {self.summaryfile}")
            mymasses = self._read_output_summary()
            if emass in mymasses:
                self._msg(f"found mass {mass}. Dont run!")
                result = True
            else:
                self._msg(f"did not find mass {mass}. Run!")
        #else:
        #    self._add_output_summary ( mass )
        return result

    def _confirmation(self, text):
        if self.auto_confirm is True:
            return True
        else:
            self._msg("text")
            confirm = input(text + " ('y'/'n')")
            if confirm == "y" or confirm == "Y" or confirm == "Yes" or confirm == "yes":
                return True
            else:
                return False

    def _decompress(self, name, out_dir):
        basename = ".".join(os.path.basename(name).split(".")[:-1])
        out_name = os.path.join(out_dir, basename)
        self._info(f"Decompressing {name} to {out_name} .")
        with open(out_name, 'wb') as f_out:
            in_f = gzip.open(name, 'rb')
            while True:
                s = in_f.read(self.GZIP_BLOCK)
                if s == b'':
                    break
                f_out.write(s)
            in_f.close()
        ## the _decompressed files should be removed immediately after
        self.tempFiles.append ( out_name )
        return out_name

    def removeTempFiles ( self ):
        """ remove all temp files that we know of """
        if self.keep:
            return
        for t in self.tempFiles:
            if not os.path.exists ( t ):
                continue
            if os.path.isdir ( t ):
                shutil.rmtree ( t )
            else:
                os.unlink ( t )
        self.tempFiles = []

    def _delete_dir(self, f):
        if os.path.exists(f):
            subprocess.getoutput("rm -rf %s" % f)

    def _get_embaked_name(self, analysis, topo, mass):
        retval = "_".join([analysis.lower().replace("-", "_"), topo, "mass", mass])
        retval = ".".join([retval, "embaked"])
        return retval

    def _pick_delphes_card(self):
        if not re.search("ATLAS", self.analysis) is None:
            return os.path.abspath("./templates/delphes_card_ATLAS.tcl")
            # return os.path.abspath("./delphes/cards/delphes_card_ATLAS.tcl")
        elif not re.search("CMS", self.analysis) is None:
            return os.path.abspath("./templates/delphes_card_CMS.tcl")
            # return os.path.abspath("./delphes/cards/delphes_card_CMS.tcl")
        else:
            self._error(f"Could not find a suitable Delphes card for analysis {self.analysis}. Exiting.")
            sys.exit()

    def _standardise_analysis(self, analysis):
        """Takes analysis name and returns it in format like: CMS-SUS-13-024"""
        analysis = analysis.replace("_", "-")
        analysis = analysis.upper()
        analysis = analysis.replace("SUSY", "SUS")
        return analysis

    @staticmethod
    def _info(*msg):
        """Print yellow info message"""
        print( f"{Fore.YELLOW}[CutLangWrapper] {' '.join(msg)}{Fore.RESET}")

    @staticmethod
    def _debug(*msg):
        """Print green debug message."""
        return
        print(f"{Fore.GREEN}[CutLangWrapper] {' '.join(msg)}{Fore.RESET}")

    @staticmethod
    def _msg(*msg):
        """Print normal message"""
        print( f"{Fore.GREEN}[CutLangWrapper] {' '.join(msg)}{Fore.RESET}")

    @staticmethod
    def _error(*msg):
        """Print red error message"""
        string = ' '.join(msg)
        print(f"{Fore.RED}[CutLangWrapper] Error: {string} {Fore.RESET}")

    @staticmethod
    def process_filter_string(string):
        """ Takes comma separated string of regions and returns a tuple
            of set and dictionary (regionList, binList).
        """

        string = string.replace(" ", "")
        filterList = string.split(",")

        binList = {}
        print(str(filterList))
        removedElements = set()
        for x in filterList:
            searchObj = re.search("bin(\d+)", x)
            if searchObj:
                removedElements.add(x)
                regionName = x[:searchObj.start()]
                if regionName in binList:
                    binList[regionName].append(int(searchObj.group(1)))
                else:
                    binList[regionName] = [int(searchObj.group(1))]

        regionList = set(filterList) - set(removedElements)
        return regionList, binList

    def _shorten_bin_name(self, name):
        result = name.replace("[", "").replace("]", "")
        result = name.replace("'", "").replace('"', "")
        result = result.replace("and", "").replace("__", "_")
        result = result.replace("Size(jets)", "njets")
        result = result.replace("Size(bjets)", "nbjets")
        return result

class Directory:
    def __init__(self, dirname, make=False):
        self.dirname = dirname
        if not os.path.exists(self.dirname):
            if make is True:
                if not os.path.exists ( "cutlang_results" ):
                    os.makedirs ( "cutlang_results", exist_ok=True )
                os.makedirs(self.dirname,exist_ok=True)
            else:
                self._error(f"Directory {self.dirname} does not exits. Aborting.")
                sys.exit()
        elif not os.path.isdir(self.dirname):
            self._error(f"Directory {self.dirname} is not a directory. Aborting.")
            sys.exit()

    def get(self):
        return self.dirname


if __name__ == "__main__":
    import argparse
    argparser = argparse.ArgumentParser(description='cutlang runner.')
    argparser.add_argument('-a', '--analyses', help='analyses, comma separated [cms_sus_19_006]',
                           type=str, default="cms_sus_19_006")
    argparser.add_argument('-d', '--hepmcfile', help='hepmcfile to be used as input for Delphes [input.hepmc]',
                           type=str, default="input.hepmc")
    argparser.add_argument('-j', '--njets', help='number of ISR jets [1]',
                           type=int, default=1)
    argparser.add_argument('-t', '--topo', help='topology [T2]',
                           type=str, default="T2")
    argparser.add_argument('-c', '--clean', help='clean all temporary files, then quit',
                           action="store_true")
    argparser.add_argument('-C', '--clean_all', help='clean all temporary files, even results directories, then quit',
                           action="store_true")
    mdefault = "Masses not specified"
    argparser.add_argument('-m', '--mass', help='mass range e.g."(100,110,10)"',
                           type=str, default=mdefault)
    argparser.add_argument('-p', '--nprocesses', help='number of process to run in parallel. 0 means 1 per CPU [1]',
                           type=int, default=1)
    argparser.add_argument('-r', '--rerun', help='force rerun, even if there is a summary file already',
                           action="store_true")
    argparser.add_argument('-f', '--filter', help='Regions and bins to be filtered out, comma separated list. E.g. "SR7, SR5, SR4bin2, SR4bin3"',
                           type=str, default="")
    argparser.add_argument ( '-l', '--list_analyses', help='list all analyses that are found in this ADL installation',
                             action="store_true" )
    args = argparser.parse_args()
    if args.list_analyses:
        cutlang = CutLangWrapper(args.topo, args.njets, args.rerun, args.analyses)
        cutlang.list_analyses()
        sys.exit()
    if args.clean:
        cutlang = CutLangWrapper(args.topo, args.njets, args.rerun, args.analyses)
        cutlang.clean()
        sys.exit()
    if args.clean_all:
        cutlang = CutLangWrapper(args.topo, args.njets, args.rerun, args.analyses)
        cutlang.clean_all()
        sys.exit()

    cutlang = CutLangWrapper(args.topo, args.njets, args.rerun, args.analyses)
    cutlang.run(args.mass, args.hepmcfile)
