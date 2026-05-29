# -*- coding: utf-8 -*-
"""
Created on Mon Feb 17 16:12:56 2025

@author: cucko
"""

import numpy as np

from typing import List
import math

from .Raster import Raster as rs
from .helpers import view, window_loop, median_filter, nextprod, filter3



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

# TODO FOR SHADOWS
def shear_matrix_projection(matrix, azimuth, steep, pixel_size, tilt):
    """
    Projects a 2D matrix into a sheared space according to azimuth angle.
    
    Parameters:
    - matrix: 2D input array (e.g., elevation)
    - azimuth: direction of light or slope in degrees (0° = North, 90° = East)
    - steep: if True, apply shearing in the vertical direction; else horizontal
    - pixel_size: real-world size of one pixel
    - tilt: scaling factor for projection
    """
    H, W = matrix.shape

    # Grid of coordinates
    y, x = np.meshgrid(np.arange(H), np.arange(W), indexing='ij')
    coords = np.stack([x.ravel(), y.ravel()], axis=0)  # shape: (2, N)

    # Convert azimuth to radians, relative to image axes (0° = North, 90° = East)
    azimuth_rad = np.radians(azimuth)
    dx = np.cos(azimuth_rad)  # x-component of light direction
    dy = np.sin(azimuth_rad)  # y-component of light direction

    # Build shear matrix based on azimuth and steepness
    if steep:
        shear_matrix = np.array([
            [1, dx],
            [0, 1]
        ])
    else:
        shear_matrix = np.array([
            [1, 0],
            [dy, 1]
        ])

    # Apply shear transformation
    sheared_coords = shear_matrix @ coords
    sheared_x = np.round(sheared_coords[0]).astype(int).reshape(H, W)
    sheared_y = np.round(sheared_coords[1]).astype(int).reshape(H, W)

    # Calculate projected offset distance
    distance = (x + y) * pixel_size * np.cos(azimuth_rad) * tilt

    # Preallocate the sheared matrix
    out_height = sheared_y.max() + 1
    out_width = sheared_x.max() + 1
    mx_temp = np.zeros((out_height, out_width))

    return sheared_x, sheared_y, distance, mx_temp    


def TPI (dem_class, mode, radius, exclude = 0,
         offset_dist=0, offset_azimuths=(0), denoise=None, 
        feedback=None):
    """
    Compute Topographic Position Index (TPI) from a DEM.

    Parameters:
        dem_class: object
            A DEM wrapper with raster access and chunking (expects .rst, .xsize, .ysize, etc.)
        mode: int
            Weighting mode:
              0 = uniform
              1 = distance weighted
              2 = inverse distance
              3 = height-difference weighted
        radius: int
            Radius of neighborhood
        exclude: int, optional NOT USED !
            Exclusion radius around the central pixel
        offset_dist: float, optional
            Distance for directional offset
        offset_azimuth: float, optional
            Azimuth in degrees (clockwise from north)
        denoise: int or None, optional
            Denoising option: 
              1 or 3 = star shape
              2 = median filter
        feedback: object or None, optional
            QGIS-style progress object with .setProgress() and .isCanceled()
    """
    
    dem = dem_class
    # ensure it's iterable
    offset_azimuths = np.atleast_1d(offset_azimuths)
       
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
    
    precalc = mode in [0,1] and not offset_dist 
    # TODO for inverse dist ( mode = 2) !
        
    if precalc: 
        mx_cnt =  visits_matrix (mx_z.shape,radius,
                                    diagonals = denoise in [1, 3], 
                                    distance_weighted = mode==1,
                                    exclusion = exclude)
    else : mx_cnt =  np.zeros(mx_z.shape)
        
 
    # handling irregular pixels (lat long)
    # attention wy , wx are swapped - give the x weight to y dimension..
    w_y, w_x = dem.pix_x/dem.pix_y, dem.pix_y/dem.pix_x
    # ensure wx + wy = 2
    if w_x < 1 : w_y = 2 - w_x
    elif w_y < 1 : w_x = 2 - w_y
      
    # Diagonal for rectangular pixels 
    w_diag = np.sqrt (w_x**2 + w_y**2)
    
    
    # TEMPORARY SOLUTION  - rerun everything for each azimuth
    # this can be made more efficently by extracting vectors for at least two directions
    for band, offset_azimuth in enumerate (offset_azimuths, start =1):
            
        # Reverse the angle direction : this is required because the algorithm 
         # is organised in corresopndance to numpy matrix ordering (y first and descending). 
         offset_azimuth = 360 - offset_azimuth
              # decompose angle and distance to pixel coords
         offset_x = offset_dist * np.sin(np.radians(offset_azimuth))
         offset_y = offset_dist * np.cos(np.radians(offset_azimuth))
         offset_x_diag = offset_dist * np.sin(np.radians(offset_azimuth - 45))
         offset_y_diag = offset_dist * np.cos(np.radians(offset_azimuth - 45))
        
        # Lines that will be searched, radiating from each pixel.
        # Denoise option : a star shaped configuration (N, NE, E, SE etc)
        # For more directions : step = 0.5; 0.25; etc
        # !! We exploit symetry, pixel pairs are neighbours to each other,
        # but in opposite directions (N-S, E-W etc.)
        # Therefore no need to loop over opposite directions (here N and W)
         directions = [(0,1, offset_y),  (1,0, offset_x)] # orthogonal directions 
         if denoise in [1,3]: directions += [(1,1, offset_y_diag), (1, -1, offset_x_diag)]
            
         counter = 0
          
        #Loop through data chunks (and write results)
         for mx_view_in, gdal_take, mx_view_out, gdal_put in window_loop ( 
            shape = (dem.xsize, dem.ysize), 
            chunk = dem.chunk_x,
            overlap = overlap) :
            
            bd = dem.rst.GetRasterBand(1)
            mx_z[mx_view_in] = bd.ReadAsArray(*gdal_take).astype(float)

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
                feedback.setProgress(100 * prog )
                if feedback.isCanceled(): return{}
          
            
            # this is a patch : the last chunk is often spilling outside raster edge 
            # so, move the edge values to match raster edge
            end = gdal_take[2]           
            if precalc and end + gdal_take[0] == dem.xsize : 
                mx_cnt[:, end -radius : end] = mx_cnt[ : , -radius : ]
            
            mx_z -= mx_a / mx_cnt # weighted mean !
            out = mx_z
            

            dem.add_to_buffer(out[mx_view_out], gdal_put, band = band)
        
    return 1 #should return the file name... 

def occlusion (dem_class, radius, openness = False, denoise= False , 
               invert=False, symmetric= False, contrast = False, 
               feedback = None):
   
    # STILL TESTING
    difference = None 
    
    dem = dem_class
    overlap = radius if not denoise else radius +1
             
    chunk_slice = (dem.ysize, dem.chunk_x + 2 * overlap)
                        
    mx_z = np.zeros(chunk_slice)
    mx_a = np.zeros(mx_z.shape)
  
    if symmetric: mx_b = mx_a
    else: mx_b = np.zeros(mx_z.shape)
    
    mx_a = np.zeros(mx_z.shape + ((radius ,) ))
    mx_b = np.zeros(mx_z.shape + ((radius ,) ))
     
    out =  np.zeros(mx_z.shape)
            
    # intialise the count of lines per pixel
    mx_cnt = np.ones(mx_z.shape)
    # set borders first  
    mx_cnt[:]= 5 if not symmetric else 3
    # main area : 8 lines per pixel (or 4 if symmetric algo)
    mx_cnt[1:-1, 1:-1] = 8 if not symmetric else 4
    # corners
    for v in [(0,0),(-1,-1),(0,-1), (-1,0)]: mx_cnt[v] = 3
           
    counter = 0
        
    for mx_view_in, gdal_take, mx_view_out, gdal_put in window_loop ( 
        shape = (dem.xsize, dem.ysize), 
        chunk = dem.chunk_x,
        overlap = overlap) :
        
        if counter : out[:] = 0 # reset
        
        dem.rst.ReadAsArray(*gdal_take, mx_z[mx_view_in]).astype(float)
        # NODATA : TODO !
        # mx_z[mx_z == nodata] = 0
        
        if invert : mx_z *= -1
        
        if denoise in [2, 3] : mx_z = median_filter(mx_z, radius= 3)
        if denoise in [1, 3] : mx_z = filter3(mx_z) # after the median filter
        

        # 8 standard lines, we use symmetry to optimise
        for dy, dx in [(0,1), (1,0), (1, -1), (1,1)]:
            
            if dx * dy : pix = np.sqrt( dem.pix_y**2 + dem.pix_x**2)
            else : pix = dem.pix_y if dx else dem.pix_x #swapped x, y
            
            for r in range (1, radius + 1): 
                # we could probably sample over radius, not all pixels are needed...
                                             
                view_in, view_out = view(r * dx, r * dy, mx_z[mx_view_in].shape)

                angles = mx_z[view_in] - mx_z[view_out]
                                               # diagonals         
                dist = r * pix
                
                angles /= dist 
 
                mx_a[view_out][:,:,r-1] = angles
                mx_b[view_in][:,:,r-1] = -angles
                
                # a patch for irregular pixels : take care of the length of the LOS
                if dist > min(dem.pix_x * radius, dem.pix_y * radius) : break
           
            if not openness:  # sky view factor - remove negative angles
                mx_a [mx_a < 0] = 0; mx_b[mx_b < 0] = 0
             
            max_a = np.max(mx_a, axis = 2)
            max_b = np.max(mx_b, axis = 2)
            
            if difference : 
                max_a -= np.min(mx_a, axis = 2)
                max_b -= np.min(mx_b, axis = 2)
                          
            # average of angles: see Kokalj et al. 2011
            # these operations are costly, however ...
            if symmetric : 
                # find the highest angle for each *pair* of LOS
                np.maximum(max_a, max_b, out=max_a)
                out += np.sin(np.arctan(max_a) )
            else: 
                out += np.sin(np.arctan(max_a)) 
                out += np.sin(np.arctan(max_b)) 
            
            mx_a[:] = 0 ; mx_b[:] = 0 # clean-up, remove old values 

            counter += 1
            
            feedback.setProgress(100 * dem.chunk_x * (counter/4) /  dem.xsize)
            if feedback.isCanceled(): return {}
        
        # this is a patch : last chunk is often spilling outside raster edge 
        # so, move the edge values to match raster edge
        end = gdal_take[2]           
        if end + gdal_take[0] == dem.xsize : 
            mx_cnt[:, end-1: end] = mx_cnt[:, -1:] 
        
        out /= mx_cnt
        out = 1 - out
        # high exposant for better contrast (in typical terrain)
        if contrast : out**=10
        dem.add_to_buffer(out[mx_view_out], gdal_put)
    
    return 1 #should return the file name... 

def texture (dem_class, alpha, feedback=None ):
  
    dem = dem_class  
    chunk_slice_x = (dem.ysize, dem.chunk_x ) 
    chunk_slice_y = (dem.chunk_y, dem.xsize) 
          
    # define empty matrices to hold data : faster
    mx_z_x = np.zeros( chunk_slice_x)
    mx_z_y = np.zeros( chunk_slice_y)
    
    # simualte a large domain, otherwise fft assumes a circular shape
   # where edges of the raster matix wrap to fix each other
    Ny = nextprod([2, 3, 5, 7], dem.ysize) 
    Nx = nextprod([2, 3, 5, 7], dem.xsize)
    fy = np.fft.rfftfreq(Ny)[:, np.newaxis].astype(mx_z_y.dtype)
    fx = np.fft.rfftfreq(Nx)[np.newaxis, :].astype(mx_z_x.dtype)
    
    # this is not the correct formula ; orginally :
    # H = (fy**2 + fx**2 ) ** (alpha / 2.0)
    # when alpha = 1 : the result is identical (i.e. pure laplacian filter)
    Hy, Hx = ((fy** 2) ** alpha)  , ((fx ** 2) ** alpha)
                     
    counter = 0
    
    # Break the operation to two axes (x, y) : this works fine for laplacian filter,
    # but it does not quite work for the *fractional* laplacian (here fraction = alpha)
    # the result is only very slightly degraded for alpha = 0.5 ...
    for axis in [0,1]:
        if axis:
          chunk = dem.chunk_y
          mx_z = mx_z_y
          N, H = Nx, Hx # bit messy x, y swaps..
        else: 
          chunk = dem.chunk_x
          mx_z = mx_z_x
          N, H = Ny, Hy 
       
        for mx_view_in, gdal_take, mx_view_out, gdal_put in window_loop ( 
                shape = (dem.xsize, dem.ysize), 
                chunk = chunk,
                axis = axis) :
            
            mx_z[mx_view_in] = dem.rst.ReadAsArray(*gdal_take).astype(float) 
            #dem.take(gdal_take, mx_z[mx_view_in], fill_nodata = 0)
                                    
            r = np.fft.rfft(mx_z, N, axis=axis) * H
            r = np.fft.irfft(r, axis=axis)
            
            # Return the same size as input
            out = r [:mx_z.shape[0], :mx_z.shape[1]]
            
            # axis = 1 : second round, add old data
            dem.add_to_buffer(out[mx_view_out], gdal_put, 
                               mode = 1 if axis else 0, # 1 = ADD, 0 = DUMP
                               automatic_save = axis)
      
            counter += 1
            if feedback:
                feedback.setProgress(100 * chunk * (counter / (dem.xsize + dem.ysize)))
                if feedback.isCanceled(): return{}
                
# TODO - DETREND ==> nmake edges match to remove shadows at the border
# but this could introduce strips/seams...
    #  dx = tile[:, -1] - tile[:, 0]
    #  dy = tile[-1, :] - tile[0, :]

    # xw = np.linspace(0, 1, tile.shape[1])
    # yw = np.linspace(0, 1, tile.shape[0])

    # corr_x = dx[:, None] * xw[None, :]
    # corr_y = dy[None, :] * yw[:, None]

    # tile2 = tile - corr_x - corr_y
        
# FUTURE IMPROVEMENT - diagonal components (we only use x and y otherwise)


            # F = np.fft.rfft2(tile, s=(Ny, Nx))
            
            # # frequency grids (per tile OR precomputed if fixed size)
            # fy = np.fft.fftfreq(Ny)[:, None]
            # fx = np.fft.rfftfreq(Nx)[None, :]
            
            # kx = fx
            # ky = fy
            
            # # isotropic
            # H0 = (kx*kx + ky*ky) ** (alpha/2)
            
            # # directional components
            # H45  = ((kx + ky)**2) ** (alpha/2)
            # H135 = ((kx - ky)**2) ** (alpha/2)
            # Hx   = (kx*kx) ** (alpha/2)
            # Hy   = (ky*ky) ** (alpha/2)
            
            # # mix
            # H = (
            #     0.4 * H0 +
            #     0.2 * H45 +
            #     0.2 * H135 +
            #     0.1 * Hx +
            #     0.1 * Hy
            # )
            
            # H[0,0] = 0
            
            # F *= H
            
            # out = np.fft.irfft2(F, s=(Ny, Nx))
            
            
    return 1
