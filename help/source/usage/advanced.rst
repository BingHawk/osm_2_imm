Advanced usage
===============
.. note::
    Most users are **strongly recomended** to use the default settings since :ref:`incorrect mappings <tag-pitfalls>`
    can lead to unexpected behaviour and crashes and there are no controlls to check that it is correct.
    It is always recomended to save a backup of the old configuration file before starting editing. 


.. _edit-tag-map:

Editing tag mapping
-------------------
The default tag mapping is described in :ref:`tag-mapping`. 

To edit the tag mapping used by OSM to IMM, you can edit the configuration file. 

Configuration file
'''''''''''''''''''
The configuration.json file defines which OSM tags are sorted into which IMM categories. 
It is located at ~osm_2_imm/settings/static/configuration.json

The structure of the configuration file is as follows: 

.. code:: javascript

    {
    "categoryName": {
    "inputGeom": "osmGeom", 
    "outputGeom": "qgisGeom",
    "inputTags": 
        { 
        "tagKey1": ["tagValue", ...],
        "tagKey2": ["tagValue", ...], 
        ...
        },
    "outputTags": ["tagKey1", "tagKey2", ...],
    },
    ...,
    }

- **categoryName** is the name of the IMM category, consisting of at least two parts (ex ""networkStreet" or ""networkPtLines" are ok, but "streets" is not).
  All categories with the same first word will be grouped in the output and if saved to file, they will be in the same geopackage file. 

- **osmGeom** can be any of "node", "way" and "rel" and should correspond to the geometry type of the desired object in OSM.
  Currently not used but kept for backwards compatibility with verion 1.0

- :ref:`qgisGeom <qgis-geom>` is the desired geometry geometry of the output layer. 

- the :ref:`inputTags <input-tags>` object describes which OSM tags should sort under this category.
  The OSM features are output in the category if any of its tags are present in this object. 

- **outputTags** refers to the OSM tag keys whos values should be an attribute of the output QGIS feature. 

Each of these object repressent an output layer. There is no limit to the number of layers that can be created and the number of tags that can be introduced in each.
Parsing time required however increases with the number of layers. 

.. _qgis-geom: 

**qgisGeom attribute**

This attribute controlls how the feature is output. It will always be output as this feature no matter the type of geometry retrieved from OSM.
The following matrix describes the handeling of the different cases that can occur. 

.. _geom-table:

.. table:: Mapping of OSM and output geometry

    +---------------+------------+-------------+------------+
    | OSM feature   | Point      | Linestring  | Polygon    |
    | type          |            |             |            |
    +===============+============+=============+============+
    | Point         | no action  | ignored     | ignored    |
    +---------------+------------+-------------+------------+
    | Linestring    | ignored    | no action   | buffer     |
    +---------------+------------+-------------+------------+
    | Polygon       | centroid   | ignored     | no action  |
    +---------------+------------+-------------+------------+

As can be seen above, if the osm type (left column) does not match the desired output type they are mostly ignored,
except for polygons that should be output as points, and linestrings that should be output as polygons.

Buffering is controled by the :ref:`buffering settings <edit-buffer-setting>`

.. note::
    All OSM node objects are interpreted as points and relations are interpreted based on thier members.
    Ways are either interpreted as linestrings or polygons, based on the same criteria as used by `overpass turbo <https://wiki.openstreetmap.org/wiki/Overpass_turbo/Polygon_Features>`_.
    See :ref:`parser` for more info. 

.. _input-tags: 

**Input tags**

The input tags are mapped as a key for the OSM tag key chacked and each key have a list of values that are accepted. 
An OSM feature is included in the category if it has any of the "tagKey" as a tag *and* the value asociated with that tag is in the corresponding list. 

.. _tag-pitfalls: 

Tag mapping pittfalls
'''''''''''''''''''''

While changing included tags in the existing categories is relatively straight forward, 
creating new categories and changing geometry settings can be more dangerous. 

All combinations of the :ref:`geometry table <geom-table>` have not been thouroughly tested,
and trying to use the geometry types as a filter for which data to output have unintended outcomes.
It is always better to use tags to filter which features should be output. 

As of version 2.0 there is no system in place to check the integrety of the configuration.json file
so human errors are likely. Follow this guide and be careful when eddeting it. 

In order for a linestring object to be changed into a polygon object, it must be described in the :ref:`buffering settings <edit-buffer-setting>`
If not properly described coercing a linestring into a polygon can lead to undesired behaviour. 

.. _edit-buffer-setting:

Editing buffer distances
------------------------

The default buffering settings are described in :ref:`buffer-settings`. 

When the configuration file outputGeom attribute is set to polygon and the feature retrieved from OSM
is a linestring, the linestring can be buffered. To make sure that the line is buffered, the categoriy
must have an entry in the bufferingSettings.json file. If not, the line will be ignored. 

The bufferingSettings.json file can be found at ~osm_2_imm/settings/static/bufferingSettings.json

The structure of the buffering settings file is as follows: 

.. code:: javascript

    {
    "categoryName": 
        {
        "tagKey": 
            {
            "tagValue1": 15,
            "tagValue2": 10,
            "tagValue3": 4,
            ...
            }
        }
    ...
    }

- **categoryName** is the same category name as in the configuration file
- **tagKey** is the OSM tag key that should determine the buffer distance.
- **tagValue** is the value of the tag and is followed by the buffering distance in meters for those features.

.. note::
    Make sure that each categoryName only has one tagKey that control the buffering.
    Two conflicting buffering settings for a feature can result in unexpected behaviour. 
