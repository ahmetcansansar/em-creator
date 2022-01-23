#!/usr/bin/env python3

"""
.. module:: emCreator
        :synopsis: code that extracts the efficiencies from MadAnalysis,
                   and assembles an eff map.

.. moduleauthor:: Wolfgang Waltenberger <wolfgang.waltenberger@gmail.com>
"""

import os, sys, colorama, subprocess, shutil, time, glob
from datetime import datetime
import bakeryHelpers
        
hasWarned = { "cutlangstats": False }

class emCreator:
    def __init__ ( self, analyses, topo, njets, keep, sqrts, cutlang ):
        """ the efficiency map creator.
        :param keep: if true, keep all files
        :param cutlang: is it a cutlang result
        """
        self.basedir = bakeryHelpers.baseDir()
        self.resultsdir = ( self.basedir + "/ma5results/" ).replace("//","/")
        self.analyses = analyses
        self.topo = topo
        self.njets = njets
        self.keep = keep
        self.sqrts = sqrts
        self.cutlang = cutlang

    def info ( self, *msg ):
        print ( "%s[emCreator] %s%s" % ( colorama.Fore.YELLOW, " ".join ( msg ), \
                   colorama.Fore.RESET ) )

    def debug( self, *msg ):
        pass

    def msg ( self, *msg):
        print ( "[emCreator] %s" % " ".join ( msg ) )

    def error ( self, *msg ):
        print ( "%s[emCreator] %s%s" % ( colorama.Fore.RED, " ".join ( msg ), \
                   colorama.Fore.RESET ) )

    def getCutlangStatistics ( self, ana, SRs ):
        """ obtain nobs, nb, etc from the ADL file
        :param ana: analysis id, e.g. atlas_susy_2016_07
        :param SRs: list of signal regions
        FIXME not yet implemented
        """
        if hasWarned["cutlangstats"] == False:
            self.error ( "getCutlangStatistics not yet implemented!" )
            hasWarned["cutlangstats"]=True
        ret = {}
        for k in SRs:
            if k.startswith("__"):
                continue
            if k in [ ]: # "signal_", "signal" ]:
                continue
            ret[k] = { "nobs": -1, "nb": -1, "deltanb": -1 }
        return ret

    def getStatistics ( self, ana = "atlas_susy_2016_07", SRs = {} ):
        ### obtain nobs, nb, etc from the PAD info files, e.g.
        ### ma5/tools/PAD/Build/SampleAnalyzer/User/Analyzer/atlas_susy_2016_07.info
        if self.cutlang:
            return self.getCutlangStatistics ( ana, SRs )
        import xml.etree.ElementTree as ET
        Dir = "ma5/tools/PAD/Build/SampleAnalyzer/User/Analyzer/"
        filename = "%s/%s.info" % ( Dir, ana )
        if not os.path.exists ( filename ):
            Dir = "ma5/tools/PADForMA5tune/Build/SampleAnalyzer/User/Analyzer/"
            filename = "%s/%s.info" % ( Dir, ana )
        if not os.path.exists ( filename ):
            self.error ( "could not find statistics file for %s" % ana )
        tree = ET.parse( filename )
        root = tree.getroot()
        ret = {}
        for child in root:
            if child.get("type") != "signal":
                continue
            Id = child.get("id" )
            signal={}
            for vk in child:
                if vk.tag in [ "nobs", "nb", "deltanb" ]:
                    signal[vk.tag]=float(vk.text)
            ret[Id]=signal
        return ret

    def getNEvents ( self, masses ):
        fname = bakeryHelpers.safFile ( self.resultsdir, self.topo, masses, self.sqrts )
        if not os.path.exists ( fname ):
            print ( "[emCreator.py] %s does not exist, cannot report correct number of events" % fname )
            return -2
        with open ( fname, "rt" ) as f:
            lines=f.readlines()
            f.close()

        for ctr,line in enumerate(lines):
            if "nevents" in line:
                tokens = lines[ctr+1].split()
                if len(tokens)<3:
                    print ( "[emCreator.py] I get confused with %s, cannot report correct number of events" % fname )
                    return -3
                return int(tokens[2])

        # ma5/ANA_T6WW_1jet.400_375_350/Output/
        return -1

    def cutlangExtract ( self, masses ):
        """ extract the efficiencies from cutlang """
        topo = self.topo
        #summaryfile = f"clsum_{self.topo}_{self.analyses}.dat"
        #if not os.path.exists ( summaryfile ):
        #    return {}, 0.
        effs = {}
        smass = "_".join(map(str,masses))
        fdir = f"cutlang_results/{self.analyses}/ANA_{self.topo}_{self.njets}jet/output/"
        timestamp = os.stat ( fdir ).st_mtime
        toglob = f"{fdir}/*_{smass}.embaked"
        emglob = glob.glob ( toglob )
        if len(emglob)==1:
            with open ( emglob[0], "rt" ) as f:
                timestamp = os.stat ( f ).st_mtime
                txt=f.read()
                p = txt.find(": ")
                D = eval( txt[p+2:] )
                f.close()
                effs[self.analyses]=D
        if len(emglob)==0:
            print ( "[emCreator] trying to extract cutlang for", masses, end=", " )
            print ( f"could not find {toglob}" )
        if len(emglob)>1:
            print ( "[emCreator] trying to extract cutlang for", masses, end=", " )
            print( f"found several files for {toglob}" )
        return effs,timestamp

    def extract ( self, masses ):
        """ extract the efficiencies from MA5 """
        if self.cutlang:
            return self.cutlangExtract ( masses )
        topo = self.topo
        njets = self.njets
        process = "%s_%djet" % ( topo, njets )
        dirname = bakeryHelpers.dirName ( process, masses )
        summaryfile = bakeryHelpers.datFile ( self.resultsdir, topo, masses, \
                                              self.sqrts )
        if not os.path.exists ( summaryfile):
            # self.info ( "could not find ma5 summary file %s. Skipping." % summaryfile )
            ret = {}
            return ret,0.
        timestamp = os.stat ( summaryfile ).st_mtime
        f=open(summaryfile,"r")
        lines=f.readlines()
        f.close()
        effs={}
        for line in lines:
            p=line.find("#")
            if p>=0:
                line=line[:p]
            line=line.strip()
            if len(line)==0:
                continue
            if "control region" in line:
                continue
            line = line.replace("signal region","signal_region")
            line = line.replace("control region ","control_region_")
            line = line.replace("signal region ","signal_region_" )
            line = line.replace("control region","control_region" )
            line = line.replace("150-1","150 -1")
            tokens=line.split()
            if len(tokens) not in [ 7, 8, 10 ]:
                print ( "[emCreator] In file %s: cannot parse ``%s'': got %d tokens, expected 8 or 10. skip it" % ( summaryfile, line[:50], len(tokens) ) )
                print ( "   - %s "  % str(tokens) )
                continue
            if len(tokens)==10:
                dsname,ananame,sr,sig95exp,sig95obs,pp,eff,statunc,systunc,totunc=tokens
            if len(tokens)==8:
            # datasetname analysisname signalregion sig95(exp) sig95(obs) efficiency stat
                dsname,ananame,sr,sig95exp,sig95obs,pp,eff,statunc=tokens
            if len(tokens)==7:
            # datasetname analysisname signalregion sig95(exp) sig95(obs) efficiency stat
                dsname,ananame,sr,sig95exp,pp,eff,statunc=tokens

            eff=float(eff)
            #if eff == 0.:
                # print ( "zero efficiency for", ananame,sr )
            #    continue
            if not ananame in effs:
                effs[ananame]={}
            effs[ananame][sr]=eff
        return effs,timestamp

    def exe ( self, cmd ):
        self.msg ( "now execute: %s" % cmd )
        ret = subprocess.getoutput ( cmd )
        if len(ret)==0:
            return
        # maxLength=60
        maxLength=560
        if len(ret)<maxLength:
            self.msg ( " `- %s" % ret )
            return
        self.msg ( " `- %s" % ( ret[-maxLength:] ) )

def countMG5 ( topo, njets ):
    """ count the number of mg5 directories """
    files = glob.glob ( "mg5results/%s_*.hepmc.gz" % ( topo ) )
    return len(files)

def countRunningMG5 ( topo, njets ):
    """ count the number of ma5 directories """
    files = glob.glob ( "%s_*jet*" % ( topo ) )
    return len(files)

def countRunningCutlang ( topo, njets ):
    """ count the number of cutlang directories """
    files = glob.glob ( f"cutlang_results/*/ANA_{topo}_*jet/temp/{topo}_*.hepmc" )
    return len(files)

def countRunningMA5 ( topo, njets ):
    """ count the number of ma5 directories """
    files = glob.glob ( "ma5_%s_%djet.*" % ( topo, njets) )
    return len(files)

def writeStatsFile ( statsfile : str, stats : dict ):
    """ write stats to statsfile """
    f = open ( statsfile, "w" )
    f.write ( f"# created {time.asctime()}\n" )
    f.write ( "{" )
    for SR,stat in stats.items():
        stat["comment"]=SR ## FIXME might need to be adapted
        f.write ( "'%s': %s,\n" % ( SR, stat ) )
    #    f.write ( "%s\n" % stats )
    f.write ( "}\n" )
    f.close()
    print ( "[emCreator] wrote stats to %s" % statsfile )

def recaster ( cutlang ):
    """ get the name of the recaster """
    ma5orcutlang = "MA5"
    if cutlang:
        ma5orcutlang = "ADL"
    return ma5orcutlang

def embakedFileName ( analysis, topo, cutlang ):
    """ get the file name of the .embaked file 
    :param analysis: e.g. CMS-SUS-16-039
    :param topo: e.g. T2
    :param cutlang: true if cutlang, false if ma5
    """
    ana_smodels = analysis.upper().replace("_","-")
    fname = "embaked/%s.%s.%s.embaked" % (ana_smodels, topo, recaster ( cutlang ) )
    return fname

def massesInEmbakedFile ( masses, analysis, topo, cutlang ):
    """ are the masses in the embaked file? 
    :param masses: e.g. (800,200)
    :param analysis: e.g. CMS-SUS-16-039
    :param topo: e.g. T2
    :param cutlang: true if cutlang, false if ma5
    """
    fname = embakedFileName ( analysis, topo, cutlang )
    if not os.path.exists ( fname ):
        # if we dont even have an embaked file, for sure the masses are not in.
        return False
    with open ( fname, "rt" ) as f:
        lines = f.read()
        f.close()
        D = eval(lines)
        if masses in D.keys():
            return True
    return False

def runForTopo ( topo, njets, masses, analyses, verbose, copy, keep, sqrts, cutlang, 
                 create_stats ):
    """
    :param analyses: analysis, e.g. cms_sus_19_006, singular. lowercase.
    :param keep: keep the cruft files
    :param cutlang: is it a cutlang result?
    :param create_stats: create also stats file
    """
    if masses == "all":
        masses = bakeryHelpers.getListOfMasses ( topo, True, sqrts, cutlang, analyses )
    else:
        masses = bakeryHelpers.parseMasses ( masses )
    if masses == []:
        return 0
    adl_ma5 = "MA5"
    if cutlang:
        adl_ma5 = "ADL"
    creator = emCreator( analyses, topo, njets, keep, sqrts, cutlang )
    effs,tstamps={},{}
    if verbose:
        print ( "[emCreator] topo %s: %d mass points considered" % ( topo, len(masses) ) )
    for m in masses:
        eff,t = creator.extract( m )
        for k,v in eff.items():
            if not k in effs:
                effs[k]={}
                tstamps[k]={}
            effs[k][m]=v
            tstamps[k][m]=t
    seffs = ", ".join(list(effs.keys()))
    if seffs == "":
        seffs = "no analysis"
    seffs_smodels = seffs.upper().replace("_","-")
    nrmg5 = countRunningMG5 ( topo, njets )
    nmg5 = countMG5 ( topo, njets )
    if cutlang:
        nrma5 = countRunningCutlang ( topo, njets )
        if False and nrmg5 == 0 and nmg5 == 0 and nrma5 == 0:
            return 0
        print ( )
        if seffs_smodels != "NO ANALYSIS":
            print ( "[emCreator] For %s%s:%s:%s%s I have efficiencies." % \
                 ( colorama.Fore.RED, seffs_smodels, topo, adl_ma5, colorama.Fore.RESET ) )
        print ( "[emCreator] I see %d mg5 points and %d running mg5 and %d running cutlang jobs." % ( nmg5, nrmg5, nrma5 ) )
    else:
        nrma5 = countRunningMA5 ( topo, njets )
        if False and nrmg5 == 0 and nmg5 == 0 and nrma5 == 0:
            return 0
        print ( )
        if seffs_smodels != "NO ANALYSIS":
           print ( "[emCreator] For %s%s:%s:%s%s I have efficiencies." % \
                 ( colorama.Fore.RED, seffs_smodels, topo, adl_ma5, colorama.Fore.RESET ) )
        print ( "[emCreator] I see %d mg5 points and %d running mg5 and %d running ma5 jobs." % ( nmg5, nrmg5, nrma5 ) )
    ntot = 0
    for ana,values in effs.items():
        if len(values.keys()) == 0:
            continue
        ts = {}
        if ana in tstamps:
            ts = tstamps[ana]
        bakeryHelpers.mkdir ( "embaked/" )
        fname = embakedFileName ( analyses, topo, cutlang )
        print ( "%s[emCreator] baking %s: %d points.%s" % \
                ( colorama.Fore.GREEN, fname, len(values), colorama.Fore.RESET ) )
        ntot += len(values)
        SRs = set()
        for k,v in values.items():
            for sr in v.keys():
                SRs.add(sr)
        f=open(fname,"w")
        f.write ( "# EM-Baked %s. %d points, %d signal regions, %s\n" % \
                   ( time.asctime(), len(values.keys()), len(SRs), recaster ( cutlang ) ) )
        # f.write ( "%s\n" % values )
        f.write ( "{" )
        for k,v in values.items():
            t=0
            if k in ts:
                t = ts[k]
            if t > 0:
                v["__t__"]=datetime.fromtimestamp(t).strftime('%Y-%m-%d_%H:%M:%S')
            else:
                v["__t__"]="?"
            if not cutlang:
                v["__nevents__"]=creator.getNEvents ( k )
            f.write ( "%s: %s, \n" % ( k,v ) )
        f.write ( "}\n" )
        f.close()
        sqrts = 13
        experiment = "CMS"
        if "atlas" in ana.lower():
            experiment = "ATLAS"
        sana = bakeryHelpers.ma5AnaNameToSModelSName ( ana )
        Dirname = "../smodels-database/%dTeV/%s/%s-eff/orig/" % ( sqrts, experiment, sana )
        if not cutlang:
            Dirname = "../smodels-database/%dTeV/%s/%s-ma5/orig/" % ( sqrts, experiment, sana )
        stats = creator.getStatistics ( ana, SRs )
        # print ( "[emCreator] obtained statistics for", ana, "in", fname )

        if copy and not os.path.exists (Dirname):
            Dirname = "../smodels-database/%dTeV/%s/%s-ma5/orig/" % ( sqrts, experiment, sana )
            if cutlang:
                Dirname = "../smodels-database/%dTeV/%s/%s-eff/orig/" % ( sqrts, experiment, sana )
            if not os.path.exists ( Dirname ):
                print ( "[emCreator] asked to copy but %s does not exist" % Dirname )
        if create_stats:
            statsfile = "./statsEM.py"
            writeStatsFile ( statsfile, stats )
        if copy and os.path.exists (Dirname):
            dest = "%s/%s.embaked" % ( Dirname, topo )
            prevN = 0
            if os.path.exists (dest ):
                f=open(dest,"r")
                try:
                    g=eval(f.read())
                    f.close()
                    prevN=len(g.keys())
                except:
                    pass
            print ( "[emCreator] previous number of data points: %d" % prevN )
            print ( "[emCreator] copying embaked to %s" % dest )
            cmd = "cp %s %s" % ( fname, dest )
            subprocess.getoutput ( cmd )
            if create_stats:
                cmd = "cp statsEM.py %s" % ( Dirname )
                o = subprocess.getoutput ( cmd )
                print ( f"[emCreator] {cmd} {o}" )
    return ntot

def getAllCutlangTopos():
    """ get all topos that we find in cutlang """
    dirname="cutlang_results/"
    files = glob.glob ( f"{dirname}/*/ANA_*jet" )
    ret = set()
    for f in files:
        t = f.replace ( dirname, "" ).replace("ANA_","")
        p1 = t.find("/")
        p2 = t.rfind("_")
        t = t[p1+1:p2]
        ret.add(t)
    return ret

def getAllTopos ( cutlang ):
    if cutlang:
        return getAllCutlangTopos ()
    import glob
    dirname="ma5results/"
    files = glob.glob ( "%s/T*.dat" % dirname )
    ret = set()
    for f in files:
        tokens = f.split("_")
        ret.add( tokens[0].replace(dirname,"") )
    ret = list(ret)
    ret.sort()
    return ret

def getCutlangListOfAnalyses():
    Dir = "cutlang_results/"
    dirs = glob.glob ( f"{Dir}*" )
    tokens = set()
    for d in dirs:
        if not "CMS" in d and not "ATLAS" in d:
            continue
        tokens.add ( d.replace ( Dir, "" ) )
    ret=",".join(tokens)
    # ret = "cms_sus_19_005,cms_sus_19_006"
    return ret

def getMA5ListOfAnalyses():
    """ compile list of MA5 analyses """
    ret = "cms_sus_16_048"
    files = glob.glob("ma5results/T*.dat" )
    tokens = set()
    for f in files:
        with open ( f, "rt" ) as handle:
            lines = handle.readlines()
            for l in lines:
                if not "cms" in l and not "atlas" in l:
                    continue
                tmp = l.split( " " )
                for t in tmp:
                    if "cms_" in t or "atlas_" in t:
                        tokens.add ( t )
    ret = ",".join ( tokens )
    return ret

def run ( args ):
    analyses = args.analyses
    #cutlang = args.cutlang
    cutlangs = [ False, True ]
    if args.cutlang:
        cutlangs = [ True ]
    if args.ma5:
        cutlangs = [ False ]
    ntot = 0
    for cutlang in cutlangs:
        if analyses in [ "None", None, "none", "" ]:
            ## retrieve list of analyses
            if cutlang:
                analyses = getCutlangListOfAnalyses()
            else:
                analyses = getMA5ListOfAnalyses()
                
        if cutlang:
           analyses = analyses.replace("_","-").upper()
        if args.topo == "all":
            topos = getAllTopos ( cutlang )
            topos = list(topos)
            topos.sort()
            for topo in topos:
                for ana in analyses.split(","):
                    ntot += runForTopo ( topo, args.njets, args.masses, ana, args.verbose,
                                 args.copy, args.keep, args.sqrts, cutlang, args.stats )
        else:
            for ana in analyses.split(","):
                ntot += runForTopo ( args.topo, args.njets, args.masses, ana, args.verbose,
                             args.copy, args.keep, args.sqrts, cutlang, args.stats )
    print ( f"[emCreator] I found a total of {ntot} points at {time.asctime()}." )
    if os.path.exists ( ".last.summary" ):
        f=open(".last.summary","rt")
        lines = f.readlines()
        f.close()
        print ( f"[emCreator]    last status was {lines[0].strip()}." )
    if args.topo == "all": #  and "," in args.analyses:
        f=open(".last.summary","wt")
        f.write ( f"{ntot} points at {time.asctime()}\n" )
        f.write ( f"t={args.topo}, a={analyses}\n" )
        f.close()

def main():
    import argparse
    argparser = argparse.ArgumentParser(description='efficiency map extractor.')
    argparser.add_argument ( '-j', '--njets', help='number of ISR jets [1]',
                             type=int, default=1 )
    argparser.add_argument ( '-s', '--sqrts', help='sqrts [13]',
                             type=int, default=13 )
    argparser.add_argument ( '-t', '--topo', help='topology, all means all you can find [all]',
                             type=str, default="all" )
    argparser.add_argument ( '-v', '--verbose', help='be verbose',
                             action="store_true" )
    argparser.add_argument ( '-S', '--stats', help='create stats files',
                             action="store_true" )
    argparser.add_argument ( '-c', '--copy', help='copy embaked (and stats if -S) file to smodels-database',
                             action="store_true" )
    argparser.add_argument ( '-k', '--keep', help='keep all cruft files',
                             action="store_true" )
    argparser.add_argument ( '-l', '--cutlang', help='cutlang only results',
                             action="store_true" )
    argparser.add_argument ( '-5', '--ma5', help='ma5 only results',
                             action="store_true" )
    defaultana = "atlas_susy_2016_07"
    defaultana = "cms_sus_19_005,cms_sus_19_006"
    argparser.add_argument ( '-a', '--analyses',
            help='analyses, comma separated. If None, find out yourself [None]',
                             type=str, default=None )
    mdefault = "all"
    argparser.add_argument ( '-m', '--masses', help='mass ranges, comma separated list of tuples. One tuple gives the range for one mass parameter, as (m_first,m_last,delta_m). m_last and delta_m may be ommitted. "all" means, try to find out yourself [%s]' % mdefault,
                             type=str, default=mdefault )
    args = argparser.parse_args()
    run ( args )


if __name__ == "__main__":
    main()
