Quickstart
==========
Current version: 2.0

Instalation
-----------

.. note::
   
   This project is under development and is only fully tested on Mac as of version 2.0. 
   Report any issues on `GitHub <https://github.com/BingHawk/osm_2_imm/issues>`_

.. _mac-install:

Mac installation
'''''''''''''''''

On windows? see :ref:`windows-install`

To start using the tool, go to `osm_2_imm github page <https://github.com/BingHawk/osm_2_imm>`_ and download a osm to imm as .zip file.
Then unpac the .zip the plugin folder of your QGIS installation:

~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins

next, install the required dependency **overpy**:
find the pip3 instalation that comes with the python instalation of QGIS and use it to install overpy

``$ /Applications/QGIS-LTR.app/Contents/MacOS/bin/pip3 install overpy``

.. note:: 
   Note that your QGIS instalation might not be called QGIS-LTR. 

.. _windows-install:

Windows installation
''''''''''''''''''''

On mac? see :ref:`mac-install`

To start using the tool, go to `osm_2_imm github page <https://github.com/BingHawk/osm_2_imm>`_ and download a osm to imm as .zip file.
Then unpac the .zip the plugin folder of your QGIS installation:

``C:\Users\USER\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins``

next, install the required dependency **overpy**:

#. Open OSGeo4W shell (packed with QGIS in the start menu)
#. Type py3_env. This should print paths of your QGIS Python installation.
#. Use Python's pip to install overpy: ``python -m pip install overpy``

.. note::
   OSM to IMM is not yet tested on windows and might not work as expected. Above instructions credited to `Zoran <https://landscapearchaeology.org/2018/installing-python-packages-in-qgis-3-for-windows/>`_

Use
---
#. Open OSM to IMM under the "plugin" menu and the main dialog appears. 
#. Input either a layer or the bounding box coordinates describing the area you want to get data from.
#. Choose if you want to save the output to files (geopackage) and if so, where. Default is that the layers are created as memory layers
#. Click ok.

.. note::
   It is important to be familiar with the :ref:`area size <area-size>` limitation described below. 

.. _limitations:

Limitations
===========

.. _area-size:

**Area size**

As of version 2.0, max area of study 50 km^2 due to restrictions in `overpass <https://wiki.openstreetmap.org/wiki/Overpass_API#Resource_management_options_(osm-script)>`_.
The currently used resource management options used when querying overpass can be found under :ref:`query`.

.. _progress-bar:

**Progress bar**

As of version 2.0, he progress bar runs in the same thread as the main program instead of using 
`slots <https://doc.qt.io/qtforpython-5/PySide2/QtCore/Slot.html>`_ and `signals <https://doc.qt.io/qtforpython-5/PySide2/QtCore/Signal.html>`_.
This has the following disadvantages:
- the progress bar blocks the interface of QGIS and no other tasks can be done while it is running. 
- the "cancel" button in the dialog only cancels the running once the current partial task is completed.



**Current bugs**

Bugs as of version 2.0:

For some bounding boxes, some nodes are not added to the output which as such contains incomplete data.
All layers with :ref:`tag mapping settings <edit-tag-map>` inputGeom = node and outputGeom = point may be affected.   