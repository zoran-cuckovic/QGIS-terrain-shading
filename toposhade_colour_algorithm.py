# -*- coding: utf-8 -*-
"""
Created on Mon May  4 22:00:51 2026

@author: Zoran
    
"""
__author__ = 'Zoran Čučković'
__date__ = '2026-02-05'
__copyright__ = '(C) 2026 by Zoran Čučković'

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
                       QgsProcessingParameterMatrix,
                       QgsProcessingUtils,
                        QgsRasterBandStats,
                       QgsMultiBandColorRenderer,
                       QgsContrastEnhancement)

from processing.core.ProcessingConfig import ProcessingConfig

try:
    from osgeo import gdal
except ImportError:
    import gdal

import numpy as np

from .modules import Raster as rs
from .modules.shaders import TPI



from qgis.core import QgsMessageLog # for testing

class ToposhadeColourAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm simulates ambient lighting over a raster DEM (in input). 
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    RADIUS= 'RADIUS'
    DENOISE = 'DENOISE'
    ANALYSIS_TYPE='ANALYSIS_TYPE'
    STRENGTH = 'STRENGTH'
   # OFFSET_AZIMUTH= 'OFFSET_AZIMUTH'
    COLOUR_SCHEME = 'COLOUR_SCHEME'
    OUTPUT = 'OUTPUT'

    COLOUR_SCHEMES = ['Classic NE', 'Classic NW', 'Colourful NE ', 'Colourful NW']
    SHADE_TYPES=['Light', 'Medium', 'Strong']
    ANALYSIS_TYPES = ['Simple',  'Distance weighted', "Inverse dist. weighted", 'Height weighted']
    DENOISE_TYPES= ['None', 'Mean', 'Median', 'Mean and median']
    
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
        
        #♣ let's keep it simple, these are TPI settings
        # self.addParameter(QgsProcessingParameterEnum (
        #     self.ANALYSIS_TYPE,
        #     self.tr('Analysis type'),
        #     self.ANALYSIS_TYPES,
        #     defaultValue=0))
                    
        self.addParameter(QgsProcessingParameterNumber(
            self.RADIUS,
            self.tr('Radius in pixels'),
            QgsProcessingParameterNumber.Integer ,
            defaultValue=3))
   
        
        # self.addParameter(QgsProcessingParameterNumber(
        #     self.OFFSET_AZIMUTH,
        #     self.tr('Azimuth'),
        #     QgsProcessingParameterNumber.Double,
        #     defaultValue=315, minValue=0, maxValue=360))
        
        self.addParameter(QgsProcessingParameterEnum (
             self.COLOUR_SCHEME,
           self.tr('Colour scheme'),
            self.COLOUR_SCHEMES,
            defaultValue=0))
        
        self.addParameter(QgsProcessingParameterEnum (
             self.STRENGTH,
           self.tr('Shade strength'),
            self.SHADE_TYPES,
            defaultValue=1))
        
        
        self.addParameter(QgsProcessingParameterEnum(
            self.DENOISE,
            self.tr('Denoise'),
            self.DENOISE_TYPES,
            defaultValue=0)) 
        
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
            self.tr("Toposhade")))
        
    def processAlgorithm(self, parameters, context, feedback):
    
            
        elevation_model= self.parameterAsRasterLayer(parameters,self.INPUT, context)

        self.output_model = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        
        radius = self.parameterAsInt(parameters,self.RADIUS, context)
        
        strength = self.parameterAsInt(parameters,self.STRENGTH, context)

        denoise = self.parameterAsInt(parameters,self.DENOISE, context) 
        
        
        if strength == 0 : offset_dist = radius//1.5
        elif strength == 1 : offset_dist = radius//1.25
        else: offset_dist = radius
        
        #o STONG SHADOW = CLOSE ANGLES sTRONG COLOURS + WIDE ANGLES    
        # COLOUR SCHEME = ROTATION
        # offset_azimuth = self.parameterAsDouble(parameters,self.OFFSET_AZIMUTH, context)
        scheme = self.parameterAsInt(parameters,self.COLOUR_SCHEME, context)
        schemes = [(315,15,75), # see Kokalj et al ==> angles seprarated by 60 degrees
                   (270,330,30), # same, but rotated
                   (315,45,135), #╩ angular separation : 90 deg
                   (270, 360, 90), 
                   (270, 30, 150)]    # symmetric angles - too wild colours
        
        dem = rs.Raster(elevation_model)
        
        err, fatal = dem.verify_raster()
        if err: feedback.reportError(err, fatalError = fatal)
        

        dem.set_output(self.output_model, bands = 3, leave_open=True) 
      
        azim = schemes[scheme]
        
     
        
        result = TPI(dem_class=dem, mode=0, radius=radius,
                 offset_dist=offset_dist, 
                 offset_azimuths=azim,
                 denoise = denoise,
                 feedback=feedback)
        
     #   dem.save_output()
        
        return {self.OUTPUT: self.output_model}

    def postProcessAlgorithm(self, context, feedback):

        output = QgsProcessingUtils.mapLayerFromString(self.output_model, context)
        provider = output.dataProvider()

        stats = provider.bandStatistics(1,QgsRasterBandStats.All,output.extent(),0)
        mean, sd = stats.mean, stats.stdDev
        
        rnd = QgsMultiBandColorRenderer(provider, 1,2,3)
        ce = QgsContrastEnhancement(provider.dataType(1))
        ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
        
        ce.setMinimumValue(mean - 3*sd)
        ce.setMaximumValue(mean + 1.5* sd)

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
        return 'Toposhade_coloured'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Toposhade - coloured')

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def shortHelpString(self):
        curr_dir = path.dirname(path.realpath(__file__))
        h = ( """
             EXPERIMENTAL : three models are made for three colour bands (RGB).  
             
            <b>Input</b> should be an elevation model in raster format. 
            
            <b>Radius</b> defines the search radius (in pixels).
            
            If you find this tool useful, consider to :
                 
             <a href='https://ko-fi.com/D1D41HYSW' target='_blank'><img height='30' style='border:0px;height:36px;' src='%s/help/kofi2.webp' /></a>
            """) % curr_dir
		
        return self.tr(h)

    def createInstance(self):
        return ToposhadeColourAlgorithm()
