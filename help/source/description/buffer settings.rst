.. _buffer-settings:

Buffer Settings
===============
How to edit buffer settigns is described in :ref:`edit-buffer-setting`. 

**Documentation Structure**

Only the voidGreyAreas category is currently buffered. It contains the highway linestring data and
is buffered according to which type of highway it is. The buffering unit is in meters. 

Information about the tags themselves is found in the `OSM wiki <https://wiki.openstreetmap.org/wiki/Map_features>`_

Version 2.0
-------------------
.. code:: javascript
    {
    "voidGreyAreas": 
        {
        "highway": 
            {
            "motorway": 15,
            "trunk": 15,
            "primary": 10,
            "secondary": 8,
            "tertiary": 8,
            "unclassified": 4,
            "residential": 4,
            "motorway_link": 15,
            "trunk_link": 15,
            "primary_link": 10,
            "secondary_link": 8,
            "tertiary_link": 8,
            "living_street": 4,
            "service": 4,
            "pedestrian": 1,
            "track": 1,
            "road": 4,
            "footway": 1,
            "steps": 1,
            "path": 1,
            "cycleway": 1,
            "bridleway": 1,
            "corridor": 1
            }
        }
    }
