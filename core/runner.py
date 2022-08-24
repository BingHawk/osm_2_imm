#%%
import geopandas as gpd
import os
import sys
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning) #Suppresses future warnings

from qgis.core import (QgsProject,
                    QgsCoordinateReferenceSystem,
                    QgsCoordinateTransform,
                    QgsVectorLayer,
                    QgsLayerTreeGroup,
                    QgsVectorFileWriter,
                    QgsRectangle
                    )

try:
    from ..settings.config import Config
except ValueError:
    from settings.config import Config
except ImportError:
    from settings.config import Config
from .query import Query
from .parser_qgis import Parser

from .utilities.tools import camelCaseSplit, getOsmBboxString

import time

CONFIG = Config()
PARSER = Parser(CONFIG)

def transformQLayer(qLayer:QgsVectorLayer, crsSrc:QgsCoordinateReferenceSystem, crsDest:QgsCoordinateReferenceSystem, project:QgsProject) -> QgsVectorLayer:
    transformContext = project.transformContext()
    xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)
    feats = []
    for f in qLayer.getFeatures():
        g = f.geometry()
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

def qgsMain(project: QgsProject = QgsProject.instance(), bbox:QgsRectangle = CONFIG.bbox_M, outLoc = None ):
        
    res = Query.bboxGet(bbox)

    layers = PARSER.parse(res)

    crsOsm = QgsCoordinateReferenceSystem("EPSG:4326")
    crsProj = QgsCoordinateReferenceSystem(CONFIG.projectedCrs) 
    voidGreyAreasTranformed = transformQLayer(layers['voidGreyAreas'], crsOsm, crsProj, project)

    buffered = PARSER.buffer(voidGreyAreasTranformed, CONFIG.bufferSettings['voidGreyAreas'])
    buffered = transformQLayer(buffered, crsProj, crsOsm, project)

    layers['voidGreyAreas'] = buffered

    groupMap = {}
    for feature in CONFIG.features:
        name = camelCaseSplit(feature)
        groupName = name[0].lower()

        if groupName in groupMap:
            groupMap[groupName].append(feature)
        else:
            groupMap[groupName] = [feature]

    root = project.layerTreeRoot()
    
    for group in groupMap.keys():
        g = root.addGroup(group) 
        for feature in groupMap[group]:
            qVectorLayer = layers[feature]
            project.addMapLayer(qVectorLayer, False)
            g.addLayer(qVectorLayer)

            if outLoc != None:
                outName = feature+'.gpkg'
                gpkg_path = os.path.join(outLoc,outName)
                saveOptions = QgsVectorFileWriter.SaveVectorOptions()
                # if os.path.exists(gpkg_path): #Denna returnerar alltid False. :(
                saveOptions.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

                saveOptions.driverName = "GPKG"
                err = QgsVectorFileWriter.writeAsVectorFormatV2(qVectorLayer, gpkg_path, project.transformContext(), saveOptions)
                print(err)



    
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
    layers = PARSER.parse(res)

    project = QgsProject.instance()

    crsOsm = QgsCoordinateReferenceSystem("EPSG:4326")
    crsProj = QgsCoordinateReferenceSystem(CONFIG.projectedCrs) 
    voidGreyAreasTranformed = transformQLayer(layers['voidGreyAreas'], crsOsm, crsProj, project)

    buffered = PARSER.buffer(voidGreyAreasTranformed, CONFIG.bufferSettings['voidGreyAreas'])
    buffered = transformQLayer(buffered, crsProj, crsOsm, project)

    layers['voidGreyAreas'] = buffered

    groupMap = {}
    for feature in CONFIG.features:
        name = camelCaseSplit(feature)
        groupName = name[0].lower()

        if groupName in groupMap.keys():
            groupMap[groupName].append(feature)
        else:
            groupMap[groupName] = [feature]
        

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
    test() # Run this line for Milano

# %%
