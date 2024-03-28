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

   $ cmsrel CMSSW_13_3_3
   $ cd CMSSW_13_3_3/src
   $ cmsenv
   $ git clone https://github.com/Junghyun-Lee-Physicist/em-creator.git

Madgraph5 and Pythia8 installation
==================================
* For madgraph::

   $ cd ${CMSSW_BASE}/src/em-creator
   $ mv mg5.template mg5 && cd mg5
   $ wget https://launchpad.net/mg5amcnlo/3.0/3.4.x/+download/MG5_aMC_v3.4.2.tar.gz
   $ tar -zxvf MG5_aMC_v3.4.2.tar.gz
   $ mv MG5_aMC_v3_4_2/* .

You can now use MadGraph by executing the mg5_aMC file found in the bin directory within the mg5 directory. 

While you may download other versions of MadGraph if you wish, the installation directory for MadGraph must be named [mg5], and the tar file must remain in the mg5 directory. This is because the em-creator searches for MadGraph in the mg5 directory and checks for its presence and version using the tar file.

* For pythia::


For cutlang wrapper:
====================

* Installing prerequisities:

  * On RHEL-like distributions run::

      yum install bison flex root python3-root root-montecarlo-eg zlib-devel

  * On Debian-like distributions run::

      apt install bison flex zlib1g-dev
    
  and install ROOT from sources

  * On Arch linux run::

      pacman -S bison flex root zlib


* Installing  python prerequisities::

    pip3 -r requirements.txt



* EOS storage is available at lxplus.cern.ch:/eos/project/s/smodels/www/ADL/

Example usage:
==============

.. code-block::

    ./bake.py -n 10000 -a -m "[(250,2201,50),(10,2001,25)]" --analyses "cms_sus_19_005,cms_sus_19_006" -t T2ttoff -p 5 -b --cutlang
