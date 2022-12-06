#%%
import os
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
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal



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

    def __init__(self, iface= None):
        self.CONFIG:Config = Config()
        self.PARSER:Parser = Parser(self.CONFIG)
        self.project: QgsProject = QgsProject.instance()
        self.bbox:QgsRectangle = self.CONFIG.bbox_M
        self.outLoc = None
        self.mainWindow = None
        self.iface = iface
        self.__createdGroups:list = []

    def transformQLayer(self, qLayer:QgsVectorLayer, crsSrc:QgsCoordinateReferenceSystem, crsDest:QgsCoordinateReferenceSystem) -> QgsVectorLayer:
        transformContext = self.project.transformContext()
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

    def saveLayer(self, feature:str, vl:QgsVectorLayer, outLoc:str) -> str:
        """
        Saves vl to a geopackage with the name of the first part of the feature name. 
        """

        groupName = getGroupNameFromFeature(feature)
        outName = groupName+'.gpkg'
        gpkgPath = os.path.join(outLoc,outName)

        saveOptions = QgsVectorFileWriter.SaveVectorOptions()
        if groupName not in self.__createdGroups:
            self.__createdGroups.append(groupName)
            saveOptions.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        else:
            saveOptions.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        saveOptions.driverName = "GPKG"
        saveOptions.layerName = getLayerNameFromFeature(feature)
        err = QgsVectorFileWriter.writeAsVectorFormatV2(vl, gpkgPath, self.project.transformContext(), saveOptions)
        return gpkgPath

    def createGroupMap(self, features: list)-> dict:
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

    def cancelRun(self, dialog):
        dialog.setLabelText("Aborting...")
        dialog.setValue(0)
        return

    def setBbox(self, bbox):
        self.bbox = bbox
        # Returns itself for methodchaining
        return self

    def setProject(self, project):
        self.project = project
        # Returns itself for methodchaining
        return self

    def setOutLoc(self, outLoc):
        self.outLoc = outLoc
        # Returns itself for methodchaining
        return self

    def qgsMain(self):
        dialog = QProgressDialog("Runner Working","Cancel",0,100,self.iface.mainWindow())
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setWindowTitle("Running OSM to IMM")

        dialog.setLabelText("Starting processess")
        dialog.setMinimumWidth(300)
        dialog.show()
        
        dialog.setLabelText("Starting processess")
        dialog.setValue(10)
        time.sleep(1)
        
        groupMap = self.createGroupMap(self.CONFIG.features)        

        self.PARSER.setOutLoc(self.outLoc)
        self.PARSER.setProject(self.project)

        if dialog.wasCanceled():
            return
        dialog.setLabelText("Querying Overpass")
        dialog.setValue(25)
        time.sleep(1)

        res = Query.bboxGet(self.bbox)
        
        if dialog.wasCanceled():
            return
        dialog.setLabelText("Parsing")
        dialog.setValue(50)
        time.sleep(1)

        layers = self.PARSER.parse(res)

        if dialog.wasCanceled():
            return
        dialog.setLabelText("Preparing output")
        dialog.setValue(75)
        time.sleep(1)

        crsOsm = QgsCoordinateReferenceSystem("EPSG:4326")
        crsProj = QgsCoordinateReferenceSystem(self.CONFIG.projectedCrs) 
        voidGreyAreasTranformed = self.transformQLayer(layers['voidGreyAreas'], crsOsm, crsProj)

        buffered = self.PARSER.buffer(voidGreyAreasTranformed, 'voidGreyAreas')
        buffered = self.transformQLayer(buffered, crsProj, crsOsm)

        layers['voidGreyAreas'] = buffered

        root = self.project.layerTreeRoot()
        
        for group in groupMap.keys():
            g = root.addGroup(group) 
            for feature in groupMap[group]:
                
                if self.outLoc is not None:
                    name = getLayerNameFromFeature(feature)
                    gpkgPath = self.saveLayer(feature,layers[feature],self.outLoc)
                    pathToLayer = gpkgPath+f"|layername={name}"
                    qVectorLayer = QgsVectorLayer(pathToLayer, name, "ogr")
                else:
                    qVectorLayer = layers[feature]
                    
                self.project.addMapLayer(qVectorLayer, False)
                g.addLayer(qVectorLayer)

        self.__createdGroups = []

        dialog.setValue(100)



    
# __________TESTING CODE_____________
    def test(self):
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
        res = Query.bboxGet(self.bbox, printquery=True)


        print("")
        groupMap = self.createGroupMap(self.CONFIG.features)

        qToc = time.time()
        qTime = qToc - qTic
        layers = self.PARSER.parse(res)

        project = QgsProject.instance()

        crsOsm = QgsCoordinateReferenceSystem("EPSG:4326")
        crsProj = QgsCoordinateReferenceSystem(self.CONFIG.projectedCrs) 
        voidGreyAreasTranformed = self.transformQLayer(layers['voidGreyAreas'], crsOsm, crsProj)

        buffered = self.PARSER.buffer(voidGreyAreasTranformed, 'voidGreyAreas')
        buffered = self.transformQLayer(buffered, crsProj, crsOsm)

        layers['voidGreyAreas'] = buffered

        groupMap = {}
        for feature in self.CONFIG.features:
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


class Worker(QThread):
    trigged = pyqtSignal(int)
    def __init__(self):
        QThread.__init__(self)


    def run(self):

        string = self.triggered.emit(1)

    
# _______ Main program calls ______
# main(CONFIG.bbox_S_D) # Run this line for Dakar 
if __name__ == "__main__":
    Runner.test() # Run this line for Milano

# %%
