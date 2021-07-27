#!/usr/bin/env python3

""" remove delphes and hepmc files for which we already have a result """

import glob, subprocess, os, sys

def run( ana ):
    fembaked = glob.glob ( f"cutlang_results/{ana}/ANA_T1_1jet/output/*embaked" )
    fdelphes = glob.glob ( f"cutlang_results/{ana}/ANA_T1_1jet/output/delphes_out_*root" )
    fhepmc = glob.glob ( f"cutlang_results/{ana}/ANA_T1_1jet/temp/T*.hepmc" )
    embaked = []
    for f in fembaked:
        p1 = f.find("mass_" )
        t = f[p1+5:-8]
        embaked.append ( t )
    for f in fdelphes:
        p1 = f.find("out_" )
        t = f[p1+4:-5]
        if t in embaked:
            print ( "removing delphes", t )
            cmd = f"rm {f}"
            subprocess.getoutput ( cmd )
    for f in fhepmc:
        p1 = f.find("temp" )
        t = f[p1+5:-9]
        p1 = t.find("_" )
        t = t[p1+1:]
        if t in embaked:
            print ( "removing hepmc", f )
            cmd = f"rm {f}"
            subprocess.getoutput ( cmd )
        else:
            pass
            # print ( "keeping hepmc", f )

if __name__ == "__main__":
    ana = "CMS-SUS-19-006"
    run( ana )
    ana = "CMS-SUS-19-005"
    run( ana )
