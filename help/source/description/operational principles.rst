Operational Principles
======================

Overview
--------
OSM to IMM is built using the `plugin builder <https://g-sherman.github.io/Qgis-Plugin-Builder/>`
plugin and as such contains the standard components of plugin builder. 

The working parts of the plugin then consists of three basic parts, a :ref:`query` class that query OSM, 
a :ref:`parser` class parsing the result into IMM format and a :ref:`runner` class that runs the above and
handles output to QGIS layers. This is then supported by a :ref:`config` class that contains
all the static information and settings. 

.. _query:

Query
-----
The Query class manages the queries with overpy. It takes the bounding box of the query as an input
and hides complexeties like writing `overpassQL <https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL>`_
queries and returns the `overpy result <https://python-overpy.readthedocs.io/en/latest/api.html#result>`_ object.

.. note::
    overpass can only query bounding boxes, and so any layer used to define the query area must
    first be converted to its bounding box. This is done by the :ref:`runner`. 


The Query class is designed to be used statically and its main job is to expose the ``Query.bboxGet()`` method 

.. py:method:: Query.bboxGet(cls, bbox:QgsRectangle, printquery = False) -> Overpass.Result

    *classmethod* queries OSM for all contents of *bbox*

    :param bbox: The bounding box for the query
    :type bbox: `QgsRectangle <https://qgis.org/pyqgis/3.2/core/other/QgsRectangle.html>`_
    :return: The result of the overpass query
    :rtyrpe: Overpass.Result


.. _parser:

Parser
-------
The Parser class converts the Overpy.Result object to a set of memory stored QGIS layers. A parser
object is initialized with the :ref:`config` object as input. Its main interface is then the ``Parser.parse``
method:

.. py:method:: Parser.parse(self, res:Overpy.result) -> Dict

    parse parses osm response to dictionary containing QgsVectorLayers

    :param res: The result of an overpass query
    :type res: Overpass.Result
    :return: A dictionary of `QgsVectorLayers <https://qgis.org/pyqgis/3.2/core/Vector/QgsVectorLayer.html>`_, 
             one QgsVectorLayer for each category specified by :ref:`config`
    :rtyrpe: Dict

The over all work flow of the parser is as follows: 

#. Create one QgsVectorLayer for each category
#. Loop though all nodes of the result 
    #. parse node into `QgsPointXY <https://qgis.org/pyqgis/3.2/core/Point/QgsPointXY.html>`_
    #. get the categories the node should be part of from config
    #. Add the point to the QgsVectorLayers corresponding to the appropriate categories
#. Loop though all ways of the result
    #. parse nodes bellonging to way into QgsPointXY and then create linestring geometry
    #. get the categories the way should be part of from config
    #. check if line should be converted to polygon
    #. Add the linestring or polygon to the QgsVectorLayers corresponding to the appropriate categories
#. Loop through all relations of the result
    #. get the categories the relation should be part of from config
    #. get the output geometry of the categories
    #. retrieve the members of the relation from previously parsed ways and nodes. 
    #. add point and linestring members of relation to the QgsVectorLayers corresponding to the appropriate categories
    #. check which polygon members are inner and outer rings and create multipart geomtries
    #. add multipart geometries to the QgsVectorLayers corresponding to the appropriate categories
#. Output the QgsVectorLayers.  

The parser calss also contains the ``Parser.buffer`` method: 

.. py:method:: Parser.buffer(self, layer: QgsVectorLayer, feature:str) -> QgsGeometry:
    
    ads a buffer for the input feature based on the buffer radii for each tag value described in the :ref:`buffer-settings`

    :param layer: The layer to be buffered
    :type layer: `QgsVectorLayer <https://qgis.org/pyqgis/3.2/core/Vector/QgsVectorLayer.html>`_
    :param feature: The name of the category that is being buffered
    :type feature: String
    :return: The buffered polygon
    :rtyrpe: `QgsGeometry <https://qgis.org/pyqgis/3.2/core/Geometry/QgsGeometry.html>`_

.. _runner:

Runner
------

.. _config:

Config
------