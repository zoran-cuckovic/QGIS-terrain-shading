# -*- coding: utf-8 -*-
"""
Created on Mon Feb 17 16:12:56 2025

@author: cucko
"""

import numpy as np

from typing import List
import math

from .Raster import Raster as rs
from .helpers import view, window_loop, median_filter



def visits_matrix(matrix_shape, radius,
                  distance_weighted = False,
                  diagonals=False, diagonal_weight = 1, exclusion=0):
    """ 
    pre-calculate the number of visits per cell 
    (cannot be done for height based weights)
    Considering mass displacement mode, the problem is to handle edges -> 
    they have shorter radii and are not always affected by displacement ...
    """
    
    sy, sx = matrix_shape
    mx_cnt = np.zeros((sy, sx))
    
    radius -= exclusion
    
    c1, c2 = np.mgrid[0 : sy, 0 : sx]
    
    if distance_weighted: 
        c1, c2 = np.cumsum(c1, axis = 0), np.cumsum(c2, axis=1)
        max_val = sum([i for i in range(radius + 1)])
    else: 
        max_val = radius
                 
    c1, c2 = np.clip(c1, 0, max_val ), np.clip(c2, 0, max_val )
    
    # reverse and find distances to back edges
    np.minimum(c1, c1[::-1,:], c1); np.minimum(c2, c2[:, ::-1], c2)
    
    # orthogonal mode
    mx_cnt[:] = c1 + c2 + max_val * 2
    
    if diagonals:
        diag =  c1 + c2 + np.minimum (c1, c2) + max_val 

        mx_cnt += diag / diagonal_weight 
    
    return mx_cnt
    

def TPI (dem_class, mode, radius, exclude = 0,
         offset_dist=0, offset_azimuth=0, denoise=None, feedback=None):
    
    #♦ !!!! TODO NODATA !!!!!        
           # nodata = dem.GetRasterBand(1).GetNoDataValue()
    
    
    dem = dem_class
    
    # Reverse the angle direction : this is required because the algorithm 
    # is organised in corresopndance to numpy matrix ordering (y first and descending). 
    offset_azimuth = 360 - offset_azimuth
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
    
    overlap = radius if not denoise else radius +1
    
    chunk_slice = (dem.ysize, dem.chunk_x + 2 * overlap)
    
    # define empty matrices to hold data : faster
    mx_z = np.zeros( chunk_slice)
    mx_a = np.zeros(mx_z.shape)
    
        
    # handling irregular pixels (lat long)
    # attention wy , wx are swapped - give the x weight to y dimension..
    w_y, w_x = dem.pix_x/dem.pix_y, dem.pix_y/dem.pix_x
    # ensure wx + wy = 2
    if w_x < 1 : w_y = 2 - w_x
    elif w_y < 1 : w_x = 2 - w_y
      
    # Diagonal for rectangular pixels 
    w_diag = np.sqrt (w_x**2 + w_y**2)
    
    
    # Lines that will be searched, radiating from each pixel.
    # Denoise option : a star shaped configuration (N, NE, E, SE etc)
    # For more directions : step = 0.5; 0.25; etc
    # !! We exploit symetry, pixel pairs are neighbours to each other,
    # but in opposite directions (N-S, E-W etc.)
    # Therefore no need to loop over opposite directions (here N and W)
    directions = [(0,1, offset_y),  (1,0, offset_x)] # orthogonal directions 
    if denoise in [1,3]: directions += [(1,1, offset_y_diag), (1, -1, offset_x_diag)]
        
    precalc = not offset_x and not offset_y and mode in [0,1] # TODO for inverse dist ( mode = 2) !
    
    if precalc: 
        mx_cnt =  visits_matrix (mx_z.shape,radius,
                                diagonals = denoise in [1, 3], 
                                distance_weighted = mode==1,
                                exclusion = exclude)
        
    else : 
        mx_cnt =  np.zeros(mx_z.shape)


    
    counter = 0
  
    #Loop through data chunks (and write results)
    for mx_view_in, gdal_take, mx_view_out, gdal_put in window_loop ( 
        shape = (dem.xsize, dem.ysize), 
        chunk = dem.chunk_x,
        overlap = overlap) :
        
        dem.rst.ReadAsArray(*gdal_take, mx_z[mx_view_in]).astype(float)

        mx_a[:]= 0
        if not precalc: mx_cnt[:]=0   
        
        # median filter ?? BEFORE OR AFTER ANALYSIS ??
        if denoise == 2 : mx_z = median_filter(mx_z, radius = 3) 
            
        for dx, dy, limit in directions:

            for r in range (1 + exclude, radius + 1):     
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
        
    return 1 #should return the file name... 