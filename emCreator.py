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

class emCreator:
    def __init__ ( self, analyses, topo, njets, keep, sqrts, cutlang ):
        """ the efficiency map creator.
        :param keep: if true, keep all files
        :param cutlang: is it a cutlang result
        """
        self.basedir = bakeryHelpers.baseDir()
        self.resultsdir = ( self.basedir + "/results/" ).replace("//","/")
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
        sys.exit()

    def getStatistics ( self, ana = "atlas_susy_2016_07" ):
        ### obtain nobs, nb, etc from the PAD info files, e.g.
        ### ma5/tools/PAD/Build/SampleAnalyzer/User/Analyzer/atlas_susy_2016_07.info
        import xml.etree.ElementTree as ET
        Dir = "ma5.template/tools/PAD/Build/SampleAnalyzer/User/Analyzer/"
        filename = "%s/%s.info" % ( Dir, ana )
        if not os.path.exists ( filename ):
            Dir = "ma5.template/tools/PADForMA5tune/Build/SampleAnalyzer/User/Analyzer/"
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
        """ extract the efficiencies from MA5 """
        topo = self.topo
        print ( "[emCreator] trying to extract cutlang for", masses, end=", " )
        summaryfile = "./CL_output_summary.dat"
        timestamp = os.stat ( summaryfile ).st_mtime
        effs = {}
        smass = "_".join(map(str,masses))
        fdir = f"cutlang_results/{self.analyses}/ANA_{self.topo}_{self.njets}jet/output/"
        toglob = f"{fdir}/*_{smass}.embaked"
        emglob = glob.glob ( toglob )
        if len(emglob)==1:
            with open ( emglob[0], "rt" ) as f:
                txt=f.read()
                p = txt.find(": ")
                D = eval( txt[p+2:] )
                f.close()
                effs[self.analyses]=D
            print ( "found!" )
        if len(emglob)==0:
            print ( f"could not find {toglob}" )
        if len(emglob)>1:
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
    """ count the number of mg5 directories """
    files = glob.glob ( "%s_*jet*" % ( topo ) )
    return len(files)

def countRunningMA5 ( topo, njets ):
    """ count the number of ma5 directories """
    files = glob.glob ( "ma5_%s_%djet.*" % ( topo, njets) )
    return len(files)

def runForTopo ( topo, njets, masses, analyses, verbose, copy, keep, sqrts, cutlang ):
    """
    :param keep: keep the cruft files
    :param cutlang: is it a cutlang result?
    """
    print ( "run for", analyses )
    if masses == "all":
        masses = bakeryHelpers.getListOfMasses ( topo, True, sqrts, cutlang, analyses )
    else:
        masses = bakeryHelpers.parseMasses ( masses )
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
    print ( )
    print ( "[emCreator] For %s%s%s I have efficiencies for: %s" % \
             ( colorama.Fore.RED, topo, colorama.Fore.RESET, seffs ) )
    nrmg5 = countRunningMG5 ( topo, njets )
    nmg5 = countMG5 ( topo, njets )
    nrma5 = countRunningMA5 ( topo, njets )
    print ( "[emCreator] I see %d mg5 points and %d running mg5 and %d running ma5 jobs." % ( nmg5, nrmg5, nrma5 ) )
    for ana,values in effs.items():
        if len(values.keys()) == 0:
            continue
        ts = {}
        if ana in tstamps:
            ts = tstamps[ana]
        if not os.path.exists( "embaked/" ):
            os.makedirs ( "embaked" )
        fname = "embaked/%s.%s.embaked" % (ana, topo )
        print ( "%s[emCreator] baking %s: %d points.%s" % \
                ( colorama.Fore.GREEN, fname, len(values), colorama.Fore.RESET ) )
        SRs = set()
        for k,v in values.items():
            for sr in v.keys():
                SRs.add(sr)
        f=open(fname,"w")
        f.write ( "# EM-Baked %s. %d points, %d signal regions.\n" % \
                   ( time.asctime(), len(values.keys()), len(SRs) ) )
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
        Dirname = "../../smodels-database/%dTeV/%s/%s-eff/orig/" % ( sqrts, experiment, sana )
        stats = creator.getStatistics ( ana )
        # print ( "[emCreator] obtained statistics for", ana, "in", fname )

        if copy and not os.path.exists (Dirname):
            print ( "[emCreator] asked to copy but %s does not exist" % Dirname )
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
            statsfile = "%s/statsEM.py" % (Dirname )
            f = open ( statsfile, "w" )
            f.write ( "%s\n" % stats )
            f.close()
            print ( "[emCreator] wrote stats to %s" % statsfile )

def getAllTopos ( ):
    import glob
    dirname="results/"
    files = glob.glob ( "%s/T*.dat" % dirname )
    ret = set()
    for f in files:
        tokens = f.split("_")
        ret.add( tokens[0].replace(dirname,"") )
    ret = list(ret)
    ret.sort()
    return ret

def getAllToposOld ( ):
    import glob
    files = glob.glob ( "T*jet.*" )
    ret = set()
    for f in files:
        tokens = f.split("_")
        ret.add( tokens[0] )
    ret = list(ret)
    ret.sort()
    return ret

def run ( args ):
    if args.cutlang:
        args.analyses = args.analyses.replace("_","-").upper()
    if args.topo == "all":
        for topo in getAllTopos():
            runForTopo ( topo, args.njets, args.masses, args.analyses, args.verbose,
                         args.copy, args.keep, args.sqrts, args.cutlang )
    else:
        runForTopo ( args.topo, args.njets, args.masses, args.analyses, args.verbose,
                     args.copy, args.keep, args.sqrts, args.cutlang )

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
    argparser.add_argument ( '-c', '--copy', help='copy embaked file to smodels-database',
                             action="store_true" )
    argparser.add_argument ( '-k', '--keep', help='keep all cruft files',
                             action="store_true" )
    argparser.add_argument ( '-l', '--cutlang', help='are these cutlang results?',
                             action="store_true" )
    defaultana = "atlas_susy_2016_07"
    defaultana = "cms_sus_19_006"
    argparser.add_argument ( '-a', '--analyses',
            help='analyses, comma separated [%s]' % defaultana,
                             type=str, default=defaultana )
    mdefault = "all"
    argparser.add_argument ( '-m', '--masses', help='mass ranges, comma separated list of tuples. One tuple gives the range for one mass parameter, as (m_first,m_last,delta_m). m_last and delta_m may be ommitted. "all" means, try to find out yourself [%s]' % mdefault,
                             type=str, default=mdefault )
    args = argparser.parse_args()
    run ( args )


if __name__ == "__main__":
    main()
