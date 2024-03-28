==============================
The efficiency map bakery, v2.
==============================

The em-creator is a helpful tool that links various simulation tools in particle physics together, and can make the efficiency of several mass points. 
This document will focus on explaining the installation of simulation tools, particularly MadGraph5, Pythia8, and CutLang, and the em-creator operation.


CMSSW environment set and em-creator installation
=================================================
The em-creator and its associated simulation tools do not depend on CMSSW. However, each simulation program requires various programs and libraries, such as Python, the GCC & G++ compilers, parsers like Bison & Flex, and libraries like zlib.

We can use the simulation tools consistently by setting up the distributed CMSSW environment.

In el9 lxplus server::

   cmsrel CMSSW_13_3_3
   cd CMSSW_13_3_3/src
   cmsenv
   git clone https://github.com/Junghyun-Lee-Physicist/em-creator.git

For Python package (smodels, colorama, numpy, ROOT) for em-creator::

   cd ${CMSSW_BASE}/src/em-creator
   pip3 install --user -r requirements.txt

Packages installed with pip3 usually don't require you to set environment variables. However, if the package isn't recognized, you may need to add the typical installation path for pip to your system's PATH environment variable as follows::

   export PATH=$PATH:~/.local/bin

ROOT is unlikely to be installed via pip typically, but that's fine. ROOT will be recognized through cmsenv.


Madgraph5 and Pythia8 installation
==================================
* For Madgraph::

   cd ${CMSSW_BASE}/src/em-creator
   mv mg5.template mg5 && cd mg5
   wget https://launchpad.net/mg5amcnlo/3.0/3.4.x/+download/MG5_aMC_v3.4.2.tar.gz
   tar -zxvf MG5_aMC_v3.4.2.tar.gz
   mv MG5_aMC_v3_4_2/* .

You can now use MadGraph by executing the mg5_aMC file found in the bin directory within the mg5 directory. 

While you may download other versions of MadGraph if you wish, the installation directory for MadGraph must be named [ mg5 ], and the tar file must remain in the mg5 directory. This is because the em-creator searches for MadGraph in the mg5 directory and checks for its presence and version using the name of tar file.

* For Pythia (and additional zlib, hepmc, boost package)::

   cd ${CMSSW_BASE}/src/em-creator/mg5
   python3 bin/mg5_aMC install.script


Delphes installation
====================
* Installation delphes from git::
   
   cd ${CMSSW_BASE}/src/em-creator
   git clone https://github.com/delphes/delphes.git
   cd delphes
   sed -i 's/CXXFLAGS += -std=c++0x/CXXFLAGS += -std=c++17/' Makefile
   make -j4

To successfully compile Delphes in the lxplus environment, it's necessary to change the CXXFLAGS std in the Makefile to c++17. As shown above, this was achieved using the sed command.

If the compilation has been completed, the [ DelphesHepMC2 ] and [ DelphesHepMC3 ] files must necessarily exist.


CutLang installation
====================
CutLang's dependencies have already been installed or set up through pip3 and cmsenv. Now, CutLang will be installed directly via Git.

* Installation CutLang from git::

   cd ${CMSSW_BASE}/src/em-creator
   git clone https://github.com/unelg/CutLang.git


The most recent version of CutLang utilizes the ONNX library, which facilitates interaction between DNN models. However, this is not easy to use in the Lxplus environment, so it must be excluded from compilation. Therefore, replace it with a Makefile that removes the ONNX relevant part.

* Replace Makefile::

   cp ${CMSSW_BASE}/src/em-creator/CutLang_Makefile CutLang/CLA/.

* Compile the CutLang::

   cd ${CMSSW_BASE}/src/em-creator/CutLang/CLA
   make

   
Example usage:
==============

.. code-block::

    ./bake.py -n 1000 -T GG_direct -m "[(2200.0,2201.0,2),(1200.0,1201.0,2)]" --analyses "ATLAS-SUSY-2018-22" --adl_file ATLAS-SUSY-2018-22_Cutlang.adl --cutlang
