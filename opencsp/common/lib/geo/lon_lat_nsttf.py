# -*- coding: utf-8 -*-
"""

Geospatial position calculations for the Sandia NSTTF.

"""

import math
import numpy as np

# COORDINATE SYSTEM ORIGIN

LON_NSTTF_ORIGIN_DEG = -106.509606  # Six decimal places correspond to about 11 cm resolution.
LAT_NSTTF_ORIGIN_DEG = 34.962276  #

LON_NSTTF_ORIGIN: float = np.deg2rad(LON_NSTTF_ORIGIN_DEG)
LAT_NSTTF_ORIGIN: float = np.deg2rad(LAT_NSTTF_ORIGIN_DEG)

NSTTF_ORIGIN = [LON_NSTTF_ORIGIN, LAT_NSTTF_ORIGIN]


# APPROXIMATION


def nsttf_lon_lat_given_xy(x, y):
    """
    Returns the (latitude,longitude) coordinates of a given (x, y) point
    in the NSTTF Field coordinate system.

    Here is the original version of this routine:

            import sys
            !conda install --yes --prefix {sys.prefix} pyproj

            from pyproj import Geod

            def angle_distance(x,y):
                # Convert to math degrees
                m_ang = (180.0/math.pi)*math.atan2(y,x)
                # Convert to true north compass heading
                c_ang = (450-m_ang)%360
                dist = math.sqrt(x*x + y*y)
                return c_ang, dist

            def xy_lat_lon(point):
                # Returns the Latitude, Longitude of a given x-y point for NSTTF Field
                geo = Geod(ellps="WGS84")
                orig_Lat =   34.962276 # NSTTF
                orig_Lon = -106.509606 # NSTTF
                x, y = point[0], point[1]
                ang, dist = angle_distance(x,y)
                lon, lat, bzaz = geo.fwd(orig_Lon, orig_Lat, ang, dist)
                return lat, lon

            # # x-y point to Lat, Lon (Example)
            # # Note: for an x,y,z point the Lat, Lon will be generated by using the x, y coordinates, and the Alt = z.
            # point = [10, 10]
            # lat, lon = xy_lat_lon(point)
            # print(lat, lon)

    Since the above code requires a Python package and I didn't have time
    to install it, below we use a simpler calculation gleaned from StackOverflow:
    https://gis.stackexchange.com/questions/2951/algorithm-for-offsetting-a-latitude-longitude-by-some-amount-of-meters

    This calculation takes advantage of the small angular difference in
    longitude and latitude between nearby (x,y) locations.  For small angles,
    sin(theta) = theta, when theta is expressed in radians.  Thus small angles
    correspond to linear measures.  The scale factor 111,111.111111 captures
    the unit conversion between meters and degrees.  Here is a nice explanation
    from the StackOverflow site:

        Incidentally, these magic numbers of 111,111 are easy to remember
        by knowing some history: The French originally defined the meter so
        that 10^7 meters would be the distance along the Paris meridian from
        the equator to the north pole. Thus, 10^7 / 90 = 111,111.1 meters
        equals one degree of latitude to within the capabilities of French
        surveyors two centuries ago. – whuber Oct 27 '10 at 21:38

    Note this only works for small displacements.  The StackOverflow site states
    "less than a few kilometers."  For NSTTF, we're nowhere near that threshold.

    Sanity check:
        The Earth diameter is 12.742e6 m.
        Radius is 6.371e6 m.
        Circumference is 40.030174e6 m.
        Dividing by 360 --> 111,194.93 m.
    We'll go with the 111,111.111 constant described above, because it is driven
    by the definition.  In any case, we do not know locations of heliostats etc
    to such fine precision.

    Later, we should consider replacing this with geospatial library calls, as
    in the original code.
    """
    delta_lon_deg = x / (111111.111111 * math.cos(LAT_NSTTF_ORIGIN))
    delta_lat_deg = y / 111111.111111

    lon = LON_NSTTF_ORIGIN_DEG + delta_lon_deg
    lat = LAT_NSTTF_ORIGIN_DEG + delta_lat_deg

    return lon, lat


def nsttf_xy_given_lon_lat(lon, lat):
    """
    Returns the (x,y) coordinates of a given (latitude,longitude) point
    in the NSTTF Field coordinate system.

    Approximation produced by inverting nsttf_lon_lat_given_xy() above.
    """
    delta_lon_deg = lon - LON_NSTTF_ORIGIN_DEG
    delta_lat_deg = lat - LAT_NSTTF_ORIGIN_DEG

    x = delta_lon_deg * (111111.111111 * math.cos(LAT_NSTTF_ORIGIN))
    y = delta_lat_deg * 111111.111111

    return x, y
