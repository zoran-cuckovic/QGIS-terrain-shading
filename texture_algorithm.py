# -*- coding: utf-8 -*-

"""

    
/***************************************************************************
 DemShading - Terrain position algorithm
 This algorithm caluclates relative topographic position of each pixel of an
 elevation model (higher/lower than the neighbourhood) 
                              -------------------
        begin                : 2020-02-20
        copyright            : (C) 2020 by Zoran Čučković
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
__date__ = '2020-02-05'
__copyright__ = '(C) 2020 by Zoran Čučković'

from os import sys, path


try : from PyQt5.QtCore import QCoreApplication
except ImportError: from PyQt6.QtCore import QCoreApplication

from qgis.core import (QgsProcessing,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterRasterDestination,
                        QgsProcessingParameterBoolean,
                      QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum,
                       QgsProcessingUtils,
                        QgsRasterBandStats,
                       QgsSingleBandGrayRenderer,
                       QgsContrastEnhancement)

from processing.core.ProcessingConfig import ProcessingConfig


import numpy as np

from .modules import Raster as rs
from .modules.shaders import texture


from qgis.core import QgsMessageLog # for testing

class TextureAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm applies a fractional laplacian filter (sharpening filter) to a raster DEM (in input). 
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    ALPHA= 'ALPHA'
    OUTPUT = 'OUTPUT'

    output_model = None #for post-processing

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT,
                self.tr('Digital elevation model')
            ) )
                    
        self.addParameter(QgsProcessingParameterNumber(
            self.ALPHA,
            self.tr('Alpha (shrapness, 0 - 1.0)'),
            QgsProcessingParameterNumber.Double, 
            defaultValue = 0.5, minValue= 0, maxValue= 1))
        
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
            self.tr("Texture shading")))
        
    def processAlgorithm(self, parameters, context, feedback):
                
        elevation_model= self.parameterAsRasterLayer(parameters,self.INPUT, context)

        if elevation_model.crs().mapUnits() != 0 :
            err= " \n ****** \n ERROR! \n Raster data should be projected in a metric system!"
            feedback.reportError(err, fatalError = False)
           # raise QgsProcessingException(err)
        #could also use:
        #raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        if  round(abs(elevation_model.rasterUnitsPerPixelX()),
                    2) !=  round(abs(elevation_model.rasterUnitsPerPixelY()),2):
            
            err= (" \n ****** \n ERROR! \n Raster pixels are irregular in shape " +
                  "(probably due to incorrect projection)!")
            feedback.reportError(err, fatalError = False)
            #raise QgsProcessingException(err)

        self.output_model = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
       
        alpha =self.parameterAsDouble(parameters,self.ALPHA, context)
        
        dem = rs.Raster(elevation_model)
        dem.set_output(self.output_model) 
        result = texture( dem, alpha, feedback )
        
        return {self.OUTPUT: self.output_model}

    def postProcessAlgorithm(self, context, feedback):

        output = QgsProcessingUtils.mapLayerFromString(self.output_model, context)
        provider = output.dataProvider()

        stats = provider.bandStatistics(1,QgsRasterBandStats.All,output.extent(),0)
        mean, sd = stats.mean, stats.stdDev
        
        rnd = QgsSingleBandGrayRenderer(provider, 1)
        ce = QgsContrastEnhancement(provider.dataType(1))
        ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)

        ce.setMinimumValue(mean - sd)
        ce.setMaximumValue(mean + sd)
        
        rnd.setContrastEnhancement(ce)

        output.setRenderer(rnd)
        
        output.triggerRepaint()

        return {self.OUTPUT: self.output_model}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Texture shading'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def shortHelpString(self):
        
        curr_dir = path.dirname(path.realpath(__file__))
        h = ( """
             This algorithm is based on wavelength analysis (Fourier transform) where terrain curvature is represented as a waveform. 
             
	     The alpha parameter controls the impact of wave-forms over elevation: when set to zero, pure elevation will be returned, when set to one, only the "noise" will be retained. The optimal value is approx 0.5.
             
	     IMPORTANT: the elevation model should not contain "NoData", i.e. empty data. These will introduce large stripes across the output raster. 
             
	     For more information, check <a href = "https://landscapearchaeology.org/qgis-terrain-shading/" >the manual</a>.
             
	     If you find this tool useful, consider to :
                 
             <a href='https://ko-fi.com/D1D41HYSW' target='_blank'><img height='30' style='border:0px;height:36px;' src='%s/help/kofi2.webp' /></a>
            """) % curr_dir
            # <img src="%s/help/compass.png"
            # alt="image comapss">
            
            #) % curr_dir
		
        return self.tr(h)

    def createInstance(self):
        return TextureAlgorithm()
