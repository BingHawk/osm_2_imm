#%%
import geopandas as gpd
import os
import sys
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning) #Suppresses future warnings

from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsVectorLayer
try:
    import processing
except ModuleNotFoundError:
    pass

try:
    from ..settings.config import Config
except ValueError:
    from settings.config import Config
except ImportError:
    from settings.config import Config
from .query import Query
from .parser_new import parse, buffer
from .parser_qgis import parse as qParse, buffer as qBuffer

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

def transformQLayer(qLayer:QgsVectorLayer, crsSrc:QgsCoordinateReferenceSystem, crsDest:QgsCoordinateReferenceSystem, project:QgsProject, backward:bool = False) -> QgsVectorLayer:
    transformContext = project.transformContext()
    xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)
    feats = []
    for f in qLayer.getFeatures():
        g = f.geometry()
        if backward:
            g.transform(xform, QgsCoordinateTransform.BackwardTransform)
        else:
            g.transform(xform)
        f.setGeometry(g)
        feats.append(f)

    columns = [field for field in qLayer.fields()]

    if qLayer.wkbType() == 1:
        vl = QgsVectorLayer("point", "grey_areas","memory")
    elif qLayer.wkbType() == 2:
        vl = QgsVectorLayer("linestring", "grey_areas","memory")
    elif qLayer.wkbType() == 3:
        vl = QgsVectorLayer("polygon", "grey_areas","memory")
        
    vl.setCrs(crsDest)
    pr = vl.dataProvider()
    pr.addAttributes(columns)
    pr.addFeatures(feats)
    vl.updateExtents()

    return vl

def qgsMain(project: QgsProject, bbox:str = None, ):
    if bbox is None:
        bbox = CONFIG.bbox_M
    res = Query.bboxGet(bbox)

    layers = qParse(res)

    crsOsm = QgsCoordinateReferenceSystem("EPSG:4326")
    crsProj = QgsCoordinateReferenceSystem(CONFIG.projectedCrs) 
    voidGreyAreasTranformed = transformQLayer(layers['voidGreyAreas'], crsOsm, crsProj, project)

    buffered = qBuffer(voidGreyAreasTranformed, CONFIG.bufferSettings['voidGreyAreas'])
    buffered = transformQLayer(buffered, crsProj, crsOsm, project)

    # parameterProject = {'INPUT': layers['voidGreyAreas'], 'TARGET_CRS': CONFIG.projectedCrs,
    #              'OUTPUT': 'memory:grey_areas_buffered'}
    # reprojected = processing.run('native:reprojectlayer', parameterProject)

    # buffered = qBuffer(reprojected['OUTPUT'], CONFIG.bufferSettings['voidGreyAreas'])



    layers['voidGreyAreas'] = buffered

    for feature in layers.keys():
        qVectorLayer = layers[feature] 
        project.addMapLayer(qVectorLayer)

def main(bbox=None, outLoc=None):
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
    tic = time.time()
    qTic = time.time()
    """ Tests nodes """
    # res = Query.tagGet(CONFIG.usesActivities['inputGeom'],
    #                 CONFIG.usesActivities['inputTags'],
    #                 CONFIG.bbox_M,
    #                 printquery=True)

    """ Tests ways """
    # res = Query.tagGet(CONFIG.networkStreet['inputGeom'],
    #                     CONFIG.networkStreet['inputTags'],
    #                     CONFIG.bbox_M,
    #                     printquery=True)

    """ Tests relations containg nodes and ways """
    # res = Query.tagGet('rel',
    #                     CONFIG.networkPTStops['inputTags'],
    #                     CONFIG.bbox_M,
    #                     printquery=True)

    """ Tests relations containng polygons"""
    # res = Query.tagGet('rel',
    #                     CONFIG.volumeBuildings['inputTags'],
    #                     CONFIG.bbox_M,
    #                     printquery=True)

    """ Tests everything in the bbox"""
    res = Query.bboxGet(CONFIG.bbox_M, printquery=True)

    print("")

    qToc = time.time()
    qTime = qToc - qTic

    layers = qParse(res)

    project = QgsProject().instance()
    
    crsOsm = QgsCoordinateReferenceSystem("EPSG:4326")
    crsProj = QgsCoordinateReferenceSystem(CONFIG.projectedCrs)

    voidGreyAreasTranformed = transformQLayer(layers['voidGreyAreas'], crsOsm, crsProj, project)

    # for f in voidGreyAreasTranformed.getFeatures():
    #     if f.id() > 493:
    #         print("Feature:", f.id(), f.attributes(), f.geometry().asWkt())

    buffered = qBuffer(voidGreyAreasTranformed, CONFIG.bufferSettings['voidGreyAreas'])

    for f in buffered.getFeatures():
        if f.id() > 493:
            print("Feature:", f.id(), f.attributes(), f.geometry().asWkt())

    bufferedtransformed = transformQLayer(buffered, crsProj, crsOsm,  project)
    print("tranformed back")

    print(bufferedtransformed.isValid())
    for f in bufferedtransformed.getFeatures():
        print(f.id())
        if f.id() > 493:
            print("Feature:", f.id(), f.attributes(), f.geometry().asWkt())


        

    # voidGreyAreasBuffered = qBuffer(parsed['voidGreyAreas'], CONFIG.bufferSettings['voidGreyAreas'])
    # for f in voidGreyAreasBuffered.getFeatures():
    #             print("")
    #             print("Feature:", f.id(), f.attributes(), f.geometry().asWkt())


    toc = time.time()

    print("Done in {} seconds.".format(toc-tic))
    print(
        """Query time: {} 
        """.format(qTime))

    for key in layers.keys():
        pr = layers[key].dataProvider()
        print(key, pr.featureCount())
        # if key == "volumeBuildings":
        #     for f in parsed[key].getFeatures():
        #         print("")
        #         print("Feature:", f.id(), f.attributes(), f.geometry().asWkt())




    
# _______ Main program calls ______
# main(CONFIG.bbox_S_D) # Run this line for Dakar 
if __name__ == "__main__":
    main() # Run this line for Milano

# %%
