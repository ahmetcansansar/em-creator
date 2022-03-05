#!/usr/bin/env python3

""" a simple tool for manipulation of embaked files, like merging and filtering
"""

def merge ( infiles : list, outfile : str, remove ):
    """ merge infile into outfile """
    comments = []
    points = {}
    overwrites = 0
    files = {}
    for f in infiles:
        h = open ( f, "rt" )
        lines = h.readlines()
        h.close()
        for line in lines:
            if line.startswith ( "#" ):
                comments.append ( "# "+f+": "+ line[1:] )
        txt = eval ( "\n".join ( lines ) )
        for k,v in txt.items():
            if k in files:
                overwrites += 1
                if overwrites < 5:
                    print ( f"[mergeEmbaked] overwriting {k} with {f}, old was {files[k]}" )
            points[k]=v
            files[k]=f
    print ( f"[mergeEmbaked] total of {overwrites} overwrites" )
    nstarved = 0
    cleaned = {}
    for k,v in points.items():
        if "__nevents__" in v and remove != None and v["__nevents__"]<remove:
            if nstarved < 5:
                print ( f"[mergeEmbaked] point {k} has {v['__nevents__']} events only, in {files[k]}." )
            nstarved+=1
        else:
            cleaned[k]=v
    points = cleaned
    print ( f"[mergeEmbaked] a total of {nstarved} points with low statistics." )
    g = open ( outfile, "wt" )
    g.write ( f"# merger of: {', '.join(infiles)}\n" )
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
    argparser.add_argument ( '-r', '--remove', help='remove entries with fewer than n events [None]',
                             type=int, default=None )
    args = argparser.parse_args()
    merge ( args.infile, args.outfile, args.remove )

if __name__ == "__main__":
    run()
