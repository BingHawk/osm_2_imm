#%%
import os
from qgis.core import ( QgsVectorLayer,
                        QgsLineString,
                        QgsMultiLineString,
                        QgsPointXY,
                        QgsGeometry,
                        QgsField,
                        QgsFeature,
                        QgsFields,
                        QgsMultiPolygon,
                        QgsCoordinateReferenceSystem,
                        QgsVectorFileWriter,
                        QgsProject)
from qgis.PyQt.QtCore import QVariant

from .utilities.tools import getGroupNameFromFeature, getLayerNameFromFeature

import overpy

try:
    from ..settings.config import Config
except ValueError:
    from settings.config import Config

class Parser:
    def __init__(self, config:Config = Config(), outLoc:str = None):
        self.__hasOutLoc:bool = False
        self.outLoc:str = outLoc
        self.__hasProject:bool = False
        self.project:QgsProject = None
        self.CONFIG:Config = config
        self.__createdGroups:list = []

        if self.outLoc is not None: 
            self.__hasOutLoc = True


    def setOutLoc(self, outLoc):
        if outLoc is not None:
            self.__hasOutLoc = True
        else:
            self.__hasOutLoc = False
        self.outLoc = outLoc
    
    def setProject(self, project:QgsProject):
        self.__hasProject = True
        self.project = project


    def isRelevant(self, osmFeat: overpy.Result, confFeature: dict) -> bool:
        """
        Checks if the tags of osmFeat are relevant for parsing.

        params:
            osmFeat - a overpy relation, way or node object which tags to check for relevance
            confFeature - the attribute of CONFIG the osmFeat should be checked against
        ret:
            returns True if the feature is relevant
        """

        relevant = False
        for key in confFeature['inputTags'].keys():
            try:
                if osmFeat.tags[key] in confFeature['inputTags'][key]:
                    relevant = True
            except KeyError:
                pass
        return relevant


    def getFeatures(self, obj:overpy.Result) -> list:
        """
        Gets the freatures that the obj is part of. 

        param obj: relation, way or node of an overpy result object. 
        ret: list of the features the object is part relevant for according to config file. 
        """
        features = []
        for tag in obj.tags.keys():
            try: 
                features.extend(self.CONFIG.reversedTags[tag])
            except KeyError:
                continue
        return features


    def createQgsFeature(self, obj:overpy.Result, feature:str) -> QgsFeature:
        """
        Creates a QgsFeature with and fills it with the tags of obj that exist in feature "outputTags" setting

        param: 
            obj type: A node, way or relation from an overpy.Result object
            obj val: The node way or relation that should be converted to a feature. 

            feature val: The feature of CONFIG the object belongs to. 
            
        ret: A QgsFeature that contains the fields specified in config filled with data from obj. Does not contain a geometry.
        """

        outTags = self.CONFIG.configJson[feature]['outputTags']

        fields = QgsFields()
        fields.append(QgsField("OSM id", QVariant.Int))
        for key in outTags : fields.append(QgsField(key, QVariant.String)) 
        f = QgsFeature(fields)
        f['OSM id'] = obj.id
        for key in obj.tags.keys(): 
            if key in outTags:
                f[key] = obj.tags[key]
        return f


    def addQgsFeature(self, lyr:QgsVectorLayer, feat:QgsFeature):
        """ Helper functions that adds a feature to a layers data provider and updates the layer"""

        pr = lyr.dataProvider()
        pr.addFeature(feat)
        lyr.updateExtents()


    def mergeLineGeoms(self, *args:QgsGeometry)-> QgsGeometry:
        """
        adds multiple polyline geometries into one geometry and tries to merges them.

        param: 
            type: QgsGeometry objects of linestring och polyline type
            val: lines to be collected into one geometry. 
        ret: 
            type: QgsGeometry of linestring or multlinestring type
            val: all input lines, merged to as few lines as possible. 
        """
        mls = QgsMultiLineString()
        for line in args:
            mls.addGeometry(QgsLineString(line.asPolyline()))
        return QgsGeometry(mls).mergeLines()


    def checkForPolygon(self, osmFeat:overpy.Result, geom:QgsGeometry) -> bool:
        """
        Checks if a way should be considered a polygon.
        
        params:
            osmFeat: the overpy way or relation that should is checked
            geom: the QgsGeometry of the object that is being checked. 
        
        returns true if it should be a polygon, otherwise false.

        logic is retrieved from https://wiki.openstreetmap.org/wiki/Overpass_turbo/Polygon_Features and is the same as overpass turbo
        uses polygon-features JSON which is developed by "tyrasd", available here: https://github.com/tyrasd/osm-polygon-features/blob/master/polygon-features.json 
        """
        pl = geom.asPolyline()
        if pl[0] == pl[-1]:
            try: 
                if osmFeat.tags['area'] == 'no':
                    return False
            except KeyError:
                pass

            for filter in self.CONFIG.polygonFeatures:
                polygon = filter['polygon']
                key = filter['key']
                if polygon == 'all':
                    if key in osmFeat.tags:
                        return True # this is a polygon
                elif polygon == 'whitelist':
                    if key in osmFeat.tags:
                        if osmFeat.tags[key] in filter['values']:
                            return True # This is a polygon
                elif polygon == 'blacklist':
                    if key in osmFeat.tags:
                        if osmFeat.tags[key] not in filter['values']:
                            return True # This is a polygon
        else: 
            return False


    def createQgsLayers(self) -> dict:
        """ creates QgsVectorLayers for each output feature and returns the in a dictionary with the layer names as keys """

        lyrs = {}
        for feature in self.CONFIG.features:
            name = getLayerNameFromFeature(feature)
            outGeom = self.CONFIG.configJson[feature]['outputGeom']
            if outGeom == 'point':
                vl = QgsVectorLayer("Point", name, "memory")
            elif outGeom == 'line':
                vl = QgsVectorLayer("LineString", name, "memory")
            elif outGeom == 'polygon':
                if feature in self.CONFIG.bufferSettings.keys():
                    vl = QgsVectorLayer("LineString", name, "memory")
                else:
                    vl = QgsVectorLayer("Polygon", name, "memory")

            crs = QgsCoordinateReferenceSystem("EPSG:4326")
            vl.setCrs(crs)
            pr = vl.dataProvider()
            columns = [QgsField("OSM id", QVariant.Int)]
            tags = [QgsField(tag, QVariant.String) for tag in self.CONFIG.configJson[feature]['outputTags']]
            columns.extend(tags)
            pr.addAttributes(columns)
            vl.updateFields()

            lyrs[feature] = vl

        return lyrs


    def parse(self, res:overpy.Result) -> dict:
        """
        parse parses osm response to dictionary containing QgsVectorLayers
        Each vector layer refers to one feature, specified by the key.

        params:
            res is a overpy result object containing all objects from OSM. 
        ret:
            output is a dictionary of QgsVectorLayers
        """

        layers = self.createQgsLayers()

        print("Parsing Nodes", end="\r")
        nodeGeoms = {}
        for node in res.nodes:
            nodeGeoms[node.id] = QgsPointXY(node.lon, node.lat)

            features = self.getFeatures(node) #list of features the node is part of. 
            if len(features) == 0:
                continue
            
            for feature in features:
                if not self.isRelevant(node,self.CONFIG.configJson[feature]):
                    continue
            
                qPointF = self.createQgsFeature(node, feature)
                qPointF.setGeometry(QgsGeometry.fromPointXY(nodeGeoms[node.id]))

                self.addQgsFeature(layers[feature], qPointF)
        
        print("Parsing Ways ", end="\r")
        wayGeoms = {}
        for way in res.ways:
            points = [QgsPointXY(node.lon, node.lat) for node in way.nodes]
            wayGeoms[way.id] = QgsGeometry.fromPolylineXY(points)

            features = self.getFeatures(way)
            if len(features) == 0:
                continue

            for feature in features: 
                if not self.isRelevant(way,self.CONFIG.configJson[feature]):
                    continue

                qLineF = self.createQgsFeature(way, feature)
                line = wayGeoms[way.id]
                # print("3", line)
                if self.checkForPolygon(way, line):
                    pollyCollection = QgsGeometry.polygonize([line])
                    outGeom = QgsGeometry.collectGeometry(pollyCollection.asGeometryCollection())
                    if self.CONFIG.configJson[feature]['outputGeom'] == 'point':
                        qLineF.setGeometry(outGeom.centroid())
                    else:
                        qLineF.setGeometry(QgsGeometry(outGeom))
                else:
                        qLineF.setGeometry(line)

                self.addQgsFeature(layers[feature], qLineF)

        print("Parsing Relations", end="\r")
        iter = 0
        for relation in res.relations: 
            iter +=1
            # print("parsing realtion",iter, "id =",relation.id)
            features = self.getFeatures(relation)
            if len(features) == 0:
                continue

            for feature in features: 
                if not self.isRelevant(relation, self.CONFIG.configJson[feature]):
                    continue
                
                qRelF = self.createQgsFeature(relation, feature)


                if self.CONFIG.configJson[feature]['outputGeom'] == 'point':
                    p = []
                    for member in relation.members:
                        if member._type_value != 'node':
                            continue
                        p.append(nodeGeoms[member.ref])
                    
                    qRelF.setGeometry(QgsGeometry.fromMultiPointXY(p))
                    
                    self.addQgsFeature(layers[feature], qRelF)


                elif self.CONFIG.configJson[feature]['outputGeom'] == 'line':
                    lines = []
                    for member in relation.members:
                        if member._type_value != 'way':
                            continue
                        lines.append(wayGeoms[member.ref])
                    
                    outGeom = self.mergeLineGeoms(*lines)
                    qRelF.setGeometry(outGeom)
                    self.addQgsFeature(layers[feature], qRelF)

                elif self.CONFIG.configJson[feature]['outputGeom'] == 'polygon':
                    soloMembers = []
                    innerMembers = []
                    outerMembers = []
                    for member in relation.members:
                        if member._type_value != 'way':
                            continue
                        line = wayGeoms[member.ref]
                        if member.role == "outer":
                            outerMembers.append(line)
                        elif member.role == "inner":
                            innerMembers.append(line)
                        else:
                            soloMembers.append(line)
                    
                    soloPolyCollection = QgsGeometry.polygonize(soloMembers)
                    innerPolyCollection = QgsGeometry.polygonize(innerMembers)
                    outerPolyCollection = QgsGeometry.polygonize(outerMembers)

                    soloMultiPoly = QgsGeometry.collectGeometry(soloPolyCollection.asGeometryCollection())
                    innerMultiPoly = QgsGeometry.collectGeometry(innerPolyCollection.asGeometryCollection())
                    outerMultiPoly = QgsGeometry.collectGeometry(outerPolyCollection.asGeometryCollection())

                    if len(innerMembers) > 0: #If inner members, subtract these from outer members.
                        holeMultiPoly = outerMultiPoly.difference(innerMultiPoly)
                    elif len(outerMembers) > 0: #outer members but no inner members
                        holeMultiPoly = outerMultiPoly
                    else: # Neither inner nor outer. Making sure holePolyCollection is empty
                        holeMultiPoly = outerMultiPoly

                    outGeom = QgsGeometry.collectGeometry([holeMultiPoly,soloMultiPoly])

                    qRelF.setGeometry(outGeom)
                    self.addQgsFeature(layers[feature], qRelF)
        return layers

        
    def buffer(self, layer: QgsVectorLayer, feature:str) -> QgsGeometry:
        """
        Buffer ads a buffer for the input feature based on a mapping setting the buffer radii for each tag value
        
        param val: 
            layer: the QgsVectorLayer object to be buffered. 
            feature: The feature that is being buffered. Used to save the buffered layer and to find bufferring settings from CONFIG
        ret val: a QgsGeometry of type polygon. 
        """
        name = getLayerNameFromFeature(feature)
        bufferScheme = self.CONFIG.bufferSettings[feature]

        vl = QgsVectorLayer("Polygon", name, "memory")

        crs = QgsCoordinateReferenceSystem(self.CONFIG.projectedCrs)
        vl.setCrs(crs)
        pr = vl.dataProvider()
        columns = [QgsField("OSM id", QVariant.Int)]
        tags = [QgsField(tag, QVariant.String) for tag in self.CONFIG.configJson[feature]['outputTags']]
        columns.extend(tags)
        pr.addAttributes(columns)
        vl.updateFields()


        layer.startEditing()
        pr = layer.dataProvider()

        for bufferKey in bufferScheme.keys():
            fieldindex = pr.fields().indexOf(bufferKey)
            for f in layer.getFeatures():
                geomTagValue = f.attributes()[fieldindex]
                try:
                    bufferVal = bufferScheme[bufferKey][geomTagValue]
                except KeyError:
                    continue

                buffered = f.geometry().buffer(bufferVal,5)
                f.setGeometry(buffered)
                self.addQgsFeature(vl,f)

        return vl

# %%
