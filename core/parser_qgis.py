#%%
from qgis.core import ( QgsVectorLayer,
                        QgsLineString,
                        QgsMultiLineString,
                        QgsPointXY,
                        QgsGeometry,
                        QgsField,
                        QgsFeature,
                        QgsFields,
                        QgsMultiPolygon,
                        QgsCoordinateReferenceSystem )
from qgis.PyQt.QtCore import QVariant

from .utilities.tools import camelCaseSplit

import overpy

try:
    from ..settings.config import Config
except ValueError:
    from settings.config import Config

## set upp ##

CONFIG = Config()


# relevant is a helper function that checks if the tags of feat are relevant for parsing
# feat - a overpy relation, way or node object which tags to check for relevance
# confFeature - the attribute of CONFIG the feature should be checked against
# returns True if the feature is relevant
def relevant(feat, confFeature):
    relevant = False
    for key in confFeature['inputTags'].keys():
        try:
            if feat.tags[key] in confFeature['inputTags'][key]:
                relevant = True
        except KeyError:
            pass
    return relevant

def getFeatures(obj:overpy.Result) -> list:
    """
    Gets the freatures that the obj is part of. 

    param obj: relation, way or node of an overpy result object. 
    ret: list of the features the object is part relevant for according to config file. 
    """
    features = []
    for tag in obj.tags.keys():
        try: 
            features.extend(CONFIG.reversedTags[tag])
        except KeyError:
            continue
    return features

# getTags is a helper function that returns a dictionary of tags that should be kept
# feat - a overpy relation, way or node whose tags are candidates. 
# confFeature - the attribute of CONFIG that decides which tags should be output
# tags - "All" or "Config" deciding if all tags or those listed in config should be outputed. 
def getTags(feat, confFeature):
    t = {}
    for key in feat.tags.keys():
        if key in confFeature['outputTags']:
            t[key] = feat.tags[key]
    return t

def initFeature(tags:dict, id:int) -> QgsFeature:
    fields = QgsFields()
    for key in tags.keys() : fields.append(QgsField(key, QVariant.String)) 
    fields.append(QgsField("OSM id", QVariant.Int))
    f = QgsFeature(fields)
    for key in tags.keys(): 
        f[key] = tags[key]
    f['OSM id'] = id
    return f

def featureAdd(lyr:QgsVectorLayer, feat:QgsFeature):
    """ Helper functions that adds a feature to a layers data provider and updates the layer"""

    pr = lyr.dataProvider()
    pr.addFeature(feat)
    lyr.updateExtents()

def mergeLineGeoms(*args:QgsGeometry)-> QgsGeometry:
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

# checkForPolygon checks if a way should be considered a polygon.
# it takes the feature from an overpy result object and its shapely geometry
# returns true if it should be a polygon, otherwise false. 
# logic is retrieved from https://wiki.openstreetmap.org/wiki/Overpass_turbo/Polygon_Features and is the same as overpass turbo
# uses polygon-features JSON which is developed by "tyrasd", available here: https://github.com/tyrasd/osm-polygon-features/blob/master/polygon-features.json 
def checkForPolygon(OsmFeat, geom):
    pl = geom.asPolyline()
    if pl[0] == pl[-1]:
        try: 
            if OsmFeat.tags['area'] == 'no':
                return False
        except KeyError:
            pass

        for filter in CONFIG.polygonFeatures:
            polygon = filter['polygon']
            key = filter['key']
            if polygon == 'all':
                if key in OsmFeat.tags:
                    return True # this is a polygon
            elif polygon == 'whitelist':
                if key in OsmFeat.tags:
                    if OsmFeat.tags[key] in filter['values']:
                        return True # This is a polygon
            elif polygon == 'blacklist':
                if key in OsmFeat.tags:
                    if OsmFeat.tags[key] not in filter['values']:
                        return True # This is a polygon
    else: 
        return False
                

def createLayers() -> dict:
    """ creates QgsVectorLayers for each output feature and returns the in a dictionary with the layer names as keys """

    lyrs = {}
    for feature in CONFIG.features:
        name = camelCaseSplit(feature)
        name = '_'.join(name[1:]).lower()
        outGeom = CONFIG.configJson[feature]['outputGeom']
        if outGeom == 'point':
            vl = QgsVectorLayer("Point", name, "memory")
        elif outGeom == 'line':
            vl = QgsVectorLayer("LineString", name, "memory")
        elif outGeom == 'polygon':
            vl = QgsVectorLayer("Polygon", name, "memory")

        crs = QgsCoordinateReferenceSystem("EPSG:4326")
        vl.setCrs(crs)
        pr = vl.dataProvider()
        columns = [QgsField(tag, QVariant.String) for tag in CONFIG.configJson[feature]['outputTags']]
        pr.addAttributes(columns)
        vl.updateFields() 


        lyrs[feature] = vl

    return lyrs


# parse parses osm response to geopandas object
# res is a overpy result object containing all objects from OSM. 
# output is a dictionary of geodataframes
# Each dataframe refers to one feature, specified by the key.
def parse(res):
    layers = createLayers()

    print("Parsing Nodes", end="\r")
    nodeGeoms = {}
    for node in res.nodes:
        nodeGeoms[node.id] = QgsPointXY(node.lon, node.lat)

        features = getFeatures(node) #list of features the node is part of. 
        if len(features) == 0:
            continue
        
        for feature in features:
            if not relevant(node,CONFIG.configJson[feature]):
                continue
        
            tags = getTags(node, CONFIG.configJson[feature])
            qPointF = initFeature(tags, node.id)
            qPointF.setGeometry(QgsGeometry.fromPointXY(nodeGeoms[node.id]))

            featureAdd(layers[feature], qPointF)
    
    print("")
    for key in layers.keys():
        pr = layers[key].dataProvider()
        print(key, pr.featureCount())

    
    print("Parsing Ways ", end="\r")
    wayGeoms = {}
    for way in res.ways:
        points = [QgsPointXY(node.lon, node.lat) for node in way.nodes]
        wayGeoms[way.id] = QgsGeometry.fromPolylineXY(points)

        features = getFeatures(way)
        if len(features) == 0:
            continue

        for feature in features: 
            if not relevant(way,CONFIG.configJson[feature]):
                continue

            tags = getTags(way, CONFIG.configJson[feature])
            qLineF = initFeature(tags, way.id)
            line = wayGeoms[way.id]
            # print("3", line)
            if checkForPolygon(way, line):
                if feature == "volumeBuildings":
                    print("polygon true")
                pollyCollection = QgsGeometry.polygonize([line])
                outGeom = pollyCollection.asGeometryCollection()[0]
                if len(pollyCollection.asGeometryCollection()) > 0:
                    print("lost geom")
                if CONFIG.configJson[feature]['outputGeom'] == 'point':
                    qLineF.setGeometry(outGeom.centroid())
                else:
                    qLineF.setGeometry(QgsGeometry(outGeom))
            else:
                if feature == "volumeBuildings":
                    print("polygon false")
                if CONFIG.configJson[feature]['outputGeom'] == 'polygon':
                    try:
                        qLineF.setGeometry(buffer(line, tags, CONFIG.bufferSettings[feature]))
                    except KeyError:
                        pass
                else:
                    qLineF.setGeometry(line)
            
            if feature == "volumeBuildings":
                print(qLineF.attributes())
                print(qLineF.geometry().asWkt())

            featureAdd(layers[feature], qLineF)

    print("")
    for key in layers.keys():
        pr = layers[key].dataProvider()
        print(key, pr.featureCount())
            # for f in layers["volumeBuildings"].getFeatures():
            #     print("Feature:", f.id(), f.attributes(), f.geometry().asWkt())

    print("Parsing Relations", end="\r")
    iter = 0
    for relation in res.relations: 
        iter +=1
        # print("parsing realtion",iter, "id =",relation.id)
        features = getFeatures(relation)
        if len(features) == 0:
            continue

        for feature in features: 
            if not relevant(relation, CONFIG.configJson[feature]):
                continue
            
            tags = getTags(relation, CONFIG.configJson[feature])
            qRelF = initFeature(tags, relation.id)


            if CONFIG.configJson[feature]['outputGeom'] == 'point':
                p = []
                for member in relation.members:
                    if member._type_value != 'node':
                        continue
                    p.append(nodeGeoms[member.ref])
                
                qRelF.setGeometry(QgsGeometry.fromMultiPointXY(p))
                
                featureAdd(layers[feature], qRelF)


            elif CONFIG.configJson[feature]['outputGeom'] == 'line':
                lines = []
                for member in relation.members:
                    if member._type_value != 'way':
                        continue
                    lines.append(wayGeoms[member.ref])
                
                outGeom = mergeLineGeoms(*lines)
                qRelF.setGeometry(outGeom)
                featureAdd(layers[feature], qRelF)

            elif CONFIG.configJson[feature]['outputGeom'] == 'polygon':
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

                if len(innerMembers) > 0: #If inner members, subtract these from outer members.
                    holePolyCollection = outerPolyCollection.makeDifference(innerPolyCollection)
                elif len(outerMembers) > 0: #outer members but no inner members
                    holePolyCollection = outerPolyCollection
                else: # Neither inner nor outer. Making sure holePolyCollection is empty
                    holePolyCollection = outerPolyCollection

                outGeom = soloPolyCollection.combine(holePolyCollection)

                qRelF.setGeometry(outGeom)
                featureAdd(layers[feature], qRelF)
    return layers

        
def buffer(geom: QgsGeometry, tags:dict, bufferScheme:dict) -> QgsGeometry:
    """
    Buffer ads a buffer for the input feature based on a mapping setting the buffer radii for each tag value
    
    param val: 
        geom: the QgsGeometry object to be buffered. 
        tags: the tags of the feature to be buffered
        bufferScheme: a CONFIG attribute containing a dictionary with buffer radii for every Key-Value tag pair in the feature.
    ret val: a QgsGeometry of type polygon. 
    """

    for keyTag in bufferScheme.keys():
        try:
            geomTagValue = tags[keyTag]
        except KeyError:
            print(f"The key {keyTag} does not exist in the feature.\n\tExisting tags are {tags}")
        try:
            bufferVal = bufferScheme[keyTag][geomTagValue]
            buffered = geom.buffer(bufferVal,5)
        except KeyError:
            print(f"The tag {keyTag}:{geomTagValue} has no buffering setting recorded")
    return buffered

# %%
