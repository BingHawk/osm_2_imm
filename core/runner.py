#%%
import geopandas as gpd
import os
import sys
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning) #Suppresses future warnings

try:
    from ..settings.config import Config
except ValueError:
    from settings.config import Config
from .query import Query
from .parser_new import parse, buffer
from .parser_qgis import parse as parse_q

from .utilities.tools import camelCaseSplit


import time

CONFIG = Config()


# write outputs a geodataframe as a geopackage file with the specified filename in a folder decided by CONFIG.outputFolder.
# gdf - the GeoGataFrame to be output
# filename:string - the decired filename for the output file. 
# layer - String. The name of layer the file should be output to. 
def qWrite(gdf, outLoc, filename, layer):

    if gdf is None: 
        print('nothing to write to layer "{}" of file "{}"'.format(layer,filename))
        pass
    else:        
        if gdf.crs != CONFIG.outputCrs:
            gdf.to_crs(CONFIG.outputCrs)

        fullpath = outLoc + "/" + filename + '.gpkg'

        if os.path.isfile(fullpath):
            print("file already exsist, edditing",fullpath)
            pass
        gdf.to_file(fullpath, driver='GPKG', layer=layer)

        print('Layer written: "{}" written to "{}"'.format(layer,fullpath))

def write(gdf, filename, layer):

    if gdf is None: 
        print('nothing to write to layer "{}" of file "{}"'.format(layer,filename))
        pass
    else:        
        if gdf.crs != CONFIG.outputCrs:
            gdf.to_crs(CONFIG.outputCrs)

        currentFolder = os.path.abspath(os.path.dirname(sys.argv[0]))
        savefolder = currentFolder+"/"+"outLayers"
        if not os.path.isdir(savefolder):
            os.mkdir(savefolder)
        fullpath = savefolder + "/" + filename + '.gpkg'

        if os.path.isfile(fullpath):
            print("file already exsist, edditing",fullpath)
            pass
        gdf.to_file(fullpath, driver='GPKG', layer=layer)

        print('Layer written: "{}" written to "{}"'.format(layer,fullpath))

     
def main(bbox, outLoc):
    tic = time.time()
    if bbox is None:
        bbox = CONFIG.bbox_M
    qTic = time.time()
    res = Query.bboxGet(bbox)
    qToc = time.time()
    qTime = qToc - qTic

    all = parse(res)

    for key in all.keys():
        words = camelCaseSplit(key)
        filename = words[0]
        layer = '_'.join(words[1:]).lower()

        if key == 'usesActivities' or key == 'usesServices' or key == 'boundariesAdministrative':
            if all[key] is not None:
                all[key]['geometry'] = all[key].centroid
        
        if key == 'voidGreyAreas':
            if all[key] is not None:
                all[key] = buffer(all[key], CONFIG.bufferSettings['voidGreyAreas'])

        if outLoc is None:
            write(all[key],filename,layer)
        else: 
            qWrite(all[key],outLoc,filename,layer)

    toc = time.time()

    print("Done in {} seconds.".format(toc-tic))
    print(
        """Query time: {} 
        """.format(qTime))









    
# __________TESTING CODE_____________
def test():
    res = Query.tagGet("way", {'highway': [ "motorway",
                                            "trunk",
                                            "primary",
                                            "secondary",
                                            "tertiary",
                                            "unclassified",
                                            "residential",
                                            "motorway_link",
                                            "trunk_link",
                                            "primary_link",
                                            "secondary_link",
                                            "tertiary_link",
                                            "living_street",
                                            "service",
                                            "road"]},
                                CONFIG.bbox_M, printquery=True)

    parsed = parse_q(res)
    print("")
    for f in parsed['voidTrees'].getFeatures():
        print("Feature:", f.id(), f.attributes(), f.geometry().asWkt())




    
# _______ Main program calls ______
# main(CONFIG.bbox_S_D) # Run this line for Dakar 
if __name__ == "__main__":
    main() # Run this line for Milano

# %%
