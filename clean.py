#!/usr/bin/env python3

def main():
    import glob, subprocess, os
    files = glob.glob ( "ma5/ANA_TGQ_*" )
    files = glob.glob ( "TGQ_*" )
    for f in files:
        #f = f.replace("ma5/ANA_","")
        #print ( f )
        l = f.replace("TGQ","").replace("1jet.","")
        tokens = l.split("_")
        numbers = list(map(int,tokens[1:] ))
        # print ( numbers )
        if numbers[0]<numbers[2] or numbers[1]<numbers[2]:
            cmd = "rm -rf %s" % f 
            print ( cmd )
            o = subprocess.getoutput ( cmd )
            cmd = "rm -rf ma5/ANA_%s" % f
            print ( cmd )
            o = subprocess.getoutput ( cmd )

main()
