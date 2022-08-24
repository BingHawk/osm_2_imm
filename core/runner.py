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
from qgis.PyQt.QtWidgets import QProgressDialog, QProgressBar
from qgis.PyQt.QtCore import Qt



try:
    from ..settings.config import Config
except ValueError:
    from settings.config import Config
except ImportError:
    from settings.config import Config
from .query import Query
from .parser_qgis import Parser

from .utilities.tools import getGroupNameFromFeature, getLayerNameFromFeature

import time

class Runner:

    
    CONFIG:Config = Config()
    PARSER:Parser = Parser(CONFIG)
    __createdGroups:list = []

    @classmethod
    def transformQLayer(cls, qLayer:QgsVectorLayer, crsSrc:QgsCoordinateReferenceSystem, crsDest:QgsCoordinateReferenceSystem, project:QgsProject) -> QgsVectorLayer:
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

    @classmethod
    def saveLayer(cls, feature:str, vl:QgsVectorLayer, outLoc:str, project: QgsProject) -> str:
        """
        Saves vl to a geopackage with the name of the first part of the feature name. 
        """

        groupName = getGroupNameFromFeature(feature)
        outName = groupName+'.gpkg'
        gpkgPath = os.path.join(outLoc,outName)

        saveOptions = QgsVectorFileWriter.SaveVectorOptions()
        if groupName not in cls.__createdGroups:
            cls.__createdGroups.append(groupName)
            saveOptions.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        else:
            saveOptions.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        saveOptions.driverName = "GPKG"
        saveOptions.layerName = getLayerNameFromFeature(feature)
        err = QgsVectorFileWriter.writeAsVectorFormatV2(vl, gpkgPath, project.transformContext(), saveOptions)
        return gpkgPath

    @classmethod
    def createGroupMap(cls, features: list)-> dict:
        """
        Creates a dictionary with the group name as keys and a list of the features included as values
        """

        groupMap = {}
        for feature in features:
            groupName = getGroupNameFromFeature(feature)

            if groupName in groupMap:
                groupMap[groupName].append(feature)
            else:
                groupMap[groupName] = [feature]
        return groupMap


    @classmethod
    def qgsMain(cls, project: QgsProject = QgsProject.instance(), bbox:QgsRectangle = CONFIG.bbox_M, outLoc = None ):
        dialog = QProgressDialog("Runner Working","Cancel",0,100)
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration = 0
        dialog.setWindowTitle("Running OSM to IMM")

        dialog.setLabelText("Starting processess")
        dialog.setValue(0)
        time.sleep(1)
        
        groupMap = cls.createGroupMap(cls.CONFIG.features)

        cls.PARSER.setOutLoc(outLoc)
        cls.PARSER.setProject(project)

        dialog.setLabelText("Querying Overpass")
        dialog.setValue(25)


        res = Query.bboxGet(bbox)

        dialog.setLabelText("Parsing")
        dialog.setValue(50)


        layers = cls.PARSER.parse(res)

        dialog.setLabelText("Preparing output")
        dialog.setValue(75)


        crsOsm = QgsCoordinateReferenceSystem("EPSG:4326")
        crsProj = QgsCoordinateReferenceSystem(cls.CONFIG.projectedCrs) 
        voidGreyAreasTranformed = cls.transformQLayer(layers['voidGreyAreas'], crsOsm, crsProj, project)

        buffered = cls.PARSER.buffer(voidGreyAreasTranformed, 'voidGreyAreas')
        buffered = cls.transformQLayer(buffered, crsProj, crsOsm, project)

        layers['voidGreyAreas'] = buffered

        root = project.layerTreeRoot()
        
        for group in groupMap.keys():
            g = root.addGroup(group) 
            for feature in groupMap[group]:
                
                if outLoc is not None:
                    name = getLayerNameFromFeature(feature)
                    gpkgPath = cls.saveLayer(feature,layers[feature],outLoc,project)
                    pathToLayer = gpkgPath+f"|layername={name}"
                    qVectorLayer = QgsVectorLayer(pathToLayer, name, "ogr")
                else:
                    qVectorLayer = layers[feature]
                    
                project.addMapLayer(qVectorLayer, False)
                g.addLayer(qVectorLayer)

        cls.__createdGroups = []
        dialog.setValue(100)



    
# __________TESTING CODE_____________
    @classmethod
    def test(cls):
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
        #                     cls.CONFIG.volumeBuildings['inputTags'],
        #                     cls.CONFIG.bbox_M,
        #                     printquery=True)

        """ Tests everything in the bbox"""
        res = Query.bboxGet(cls.CONFIG.bbox_M, printquery=True)


        print("")
        groupMap = cls.createGroupMap(cls.CONFIG.features)

        qToc = time.time()
        qTime = qToc - qTic
        layers = cls.PARSER.parse(res)

        project = QgsProject.instance()

        crsOsm = QgsCoordinateReferenceSystem("EPSG:4326")
        crsProj = QgsCoordinateReferenceSystem(cls.CONFIG.projectedCrs) 
        voidGreyAreasTranformed = cls.transformQLayer(layers['voidGreyAreas'], crsOsm, crsProj, project)

        buffered = cls.PARSER.buffer(voidGreyAreasTranformed, 'voidGreyAreas')
        buffered = cls.transformQLayer(buffered, crsProj, crsOsm, project)

        layers['voidGreyAreas'] = buffered

        groupMap = {}
        for feature in cls.CONFIG.features:
            groupName = getGroupNameFromFeature(feature)

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
    Runner.test() # Run this line for Milano

# %%
