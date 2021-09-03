#!/usr/bin/env python3

""" script to check the jet matching schema """

def match():
    import sys, subprocess, argparse, gzip, io, tempfile, os
    argparser = argparse.ArgumentParser(description='jetmatching runner.')

    argparser.add_argument ( '-f', '--hepmc', help='path to hepmc file [default.hepmc]',
                             type=str, default="default.hepmc" )

    args = argparser.parse_args()
    hepmcfile = args.hepmc
    if hepmcfile.endswith ( ".gz" ):
        hepmcfile = tempfile.mktemp(suffix=".hepmc",prefix="tmp" )
        # hepmcfile = "default.hepmc"
        with open( hepmcfile, 'wb') as f_out:
            in_f = gzip.open( args.hepmc, 'rb' )
            while True:
                s = in_f.read( 1 << 24 )
                if s == b'':
                    break
                f_out.write(s)
            in_f.close()

    f = open ( "jetmatching.template", "rt" )
    lines = f.readlines()
    f.close()

    g=open("match.ma5","wt" )
    for line in lines:
        line = line.replace("@@HEPMCFILE@@", hepmcfile )
        g.write ( line )
    g.close()
    cmd = "python3 ma5/bin/ma5 -H -s match.ma5"
    print ( cmd )
    pipe = subprocess.Popen ( cmd, shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE )
    for line in io.TextIOWrapper(pipe.stderr, encoding="latin1"):
        print ( line )
    for line in io.TextIOWrapper(pipe.stdout, encoding="latin1"):
        print ( line )
    # subprocess.getoutput ( cmd )
    if args.hepmc != hepmcfile:
        os.unlink ( hepmcfile )

if __name__ == "__main__":
    match()
