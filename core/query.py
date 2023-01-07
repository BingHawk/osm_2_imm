import overpy
import time

from .utilities.tools import getOsmBboxString

from qgis.core import QgsRectangle

class Query:
    API = overpy.Overpass()

    @staticmethod
    def __unionTags(geom, tags = None, **kwargs):
        """ 
        Takes one or more list of tags as key = [values] or as a dictionary with {key = [values]} and returns a string to be used in Overpass QL query.
        All tags must be of the same type specified in geom = "node", "way", "area" or "rel"
        returns the union of the tags as string
        """

        outString = '('
        if tags == None:
            for key in kwargs.keys():
                for tag in kwargs[key]:
                    outString += '''{}["{}"="{}"];'''.format(geom, key, tag)
        else:
            for tagKey in tags.keys():
                for tagValue in tags[tagKey]:
                    outString += '''{}["{}"="{}"];'''.format(geom, tagKey, tagValue)
        outString += ')'
        return outString
    
    
    @classmethod
    def tagGet(cls, geom:str, tags:dict, bbox:str, printquery = False) -> overpy.Result:
        """
        Formats and sends a query to overpass with overpy and returns the result. 

        param val:
            geom: enum node|way|rel|nw|nr|wr|nwr
            tags: dictionary containging the key-value pairs to be queried
            bbox: a string of coordinates in format "(west,south,east,north)" in wgs84 coordinates
            printquery: True will print the querystring sent to overpy. 
        ret val: 
            the result from overpass as an overpy.Result object.
        """

        queryString = '''
        [out:json][bbox:{}];
        {};
        (._;>;);
        out;
        '''.format(getOsmBboxString(bbox), cls.__unionTags(geom, tags))
        if printquery:
            print(queryString)
        while True:
            try:
                print("querying OSM", end="\r")
                res = cls.API.query(queryString)
                print("query completed sucsessfully")
                break
            except overpy.exception.OverpassTooManyRequests:
                print("Too many requests, sleeping")
                time.sleep(30)
            except overpy.exception.OverpassGatewayTimeout:
                print("Server load too high, sleeping 30s")
                time.sleep(30)               

        return res

    @classmethod
    def bboxGet(cls, bbox:QgsRectangle, printquery = False):
        """
        testing
        """
        queryString = '''
        [out:json];
        nwr({});
        (._;>;);
        out;
        '''.format(getOsmBboxString(bbox))

        if printquery:
            print(queryString)

        while True:
            try:
                print("querying OSM")
                res = cls.API.query(queryString)
                print("query completed sucsessfully")
                break
            except overpy.exception.OverpassTooManyRequests:
                print("Too many requests, sleeping 30s")
                time.sleep(30)
            except overpy.exception.OverpassGatewayTimeout:
                print("Server load too high, sleeping 30s")
                time.sleep(30)
        return res

    @classmethod
    def getQueryString(self, geom, tags, bbox):
        """ 
        Retuerns the query string without making the query. 
        Useful for testing query in overpass turbo first. 
        """
        queryString = '''
        [out:json][bbox:{}];
        {};
        (._;>;);
        out;
        '''.format(bbox, self.__unionTags(geom, tags))
        return queryString