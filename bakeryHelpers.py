#!/usr/bin/env python3

"""
.. module:: helpers
        :synopsis: little helper snippets for the bakery.

.. moduleauthor:: Wolfgang Waltenberger <wolfgang.waltenberger@gmail.com>
"""

import numpy, sys, os, time, subprocess, glob
sys.path.insert(0,"../../smodels" )
from smodels.tools.runtime import nCPUs

def getAge ( f ):
    """ get the age of file in hours. age goes by last modification """
    if not os.path.exists ( f ):
        return 0.
    t0 = time.time()
    mt = os.stat ( f ).st_mtime
    dt = ( t0 - mt ) / 60. / 60. ## hours
    return dt

def safFile ( dirname, topo, masses, sqrts ):
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
    """ parse the mass string, e.g. (500,510,10),(100,110,10). keywords like "half" are
        accepted.
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
            else:
                print ( "error: i know only 'half' for a string, and only in middle position" )
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
    if lists[1][0]=="half":
        for x  in lists[0]:
            for z in lists[2]:
                y=int(.5*x+.5*z)
                ret.append ( (int(x),y,int(z)) )
    elif len(lists)==2:
        for x in range ( len(lists[0] ) ):
            for y in range ( len(lists[1]) ):
                ret.append ( (int(lists[0][x]),int(lists[1][y])) )
    elif len(lists)==3:
        for x in range ( len(lists[0] ) ):
            for y in range ( len(lists[1]) ):
                for z in range ( len(lists[2]) ):
                    ret.append ( (int(lists[0][x]),int(lists[1][y]),int(lists[2][z])) )
    ret = filterForGap ( ret, mingap1, True, [0,1] )
    ret = filterForGap ( ret, mingap2, True, [1,2] )
    ret = filterForGap ( ret, mingap13, True, [0,2] )
    ret = filterForGap ( ret, maxgap1, False, [0,1] )
    ret = filterForGap ( ret, maxgap2, False, [1,2] )
    ret = filterForGap ( ret, maxgap13, True, [0,2] )
    return ret

def filterForGap ( masses, gap, isMin=True, indices=[0,1] ):
    """ filter out tuples for which gap is not met
        between <indices> particles
    :param isMin: if True, filter out too low gaps, if False,
                  filter out too high gaps
    """
    if gap == None:
        return masses
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

def listAnalysesCutLang():
    """ list the analyses that are available in cutlang """
    dirname = "CutLang/ADLLHCanalyses/"
    files = glob.glob ( "%s*" % dirname )
    for f in files:
        f = f.replace(dirname,"")
        if "README" in f:
            continue
        print ( f )

def listAnalyses ( cutlang ):
    """ list the analyses that are available in MA5 or cutlang """
    if cutlang:
        listAnalysesCutLang()
    else:
        listAnalysesMA5()

def listAnalysesMA5():
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
    print ( "List of analyses:" )
    print ( "=================" )
    for f in files:
        f = f.replace(".saf","").replace(".cpp","")
        for d in dn:
            f = f.replace(d,"")
        print  ( "  %s" % f )

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

def getListOfCutlangMasses( topo, sqrts=13 ):
    """ get a list of the masses of an cutlang scan.
    :param topo: e.g. T1
    :param sqrts: sqrt(s) in tev
    """
    import glob
    ret=[]
    files = glob.glob( f"cutlang_results/*/ANA_{topo}*/output/*embaked" )
    for f in files:
        fname = f.replace(".embaked","")
        p = f.rfind("mass_")
        fname = fname[p+5:]
        tokens = fname.split("_")
        tokens = tuple ( map ( int, tokens ) )
        if not tokens in ret:
            ret.append ( tokens )
    return ret

def getListOfMasses(topo, postMA5=False, sqrts=13, cutlang=False ):
    """ get a list of the masses of an mg5 scan. to be used for e.g. ma5.
    :param postMA5: query the ma5 output, not mg5 output.
    :param cutlang: query the cutlang output, not the mg5 output
    """
    if cutlang:
        return getListOfCutlangMasses ( topo, sqrts )
    import glob
    ret=[]
    # fname = "%s_%djet.*" % ( topo, njets )
    dirname = "mg5results/"
    extension = "%d.hepmc.gz" % sqrts
    if postMA5:
        dirname = "results/"
        extension = "dat"
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

if __name__ == "__main__":
    print ( getListOfMasses ( "T2tt", True, 8 ) )
    """
    ms = "[(200,400,50.),(200,400.,50),(150.,440.,50)]"
    masses = parseMasses ( ms, mingap13=0., mingap2=0. )
    print ( "masses", masses )
    print ( nRequiredMasses("T5ZZ") )
    """

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


if __name__ == "__main__":
    print ( parseMasses ( "[(350,691,50),(0,2351,50)]", mingap1 = 1., maxgap1 = 360. ) )
