#!/usr/bin/env python3

"""
.. module:: helpers
        :synopsis: little helper snippets for the bakery.

.. moduleauthor:: Wolfgang Waltenberger <wolfgang.waltenberger@gmail.com>
"""

import numpy, sys, os, time, subprocess, glob
from os import PathLike
from typing import List, Union
sys.path.insert(0,"../../smodels" )

def nCPUs():
    """ obtain the number of CPU cores on the machine, for several
        platforms and python versions. """
    try:
        from smodels.tools.runtime import nCPUs as smodelsNCPUs
        return smodelsNCPUs()
    except ImportError:
        pass
    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except ImportError:
        pass
    try:
        import psutil
        return psutil.NUM_CPUS
    except ImportError:
        pass
    try:
        import os
        res = int(os.sysconf('SC_NPROCESSORS_ONLN'))
        if res>0: return res
    except ImportError:
        pass
    return None

def yesno ( boolean : bool ) -> str:
    if boolean:
        return "yes"
    return "no"

def mkdir ( dirname : PathLike ):
    if not os.path.exists ( dirname ):
        os.mkdir ( dirname )

def getAge ( f : PathLike ) -> float:
    """ get the age of file in hours. age goes by last modification """
    if not os.path.exists ( f ):
        return 0.
    t0 = time.time()
    mt = os.stat ( f ).st_mtime
    dt = ( t0 - mt ) / 60. / 60. ## hours
    return dt

def safFile ( dirname : PathLike, topo : str, masses, sqrts ) -> str:
    """ return saf file name """
    smass = "_".join ( map ( str, masses ) )
    ret = "%s/%s_%s.%d.saf" % ( dirname, topo, smass, sqrts )
    ret = ret.replace("//","/")
    return ret

def datFile ( dirname, topo, masses, sqrts ):
    """ return dat file name """
    smass = "_".join ( map ( str, masses ) )
    ret = "%s/%s_%s.%d.dat" % ( dirname, topo, smass, sqrts )
    ret = ret.replace("//","/")
    return ret

def isAssociateProduction ( topo ):
    """ return true if topo is associate squark gluino production
    :param topo: str, e.g. TGQ
    """
    if topo in [ "TGQ", "T3GQ", "T5GQ" ]:
        return True
    if topo in [ "TChiWZ", "TChiWZoff", "THigWZ", "THigWZoff", "TChiWH", "TChiWHoff", \
                 "THigWH", "THigWHoff" ]:
        return True
    return False

def baseDir():
    """ our basedir """
    conffile = "baking.conf"
    if os.path.exists ( conffile ):
        with open ( conffile, "rt" ) as f:
            ret = f.read()
        ret = ret.strip()
        return ret
    # ret = "/scratch-cbe/users/wolfgan.waltenberger/git/em-creator/"
    subdir = "git/em-creator"
    ret = "~/%s/" % subdir
    ret = os.path.expanduser ( ret )
    if ret.count ( subdir ) == 2:
        ret = ret.replace(subdir,"",1)
    while ret.find("//")>0:
        ret = ret.replace("//","/")
    return ret

def tempDir():
    """ our temp dir """
    ret = baseDir()+"/temp/"
    while ret.find("//")>0:
        ret = ret.replace("//","/")
    if not os.path.exists ( ret ):
        os.mkdir ( ret )
    return ret

def dirName ( process, masses, basedir=None ):
    """ the name of the directory of one process + masses
    :param process: e.g. T2_1jet
    :param masses: tuple or list of masses, e.g. (1000, 800)
    """
    filename = process + "." + "_".join(map(str,masses))
    if basedir == None:
        return filename
    return basedir + "/" + filename

def parseMasses ( massstring, mingap1=None, maxgap1=None,
                  mingap2=None, maxgap2=None, mingap13=None, maxgap13=None ):
    """ parse the mass string, e.g. (500,510,10),(100,110,10). keywords like "half" or "same" are accepted.
    :param mingap1: min mass gap between first and second particle, ignore if None.
                    this is meant to force onshellness or a mass hierarchy
    :param maxgap1: max mass gap between second and third particle, ignore if None.
                    this is meant to force offshellness
    :param mingap2: min mass gap between second and third particle, ignore if None.
                    this is meant to force onshellness or a mass hierarchy
    :param maxgap2: max mass gap between second and third particle, ignore if None.
                    this is meant to force offshellness
    :param mingap13: min mass gap between second and third particle, ignore if None.
                    this is meant to force onshellness or a mass hierarchy
    :param maxgap2: max mass gap between first and third particle, ignore if None.
                    this is meant to force offshellness
    :returns: a list of all model points. E.g. [ (500,100),(510,100),(500,110),(510,110)].
    """
    try:
        masses = eval ( massstring )
    except NameError as e:
        masses = ""
    if type(masses) not in [ list, tuple ] or len(masses)<2:
        mdefault = "(500,510,10),(100,110,10)"
        print ( "Error: masses need to be given as e.g. %s (you will need to put it under parentheses)" % mdefault )
        sys.exit()
    lists=[]
    for ctr,mtuple in enumerate(masses): ## tuple by tuple
        tmp=[]
        if type(mtuple) in [ str ]: ## descriptive strings
            if mtuple == "half" and ctr == 1:
                tmp.append ( mtuple )
                lists.append ( tuple(tmp) )
                continue
            elif mtuple == "same" and ctr == 1:
                tmp.append ( mtuple )
                lists.append ( tuple(tmp) )
                continue
            elif any(f"M0+{i}" in mtuple for i in range(5, 50, 1)) and ctr == 2:
                tmp.append ( mtuple )
                lists.append ( tuple(tmp) )
                continue
            else:
                print ( "error: i know only 'half' or 'same' for a string, and only in middle position. the only exception is 'M0+nb' in the third position when we have 4 mass tuples with nb in range(5,50,1) and M0 is the mass of the LSP, this can't be used with 'half' though" )
                sys.exit()
        if type(mtuple) in [ int, float ]:
            tmp.append ( mtuple )
            lists.append ( tuple(tmp) )
            continue
        if len(mtuple) == 1:
            tmp.append ( mtuple[0] )
            continue
        if len(mtuple) == 2:
            mtuple = ( mtuple[0], mtuple[1], 10 )
        for i in numpy.arange(mtuple[0],mtuple[1],mtuple[2] ):
            tmp.append ( i )
        lists.append ( tuple(tmp) )
    # mesh = numpy.meshgrid ( *lists )
    ret = []
    if len(lists[1]) == 0:
        print ( "[bakeryHelpers] no daughter masses found. you sure you specified a meaningful mass array?" )
        sys.exit(-1)
    if lists[1][0]=="half":
        for x  in lists[0]:
            for z in lists[2]:
                y=int(.5*x+.5*z)
                ret.append ( (int(x),y,int(z)) )
   # elif lists[1][0]=="same":
   #     for x  in lists[0]:
   #         for z in lists[2]:
   #             ret.append ( (int(x),int(x),int(z)) )
   # elif len(lists)==2:
   #     for x in range ( len(lists[0] ) ):
   #         for y in range ( len(lists[1]) ):
   #             ret.append ( (int(lists[0][x]),int(lists[1][y])) )
   # elif len(lists)==3:
   #     for x in range ( len(lists[0] ) ):
   #         for y in range ( len(lists[1]) ):
   #             for z in range ( len(lists[2]) ):
   #                 ret.append ( (int(lists[0][x]),int(lists[1][y]),int(lists[2][z])) )
    elif lists[1][0]=="same" and len(lists)<4:
        for x  in lists[0]:
            for z in lists[2]:
                ret.append ( (int(x),int(x),int(z)) )
    elif lists[1][0]=="same" and not isinstance(lists[2][0], str) and len(lists)==4:
        for x  in lists[0]:
            for z in lists[2]:
                for k in lists[3]:
                    ret.append ( (int(x),int(x),int(z),int(k)) )
    elif lists[1][0]=="same" and any(f"M0+{i}" in lists[2][0] for i in range(5, 50, 1)) and len(lists)==4:
        substrings = lists[2][0].split("+")
        for x  in lists[0]:
                for k in lists[3]:
                    ret.append ( (int(x),int(x),int(k)+int(substrings[1]),int(k)) )
    elif len(lists)==2:
        for x in range ( len(lists[0] ) ):
            for y in range ( len(lists[1]) ):
                ret.append ( (int(lists[0][x]),int(lists[1][y])) )
    elif len(lists)==3:
        for x in range ( len(lists[0] ) ):
            for y in range ( len(lists[1]) ):
                for z in range ( len(lists[2]) ):
                    ret.append ( (int(lists[0][x]),int(lists[1][y]),int(lists[2][z])) )
    elif len(lists)==4 and not isinstance(lists[2][0], str):
        for x in range ( len(lists[0] ) ):
            for y in range ( len(lists[1]) ):
                for z in range ( len(lists[2]) ):
                    for k in range ( len(lists[3]) ):
                        ret.append ( (int(lists[0][x]),int(lists[1][y]),int(lists[2][z]),int(lists[3][k])) )
    elif len(lists)==4 and any(f"M0+{i}" in lists[2][0] for i in range(5, 50, 1)):
        substrings = lists[2][0].split("+")
        for x in range ( len(lists[0] ) ):
            for y in range ( len(lists[1]) ):
                    for k in range ( len(lists[3]) ):
                        ret.append ( (int(lists[0][x]),int(lists[1][y]),int(lists[3][k])+int(substrings[1]),int(lists[3][k])) )
    ret = filterForGap ( ret, mingap1, True, [0,1] )
    ret = filterForGap ( ret, mingap2, True, [1,2] )
    ret = filterForGap ( ret, mingap13, True, [0,2] )
    ret = filterForGap ( ret, maxgap1, False, [0,1] )
    ret = filterForGap ( ret, maxgap2, False, [1,2] )
    ret = filterForGap ( ret, maxgap13, False, [0,2] )
    return ret

def filterForGap ( masses, gap, isMin=True, indices=[0,1] ):
    """ filter out tuples for which gap is not met
        between <indices> particles
    :param isMin: if True, filter out too low gaps, if False,
                  filter out too high gaps
    """
    if gap == None:
        return masses
    if len(masses)==0:
        print ( f"[bakeryHelpers] empty mass list, check your constraints on the masses!" )
        sys.exit(-1)
    if len(masses[0])<=max(indices): ## not enough masses
        return masses
    ret = []
    for t in masses:
        if isMin and t[ indices[0] ] > t[ indices[1] ]+  gap:
            ret.append ( t )
        if not isMin and t[ indices[0] ] < t[ indices[1] ]+ gap:
            ret.append ( t )
    return ret

def ma5AnaNameToSModelSName ( name ):
    """ translate an analysis name from MA5 naming to
        SModelS naming (atlas -> ATLAS, etc) """
    name = name.replace("atlas","ATLAS")
    name = name.replace("cms","CMS")
    name = name.replace("susy","SUSY")
    name = name.replace("sus","SUS")
    name = name.replace("_","-")
    return name

def cm2AnaNameToSModelSName ( name : str ) -> str:
    """ translate an analysis name from checkmate2 naming to
        SModelS naming (looking up arxiv ids) """
    if "," in name:
        names = name.split(",")
        allnames = [ self.cm2AnaNameToSModelSName(n) for n in names ]
        return ",".join(allnames)
    transD = loadCM2DictionaryFile()
    if name in transD.keys():
        return transD[name]
    f = name
    if "sus" in f or "exo" in f or "smp" in f or "conf" in f or "higg" in f:
        f = f.upper().replace("_","-")
    return f

def sModelsName2cm2AnaName ( name : str ) -> str:
    """ translate an analysis name from SModelS naming to
        checkmate2 naming (looking up arxiv ids) """
    if "," in name:
        names = name.split(",")
        allnames = [ self.sModelsName2cm2AnaName(n) for n in names ]
        return ",".join(allnames)
    transD = loadCM2DictionaryFile()
    inverted = { v:k for k,v in transD.items() }
    """ additional entries, hand-written """
    inverted["ATLAS-SUSY-2018-22"] = 'atlas_2010_14293'
    if name in inverted.keys():
        return inverted[name]
    mname = name.upper().replace("_","-")
    if mname in inverted.keys():
        return inverted[mname]
    f = name
    if "SUS" in f or "EXO" in f or "SMP" in f or "CONF" in f or "HIGG" in f:
        f = f.lower().replace("-","_")
    return f

def listAnalysesCutLang( ):
    """ list the analyses that are available in cutlang """
    dirname = "CutLang/ADLLHCanalyses/"
    files = glob.glob ( "%s*" % dirname )
    print ( "List of ADL analyses:" )
    print ( "=====================" )
    for f in files:
        f = f.replace(dirname,"")
        if "README" in f:
            continue
        print ( f )

def listAnalyses ( cutlang : bool, checkmate : bool ):
    """ list the analyses that are available in MA5 or cutlang """
    if cutlang:
        listAnalysesCutLang( )
    elif checkmate:
        listAnalysesCheckMATE( )
    else:
        listAnalysesMA5( )

def listAnalysesMA5( ):
    """ list the analyses that are available in MA5 """
    import glob
    # dname = "ma5/tools/PAD/Build/"
    dn = [ "ma5/tools/PAD/Build/SampleAnalyzer/User/Analyzer/",
           "ma5/tools/PADForMA5tune/Build/SampleAnalyzer/User/Analyzer/" ]
    # print ( "[bakeryHelpers] searching for analyses in %s" % dname )
    files = []
    for d in dn:
        files += glob.glob ( "%s/*.cpp" % d )
    files = list ( set ( files ) )
    files.sort()
    print ( "List of MA5 analyses:" )
    print ( "=====================" )
    for f in files:
        f = f.replace(".saf","").replace(".cpp","")
        for d in dn:
            f = f.replace(d,"")
        print  ( "  %s" % f )

def loadCM2DictionaryFile():
    """ load the checkmate2 <-> SModelS analyses names dictionary """
    if not os.path.exists ( "cm2names.dict" ):
        return {}
    f=open("cm2names.dict")
    D=eval(f.read())
    f.close()
    return D

def listAnalysesCheckMATE( ):
    """ list the analyses that are available in CheckMATE """
    import glob
    path = "cm2/checkmate2/tools/analysis/include/analyses/"
    files = glob.glob ( f"{path}/*/*.h" )
    files = list ( set ( files ) )
    files.sort()
    transD = loadCM2DictionaryFile()
    print ( "List of cm2 analyses:" )
    print ( "=====================" )
    cleaned = {}
    cm2Names = {}
    for f in files:
        f = f.replace(".h","")
        f = f.replace( path, "" )
        p = f.find("/")
        f = f[p+1:]
        nr = f.lower().replace("atlas","").replace("cms","")
        nr = nr.replace("phys","").replace("conf","").replace("exo","")
        nr = nr.replace( "higg", "" ).replace ("pas","").replace("pub_","")
        nr = nr.replace("_","").replace("smp","").replace("susy","")
        nr = nr.replace("atl","").replace("sus","").replace("-","")
        newf = cm2AnaNameToSModelSName ( f )
        cm2Names[nr] = f
        cleaned[nr]=newf
    cleanedkeys = list ( cleaned.keys() )
    cleanedkeys.sort()
    import colorama
    for k in cleanedkeys:
        cName = cleaned[k]
        oldName = ""
        if cm2Names[k] != cName:
            oldName = " ("+cm2Names[k]+")"
        col,res = "", ""
        if "SUS" in cName or "EXO" in cName:
            col,res = colorama.Fore.GREEN, colorama.Fore.RESET
        if "atlas" in cName:
            col,res = colorama.Fore.RED, colorama.Fore.RESET
        print  ( f"{col} * {cName}{res}{oldName}" )

def nJobs ( nproc, npoints ):
    """ determine the number of jobs we should run, given nproc is
        the user's input for number of processes, and npoints is the number
        of points to be processed. """
    ret = nproc
    if ret < 1:
        ret = nCPUs() + ret
    if ret > npoints:
        ret = npoints
    return ret

def getListOfCutlangMasses( topo, sqrts=13, ana=None ):
    """ get a list of the masses of an cutlang scan.
    :param topo: e.g. T1
    :param sqrts: sqrt(s) in tev
    """

    ret=[]
    sana = "*"
    if ana != None:
        sana = ana.replace("_","-").upper()
        sana += "*"
    pattern = f"cutlang_results/{sana}/ANA_{topo}_*/output/*embaked"
    files = glob.glob( pattern )
    for f in files:
        fname = f.replace(".embaked","")
        p = f.rfind("mass_")
        fname = fname[p+5:]
        tokens = fname.split("_")
        tokens = tuple ( map ( int, tokens ) )
        if not tokens in ret:
            ret.append ( tokens )
    return ret

def getListOfMasses(topo, postMA5=False, sqrts=13, recaster=[], ana=None ):
    """ get a list of the masses of an mg5 scan. to be used for e.g. ma5.
    :param postMA5: query the ma5 output, not mg5 output.
    :param recaster: which recaster do we consider
    :param ana: analysis, if None, then all analyses
    """
    if "adl" in recaster:
        return getListOfCutlangMasses ( topo, sqrts, ana )
    if "MA5" in recaster:
        return getListOfMA5Masses ( topo, sqrts, ana )
    if "cm2" in recaster:
        return getListOfCm2Masses ( topo, sqrts, ana )

def createSlurmLink():
    """ simple convenience method to create a symlink to slurm.py """
    for f in [ "slurm.py", "cancel_jobs.py" ]:
        if not os.path.exists ( f ):
            if os.path.exists ( f"/users/wolfgan.waltenberger/{f}" ):
                cmd = f"ln -s /users/wolfgan.waltenberger/{f} ."
                subprocess.getoutput ( cmd )

def getListOfMA5Masses ( topo, sqrts, ana ):
    import glob
    ret=[]
    # fname = "%s_%djet.*" % ( topo, njets )
    dirname = "mg5results/"
    extension = "%d.hepmc.gz" % sqrts
    if postMA5:
        dirname = "ma5results/"
        extension = "dat"
        fname="%s/%s_*.%s" % ( dirname, topo, extension )
        files = glob.glob( fname )
        for f in files:
            with open ( f ) as handle:
                txt= handle.read()
                if not ana in txt:
                    continue
            f = f.replace( dirname, "" )
            f = f.replace( topo+"_", "" )
            f = f.replace( "."+extension, "" )
            p1 = f.find(".")
            f = f[:p1]
            masses = tuple(map(int,map(float,f.split("_"))))
            ret.append ( masses )
        return ret
    fname="%s/%s_*.%s" % ( dirname, topo, extension )
    files = glob.glob( fname )
    for f in files:
        f = f.replace( dirname, "" )
        f = f.replace( topo+"_", "" )
        f = f.replace( "."+extension, "" )
        p1 = f.find(".")
        f = f[:p1]
        masses = tuple(map(int,map(float,f.split("_"))))
        ret.append ( masses )
    return ret

def getListOfCm2Masses ( topo, sqrts, ana ):
    """ FIXME need to get list of cm2 masses, from cm2results.
    for now lets just list the ones in the embaked files """
    ret = []
    return ret

def nRequiredMasses(topo):
    """ find out how many masses a topology requires """
    M=set()
    with open("slha/%s_template.slha" % topo, "r" ) as f:
        for line in f.readlines():
            if not "M" in line:
                continue
            p = line.find("M")
            num=line[p+1]
            if num not in list(map(str,range(6))):
                continue
            M.add(num)
    return len(M)

def clean ():
    """ do the usual cleaning, but consider only files older than 2 hrs """
    t = tempDir()
    b = baseDir()
    files = []
    for i in [ "mg5cmd*", "mg5proc*", "tmp*slha", "run*card" ]:
        pattern = "%s/%s" % ( t, i ) 
        files += glob.glob ( pattern )
    for i in [ "recast*", "ma5cmd*" ]:
        pattern = "%s/ma5/%s" % ( b, i )
        files += glob.glob ( pattern )
    for i in [ "ma5_T*" ]:
        pattern = "%s/%s" % ( b, i )
        files += glob.glob ( pattern )
    for i in [ "T*jet.*" ]:
        pattern = "%s/%s" % ( b, i )
        files += glob.glob ( pattern )
    files += glob.glob ( "%s/.lock*" % b )
    files += glob.glob ( "%s/../clip/_B*sh" % b )
    files += glob.glob ( "/users/wolfgan.waltenberger/B*sh" )
    files += glob.glob ( "/scratch-cbe/users/wolfgan.waltenberger/outputs/slurm*out" )
    cleaned = []
    for f in files:
        dt = getAge ( f )
        if dt < 5.:
            continue
        subprocess.getoutput ( "rm -rf %s" % f )
        cleaned.append ( f )
    print ( "Cleaned %d temporary files" % len(cleaned) )
    checkEventFiles()

def checkEventFiles():
    """ look at the event files, remove all that are old and cannot be opened """
    files = glob.glob("mg5results/T*hepmc.gz")
    for f in files:
        dt = getAge ( f )
        if dt < 5.:
            continue
        subprocess.getoutput ( "rm %s" % f )
        print ( "%s: %.2fh" % ( f, dt ) )

def cleanAll():
    clean()
    b = baseDir()
    t = tempDir()
    files = []
    files += glob.glob ( "%s/*" % t )
    files += glob.glob ( "%s/T*jet*" % b )
    files += glob.glob ( "%s/ma5_T*jet*" % b )
    for i in [ "mg5cmd*", "mg5proc*", "tmp*slha", "run*card" ]:
        files += glob.glob ( "%s/%s" % ( t, i ) )
    for i in [ "recast*", "ma5cmd*" ]:
        files += glob.glob ( "%s/ma5/%s" % ( b, i ) )
    files += glob.glob ( "%s/.lock*" % b )
    files += glob.glob ( "%s/../clip/_B*sh" % b )
    files += glob.glob ( "/users/wolfgan.waltenberger/B*sh" )
    files += glob.glob ( "/scratch-cbe/users/wolfgan.waltenberger/outputs/slurm*out" )
    cleaned = []
    for f in files:
        dt = getAge ( f )
        #if dt < 0.:
        #    continue
        subprocess.getoutput ( "rm -rf %s" % f )
        cleaned.append ( f )
    print ( "Cleaned %d temporary files" % len(cleaned) )

def rmLocksOlderThan ( hours=8 ):
    """ remove all locks older than <hours> """
    files = glob.glob ( ".lock*" )
    t = time.time()
    for f in files:
        try:
            ts = os.stat(f).st_mtime
            dt = ( t - ts ) / 60. / 60.
            if dt > hours:
                self.msg ( "removing old lock %s [%d hrs old]" % ( f, int(dt) ) )
                subprocess.getoutput ( "rm -f %s" % f )
        except:
            pass

def nCPUs():
    """ obtain the number of *available* CPU cores on the machine, for several
        platforms and python versions. """
    try:
        # next few lines taken from
        # https://stackoverflow.comhttps//stackoverflow.com/questions/1006289/how-to-find-out-the-number-of-cpus-using-python/questions/1006289/how-to-find-out-the-number-of-cpus-using-python
        import re
        with open('/proc/self/status') as f:
            m = re.search(r'(?m)^Cpus_allowed:\s*(.*)$', f.read())
        if m:
            res = bin(int(m.group(1).replace(',', ''), 16)).count('1')
            if res > 0:
                return res
    except IOError:
        pass


def execute( cmd:List[str], logfile:str=None, maxLength=100, cwd:str=None,
             exit_on_fail=False ):
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
    shell=False
    scmd = " ".join(cmd)
    if type(cmd)==str:
        shell=True
        scmd=cmd
    if cwd is None:
        directory = os.getcwd()
    else:
        directory = cwd
    print(f'[helpers] exec: {directory} $$ {scmd}')
    ctr=0
    while ctr < 5:
        try:
            proc = subprocess.Popen( cmd, cwd=cwd, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, shell=shell )
            for c in iter(lambda: proc.stdout.read(1), b""):
                sys.stdout.buffer.write(c)
            #    # f.buffer.write(c)
            #out, err = proc.communicate()
            #print(out.decode('utf-8'))
            #print(err.decode('utf-8'))
            proc.wait()
            if logfile is not None:
                with open(logfile, "a") as log:
                    log.write(f'exec: {directory} $$ {" ".join(cmd)}')
            if not (proc.returncode == 0):
                print(f"[helpers] Executed process: \n{' '.join(cmd)}\n\nin"
                            f" directory:\n{directory}\n\nproduced an error\n\n"
                            f"value {proc.returncode}.")
                if exit_on_fail is True:
                    sys.exit()
            return proc.returncode
        except BlockingIOError as e:
            print( "[helpers] ran into blocking io error. wait a bit then try again." )
            time.sleep ( random.uniform(1,10)+ctr*30 )
            ctr += 1
        sys.exit()

def checkDelphesInstall( installdir : PathLike = "delphes" ) -> bool:
    """ check if we have a functioning delphes installation at 
    installdir 
    :returns: True, if all is ok
    """
    if not os.path.isdir( installdir ):
        print("[delphesInstaller] Delphes directory missing, download from github!")
        if True: # self._confirmation("Download from github?"):
            args = ['git', 'clone', '-b', '3.5.0', 'https://github.com/delphes/delphes']
            #args = ['git', 'clone', 'https://github.com/delphes/delphes']
            execute(args, exit_on_fail=True)
            args = [ 'cp', 'templates/delphes_card_CMS.tcl', 'delphes/cards/' ]
            execute(args, exit_on_fail=True)
        else:
            print("[delphesInstaller] ERROR: No Delphes dir. Exiting.")
    # if there is no executable, compile it
    delphes_exe = os.path.abspath( installdir + "/DelphesHepMC2")
    if not os.path.exists( delphes_exe):
        print(f"[delphesInstaller] Cannot find delphes installation at {delphes_exe}" )
        compile_path = os.path.abspath(installdir)
        # Check for existence of makefile, if not present exit, else make
        makefile_path = os.path.join(compile_path, "Makefile")
        if not os.path.isfile(makefile_path):
            print("[delphesInstaller] No executable and no Makefile. Bailing out.")
            sys.exit()
        print("[delphesInstaller] Compiling Delphes...")
        args = ['make']
        execute(args, cwd=compile_path, exit_on_fail=True )
    print("[delphesInstaller] Delphes initialised.")
    print("[delphesInstaller] Initialisation complete.")
    return delphes_exe

if __name__ == "__main__":
    import argparse
    argparser = argparse.ArgumentParser(description='show the masses for a given mass string')
    argparser.add_argument ( '-m', '--masses', help='masses',
                             type=str, default=None )
    argparser.add_argument ( '--maxgap2', help='maximum mass gap between second and third, to force offshell [None]',
                             type=float, default=None )
    argparser.add_argument ( '--mingap1', help='minimum mass gap between first and second, to force onshell or a mass hierarchy [None]',
                             type=float, default=None )
    argparser.add_argument ( '--mingap2', help='minimum mass gap between second and third, to force onshell or a mass hierarchy [0.]',
                             type=float, default=0. )
    argparser.add_argument ( '--mingap13', help='minimum mass gap between first and third, to force onshell or a mass hierarchy [0.]',
                             type=float, default=None )
    argparser.add_argument ( '--maxgap13', help='maximum mass gap between first and third, to force offshell [None]',
                             type=float, default=None )
    argparser.add_argument ( '--maxgap1', help='maximum mass gap between first and second, to force offshell [None]',
                             type=float, default=None )
    args = argparser.parse_args()
    masses=parseMasses ( args.masses, mingap1 = args.mingap1, maxgap1 = args.maxgap1,
           mingap2 = args.mingap2, maxgap2 = args.maxgap2, mingap13 = args.mingap13,
           maxgap13 = args.maxgap13 ) 
    print ( f"the input will produce {len(masses)} mass vectors:" )
    for c,m in enumerate ( masses ):
        print ( f"    {m}", end="" )
        if c%3==0:
            print()
        if c  == 30:
            print ( " ..... " )
            break
    print()
