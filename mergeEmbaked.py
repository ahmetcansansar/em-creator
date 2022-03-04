#!/usr/bin/env python3

def merge ( infiles : list, outfile : str ):
    """ merge infile into outfile """
    comments = []
    points = {}
    for f in infiles:
        h = open ( f, "rt" )
        lines = h.readlines()
        for line in lines:
            if line.startswith ( "#" ):
                comments.append ( line )
        txt = eval ( "\n".join ( lines ) )
        for k,v in txt.items():
            points[k]=v
        h.close()
    g = open ( outfile, "wt" )
    g.write ( "# merger of {','.join(infiles)}\n" )
    print ( f"[mergeEmbaked] added {len(comments)} comments to {outfile}" )
    for c in comments:
        g.write ( c )
    g.write ( "{" )
    masses = list ( points.keys() )
    masses.sort()
    for ctr,k in enumerate(masses):
        v = points[k]
        com = ","
        if ctr >= len(masses)-1:
            com=""
        g.write ( f"{k}: {v}{com}\n" )
    g.write ( "}\n" )
    print ( f"[mergeEmbaked] added {len(masses)} points to {outfile}" )
    g.close()

def run():
    import argparse
    argparser = argparse.ArgumentParser(description='tool to merge embaked files')
    argparser.add_argument ( '-o', '--outfile', help='outputfile [out.embaked]',
                             type=str, default="out.embaked" )
    argparser.add_argument ( '-i', '--infile', nargs="+", 
            help='input file(s)', type=str )
    args = argparser.parse_args()
    merge ( args.infile, args.outfile )

if __name__ == "__main__":
    run()
