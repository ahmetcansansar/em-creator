==============================
The efficiency map bakery, v2.
==============================

The em-creator is a helpful tool that links various simulation tools in particle physics together, and can make the efficiency of several mass points. 
This document will focus on explaining the installation of simulation tools, particularly MadGraph5, Pythia8, and CutLang, and the em-creator operation.

CMSSW environment set and em-creator installation
=================================================
The em-creator and its associated simulation tools do not depend on CMSSW. However, each simulation program requires various programs and libraries, such as Python, the GCC & G++ compilers, parsers like Bison & Flex, and libraries like zlib. By setting up the distributed CMSSW environment, we can use the simulation tools in a consistent environment.

.. code-block:: bash

   # Please log in el9 lxplus server
   $ ssh <User user name>@lxplus.cern.ch
   $ cmsrel CMSSW_13_3_3
   $ cd CMSSW_13_3_3/src
   $ cmsenv
   $ git clone https://github.com/Junghyun-Lee-Physicist/em-creator.git

Installation
============

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
