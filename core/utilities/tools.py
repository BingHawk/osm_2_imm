from qgis.core import QgsRectangle

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
    return qRect.toString().replace(" : ", ",")
