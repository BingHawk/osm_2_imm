# osm_2_imm
 Repository for the osm_2_imm QGIS plugin
 
# Installation of the plugin 
As the plug-in is in pre-release, it is not available through official channels. Follow this process to install: 

Make sure geopandas is installed in the qgis python installation. (see below)

Fork this repository to the following folder. 
- Linux: ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins
- Windows: C:\Users\USER\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins
- Mac OS: Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins

Restart QGIS, go to the plugin browser and serach for "OSM to IMM". 

# Installing geopandas dependency

Locate the /bin of your qgis installation and install with pip.

## Mac OS: 
 /Applications/QGIS-LTR.app/Contents/MacOS/bin/pip3 install geopandas
 
## Windows: 
- Open OSGeo4W shell (packed with QGIS in the start menu)
- Type py3_env. This should print paths of your QGIS Python installation.
- Use Python’s pip to install the library of your choice: python -m pip install geopandas

[(Instructions by Zoran)](https://landscapearchaeology.org/2018/installing-python-packages-in-qgis-3-for-windows/)



