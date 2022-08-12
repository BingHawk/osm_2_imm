# Imports the configuration file and populatates an object of the config class
import importlib.resources
import json

from . import static

class Config:
    def __init__(self):
        self.sortedTags={} # dictionary that contains exactly one key for every osm key to be called and the list of osm values to that key as value
        self.reversedTags={}
        self.features=[] #list of the different layers. ex. voidGreyAreas or networkStreet
        self.__configurationFilePath = 'configuration.json'
        self.__bufferingSettingsFilePath = 'bufferingSettings.json'
        self.__polygon_featuresFilePath = 'polygon-features.json'

        with importlib.resources.open_text(static, self.__configurationFilePath) as file:
            self.configJson = json.load(file)

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
        self.bbox_XXL = self.configJson['bbox']['bbox_xxlarge']
        self.bbox_XL = self.configJson['bbox']['bbox_xlarge']
        self.bbox_L = self.configJson['bbox']['bbox_large']
        self.bbox_M = self.configJson['bbox']['bbox_std']
        self.bbox_S = self.configJson['bbox']['bbox_small']
        self.bbox_XL_D = self.configJson['bbox']['bbox_xlarge_dakar']
        self.bbox_L_D = self.configJson['bbox']['bbox_large_dakar']
        self.bbox_M_D = self.configJson['bbox']['bbox_std_dakar']

        # Adding the features as attributes of the config object
        # TODO: make dynamic so user can specify wanted attributes. 
        
        self.networkStreet = self.configJson["networkStreet"]
        self.networkBikelanes = self.configJson["networkBikelanes"]
        self.networkBikeRacks = self.configJson["networkBikeRacks"]
        self.networkParkings = self.configJson["networkParkings"]
        self.networkTaxi = self.configJson["networkTaxi"]
        self.networkPTLines = self.configJson["networkPtLines"]
        self.networkPTStops = self.configJson["networkPtStops"]
        self.usesActivities = self.configJson["usesActivities"]
        self.usesLanduse = self.configJson["usesLanduse"]
        self.usesServices = self.configJson["usesServices"]
        self.boundariesAdministrative = self.configJson["boundariesAdministrative"]
        self.voidAreasOpenAir = self.configJson["voidAreasOpenAir"]
        self.voidBlocks = self.configJson["voidBlocks"]
        self.voidBlueAreas = self.configJson["voidBlueAreas"]
        self.voidGreenAreas = self.configJson["voidGreenAreas"]
        self.voidGreyAreas = self.configJson["voidGreyAreas"]
        self.voidTrees = self.configJson["voidTrees"]
        self.volumeBuildings = self.configJson["volumeBuildings"]

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
        for feature in self.configJson.values():
            try:
                for tagKey in feature['inputTags'].keys():
                    if tagKey not in self.sortedTags:
                        self.sortedTags[tagKey] = feature['inputTags'][tagKey]
                    else:
                        self.sortedTags[tagKey].extend(feature['inputTags'][tagKey])
            except KeyError: # For entrances in the config that is not features and thus lack 'inputTags' field
                continue
            except TypeError: # For entrances that does not have aditional levels of dictionaries
                continue
        
        for tagKey in self.sortedTags.keys(): #Remove duplicates in each tagValue list. 
            self.sortedTags[tagKey] = list(dict.fromkeys(self.sortedTags[tagKey]))
        



if __name__ == "__main__":
    config = Config()

    print(config.features)