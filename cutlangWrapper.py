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
import random                  # Used to randomize waiting time after blocking io error
from datetime import datetime  # For timestamp of embaked files
from typing import List        # For type hinting

# 3 party imports
import ROOT                # To parse CutLang output

# local imports
import bakeryHelpers       # For dirnames


class CutLangWrapper:

    GZIP_BLOCK = 1 << 24  # Block to decompress gzipped file, ~ 16 MB

    def __init__(self, topo: str, njets: int, rerun: bool, analyses: str,
                 auto_confirm: bool = True, filterString: str = "",
                 keep: bool = False ) -> None:
        """
        If not already present, clones and builds Delphes, CutLang and ADLLHC Analyses.
        Prepares output directories.

        :param topo:    SMS topology
                        (see https://smodels.github.io/docs/SmsDictionary )
        :param njets:   Number of jets
        :param rerun:   True for rerunning the analyses already done
        :param analyses: Analysis to be done FIXME need to implement in plural!!
                        (see https://smodels.github.io/docs/ListOfAnalyses )
        :param auto_confirm: Proceed with downloads without prompting
        :param keep: keep temporary files for debugging?
        """
        # General vars
        self.njets = njets
        self.keep = False ## keep temporary files?
        self.topo = topo
        if "," in analyses:
            self.error ( "multiple analyses supplied. cannot yet handle this!" )
            sys.exit(-1)
        self.analyses = self._standardise_analysis(analyses)
        self.rerun = rerun
        self.auto_confirm = auto_confirm
        if len(filterString) > 0:
            self.filterRegions, self.filterBins =\
                             CutLangWrapper.process_filter_string(filterString)
        else:
            self.filterRegions, self.filterBins = set(), {}

        # make auxiliary directories
        self.base_dir = Directory(f"cutlang_results/{self.analyses}", make=True)
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
        self.summaryfile = os.path.join("./", "CL_output_summary.dat")

        # ADLLHCAnalysis vars
        self.adllhcanalyses = "./CutLang/ADLLHCanalyses"

        # Delphes vars
        self.delphesinstall = "./delphes/"

        # =====================
        #      Cutlang Init
        # =====================
        # Check if Cutlang dir is present and if not, attempt to clone it from github
        if not os.path.isdir(self.cutlanginstall):
            self._info("cutlang directory missing, download from github?")
            if self._confirmation("Download from github?"):
                args = ['git', 'clone', '-b', 'v.2.9.0', 'https://github.com/unelg/CutLang']
                # args = ['git', 'clone', 'https://github.com/unelg/CutLang']
                self.exe(args, exit_on_fail=True, logfile=self.initlog)
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
            self._info("Compiling CutLang...")
            ncpus = 4
            try:
                from smodels.tools.runtime import nCPUs
                ncpus = nCPUs()
            except ImportError:
                pass
            args = [ 'make', '-j', str(ncpus) ]
            self.exe(args, cwd=compile_path, exit_on_fail=True, logfile=self.initlog)
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
        if len(os.listdir(self.adllhcanalyses)) == 0:
            args = ["rm", "-rf", self.adllhcanalyses]
            self.exe(args)
            args = ["git", "clone", "https://github.com/ADL4HEP/ADLLHCanalyses"]
            self.exe(args, cwd=os.path.dirname(self.adllhcanalyses),
                     exit_on_fail=True, logfile=self.initlog)
        self._info("ADLLHC Analyses initialisation finished.")

        # ====================
        #      Delphes Init
        # ====================
        # Check if Delphes dir is present and if not, attempt to clone it from github
        if not os.path.isdir(self.delphesinstall):
            self._info("Delphes directory missing, download from github?")
            if self._confirmation("Download from github?"):
                args = ['git', 'clone', '-b', '3.5.0', 'https://github.com/delphes/delphes']
                #args = ['git', 'clone', 'https://github.com/delphes/delphes']
                self.exe(args, exit_on_fail=True, logfile=self.initlog)
            else:
                self._error("No Delphes dir. Exiting.")
        # if there is no executable, compile it
        self.delphes_exe = os.path.abspath(self.delphesinstall + "DelphesHepMC2")
        if not os.path.exists(self.delphes_exe):
            self._info("Cannot find delphes installation at %s" % self.delphesinstall)
            compile_path = os.path.abspath(self.delphesinstall)
            # Check for existence of makefile, if not present exit, else make
            makefile_path = os.path.join(compile_path, "Makefile")
            if not os.path.isfile(makefile_path):
                self._error("No executable and no Makefile. Bailin' it.")
                sys.exit()
            self._info("Compiling Delphes...")
            args = ['make']
            self.exe(args, cwd=compile_path, exit_on_fail=True, logfile=self.initlog)
        self._info("Delphes initialised.")
        self._info("Initialisation complete.")

    def error ( self, *msg ):
        print ( "%s[cutlangWrapper] %s%s" % ( colorama.Fore.RED, " ".join ( msg ), \
                   colorama.Fore.RESET ) )

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
            self.exe(args, logfile=logfile)


        # run delphes
        self._debug("Running delphes.")
        args = [self.delphes_exe, delphes_card, delph_out, hepmcfile]
        self.exe(args, logfile=logfile)
        self._debug("Delphes finished.")

        # ======================
        #        CutLang
        # ======================
        # Prepare input paths
        cla_input = os.path.abspath(delph_out)
        cutlangfile = self.pickCutLangFile(self.analyses)

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
        self.exe(cmd, cwd=cla_run_dir, logfile=logfile)
        self._debug("CLA finished.")

        ## now that we ran cutlang, mark the delphes root file as to-be-deleted
        self.tempFiles.append ( delph_out )

        # ====================
        #  Postprocessing
        # ====================
        # efficiency file name
        effi_file = os.path.join(self.out_dir.get(),
                                 self._get_embaked_name(self.analyses,
                                                        self.topo,
                                                        mass_stripped))
        self._info(f"Writing partial efficiencies into file: {effi_file}")
        # to store intermediate results
        nevents = []
        entries = ""
        # go over all the .root files made by CLA
        for filename in os.listdir(cla_run_dir):
            if filename.startswith("histoOut-BP") and filename.endswith(".root"):
                filename = os.path.join(cla_run_dir, filename)
                # get partial efficiencies from each file
                tmp_entries, tmp_nevents = self.extract_efficiencies(filename,
                                                                     cutlangfile)
                nevents += tmp_nevents
                entries += tmp_entries
                shutil.move(filename, os.path.join(self.tmp_dir.get(),
                                                   os.path.basename(filename)))
        self._debug(f"Nevents: {nevents}")
        # check that the number of events was the same for all regions
        if len(set(nevents)) > 1:
            self._error("Number of events before selection is not constant in all regions:")
            self._error(f"Numbers of events: {nevents}")
            self._error(f"Using the value: {nevents[0]}")
        # write efficiencies to .embaked file
        self._add_output_summary ( mass )
        if len(nevents) > 0:
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
            ## now that we have an embaked file, mark also the CLA dir as removable
            self.tempFiles.append ( f"{cla_temp_name}" )
            self.removeTempFiles()
            return 0
        else:
            self.removeTempFiles()
            return -4

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
        """ Extracts the efficiencies from CutLang output.
            returns:
                entries, nevents tuple:
                        entries -- String containing efficiencies extracted from the cla_out file
                        nevents -- Tuple of numbers of events for each entry.
            :param cla_out:  .root file output of CLA
            :param cla_file:  .adl file specifying CutLang regions
        """

        # open the ROOT file
        rootFile = ROOT.TFile(cla_out)
        if rootFile is None:
            self._error("Cannot find CutLang results at {cla_out}.")
            return None

        # temporary TH1D structure to write results in
        rootTmp = ROOT.TH1D()
        nevents = []  # list of starting numbers of events
        entries = ""  # efficiency entries for output
        contains_eff = False  # Whether this root file yielded an efficiencies
        ignorelist = {'baseline', 'presel'} & self.filterRegions

        self._debug("Objects found in CutLang results:")
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
                self._debug(entry)
                nevents.append(rootTmp[2])
                entries += entry
                contains_eff = True
                # if the region contains bins, process them
                if "bincounts" in keys:
                    self._info(f"Found bins in {regionName} section.")
                    rootTmp = x.bincounts
                    # set the bins to be excluded from printout
                    if regionName in self.filterBins:
                        filterBinNums = self.filterBins[regionName]
                    else:
                        filterBinNums = []

                    nbins = rootTmp.GetNbinsX()
                    for i in range(nbins):
                        # if bin number i is filtered out, skip it
                        if i in filterBinNums:
                            continue
                        bin_name = rootTmp.GetXaxis().GetBinLabel(i)
                        bin_name = "_".join([regionName, bin_name.replace(" ", "_")])
                        bin_name = self._shorten_bin_name(bin_name)
                        entry = "".join(["'", bin_name, "': "])
                        self._debug(f"bin no {rootTmp[i]} nevents: {nevents[-1]}.")
                        entry += str(rootTmp[i]/nevents[-1]) + ', '
                        entries += entry
            else:
                self._debug(f"{x.GetName()} is not a Directory File.")
                self._debug(f"{x.GetName()} is of type {type(x)}")
            # entry ~ data point to write into efficiency map
        if contains_eff is False:
            self._error(f"No efficiencies found in file {cla_out}.")
        return entries, nevents

    def pickCutLangFile(self, a_name):
        """ Returns absolute path to ADLLHC Analysis file. If not available raises error.
            :param a_name string Analysis name in standard format (see _standardise_analysis)
                                 e.g. 'CMS_SUS_012_32'
        """
        a_name = a_name.replace("_", "-")
        cla_path = os.path.join(self.adllhcanalyses, a_name.upper(), a_name.upper() + "_CutLang.adl")
        if os.path.isfile(cla_path):
            return os.path.abspath(cla_path)
            self._msg(f"Using CutLang file {cla_path}.")
        else:
            raise Exception(f"No analysis file found for analysis {a_name} found at: \n" + cla_path)


    @classmethod
    def get_effi_name(cls, mass):
        mass_stripped = str(mass).replace("(", "").replace(")", "")
        return os.path.join(cls.out_dir.get(), cls._get_embaked_name(cls.analyses, cls.topo, mass_stripped))

    @staticmethod
    def join_embaked(cls, out_dir, effi_name, time):
        effi_file = os.path.join(out_dir, effi_name)
        with open(effi_file, "w") as f:
            cls.info(f"Writing joint efficiencies into {effi_file}")
            f.write("{ # EM-Baked %s.\n" % time)
            for filename in os.listdir(out_dir):
                if filename.endswith(".embaked"):
                    filename = os.path.join(cls.out_dir, filename)
                    with open(filename, "r") as g:
                        f.write(g.read() + ",\n")
            f.write("}")

    def exe(self, cmd:List[str], logfile:str=None, maxLength=100, cwd:str=None,
            exit_on_fail=False):
        """ execute cmd in shell
        :param maxLength: maximum length of output to be printed,
                          if == -1 then all output will be printed
        :param cmd       List of strings that make the command
                         e.g. ["cp", "foo", "bar"]
        :param logfile   File where command and its output will be written
        :param cwd       Directory where the command should be executed
        :param exit_on_fail  Whether to invoke sys.exit() on nonzero return value
        :return return value of the command
        """
        if cwd is None:
            directory = os.getcwd()
        else:
            directory = cwd
        self._msg(f'exec: {directory} $$ {" ".join(cmd)}')
        ctr=0
        while ctr < 5:
            try:
                proc = subprocess.Popen( cmd, cwd=cwd, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE )
                out, err = proc.communicate()
                print(out.decode('utf-8'))
                print(err.decode('utf-8'))
                proc.wait()
                if logfile is not None:
                    with open(logfile, "a") as log:
                        log.write(f'exec: {directory} $$ {" ".join(cmd)}')
                        log.write(out.decode('utf-8'))
                        log.write(err.decode('utf-8'))
                if not (proc.returncode == 0):
                    self._error(f"Executed process: \n{' '.join(cmd)}\n\nin"
                                f" directory:\n{directory}\n\nproduced an error\n\n"
                                f"value {proc.returncode}.")
                    if exit_on_fail is True:
                        sys.exit()
                return proc.returncode
            except BlockingIOError as e:
                self._error( "ran into blocking io error. wait a bit then try again." )
                time.sleep ( random.uniform(1,10)+ctr*30 )
                ctr += 1
            sys.exit()

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
            if self.exe(cmd, logfile=logfile) != 0:
                return False
        # To prevent redefinitions we have to replace all the shared libraries
        # in the tmp directory with links to the original ones
        core_dir = os.path.join(self.cutlanginstall, 'analysis_core')
        self._error(core_dir)
        for filename in os.listdir(core_dir):
            if filename.endswith(".so"):
                link_name = os.path.join(where, 'analysis_core', filename)
                origin_name = os.path.abspath(os.path.join(core_dir, filename))
                cmd = ['ln', '-sf', origin_name, link_name]
                if self.exe(cmd, logfile=logfile) != 0:
                    return False
        return True

    def _read_output_summary ( self ):
        """ read the output summary """
        f = open(self.summaryfile, "r+")
        Dict=eval(f.read())
        f.close()
        return Dict

    def _add_output_summary ( self, mass ):
        """ append to the output summary """
        Dict={}
        if os.path.exists(self.summaryfile) and os.stat(self.summaryfile).st_size > 0:
            f = open(self.summaryfile, "r+")
            Dict=eval(f.read())
            f.close()
        if self.analyses in Dict and mass in Dict[self.analyses]:
            return Dict ## nothing needs to be done
        anatopo = f"{self.analyses}:{self.topo}"
        if not anatopo in Dict:
            Dict[anatopo]=set()
        emass = mass
        try:
            emass = eval(mass)
        except TypeError as e:
            pass
        if type(Dict[anatopo])==list:
            Dict[anatopo].append ( emass )
        else:
            Dict[anatopo].add ( emass )
        f = open(self.summaryfile, "w")
        f.write ( str(Dict)+"\n" )
        f.close()
        return Dict

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
        anatopo = f"{self.analyses}:{self.topo}"
        if os.path.exists(self.summaryfile) and os.stat(self.summaryfile).st_size > 0:
            self._msg(f"It seems like there is already a summary file {self.summaryfile}")
            Dict = self._read_output_summary()
            for anat,masses in Dict.items():
                if anat != anatopo:
                    continue
                self._msg(f"{anatopo} is in the summary file. Now check for mass")
                if emass in masses:
                    self._msg(f"found mass {mass}. Dont run!")
                    result = True
                else:
                    self._msg(f"did not find mass {mass}. Run!")
        else:
            self._add_output_summary ( mass )
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
        if not re.search("ATLAS", self.analyses) is None:
            return os.path.abspath("./delphes/cards/delphes_card_ATLAS.tcl")
        elif not re.search("CMS", self.analyses) is None:
            return os.path.abspath("./delphes/cards/delphes_card_CMS.tcl")
        else:
            self._error(f"Could not find a suitable Delphes card for analysis {self.analyses}. Exiting.")
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
        print("%s[CutLangWrapper] %s%s" % (colorama.Fore.YELLOW, " ".join(msg),
              colorama.Fore.RESET))

    @staticmethod
    def _debug(*msg):
        """Print green debug message."""
        print("%s[CutLangWrapper] %s%s" % (colorama.Fore.GREEN, " ".join(msg),
              colorama.Fore.RESET))

    @staticmethod
    def _msg(*msg):
        """Print normal message"""
        print("[CutLangWrapper] %s" % " ".join(msg))

    @staticmethod
    def _error(*msg):
        """Print red error message"""
        string = ' '.join(msg)
        print(f"{colorama.Fore.RED}[CutLangWrapper] Error: {string} {colorama.Fore.RESET}")

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
        result = result.replace("and", "").replace("__", "_")
        result = result.replace("Size(jets)", "njets")
        result = result.replace("Size(bjets)", "nbjets")
        return result

class Directory:
    def __init__(self, dirname, make=False):
        self.dirname = dirname
        if not os.path.exists(self.dirname):
            if make is True:
                os.makedirs(self.dirname)
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
    args = argparser.parse_args()
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
