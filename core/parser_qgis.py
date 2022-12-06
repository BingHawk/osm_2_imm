#%%
from qgis.core import ( QgsVectorLayer,
                        QgsLineString,
                        QgsMultiLineString,
                        QgsPointXY,
                        QgsPoint,
                        QgsGeometry,
                        QgsField,
                        QgsFeature,
                        QgsFields,
                        QgsMultiPolygon,
                        QgsCoordinateReferenceSystem,
                        QgsVectorFileWriter,
                        QgsProject)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QProgressDialog, QProgressBar


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
        self.fid = 0

        self.qgsLyrs:dict = {}
        self.qgsFields:dict = {}
        
        self.createQgsLayers()

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

    def createQgsLayers(self) -> None:
        """ 
        creates QgsVectorLayers for each output feature.
        Creates the following properties:
            self.qgsLayers:  a dictionary with the layer names as keys and a QgsLayer as value
        """

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

            if not vl or not vl.isValid:
                print(f"layer {feature} was not created")

            self.qgsLyrs[feature] = vl


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

        fields = self.qgsLyrs[feature].fields()
        f = QgsFeature(fields)
        f['OSM id'] = obj.id
        for key in obj.tags.keys(): 
            if key in outTags:
                f[key] = obj.tags[key]
        return f


    def addQgsFeatures(self, lyr:QgsVectorLayer, feat:QgsFeature) -> bool:
        """ 
        Helper functions that adds a feature to a layers data provider and updates the layer
        param: 
            lyr: a QgsVectorLayer to which the feature should be added
            feat: a list of QgsFeature objects to be added to the layer
        ret: tuple (exitFlag: bool, nSuccess: int, nFailed: int)
            exitFlag: True if all features in feat was added successfully. 
            nSuccess: number of features added
            nFailed: number of features that was not added. 
        """
        # filter out features that does not have same geometry type as layer. 
        lyrGeomType = lyr.geometryType()
        filteredFeat = [f for f in feat if f.geometry().type() == lyrGeomType]
        if len(filteredFeat) == 0:
            return False, 0, len(feat)

        pr = lyr.dataProvider()
        countBefore = pr.featureCount()

        res, lyrFeatures = pr.addFeatures(filteredFeat)
        lyr.updateExtents()

        countAfter = pr.featureCount()
        nSucsess = countAfter - countBefore
        nFailed = len(lyrFeatures) - nSucsess

        return res, nSucsess, nFailed



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



    def parse(self, res:overpy.Result) -> dict:
        """
        parse parses osm response to dictionary containing QgsVectorLayers
        Each vector layer refers to one feature, specified by the key.

        params:
            res is a overpy result object containing all objects from OSM. 
        ret:
            output is a dictionary of QgsVectorLayers
        """

        nodesParsed = 0
        waysParsed = 0
        relsParsed = 0
        nodeSuccess = 0
        nodeFailed = 0
        waySuccess = 0
        wayFailed = 0
        relSuccess = 0
        relFailed = 0
        validNodes = 0

        failedLayers = []

        #layers = self.createQgsLayers()

        print("Parsing Nodes", end="\r")
        nodeGeoms = {}
        nodeQgsFeatures = {}
        for node in res.nodes:
            nodeGeoms[node.id] = QgsPointXY(node.lon, node.lat)
            if node.id == 5684222890:
                print("Found the taxi!")

            # try: 
            #     if node.tags['natural'] != "tree":
            #         continue
            # except KeyError:
            #     continue

            features = self.getFeatures(node) #list of features the node is part of. 
            if len(features) == 0:
                continue
            
            for feature in features:
                if not self.isRelevant(node,self.CONFIG.configJson[feature]):
                    continue
                
                # print("parsing {} feature".format(feature))

                qPointF = self.createQgsFeature(node, feature)
                pointGeom = QgsGeometry.fromPointXY(nodeGeoms[node.id])
                # pointGeom = QgsGeometry(QgsPoint(node.lon, node.lat))

                qPointF.setGeometry(pointGeom)

                geosValid = qPointF.geometry().isGeosValid()
                qPointF.setGeometry(qPointF.geometry().centroid())
                featureValid = qPointF.isValid()

                # if feature not in nodeQgsFeatures.keys():
                #     nodeQgsFeatures[feature] = []
                # nodeQgsFeatures[feature].append(qPointF)

                success, _, _ = self.addQgsFeatures(self.qgsLyrs[feature], [qPointF])
                if success:
                    nodeSuccess += 1
                else:
                    nodeFailed += 1
                    failedLayers.append(feature)

            nodesParsed += 1
        
        # for feature in nodeQgsFeatures.keys():
        #     success, nSuccess, nFalied = self.addQgsFeatures(self.qgsLyrs[feature], nodeQgsFeatures[feature])
        #     if success:
        #         nodeSuccess += nSuccess
        #     else:
        #         nodeFailed += nFalied
        #         nodeSuccess += nSuccess
        #         failedLayers.append(feature)
    
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

                success = self.addQgsFeatures(self.qgsLyrs[feature], [qLineF])
                if success:
                    waySuccess += 1
                else:
                    wayFailed += 1
                    failedLayers.append(feature)
            
            waysParsed += 1

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

                    
                    self.addQgsFeatures(self.qgsLyrs[feature], [qRelF])


                elif self.CONFIG.configJson[feature]['outputGeom'] == 'line':
                    lines = []
                    for member in relation.members:
                        if member._type_value != 'way':
                            continue
                        lines.append(wayGeoms[member.ref])
                    
                    outGeom = self.mergeLineGeoms(*lines)
                    qRelF.setGeometry(outGeom)
                    self.addQgsFeatures(self.qgsLyrs[feature], [qRelF])

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
                    success = self.addQgsFeatures(self.qgsLyrs[feature], [qRelF])
                    if success:
                        relSuccess += 1
                    else:
                        relFailed += 1
                        failedLayers.append(feature)
            
            relsParsed += 1

        print(f"Statistics Nodes:\n\tnodes parsed: {nodesParsed}\n\tsuccess: {nodeSuccess}\n\tfailed: {nodeFailed}\n\tvalid: {validNodes}")
        print(f"Statistics Ways:\n\tways parsed: {waysParsed}\n\tsuccess: {waySuccess}\n\tfailed: {wayFailed}")
        print(f"Statistics Relations\n\trelations parsed: {relsParsed}\n\tsuccess: {relSuccess}\n\tfailed: {relFailed}")
        print(f"Statistics Total\n\tparsed: {nodesParsed+waysParsed+relsParsed}\n\tsuccess: {nodeSuccess+waySuccess+relSuccess}\n\tfailed: {nodeFailed+wayFailed+relFailed}")
        print(set(failedLayers))
        return self.qgsLyrs

        
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
                self.addQgsFeatures(vl,[f])

        return vl

# %%
