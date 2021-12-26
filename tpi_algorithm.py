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
                       QgsProcessingParameterMatrix,
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
from .modules.helpers import view, window_loop, median_filter

from qgis.core import QgsMessageLog # for testing

class TpiAlgorithm(QgsProcessingAlgorithm):
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
    OFFSET_DISTANCE = 'OFFSET_DISTANCE'
    OFFSET_AZIMUTH= 'OFFSET_AZIMUTH'
    OUTPUT = 'OUTPUT'

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
        
        self.addParameter(QgsProcessingParameterEnum (
            self.ANALYSIS_TYPE,
            self.tr('Analysis type'),
            self.ANALYSIS_TYPES,
            defaultValue=0))
                    
        self.addParameter(QgsProcessingParameterNumber(
            self.RADIUS,
            self.tr('Radius in pixels'),
            0, # QgsProcessingParameterNumber.Integer = 0
            5, False, 0, 100))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.OFFSET_DISTANCE,
            self.tr('Center of mass: offset in pixels (< radius)'),
            0, # QgsProcessingParameterNumber.Integer = 0
            0, False, 0, 1000))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.OFFSET_AZIMUTH,
            self.tr('Center of mass: azimuth'),
            0, # QgsProcessingParameterNumber.Integer = 0
            315, False, 0, 360))
        
        self.addParameter(QgsProcessingParameterEnum(
            self.DENOISE,
            self.tr('Denoise'),
            self.DENOISE_TYPES,
            defaultValue=0)) 
        
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
            self.tr("Topographic position index")))
        
    def processAlgorithm(self, parameters, context, feedback):
    
            
        elevation_model= self.parameterAsRasterLayer(parameters,self.INPUT, context)

        self.output_model = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        
        radius = self.parameterAsInt(parameters,self.RADIUS, context)

        mode = self.parameterAsInt(parameters,self.ANALYSIS_TYPE, context)

        denoise = self.parameterAsInt(parameters,self.DENOISE, context) 
        
        offset_dist = self.parameterAsInt(parameters,self.OFFSET_DISTANCE, context)
        if offset_dist > radius :
            err= (" \n ****** \n ERROR! \n Center of mass is beyond the analysis range: " +
                  "offset distance should be less than radius!")
            feedback.reportError(err, fatalError = False)
            raise QgsProcessingException(err)
            offset_dist = radius - 1
            
        # Reverse the angle direction : this is required because the algorithm 
        # is organised in corresopndance to numpy matrix ordering (y first and descending). 
        offset_azimuth = 360 - self.parameterAsInt(parameters,self.OFFSET_AZIMUTH, context)
        # decompose angle and distance to pixel coords
        offset_x = round(offset_dist * np.sin(np.radians(offset_azimuth)))
        offset_y = round(offset_dist * np.cos(np.radians(offset_azimuth)))
        offset_x_diag = round(offset_dist * np.sin(np.radians(offset_azimuth - 45)))
        offset_y_diag = round(offset_dist * np.cos(np.radians(offset_azimuth - 45)))
        
        # TODO
        # A better solution is to divide the matrix into heavy and light parts, 
        # and express the weight as the percentage of the heavy part (e.g. 75 %)
        # The weight is then 2w * percentage ; 2w * (1-percentage) 
        # (2w, because heavy + light = 2w)
        # ...need to select light/heavy branches !
               
        dem = rs.Raster(elevation_model)
        
        err, fatal = dem.verify_raster()
        if err: feedback.reportError(err, fatalError = fatal)
        
        dem.set_output(self.output_model) 
            
        overlap = radius if not denoise else radius +1
        
        chunk_slice = (dem.ysize, dem.chunk_x + 2 * overlap)
        
        # define empty matrices to hold data : faster
        mx_z = np.zeros( chunk_slice)
        mx_a = np.zeros(mx_z.shape)
        mx_cnt = np.zeros(mx_z.shape)
        
        # Lines that will be searched, radiating from each pixel.
        # Denoise option : a star shaped configuration (N, NE, E, SE etc)
        # For more directions : step = 0.5; 0.25; etc
        # !! We exploit symetry, pixel pairs are neighbours to each other,
        # but in opposite directions (N-S, E-W etc.)
        # Therefore no need to loop over opposite directions (here N and W)
        directions = [(0,1, offset_y),  (1,0, offset_x)] # orthogonal directions 
        if denoise in [1,3]: directions += [(1,1, offset_y_diag), (1, -1, offset_x_diag)]
            
        precalc = not offset_x and not offset_y and mode in [0,1] # TODO for inverse height ( mode = 2) !

        
        # handling irregular pixels (lat long)
        # attention wy , wx are swapped - give the x weight to y dimension..
        w_y, w_x = dem.pix_x/dem.pix_y, dem.pix_y/dem.pix_x
        # ensure wx + wy = 2
        if w_x < 1 : w_y = 2 - w_x
        elif w_y < 1 : w_x = 2 - w_y
      
        # Diagonal for rectangular pixels 
        w_diag = np.sqrt (w_x**2 + w_y**2)

        # pre-calculate the number of visits per cell 
        # (cannot be done for height based weights)
        # Considering mass displacement mode, the problem is to handle edges -> 
        # they have shorter radiuses and are not always affected by displacement ...
        if precalc:

            sy, sx = mx_z.shape
            c1, c2 = np.mgrid[0 : sy, 0 : sx]
            
            if mode in [1, 2]: #'distance_weighted'
                c1, c2 = np.cumsum(c1, axis = 0), np.cumsum(c2, axis=1)
                max_val = sum([i for i in range(radius + 1)])
            else: 
                max_val = radius
                         
            c1, c2 = np.clip(c1, 0, max_val ), np.clip(c2, 0, max_val )
            
            # reverse and find distances to back edges
            np.minimum(c1, c1[::-1,:], c1); np.minimum(c2, c2[:, ::-1], c2)
            
            # orthogonal mode
            mx_cnt[:] = c1 + c2 + max_val * 2
            
            if denoise in [1, 3]: # diagonal mode
                diag =  c1 + c2 + np.minimum (c1, c2) + max_val 

                mx_cnt += diag / w_diag
                
        counter = 0
      
        #Loop through data chunks (and write results)
        for mx_view_in, gdal_take, mx_view_out, gdal_put in window_loop ( 
            shape = (dem.xsize, dem.ysize), 
            chunk = dem.chunk_x,
            overlap = overlap) :
            
            dem.rst.ReadAsArray(*gdal_take, mx_z[mx_view_in]).astype(float)

            mx_a[:]= 0
            if not precalc: mx_cnt[:]=0   
            
            # median filter
            if denoise == 2 : mx_z = median_filter(mx_z, radius = 3) 
                
            for dx, dy, limit in directions:

                for r in range (1, radius + 1):     
                    # ! analyse only the supplied data : mx_z[mx_view_in]
                    view_in, view_out = view(r * dy, r * dx, mx_z[mx_view_in].shape)
                    # this is for readability only
                    view_out2, view_in2 = view_in, view_out
                    
                    z, z2 = mx_z[view_in], mx_z[view_in2] 
                    
                    if mode == 3 : # height diffrence as weight
                        w = abs (z - z2) 
                    elif  mode == 1:    #'distance_weighted'
                        w = r
                    elif mode == 2: # inverse dist weighted
                        w = radius + 1 - r
                    else: w = 1   
                    
                    
                   # diagonal distance correction
                    if dx * dy != 0 : w /= w_diag
                    elif dx : w *= w_x # pixel size correction
                    else : w *= w_y 
          
                    
                   # NB - this is very expensive for heights: we can divide the entire DEM, 
                   # but we still need to keep the original for subtraction 
                                        
                    if limit: # threshold between light and heavy matrix regions
                        l = abs (limit)
                        w1 = w * (radius / (radius + l))
                        if r > l: # heavy region of the matrix
                            w2 = w * (radius / (radius - l)) 
                            # swap to change direction
                            if limit < 0: w2, w1 = w1, w2
                        else :   w2 = w1 # light region
                    else:  w1, w2 = w, w 
                                     
                    mx_a[view_out] += z * w1 
                    mx_a[view_out2] += z2 * w2 
                    
                    if not precalc :
                        # cannot predict these weights,
                        # in contrast to constant weights
                        mx_cnt[view_out] += w1
                        mx_cnt[view_out2] += w2
                        
                counter += 1 
                prog = dem.chunk_x * (counter/ (4 if denoise in [ 1, 3] else 2)) / dem.xsize
                feedback.setProgress(100 * prog)
                if feedback.isCanceled(): return{}
      
            
            # this is a patch : the last chunk is often spilling outside raster edge 
            # so, move the edge values to match raster edge
            end = gdal_take[2]           
            if precalc and end + gdal_take[0] == dem.xsize : 
                mx_cnt[:, end -radius : end] = mx_cnt[ : , -radius : ]
            
            mx_z -= mx_a / mx_cnt # weighted mean !
            out = mx_z
            
            dem.add_to_buffer(out[mx_view_out], gdal_put)
	
        return {self.OUTPUT: self.output_model}

    def postProcessAlgorithm(self, context, feedback):

        output = QgsProcessingUtils.mapLayerFromString(self.output_model, context)
        provider = output.dataProvider()

        stats = provider.bandStatistics(1,QgsRasterBandStats.All,output.extent(),0)
        mean, sd = stats.mean, stats.stdDev
        
        rnd = QgsSingleBandGrayRenderer(provider, 1)
        ce = QgsContrastEnhancement(provider.dataType(1))
        ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
        
        ce.setMinimumValue(mean - 2*sd)
        ce.setMaximumValue(mean + 2*sd)

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
        return 'Topographic position (TPI)'

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
             Topographic position index expresses the relative height of each elevation point within a specified radius. 
             
            <b>Input</b> should be an elevation model in raster format. 
            
            <b>Radius</b> defines the search radius (in pixels).

            There are 3 <b>analysis types</b>: 1) standard TPI, 2) distance weighted and 3) height weighted. Weighted options use elevation point distance or height discrepancy as weighting factor.   
            
            <b>Center of mass</b> : normally, when two altitudes are equal, their center of mass is precisely at half distance. Here, we can force this center to move (offset distance and azimuth).
            
            <b>Denoise</b> apply a smoothing filter. 
            
             For more information, check <a href = "https://landscapearchaeology.org/qgis-terrain-shading/" >the manual</a>.
            
            If you find this tool useful, consider to :
                 
             <a href='https://ko-fi.com/D1D41HYSW' target='_blank'><img height='30' style='border:0px;height:36px;' src='%s/help/kofi2.webp' /></a>
            """) % curr_dir
		
        return self.tr(h)

    def createInstance(self):
        return TpiAlgorithm()
