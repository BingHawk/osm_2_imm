# Imports the configuration file and populatates an object of the config class
import importlib.resources
import json
from qgis.core import QgsRectangle

try: 
    from . import static
except ImportError:
    import static

class Config:
    """
    Creates the config object with the following properties: 

    :ivar sortedTags: dictionary that contains exactly one key for every osm key to be called and the list of osm values to that key as value
    :vartype sortedTags: Dict
    :ivar reversedTags: contains tags as keys and the features containing that tag as values in a list. 
    :vartype reversedTags: Dict
    :ivar features: Lists the different categories. 
    :vartype features: List
    :ivar configJson: the unedited configuration.json
    :vartype configJson: Dict
    :ivar polygonFeatures: the unedited polygon-features.json
    :vartype polygonFeatures: Dict
    :ivar bufferSettings: the unedited bufferingSettings.json
    :vartype polygonFeatures: Dict
    :ivar projectedCrs: epsg code for the projected reference system used
    :vartype projectedCrs: String
    :pram outputCrs: epsg code for the reference system used for output
    :vartype projectedCrs: String
    :ivar bbox_[S|M|L|XL|XXL|XL_D|L_D|M_D]: Example bounding boxes of different sizes. Milano without D, Dakar with D. 
    :vartype bbox_[S|M|L|XL|XXL|XL_D|L_D|M_D]: QgsRectangle
    """
    def __init__(self):
        self.sortedTags={} # dictionary that contains exactly one key for every osm key to be called and the list of osm values to that key as value
        self.reversedTags={}
        self.features=[] #list of the different layers. ex. voidGreyAreas or networkStreet
        self.__configurationFilePath = 'configuration.json'
        self.__bufferingSettingsFilePath = 'bufferingSettings.json'
        self.__polygon_featuresFilePath = 'polygon-features.json'

        with importlib.resources.open_text(static, self.__configurationFilePath) as file:
            self.configJson = json.load(file)
            self.layerDefenition = {key: val for key, val in self.configJson.items() if key != 'bbox' and key != 'crs'}

        with importlib.resources.open_text(static, self.__polygon_featuresFilePath) as file:
            self.polygonFeatures = json.load(file)

        with importlib.resources.open_text(static, self.__bufferingSettingsFilePath) as file:
            self.bufferSettings = json.load(file)

        self.__sortTags()
        self.__reverseTags()
        # Addign the CRS:s chosen
        self.projectedCrs = self.configJson["crs"]["projected"]
        self.outputCrs = self.configJson["crs"]["output"]

        # adding the bboxs for testing on smaller area. 
        self.bbox_XXL = self.__createQgsRectangle(self.configJson['bbox']['bbox_xxlarge'])
        self.bbox_XL = self.__createQgsRectangle(self.configJson['bbox']['bbox_xlarge'])
        self.bbox_L = self.__createQgsRectangle(self.configJson['bbox']['bbox_large'])
        self.bbox_M = self.__createQgsRectangle(self.configJson['bbox']['bbox_std'])
        self.bbox_S = self.__createQgsRectangle(self.configJson['bbox']['bbox_small'])
        self.bbox_XS = self.__createQgsRectangle(self.configJson['bbox']['bbox_xsmall'])
        self.bbox_XL_D = self.__createQgsRectangle(self.configJson['bbox']['bbox_xlarge_dakar'])
        self.bbox_L_D = self.__createQgsRectangle(self.configJson['bbox']['bbox_large_dakar'])
        self.bbox_M_D = self.__createQgsRectangle(self.configJson['bbox']['bbox_std_dakar'])

        # Adding the features as attributes of the config object
        # TODO: make dynamic so user can specify wanted attributes. 
        
        # self.networkStreet = self.configJson["networkStreet"]
        # self.networkBikelanes = self.configJson["networkBikelanes"]
        # self.networkBikeRacks = self.configJson["networkBikeRacks"]
        # self.networkParkings = self.configJson["networkParkings"]
        # self.networkTaxi = self.configJson["networkTaxi"]
        # self.networkPTLines = self.configJson["networkPtLines"]
        # self.networkPTStops = self.configJson["networkPtStops"]
        # self.usesActivities = self.configJson["usesActivities"]
        # self.usesLanduse = self.configJson["usesLanduse"]
        # self.usesServices = self.configJson["usesServices"]
        # self.boundariesAdministrative = self.configJson["boundariesAdministrative"]
        # self.voidAreasOpenAir = self.configJson["voidAreasOpenAir"]
        # self.voidBlocks = self.configJson["voidBlocks"]
        # self.voidBlueAreas = self.configJson["voidBlueAreas"]
        # self.voidGreenAreas = self.configJson["voidGreenAreas"]
        # self.voidGreyAreas = self.configJson["voidGreyAreas"]
        # self.voidTrees = self.configJson["voidTrees"]
        # self.volumeBuildings = self.configJson["volumeBuildings"]

    def __createQgsRectangle(self, coordString:str) -> QgsRectangle:
        coords = list(map(lambda x: float(x), coordString.split(",")))
        coords = [coords[1],coords[0],coords[3],coords[2]]
        return QgsRectangle(*coords)

    def __reverseTags(self):
        for feature in self.configJson.keys():
            try:
                for key in self.configJson[feature]['inputTags'].keys():
                    if key in self.reversedTags:
                        if feature not in self.reversedTags[key]:
                            self.reversedTags[key].append(feature)
                    else: 
                        self.reversedTags[key] = [feature]
            except KeyError: # For entrances in the config that is not features and thus lack 'inputTags' field
                continue
            except TypeError: # For entrances that does not have aditional levels of dictionaries
                continue
        
            self.features.append(feature)


    # Sorting tags and placing them in sorted tags.
    def __sortTags(self):
        for feature in self.layerDefenition.values():
            inputTags = feature['inputTags']
            for tagKey in inputTags.keys():
                if tagKey not in self.sortedTags:
                    self.sortedTags[tagKey] = []
                self.sortedTags[tagKey].extend(inputTags[tagKey])
        
        for tagKey in self.sortedTags.keys(): #Remove duplicates in each tagValue list. 
            self.sortedTags[tagKey] = list(dict.fromkeys(self.sortedTags[tagKey]))
        



if __name__ == "__main__":
    config = Config()

    print("json", config.configJson['networkParkings']['inputTags'])