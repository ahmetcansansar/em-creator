## Makefile, static linking. Pythia8 is fetched and built
## automatically.
## on a mac, for now please use the DYLD_LIBRARY_PATH variable  
## for pythia8.exe to find the shared object.

homeDIR = $(shell pwd)
PYTHIA8HOME := $(homeDIR)/pythia8

all: main_hscp.exe

install:
	./installer.sh

clean:
	cd CMS-EXO-12-026 && make clean

main_hscp.exe:
	cd CMS-EXO-12-026 && make main_hscp.exe pythia8path=$(PYTHIA8HOME)

