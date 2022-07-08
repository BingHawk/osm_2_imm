# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Main
                                 A QGIS plugin
 This plugin loads data from OSM in layers suitable for IMM
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2022-07-08
        copyright            : (C) 2022 by Leonard Hökby
        email                : bing.hawk@telia.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load Main class from file Main.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .osm_2_imm import Main
    return Main(iface)
