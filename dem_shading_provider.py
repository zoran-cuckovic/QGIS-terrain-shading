# -*- coding: utf-8 -*-

"""
/***************************************************************************
 DemShading
                                 A QGIS plugin
 This plugin simulates natural shadows over an elevation model (DEM)
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-06-05
        copyright            : (C) 2019 by Zoran Čučković
        email                : cuckovic.zoran@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Zoran Čučković'
__date__ = '2019-06-05'
__copyright__ = '(C) 2019 by Zoran Čučković'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.core import QgsProcessingProvider
from processing.core.ProcessingConfig import Setting, ProcessingConfig

from os import path
from PyQt5.QtGui import QIcon

from .shading_algorithm import DemShadingAlgorithm
from .occlusion_algorithm import OcclusionAlgorithm
from .tpi_algorithm import TpiAlgorithm
from .hillshade_algorithm import HillshadeAlgorithm
from .texture_algorithm import TextureAlgorithm


class DemShadingProvider(QgsProcessingProvider):

    def __init__(self):
        
        super().__init__() # should resolve "key error" on unload
        #QgsProcessingProvider.__init__(self)

        # Load algorithms
        self.alglist =[DemShadingAlgorithm(),  HillshadeAlgorithm(),
                        OcclusionAlgorithm(),  TpiAlgorithm(), 
                        TextureAlgorithm()]
        
    def load(self):

        ProcessingConfig.settingIcons[self.name()] = self.icon()
	# Activate provider by default
        ProcessingConfig.addSetting(
            Setting(self.name(), 'TERRAIN_SHADING_ACTIVATED',
                                   'Activate', True))
        ProcessingConfig.addSetting(
            Setting(self.name(), 'DATA_CHUNK',
                                    'Data chunk size (megapixels)', 5))
									
        ProcessingConfig.readSettings()
        self.refreshAlgorithms()
        return True

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        ProcessingConfig.removeSetting('TERRAIN_SHADING_ACTIVATED')
        ProcessingConfig.removeSetting('DATA_CHUNK')

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        if self.isActive():
            for alg in self.alglist:
                self.addAlgorithm( alg )

    def isActive(self):
        """Return True if the provider is activated and ready to run algorithms"""
        return ProcessingConfig.getSetting('TERRAIN_SHADING_ACTIVATED')

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return 'terrain_shading'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return self.tr('Terrain shading')

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()
    
    def icon(self):
        """
		We return the default icon.
		QgsProcessingProvider.icon(self)
        """
        return QIcon(path.dirname(__file__) + '/icon.png')
