# -*- coding: utf-8 -*-

"""
/***************************************************************************
 This algorihm calculates simple, lambertian reflectance of a surface, given
 an elevation model (DEM), in a raster format
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
__date__ = '2020-02-05'
__copyright__ = '(C) 2020 by Zoran Čučković'

from os import sys, path

from PyQt5.QtCore import QCoreApplication
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

try:
    from osgeo import gdal
except ImportError:
    import gdal

import numpy as np

from .modules import Raster as rs
from .modules.helpers import view, window_loop,  median_filter

from qgis.core import QgsMessageLog # for testing

class HillshadeAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm simulates natural shade over a raster DEM (in input). 
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    DIRECTION= 'DIRECTION'
    BIDIRECTIONAL= 'BIDIRECTIONAL'
    ANGLE = 'ANGLE'
    LON_Z ='LON_Z'
    LAT_Z = 'LAT_Z'
    DENOISE = 'DENOISE'
    BYTE_FORMAT = 'BYTE_FORMAT'
    OUTPUT = 'OUTPUT'
    
    DENOISE_TYPES= ['None', 'Mean', 'Mean and median']

    output_model = None #for post processing
    val_range = None

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
        
        self.addParameter(QgsProcessingParameterBoolean(
            self.BIDIRECTIONAL,
            self.tr('Bidirectional hillshade'),
            False, False)) 
        
        self.addParameter(QgsProcessingParameterNumber(
            self.DIRECTION,
            self.tr('Direction (0 to 360°)'),
            1, 315, False, 0, 360))
                
        self.addParameter(QgsProcessingParameterNumber(
            self.ANGLE,
            self.tr('Sun angle (0 to 90°)'),
            1, 45, False, 0, 90))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.LAT_Z,
            self.tr('Lateral Z factor'),
            1, 2, False, 0, 100))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.LON_Z,
            self.tr('Longitudinal Z factor'),
            1, 1, False, 0, 100))
        """
        These parameters give poor results : to be studied
        self.addParameter(QgsProcessingParameterNumber(
            self.GAMMA,
            self.tr('Contrast (gamma)'),
            1, 1, False, 0, 10))
        """
        self.addParameter(QgsProcessingParameterEnum(
            self.DENOISE,
            self.tr('Denoise'),
            self.DENOISE_TYPES,
            defaultValue=1)) 
        
        self.addParameter(QgsProcessingParameterBoolean(
            self.BYTE_FORMAT,
            self.tr('Byte sized output (0-255)'),
            False, False)) 
        
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
            self.tr("Hillshade")))
        
    def processAlgorithm(self, parameters, context, feedback):
       
        
        elevation_model= self.parameterAsRasterLayer(parameters,self.INPUT, context)

        self.output_model = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)

        direction = self.parameterAsDouble(parameters,self.DIRECTION, context)

        bidirectional = self.parameterAsInt(parameters,self.BIDIRECTIONAL, context)  
        # patch to communicate with postprocessing...
        # because folks believe the output is wrong if the contrast is not set ....
        self.bidir = bidirectional 
        
        if bidirectional : # because of vector addition, the effective lighting is shifted 
            direction -= 45  
            if direction < 0 : direction += 360 
        
              
        sun_angle =  self.parameterAsDouble(parameters,self.ANGLE, context)

        
        smooth = self.parameterAsInt(parameters,self.DENOISE, context)     
        byte =  self.parameterAsInt(parameters,self.BYTE_FORMAT, context) 
        
        lat_factor = self.parameterAsDouble(parameters,self.LAT_Z, context)
        lon_factor = self.parameterAsDouble(parameters,self.LON_Z, context)
        
        if bidirectional and lat_factor <= lon_factor: 
            err= (" \n ****** \n ERROR! \n Bidirectional hillshade has to be used " +
                  "with lateral exaggeration greater that the longitudianl one ! ")
            feedback.reportError(err, fatalError = True)
            
        
        
        dem = rs.Raster(elevation_model)
        
        err, fatal = dem.verify_raster()
        if err: feedback.reportError(err, fatalError = fatal)

        dem.set_output(self.output_model, 
                       data_format_override =  byte , 
                       compression = True)
                        # data_format = None : fallback to the general setting
               
        sun_angle = np.radians( sun_angle)  
            
        s = np.radians(360 - direction)  # reverse the sequence (more simple than to fiddle with sin/cos...)
        
 #       for two prependicualr vectors, directions can be decomposed according to sin/cos rule
        a, b = np.cos(s) , np.sin(s)     
       
        if smooth :
            # larger matrix, same principle ( standards for hillshades )
            win = np.array([[-1, -2 ,-1],
                            [0,  0 ,0],
                            [1, 2 ,1]]) 
    
        else: # can be interesting for feature detection, not standard for hillshades
            win = np.array([[0, -1 ,0],
                            [0,  0 ,0],
                            [0, 1 ,0]])  
 
        # perpendicular win : second vector
        win2 = np.rot90(win) 
        # for some reason, numpy's rotation is anti-clockwise !!
        
        win_size = win.shape[0]
 
        # to avoid edge effects, windows have to overalp
        overlap = win_size if not smooth else win_size + 1
   
                                                # adjust for angular offset
        pix_x = dem.pix_x * 2
        pix_y = dem.pix_y * 2
        
        
        # for the record : diag_size = pix / np.cos(np.radians(s%45))   

        
        chunk_slice = (dem.ysize, dem.chunk_x + 2 * overlap)
                             
        
        # matrices that will hold data
        mx_z = np.zeros(chunk_slice)
        mx_a = np.zeros(chunk_slice)
        mx_a2 = np.zeros(chunk_slice)
                           
        counter = 0
      
        # loop though data chunks  
        for mx_view_in, gdal_take, mx_view_out, gdal_put in window_loop ( 
            shape = (dem.xsize, dem.ysize), 
            chunk = dem.chunk_x,
            overlap = overlap ) :
            
            # for speed : read into an allocated array
            dem.rst.ReadAsArray(*gdal_take, mx_z[mx_view_in])
            
            if smooth == 2 : mx_z = median_filter(mx_z, 2)
            
            mx_a [:], mx_a2[:] = 0,0
                       
            for (y,x), weight in np.ndenumerate(win):

                view_in, view_out = view(y - win_size//2, x - win_size//2, mx_z.shape)
                          
                if weight : 
                    mx_a[view_out] += mx_z[view_in] * weight
     
                w2 = win2[y,x]    
                if w2: 
                    mx_a2[view_out] += mx_z[view_in] * w2
                      
                counter += 1
                feedback.setProgress(100 * dem.chunk_x * (counter/9) /  dem.xsize)
                if feedback.isCanceled(): return {}   
                    
            # slope = dz / dx;
            px = 1 / (abs(pix_x) * np.sum(win[win >0])) # take 1/dist to use multiplication
            py = 1 / (abs(pix_y) * np.sum(win[win >0]))
            
             
            # using vector addition to isolate directions, i.e the slope along such directions
            # (knowing that all but cardinal directions have to be calculated from two vector components)
            # (proof : for 45° sin = 0,7 ; cos = 0,7, which adds to 1,4 = sqrt(2))
            lon_z =  mx_a * (py * a) + mx_a2 * (px * b)
            
            # attention :  mx_a * -1 (= reverse direction !)
            lat_z = mx_a * (py * -b) + mx_a2 * (px * a)

            # to adjust slope for sun angle (slope * distance)
            # mx_a -= np.tan(sun_angle) 
            
            # everything is cast to an angle (atan), which is costly ...
            lon = np.arctan(lon_z * lon_factor)
            lat = np.arctan(lat_z * lat_factor)    
                 
                # COSINE LAW (Lambertian reflectance)
                # a shadow below an illuminated object is a parallelogram
                # with height = cos(inclination) * true_height and 
                # width = cos(inclination) * true_width
                
            out = np.cos(lon - sun_angle) * np.cos(lat)
            # NB :  cos(arctan(x)) = 1 / sqrt(1+x²)  - to compress the calculation 
            # while here we do first arctan, and then cos
            # but - where to plug the adjustement for the sun angle ??

            if bidirectional:
                #acessory direction: swap matrices and factors !
                #lon = lat etc.
                lat[:] = np.arctan(lon_z * lat_factor)
                lon[:] = np.arctan(-lat_z * lon_factor)
                
                #add two hillshades
                out += np.cos(lon - sun_angle) * np.cos(lat) 
                
                # normalise for byte conversion 
                if byte: out /= 2            
	    # To be studied : values can be stretched for better contrast, 
	    # but this may produce unintutuive results in combination with varying sun height
            # out **= gamma 
                    
            dem.add_to_buffer (out[mx_view_out], gdal_put) 
        

        return {self.OUTPUT: self.output_model}

    def postProcessAlgorithm(self, context, feedback):
        
        output = QgsProcessingUtils.mapLayerFromString(self.output_model, context)
        provider = output.dataProvider()
        ext = output.extent()

        stats = provider.bandStatistics(1,QgsRasterBandStats.All,ext,0)
        mean, sd = stats.mean, stats.stdDev

        rnd = QgsSingleBandGrayRenderer(provider, 1)
        ce = QgsContrastEnhancement(provider.dataType(1))
        ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
        
        ce.setMinimumValue(mean - sd * 2)
        ce.setMaximumValue(mean + sd * (1 if self.bidir else 2))
        
       # to do QgsBrightnessContrastFilter

        
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
        return 'Hillshade (terrain shading)'

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
             <h3>    This algorithm calculates surface shading - hillshade - for elevation models.
             
            <b>Input</b> should be an elevation model in raster format. 
            
            The <b>output</b> is expressing lambertian reflectance (with possible adjustements for better contrast).
           
            <b>Bidirectional hillshade</b>: combine with a second hillshade, from a perpendicular direction. IMPORTANT: this will work only when lateral terrain exaggeration is set above 1.0.
            
            <b>Sun direction</b> and <b>sun angle</b> parmeters define horizontal and vertical position of the light source, where 0° is on the North, 90° on the East and 270° on the West.

            <b>Lateral and longitudinal Z factor </b> introduce artifical exaggeration of the elevation model, in order to achieve higher shading contrast.   
                
            <b>Denoise</b>: apply a filter to produce smoother results. 
	    
	    For more information, check <a href = "https://landscapearchaeology.org/qgis-terrain-shading/" >the manual</a>.
             
            If you find this tool useful, consider to :
                 
             <a href='https://ko-fi.com/D1D41HYSW' target='_blank'><img height='30' style='border:0px;height:36px;' src='%s/help/kofi2.webp' /></a>
            """) % curr_dir
		
        return self.tr(h)

    def createInstance(self):
        return HillshadeAlgorithm()
