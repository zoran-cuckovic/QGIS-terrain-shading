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
import numpy.fft as npfft #T€ST


from .modules.helpers import view, window_loop, filter3, nextprod

from qgis.core import QgsMessageLog # for testing

class TextureAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm simulates ambient lighting over a raster DEM (in input). 
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
            1, # QgsProcessingParameterNumber.Integer = 0
            0.5, False, 0, 1.0))
        
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

        
        dem = gdal.Open(elevation_model.source())
        
        # ! attention: x in gdal is y dimension un numpy (the first dimension)
        xsize, ysize = dem.RasterXSize,dem.RasterYSize
        # assuming one band dem !
        nodata = dem.GetRasterBand(1).GetNoDataValue()
         # problems when noadata is nan, etc. 
         # this is for soft errors, not for calculation
#        try: 
#            if nodata < -9990: nodata = -9990
#        # PRBLEM NODATA AS NONE  POZEGA !
#        except: pass
        
        pixel_size = dem.GetGeoTransform()[1]
        
        rmin, rmax, rmean, rSD = dem.GetRasterBand(1).GetStatistics(0,1)[:4]

 
        chunk = int(ProcessingConfig.getSetting('DATA_CHUNK')) * 1000000
        
        chunk_x = min(chunk // xsize, xsize) 
        chunk_slice_x = (ysize, chunk_x ) 
            
        chunk_y = min(ysize, chunk // ysize) 
        chunk_slice_y = (chunk_y, xsize) 
              
        # define empty matrices to hold data : faster
        mx_z_x = np.zeros( chunk_slice_x)
        mx_z_y = np.zeros( chunk_slice_y)
   
        Ny, Nx = nextprod([2, 3, 5, 7], ysize) , nextprod([2, 3, 5, 7], xsize)
        fy = npfft.rfftfreq(Ny)[:, np.newaxis].astype(mx_z_y.dtype)
        fx = npfft.rfftfreq(Nx)[np.newaxis, :].astype(mx_z_x.dtype)
        
        # this is not the correct formula ; orginally :
        # H = (fy**2 + fx**2 ) ** (alpha / 2.0)
        # Now, (a + b)^2 = a^2 + b^2 + 2ab .... 
        # when alpha = 1 : the result is identical (i.e. pure laplacian filter)
        Hy, Hx = ((fy** 2) ** alpha)  , ((fx ** 2) ** alpha)
              
            # writing output to dump data chunks
        driver = gdal.GetDriverByName('GTiff')
        ds = driver.Create(self.output_model, xsize,ysize, 1, gdal.GDT_Float32)
        ds.SetProjection(dem.GetProjection())
        ds.SetGeoTransform(dem.GetGeoTransform())
        
        counter = 0
        
        # Break the operation to two axes (x, y) : this works fine for laplacian filter,
        # but it does not quite work for the *fractional* laplacian (here fraction = alpha)
        # the result is only very slightly degraded for alpha = 0.5 ...
        for axis in [0,1]:
            if axis:
                chunk = chunk_y
                mx_z = mx_z_y
                N, H = Nx, Hx # bit messy x, y swaps..
            else: 
                chunk = chunk_x
                mx_z = mx_z_x
                N, H = Ny, Hy 
       
            for mx_view_in, gdal_take, mx_view_out, gdal_put in window_loop ( 
                    shape = (xsize, ysize), 
                    chunk = chunk,
                    axis = axis) :
                
                mx_z[mx_view_in]=dem.ReadAsArray(*gdal_take).astype(float)
                               
                r = npfft.rfft( mx_z, N, axis=axis) * H
                r = npfft.irfft(r, axis=axis)
                
                # Return the same size as input
                out = r [:mx_z.shape[0], :mx_z.shape[1]]
                
                if axis : # SECOND ROUND, add old data
                    out[mx_view_in] += ds.ReadAsArray(*gdal_take) 
            
                ds.GetRasterBand(1).WriteArray(out[mx_view_out], * gdal_put[:2])
                
                
                counter += 1
                feedback.setProgress(100 * chunk * (counter / ( xsize + ysize)))
                if feedback.isCanceled(): return{}
            
            
            ds.FlushCache() #important, to save gdal dataset to disk!
        
        ds = None
        
        return {self.OUTPUT: self.output_model}

    def postProcessAlgorithm(self, context, feedback):

        output = QgsProcessingUtils.mapLayerFromString(self.output_model, context)
        provider = output.dataProvider()

        stats = provider.bandStatistics(1,QgsRasterBandStats.All,output.extent(),0)
        mean, sd = stats.mean, stats.stdDev
        
        rnd = QgsSingleBandGrayRenderer(provider, 1)
        ce = QgsContrastEnhancement(provider.dataType(1))
        ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)

        ce.setMinimumValue(mean-2*sd)
        ce.setMaximumValue(min(1, mean+2*sd))

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
             This algorithm is based on wawelength analysis (Fourrier transform) where terrain curvature is represented as a waweform. 
             The alpha paramter controls the impact of wawe-forms over elevation: when set to zero, pure elevation will be returned, when set to one, only the "noise" will be retained. The optimal value is approx 0.5.
             IMPORTANT: the elevation model should not contain "NoData", i.e. empty data. These will introduce large stripes across the output raster. 
             See also at <a href = http://www.textureshading.com>www.textureshading.com</a>.
             If you find this tool useful, consider to :
                 
             <a href='https://ko-fi.com/D1D41HYSW' target='_blank'><img height='30' style='border:0px;height:36px;' src='%s/help/kofi2.webp' /></a>
            """) % curr_dir
            # <img src="%s/help/compass.png"
            # alt="image comapss">
            
            #) % curr_dir
		
        return self.tr(h)

    def createInstance(self):
        return TextureAlgorithm()
