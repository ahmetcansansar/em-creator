==============================
The efficiency map bakery, v2.
==============================

To bake, run ./bake.py

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
