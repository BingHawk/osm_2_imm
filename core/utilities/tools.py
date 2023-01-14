from qgis.core import QgsRectangle, QgsVectorLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject

def camelCaseSplit(str):
    """
    Split a string into list on camel case. 

    ex: "camelCaseSplit" will return ["camel", "Case", "Split"]

    :param str: string to split.
    :type str: string.

    :return: all words in param string
    :rtype: list. 
    """
     
    start_idx = [i for i, e in enumerate(str)
                 if e.isupper()] + [len(str)]
 
    start_idx = [0] + start_idx
    return [str[x: y] for x, y in zip(start_idx, start_idx[1:])]

def getOsmBboxString(qRect: QgsRectangle) -> str:
    """
    converts a QgsRectangle into a String usable for querying OSM
    """
    out = f"{qRect.yMinimum()},{qRect.xMinimum()},{qRect.yMaximum()},{qRect.xMaximum()}"
    return out

def getLayerNameFromFeature(feature:str) -> str:
    name = camelCaseSplit(feature)
    return '_'.join(name[1:]).lower()

def getGroupNameFromFeature(feature:str) -> str:
    name = camelCaseSplit(feature)
    return name[0]

def transformQLayer(project:QgsProject, qLayer:QgsVectorLayer, crsSrc:QgsCoordinateReferenceSystem, crsDest:QgsCoordinateReferenceSystem) -> QgsVectorLayer:
    """ Transforms qLayer from crsSrc to crsDest coordinate systems using project.transformContext. Can only transform layers of WKB types, 1,2,3,5 or 6 """
    
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
    elif qLayer.wkbType() == 2 or qLayer.wkbType() == 5:
        vl = QgsVectorLayer("linestring", "grey_areas","memory")
    elif qLayer.wkbType() == 3 or qLayer.wkbType() == 6:
        vl = QgsVectorLayer("polygon", "grey_areas","memory")
    else:
        raise TypeError(f"unexpected wkbType of input layer: {qLayer.wkbType()}. input layer: {qLayer}")

    vl.setCrs(crsDest)
    pr = vl.dataProvider()
    pr.addAttributes(columns)
    pr.addFeatures(feats)
    vl.updateExtents()

    return vl