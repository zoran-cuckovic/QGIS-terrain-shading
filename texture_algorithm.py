# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 10:00:17 2020

@author: zcuckovi
"""

# -*- coding: utf-8 -*-

"""
BUGS: 
  
NO DATA error
BORDERS ?? 
    
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
    DENOISE = 'DENOISE'
    DETREND='DETREND'
    OVERLAP = 'OVERLAP'
    ANALYSIS_TYPE='ANALYSIS_TYPE'
    OUTPUT = 'OUTPUT'

    ANALYSIS_TYPES = ['None to choose', 'None']
    OVERLAP_TYPES = ['None (recomended)', '250 px', '500 px','750 px', '1000 px']

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
        
        self.addParameter(QgsProcessingParameterEnum (
            self.ANALYSIS_TYPE,
            self.tr('Analysis type'),
            self.ANALYSIS_TYPES,
            defaultValue=0))
                    
        self.addParameter(QgsProcessingParameterNumber(
            self.ALPHA,
            self.tr('Alpha (shrapness, 0 - 2.0)'),
            1, # QgsProcessingParameterNumber.Integer = 0
            0.5, False, 0, 1.0))

        self.addParameter(QgsProcessingParameterBoolean(
            self.DENOISE,
            self.tr('Denoise'),
            False, False)) 
        
        self.addParameter(QgsProcessingParameterBoolean(
            self.DETREND,
            self.tr('Detrend'),
            False, False)) 
        
        self.addParameter(QgsProcessingParameterEnum (
            self.OVERLAP,
            self.tr('Overlap of data chunks'),
            self.OVERLAP_TYPES,
            defaultValue=0))
        
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

        denoise = self.parameterAsInt(parameters,self.DENOISE, context)     
        detrend = self.parameterAsInt(parameters,self.DETREND, context)    
       
        alpha =self.parameterAsDouble(parameters,self.ALPHA, context)

        weighted = self.parameterAsInt(parameters,self.ANALYSIS_TYPE, context)
        
        overlap = self.parameterAsInt(parameters,self.OVERLAP, context)
        
        overlap *= 250

        dem = gdal.Open(elevation_model.source())
        
        # ! attention: x in gdal is y dimension un numpy (the first dimension)
        xsize, ysize = dem.RasterXSize,dem.RasterYSize
        # assuming one band dem !
        nodata = dem.GetRasterBand(1).GetNoDataValue()
         # problems when noadata is nan, etc. 
         # this is for soft errors, not for calculation
        if nodata < -9990: nodata = -9990
        
        pixel_size = dem.GetGeoTransform()[1]
        
        rmin, rmax, rmean, rSD = dem.GetRasterBand(1).GetStatistics(0,1)[:4]

         # Chunk size should be NEXT PROD to fit ftt 
        if overlap : 
            chunk = int(ProcessingConfig.getSetting('DATA_CHUNK')) * 1000000
            chunk_x = min(chunk // xsize, xsize) 
            chunk_slice_x = (ysize, chunk_x + 2 * overlap) 
            
            chunk_y = min(ysize, chunk // ysize) 
            chunk_slice_y = (chunk_y + 2 * overlap, chunk_x) 
        else : 
            chunk_x, chunk_slice_x =  xsize, (ysize, xsize)
            chunk_y, chunk_slice_y =  ysize, (ysize, xsize)
            
        # define empty matrices to hold data : faster
        mx_z_x = np.zeros( chunk_slice_x)
        mx_z_y = np.zeros( chunk_slice_y)
   #     mx_a = np.zeros(mx_z.shape)
   
        Ny, Nx = nextprod([2, 3, 5, 7], ysize) , nextprod([2, 3, 5, 7], xsize)
        fy = npfft.rfftfreq(Ny)[:, np.newaxis].astype(mx_z_y.dtype)
        fx = npfft.rfftfreq(Nx)[np.newaxis, :].astype(mx_z_x.dtype)
        
        # this is not the correct formula ; orginally :
        # H = (fy**2 + fx**2 ) ** (alpha / 2.0)
        # Now, (a + b)^2 = a^2 + b^2 + 2ab .... but should we care ? 
        Hy, Hx = (fy** 2) ** alpha , (fx ** 2) ** alpha
              
            # writing output to dump data chunks
        driver = gdal.GetDriverByName('GTiff')
        ds = driver.Create(self.output_model, xsize,ysize, 1, gdal.GDT_Float32)
        ds.SetProjection(dem.GetProjection())
        ds.SetGeoTransform(dem.GetGeoTransform())
        
        counter = 0
        #X axis is chunked : calculate for y axis !
        for mx_view_in, gdal_take, mx_view_out, gdal_put in window_loop ( 
                shape = (xsize, ysize), 
                chunk = chunk_x,
                overlap = overlap) :
            
           

            dem.ReadAsArray(*gdal_take, mx_z_y[mx_view_in]).astype(float)
            
            if np.min(mx_z_y) <= nodata:
                err= (" \n ****** \n ERROR! \n Potential NoData values detected,\n this may introduce dark bands !")
                feedback.reportError(err, fatalError = False)
            print (nodata, np.count_nonzero(mx_z_y==nodata))
        
        # WAVELENGTH : to get a clean DEM : yr * fy
        # where fy = frequency of sampling

       
   
            
#            yr = scifft.rfft(mx_z_y, Ny, 0, True) * Hy
#                
#            yr = scifft.irfft(yr, axis=0, overwrite_x=True)
            
            # ==========================================================
            
            yr = npfft.rfft( mx_z_y, Ny, 0) * Hy
            
            yr = npfft.irfft(yr, axis=0)
            
              # Return the same size as input
            
            out = yr[:mx_z_y.shape[0], :mx_z_y.shape[1]]
        
            ds.GetRasterBand(1).WriteArray(out[mx_view_out], * gdal_put[:2])
            
            
            counter += 1
            feedback.setProgress(100 * chunk_x * (counter / 2 / xsize))
            if feedback.isCanceled(): sys.exit()
            
            
        ds.FlushCache() #important, to save gdal dataset to disk!
        


        for mx_view_in, gdal_take, mx_view_out, gdal_put in window_loop ( 
                shape = (xsize, ysize), 
                chunk = chunk_y,
                axis = 1,
                overlap = overlap) :
            
     
            
            dem.ReadAsArray(*gdal_take, mx_z_x[mx_view_in]).astype(float)
        
            """FFT-based texture shading elevation

              Given an array `x` of elevation data and an `alpha` > 0, apply the
              texture-shading algorithm using the full (real-only) FFT: the entire `x` array
              will be FFT'd.
            
              `alpha` is the shading detail factor, i.e., the power of the
              fractional-Laplacian operator. `alpha=0` means no detail (output is the
              input). `alpha=2.0` is the full (non-fractional) Laplacian operator and is
              probably too high. `alpha <= 1.0` seem aesthetically pleasing.
            
              Returns an array the same dimensions as `x` that contains the texture-shaded
              version of the input array.
            
              If `x` is memory-mapped and/or your system doesn't have 5x `x`'s memory
              available, consider using `texshade.texshadeSpatial`, which implements a
              low-memory version of the algorithm by approximating the frequency response of
              the fractional-Laplacian filter with a finite impulse response filter applied
              in the spatial-domain.
            
              Implementation note: this function uses Scipy's FFTPACK routines (in
              `scipy.fftpack`) instead of Numpy's FFT (`numpy.fft`) because the former can
              return single-precision float32. In newer versions of Numpy/Scipy, this
              advantage may have evaporated [1], [2].
            
              [1] https://github.com/numpy/numpy/issues/6012
              [2] https://github.com/scipy/scipy/issues/2487
              
              
              
              wave length = fft * n_sampling_points
              power spectrum = 2* (abs(fft/n)**2)
              frequency = 1/fft (replace 0 with ____)
              """
          
      
            
            xr = npfft.rfft(mx_z_x, Nx, 1) * Hx
                                    
            xr = npfft.irfft(xr, axis=1) 

            out = xr[:mx_z_x.shape[0], :mx_z_x.shape[1]]       
                        
            out[mx_view_in] += ds.ReadAsArray(*gdal_take)[mx_view_in]
            
            ds.GetRasterBand(1).WriteArray(out[mx_view_out], * gdal_put[:2])
            
            counter += 1
            feedback.setProgress(100 * chunk_y * (counter / 2 /  xsize))
            if feedback.isCanceled(): sys.exit()

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
             The alpha paramter controls the impact of wawe-forms over elevation: when set to zero, pure elevation will be returned, when set to one, only the "noise" will be retained. The optimal value is approx 0.5
             
             See also ____ BLOG POST ----- . 
             
             If you find this tool useful, consider suppporting its mainetnance/developement :
                 
             <a href='https://ko-fi.com/D1D41HYSW' target='_blank'><img height='30' style='border:0px;height:36px;' src='%s/help/kofi2.webp' /></a>
            """) % curr_dir
            # <img src="%s/help/compass.png"
            # alt="image comapss">
            
            #) % curr_dir
		
        return self.tr(h)

    def createInstance(self):
        return TextureAlgorithm()
