#%%
from shapely.geometry import MultiPolygon, Polygon, Point, MultiPoint, LineString, MultiLineString
from shapely.ops import linemerge
import geopandas as gpd

try:
    from ..settings.config import Config
except ValueError:
    from settings.config import Config
from .query import Query

import time

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


# Gets the freatures that the obj is part of. 
# obj can be a relation, way or node of an overpy result object. 
# Returns a list of the features the object is part relevant for according to config file. 
def getFeatures(obj):
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


# checkForPolygon checks if a way should be considered a polygon.
# it takes the feature from an overpy result object and its shapely geometry
# returns true if it should be a polygon, otherwise false. 
# logic is retrieved from https://wiki.openstreetmap.org/wiki/Overpass_turbo/Polygon_Features and is the same as overpass turbo
# uses polygon-features JSON which is developed by "tyrasd", available here: https://github.com/tyrasd/osm-polygon-features/blob/master/polygon-features.json 
def checkForPolygon(way, geom):
    if not geom.is_closed:
        return False
    try: 
        if way.tags['area'] == 'no':
            return False
    except KeyError:
        pass

    for filter in CONFIG.polygonFeatures:
        polygon = filter['polygon']
        key = filter['key']
        if polygon == 'all':
            if key in way.tags:
                return True # this is a polygon
        elif polygon == 'whitelist':
            if key in way.tags:
                if way.tags[key] in filter['values']:
                    return True # This is a polygon
        elif polygon == 'blacklist':
            if key in way.tags:
                if way.tags[key] not in filter['values']:
                    return True # This is a polygon
            

# parse parses osm response to geopandas object
# res is a overpy result object containing all objects from OSM. 
# output is a dictionary of geodataframes
# Each dataframe refers to one feature, specified by the key.
def parse(res):
    all = {}
    for confFeature in CONFIG.features:
        all[confFeature] = []

    print("Parsing Nodes", end="\r")
    nodeCoords = {}
    for node in res.nodes:
        nodeCoords[node.id] = Point(node.lon, node.lat)

        features = getFeatures(node)
        if len(features) == 0:
            continue
        
        for feature in features:
            if not relevant(node,CONFIG.configJson[feature]):
                continue
            n = {}
            n['geometry']=nodeCoords[node.id]
            n['id']=node.id
            n.update(getTags(node, CONFIG.configJson[feature]))

            all[feature].append(n)
    
    print("Parsing Ways", end="\r")
    wayCoords = {}
    for way in res.ways:
        points = [Point(node.lon, node.lat) for node in way.nodes]
        wayCoords[way.id] = LineString(points)
        features = getFeatures(way)
        if len(features) == 0:
            continue

        for feature in features: 
            if not relevant(way,CONFIG.configJson[feature]):
                continue

            w = {}
            line = wayCoords[way.id]
            if checkForPolygon(way, line):
                w['geometry'] = Polygon(line)
            else: 
                w['geometry'] = line

            w['id']=way.id
            w.update(getTags(way, CONFIG.configJson[feature]))

            all[feature].append(w)

    print("Parsing Relations", end="\r")
    for relation in res.relations: 
        features = getFeatures(relation)
        if len(features) == 0:
            continue

        for feature in features: 
            if not relevant(relation, CONFIG.configJson[feature]):
                continue
            r = {}
            r['id'] = relation.id

            if CONFIG.configJson[feature]['inputGeom'] == 'node':
                p = []
                for member in relation.members:
                    if member._type_value != 'node':
                        continue
                    p.append(nodeCoords[member.ref])

                r['geometry'] = MultiPoint(p)
                r.update(getTags(relation, CONFIG.configJson[feature]))
                all[feature].append(r)

            elif CONFIG.configJson[feature]['inputGeom'] == 'way':
                l = []
                inner = []
                outer = []
                for member in relation.members:
                    if member._type_value != 'way':
                        continue
                    line = wayCoords[member.ref]
                    if member.role == "outer":
                        outer.append(line)
                    elif member.role == "inner":
                        inner.append(line)
                    else:
                        l.append(line)

                polys = []
                lines = []

                openLines = MultiLineString(l)
                openLines = linemerge(openLines)

                if openLines.geom_type == "LineString":
                    if checkForPolygon(relation, openLines):
                        polys.append(Polygon(openLines))
                    else:
                        lines.append(openLines)
                elif openLines.geom_type != "LineString":
                    for openLine in openLines.geoms:
                        if checkForPolygon(relation, openLine):
                            polys.append(Polygon(openLine))
                        else:
                            lines.append(openLine)
                        
                
                outLines = MultiLineString(outer)
                outLines = linemerge(outLines)

                inLines = MultiLineString(inner)
                inLines = linemerge(inLines)

                if outLines.geom_type == 'LineString' and inLines.geom_type == 'LineString':
                    poly = Polygon(outLines)
                    if inLines.is_closed:
                        poly = poly.difference(Polygon(inLines))
                    polys.append(poly)

                elif outLines.geom_type == 'LineString' and inLines.geom_type != 'LineString':
                    poly = Polygon(outLines)
                    for inLine in inLines.geoms:
                        if inLine.is_closed:
                            poly = poly.difference(Polygon(inLine))
                        else:
                            continue
                    polys.append(poly)

                elif outLines.geom_type != 'LineString' and inLines.geom_type == 'LineString':
                    for outLine in outLines.geoms:
                        if outLine.is_closed:
                            poly=Polygon(outLine)
                        else:
                            continue
                        if inLines.is_closed:
                            poly = poly.difference(Polygon(inLines))
                        polys.append(poly)
                
                elif outLines.geom_type != 'LineString' and inLines.geom_type != 'LineString':
                    for outLine in outLines.geoms:
                        if outLine.is_closed:
                            poly=Polygon(outLine)
                        else:
                            continue
                        for inLine in inLines.geoms:
                            if inLine.is_closed:
                                poly = poly.difference(Polygon(inLine))
                            else:
                                continue
                        polys.append(poly)


                r.update(getTags(relation, CONFIG.configJson[feature]))
                if len(lines) == 0 and len(polys) != 0:
                    r['geometry'] = MultiPolygon(polys)
                    all[feature].append(r)
                elif len(lines) != 0 and len(polys) == 0:
                    r['geometry'] = MultiLineString(lines)
                    all[feature].append(r)
                elif len(lines) != 0 and len(polys) != 0:
                    print("Waring, relation {} has both lines and polygons".format(relation.id))
                    r['geometry'] = MultiLineString(lines)
                    all[feature].append(r)
                    r['geometry'] = MultiPolygon(polys)
                    all[feature].append(r)

    for feature in all.keys():
        if len(all[feature]) > 0:
            all[feature] = gpd.GeoDataFrame(all[feature]).set_crs("epsg:4326").to_crs(CONFIG.projectedCrs)
        else: 
            all[feature] = None
    
    return all

            
# buffer ads a buffer for the input feature based on a mapping setting the buffer radii for each tag value
# gdf - the geodataframe containg the features to be buffered. 
# bufferScheme - a CONFIG attribute containing a dictionary with buffer radii for every Key-Value tag pair in the feature.
# Output - a GeoDataFrame with all geometries buffered. 
def buffer(gdf, bufferScheme):
    for keyTag in bufferScheme.keys():
        length = len(gdf)
        bufferPolys = []
        for i in range(length):
            try:
                bufferVal = bufferScheme[keyTag][gdf.loc[i,keyTag]]
            except KeyError: #no buffer info on this tag value
                print("The value {} has no buffering setting recorded".format(gdf.loc[i,keyTag]), "id = ",i)
                continue
            bufferGeom = gdf.loc[i,'geometry'].buffer(bufferVal)
            bufferPolys.append(bufferGeom)
        gdf = gdf.set_geometry(bufferPolys)
        print(keyTag, "buffered")
    return gdf


# subtract takes a geodataframe containing polygons and a CONFIG.bbox object, and subtracts the GDF from the bbox square
# gdf - a GeoDataFrame containing polygons
# bbox - a CONFIG.bbox attribute. 
def subtract(gdf, bbox):
    bbox = bbox.split(", ")
    lowLeft = Point(float(bbox[1]),float(bbox[0]))
    lowRight = Point(float(bbox[1]),float(bbox[2]))
    topRight = Point(float(bbox[3]),float(bbox[2]))
    topLeft = Point(float(bbox[3]),float(bbox[0]))
    bbox = gpd.GeoDataFrame({"geometry":Polygon([lowLeft, lowRight, topRight, topLeft])}, index = [0]).set_crs("epsg:4326").to_crs(CONFIG.projectedCrs)

    if gdf.crs != CONFIG.projectedCrs:
        gdf.set_crs(CONFIG.projectedCrs)
    gdf.plot()
    #ticO = time.time()
    polys = bbox.overlay(gdf, how='difference', make_valid=False)
    #tocO = time.time()

    #print("overlay took",tocO-ticO,"seconds")
    out = polys.explode()

    return out



# %%
