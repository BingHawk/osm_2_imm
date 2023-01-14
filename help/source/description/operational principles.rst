Operational Principles
======================

Overview
--------
OSM to IMM is built using the `plugin builder <https://g-sherman.github.io/Qgis-Plugin-Builder/>`_
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

.. note::
    overpass is the current preformance bottleneck of the code both in terms of bounding :ref:`box size limitations <area-size>`
    and time to run the tool. More :ref:`limitations`. 


The Query class is designed to be used statically and its main job is to expose the ``Query.bboxGet()`` method 

.. py:function:: Query.bboxGet(cls, bbox:QgsRectangle, printquery = False) -> Overpass.Result

    *classmethod* queries OSM for all contents of *bbox*

    :param bbox: The bounding box for the query
    :type bbox: `QgsRectangle <https://qgis.org/pyqgis/3.2/core/other/QgsRectangle.html>`_
    :return: The result of the overpass query
    :rtyrpe: Overpy.Result


.. _parser:

Parser
-------
The Parser class converts the Overpy.Result object to a set of memory stored QGIS layers. A parser
object is initialized with the :ref:`config` object as input. Its main interface is then the ``Parser.parse``
method:

.. py:function:: Parser.parse(self, res:Overpy.result) -> Dict

    parse parses osm response to dictionary containing QgsVectorLayers

    :param res: The result of an overpass query
    :type res: Overpy.Result
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

.. py:function:: Parser.buffer(self, layer: QgsVectorLayer, feature:str) -> QgsGeometry:
    
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
Runner is the conductor of the orchestra and it runs the other classes in the correct order as well
as showing a :ref:`progress bar <progress-bar>` dialog for the project. This is the class that is
imported into the osm_2_imm.py template file created by `plugin builder <https://g-sherman.github.io/Qgis-Plugin-Builder/>`_

The Runner class is initalized as ``Project(iface)`` using the `QgsInterface <https://qgis.org/pyqgis/3.2/gui/other/QgisInterface.html?highlight=iface#qgis.gui.QgisInterface.statusBarIface>`_
class as iface. Then, a project instance, bounding box and output location can be set with the following methods: 

.. py:function:: Runner.setBbox(self, bbox) -> Runner

    Optional. Sets the bounding box to be used in parsing. Bounding box Defaults to "45.47692, 9.22551, 45.47945, 9.23028",
    (Milano, politecnico Leonardo Campus area)

    :param bbox: The bounding box to be queried
    :type bbox: `QgsRectangle <https://qgis.org/pyqgis/3.2/core/other/QgsRectangle.html>`_
    :return: returns itself for method chaining
    :rtype: Runner

.. py:function:: Runner.setProject(self, project) -> Runner

    Required. Used for `tranformation contexts <https://qgis.org/pyqgis/3.2/core/Coordinate/QgsCoordinateTransformContext.html>`_. 

    :param project: The project instance
    :type project: `QgsProject.instance() <https://qgis.org/pyqgis/3.2/core/Project/QgsProject.html?#qgis.core.QgsProject.instance>`_
    :return: returns itself for method chaining
    :rtype: Runner

.. py:function:: Runner.setOutLoc(self, outLoc) -> Runner

    Optional. Defaults to `None` and if so the layers are only produced as memory layers. 

    :param outLoc: The path to where geopackages should be saved.
    :type outLoc: String
    :return: returns itself for method chaining
    :rtype: Runner

After set up, the the project can be run with the ``Runner.qgsMain()`` method. 

.. py:function:: Runner.qgsMain(self)

    Runs the querying and parsing logics and outputs the resulting layers into the QgsInterface specified in constructor. 

The workorder of the qgsMain method is as following: 

#. Create the brogress bar dialog
#. Set up the grouping of the output layers, output locations and project context for the parser.
#. Update progress
#. Run :py:func:`Query.bboxGet` method with the input bounding box
#. Update progress
#. Run :py:func:`Parser.parse` on the query result. 
#. Update progress
#. On layers that will be buffered: 
    #. Reproject layer into a projected coordinate system (EPSG:3857 as of version 2.0)
    #. Run :py:func:`Parser.buffer` on the projected layer
    #. Reproject layer back to EPSG:4326
#. If save is chosen, save output to desired output location.
#. Create layer tree in the open QGIS project. 

.. _config:

Config
------
The Config class is the container class for the :ref:`configuration-file`. Upon construction it loads the
configuration file, the buffer settings and the polygon-features files and exposes them as properties of
the Config object.

The ``config`` class has the following attributes: 

.. py:class:: Config

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
    :vartype bufferSettings: Dict
    :ivar projectedCrs: epsg code for the projected reference system used
    :vartype projectedCrs: String
    :ivar outputCrs: epsg code for the reference system used for output
    :vartype outputCrs: String
    :ivar bbox_S: Example bounding box of size S. Located in Milano
    :vartype bbox_S: `QgsRectangle <https://qgis.org/pyqgis/3.2/core/other/QgsRectangle.html>`_
    :ivar bbox_M: Example bounding box of size M. Located in Milano
    :vartype bbox_M: `QgsRectangle <https://qgis.org/pyqgis/3.2/core/other/QgsRectangle.html>`_
    :ivar bbox_L: Example bounding box of size L. Located in Milano
    :vartype bbox_L: `QgsRectangle <https://qgis.org/pyqgis/3.2/core/other/QgsRectangle.html>`_
    :ivar bbox_XL: Example bounding box of size XL. Located in Milano
    :vartype bbox_XL: `QgsRectangle <https://qgis.org/pyqgis/3.2/core/other/QgsRectangle.html>`_
    :ivar bbox_XXL: Example bounding box of size XXL. Located in Milano
    :vartype bbox_XXL: `QgsRectangle <https://qgis.org/pyqgis/3.2/core/other/QgsRectangle.html>`_
    :ivar bbox_XL_D: Example bounding box of size XL. Located in Dakar
    :vartype bbox_XL_D: `QgsRectangle <https://qgis.org/pyqgis/3.2/core/other/QgsRectangle.html>`_
    :ivar bbox_L_D: Example bounding box of size L. Located in Dakar
    :vartype bbox_L_D: `QgsRectangle <https://qgis.org/pyqgis/3.2/core/other/QgsRectangle.html>`_
    :ivar bbox_M_D: Example bounding box of size M. Located in Dakar
    :vartype bbox_M_D: `QgsRectangle <https://qgis.org/pyqgis/3.2/core/other/QgsRectangle.html>`_

.. note:: 
    The boundingboxes of size L and bigger can take some time to run. Chsck the :ref:`configuration-file` to find their coordinates. 