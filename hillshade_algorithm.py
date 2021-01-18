# -*- coding: utf-8 -*-

"""
ERROR : CHUNKS ARE NOT CALCULATED PROPERLY 
CHUNK = SIZE ON X/Y, therefore  sqrt2 !! for a square 
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

import gdal
import numpy as np

from .modules import helpers

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
    ANGLE = 'ANGLE'
    LON_EX ='LONG_EX'
    LAT_EX = 'LAT_EX'
    DENOISE = 'DENOISE'
    BYTE_FORMAT = 'BYTE_FORMAT'
    OUTPUT = 'OUTPUT'


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
        
        self.addParameter(QgsProcessingParameterNumber(
            self.DIRECTION,
            self.tr('Direction (0 to 360°)'),
            1, 315, False, 0, 360))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.ANGLE,
            self.tr('Sun angle (0 to 90°)'),
            1, 45, False, 0, 90))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.LAT_EX,
            self.tr('Lateral exaggeration'),
            1, 2, False, 0, 100))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.LON_EX,
            self.tr('Longitudinal exaggeration'),
            1, 1, False, 0, 100))
        """
        These parameters give poor results : to be studied
        self.addParameter(QgsProcessingParameterNumber(
            self.GAMMA,
            self.tr('Contrast (gamma)'),
            1, 1, False, 0, 10))
        """
        self.addParameter(QgsProcessingParameterBoolean(
            self.DENOISE,
            self.tr('Denoise'),
            False, False)) 
        
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

        if elevation_model.crs().mapUnits() != 0 :
            err= " \n ****** \n ERROR! \n Raster data has to be projected in a metric system!"
            feedback.reportError(err, fatalError = False)
            # raise QgsProcessingException(err)

        if  round(abs(elevation_model.rasterUnitsPerPixelX()),
                    2) !=  round(abs(elevation_model.rasterUnitsPerPixelY()),2):
            
            err= (" \n ****** \n ERROR! \n Raster pixels are irregular in shape " +
                  "(probably due to incorrect projection)!")
            feedback.reportError(err, fatalError = False)
            # raise QgsProcessingException(err)

        self.output_model = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)

        direction = self.parameterAsDouble(parameters,self.DIRECTION, context)

        s = 315 - direction  # reverse the sequence and center on 45 (just so...)
        
        sun_angle =  self.parameterAsDouble(parameters,self.ANGLE, context)
        sun_angle = np.radians( 90 - sun_angle) # taking orthogonal angle !!    
        
        smooth = self.parameterAsInt(parameters,self.DENOISE, context)     
        byte =  self.parameterAsInt(parameters,self.BYTE_FORMAT, context) 
        
        lat_factor = self.parameterAsDouble(parameters,self.LAT_EX, context)
        lon_factor = self.parameterAsDouble(parameters,self.LON_EX, context)
                
        # for two prependicualr vectors, directions can be decomposed according to sin/cos rule
        a, b = np.cos(np.radians(s)) , np.sin(np.radians(s)) 
        
        if smooth: # larger matrix, same principle ( VERY POOR DENOISING ! )
            win = np.array([[0, 0, 0,  0, 0],
                            [ 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 1],
                             [ 0, 0, 0, 0, 0],
                             [0, 0,  1, 0, 1]]) 
        
        else: 

            win = np.array([[0, 0 ,0],
                            [0,  0 , 1],
                            [0,  1, 1]])  
    
    
            
        # fipping and flopping to deploy on a 0-360 range     
#        if steep :  win = win.T
#
#        if rev_y : win = np.flipud(win)
#        if rev_x : win = np.fliplr(win)
        
        win2 = np.rot90(win)
        
        win_size = win.shape[0]
        
        # to avoid edge effects, windows have to overalp
        overlap = win_size if not smooth else win_size + 1

        dem = gdal.Open(elevation_model.source())
          
        # ! attention: x in gdal is y dimension un numpy (the first dimension)
        xsize, ysize = dem.RasterXSize,dem.RasterYSize
        #assuming one band dem !
        nodata = dem.GetRasterBand(1).GetNoDataValue()  
             
                                                # adjust for angular offset
        pixel_dist = dem.GetGeoTransform()[1] * (4 if smooth else 2)
        # for the record : diag_size = pix / np.cos(np.radians(s%45))   
        
#        # distances for altitude measures 
#        dist = (win_size - 1) * pixel_size 
#   
#        # take weights per pair of mesures because we use altitude differences. 
#        weights = np.sum(win[win>0]) 
   
        chunk = int(ProcessingConfig.getSetting('DATA_CHUNK')) * 1000000
        chunk = min(chunk // xsize, xsize)
       
        
        # setting up output writing parameters. 
        driver = gdal.GetDriverByName('GTiff')
        ds = driver.Create(self.output_model, xsize,ysize, 1, 
                           gdal.GDT_Byte if byte else gdal.GDT_Float32)
        ds.SetProjection(dem.GetProjection())
        ds.SetGeoTransform(dem.GetGeoTransform())
        
        chunk_slice = (ysize, chunk + 2 * overlap)
        
        # matrices that will hold data
        mx_z = np.zeros(chunk_slice)
        mx_a = np.zeros(mx_z.shape)
        mx_a2 = np.zeros(mx_z.shape)
                           
        counter = 0
      
        # loop though data chunks  
        for mx_view_in, gdal_take, mx_view_out, gdal_put in helpers.window_loop ( 
            shape = (xsize, ysize), 
            chunk = chunk,
            overlap = overlap ) :
            
            # for speed : read into an allocated array
            dem.ReadAsArray(*gdal_take, mx_z[mx_view_in])
            
            mx_a [:], mx_a2[:] = 0,0
                       
            for (y,x), weight in np.ndenumerate(win):

                view_in, view_out = helpers.view(y - win_size//2, x - win_size//2, mx_z.shape)
                          
                if weight : 
                    mx_a[view_out] += mx_z[view_in]  
                    # mirrored value
                    mx_a[view_in] -= mx_z[view_out] 
                    
                w2 = win2[y,x]    
                if w2: 
                    mx_a2[view_out] += mx_z[view_in]
                    mx_a2[view_in] -= mx_z[view_out]
                
                counter += 1
                feedback.setProgress(100 * chunk * (counter/9) /  xsize)
                if feedback.isCanceled(): sys.exit()
            
            # slope = dz / dx
            mx_a /= pixel_dist * 3       
            mx_a2/=  pixel_dist * 3

            # to adjust slope for sun angle (slope * distance)
            # mx_a -= np.tan(sun_angle) 
            
            # using vector addition to isolate directions, i.e the slope along such directions
            # (knowing that all but cardinal directions have to be calculated from two vector components)
            # everything is cast to an angle (atan), which is costly ...
            lon =  np.arctan((mx_a * a + mx_a2 * b) * lon_factor) - sun_angle
            # attention :  mx_a * -1 (= reverse direction !)
            lat =  np.arctan((mx_a * -b + mx_a2 * a) * lat_factor) 
    
            # COSINE LAW (Lambertian reflectance)
            # a shadow below an illuminated object is a parallelogram
            # with height = cos(inclination) * true_height and 
            # width = cos(inclination) * true_width
            out = np.cos(lon) * np.cos(lat)
            if byte : out *= 255
            
	    # To be studied : values can be stretched for better contrast, 
	    # but this may produce unintutuive results in combination with varying sun height
            # out **= gamma 
            
            ds.GetRasterBand(1).WriteArray(out[mx_view_out], * gdal_put[:2])

        ds = None
        
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


        ce.setMinimumValue(mean - 3*sd)
        ce.setMaximumValue(mean + 3*sd)
        
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
           
            <b>Sun direction</b> and <b>sun angle</b> parmeters define horizontal and vertical position of the light source, where 0° is on the North, 90° on the East and 270° on the West.

            <b>Lateral and longitudinal exaggeration</b> introduce artifical deformations of the elevation model, in order to achieve higher shading contrast.   
                
            <b>Denoise</b> option is using larger search radius, producing smoother results. 
            
            If you find this tool useful, consider to :
                 
             <a href='https://ko-fi.com/D1D41HYSW' target='_blank'><img height='30' style='border:0px;height:36px;' src='%s/help/kofi2.webp' /></a>
            """) % curr_dir
		
        return self.tr(h)

    def createInstance(self):
        return HillshadeAlgorithm()
