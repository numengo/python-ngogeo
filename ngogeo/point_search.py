# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import difflib
from collections import OrderedDict
from pprint import pprint
import pandas as pd
import geopandas as gpd
import shapely
import shapely.geometry
from shapely.geometry import Point, Polygon, MultiPoint
import overpy

from ngoschema.protocols import with_metaclass, SchemaMetaclass, ObjectProtocol
from ngogeo import settings as geo_settings

api = overpy.Overpass()

DEFAULT_RADIUS_SEARCH = geo_settings.DEFAULT_RADIUS_SEARCH


def _make_point_to_crs(point, point_crs=None, dest_crs=None):
    if isinstance(point, gpd.GeoDataFrame):
        point_gdf = point
    else:
        point_gdf = gpd.GeoDataFrame(geometry=[point] if isinstance(point, Point) else [Point(*point)], crs=point_crs)
    dest_crs = dest_crs or point_gdf.crs
    if not point_gdf.crs.is_exact_same(dest_crs):
        point_gdf = point_gdf.to_crs(dest_crs)
    res = point_gdf.geometry[0]
    res._crs = dest_crs
    return res


def _search_name(df, name, regex=False, **kwargs):
    """Returns the most likely result as a pandas Series"""
    # Make a copy of the dataset to preserve the original

    # Filter data by string queries before searching
    filters = {**kwargs}
    for key, val in filters.items():
        if val is not None:
            df = df[
                df[key].str.contains(val, case=False, regex=regex, na=False)
            ]

    # Use difflib to find matches
    diffs = difflib.get_close_matches(name, df['name'].tolist(), n=1, cutoff=0)
    matches = df[df['name'] == diffs[0]]

    def certainty(result_name):
        return difflib.SequenceMatcher(None, result_name, name).ratio()

    matches['certainty'] = matches['name'].apply(certainty)
    return matches.sort_values(by=['certainty'], ascending=False)


def _search_radius(gdf, point, radius=DEFAULT_RADIUS_SEARCH, point_crs=None, regex=False, **kwargs):
    # Filter data by string queries before searching
    filters = {**kwargs}
    for key, val in filters.items():
        gdf = gdf[
            gdf[key].str.contains(val, case=False, regex=regex, na=False)
        ]
    # https://gis.stackexchange.com/questions/349637/given-list-of-points-lat-long-how-to-find-all-points-within-radius-of-a-give
    if isinstance(point, gpd.GeoDataFrame):
        point_gdf = point
    else:
        point_crs = point_crs or geo_settings.EPSG4326_CRS
        point_gdf = gpd.GeoDataFrame(geometry=[point] if isinstance(point, Point) else [Point(*point)], crs=point_crs)
    if not point_gdf.crs.is_exact_same(gdf.crs):
        point_gdf = point_gdf.to_crs(gdf.crs)
    x = point_gdf.buffer(radius).convex_hull.unary_union
    ret = gdf[gdf["geometry"].within(x)]
    ret['distance'] = ret.geometry.distance(point_gdf.geometry[0])
    return ret.sort_values(by=['distance'])


def _search_elements(bbox, element='node', crs=None, **kwargs):
    crs = crs or geo_settings.WSG84_CRS
    attrs = ', '.join([f'"{k}"="{v}"' for k, v in kwargs.items()])
    result = api.query(f"[out:xml];{element}[{attrs}]({bbox});out;")
    elements = getattr(result, element + 's')
    ids = [n.id for n in elements]
    points = [Point(n.lon, n.lat) for n in elements]
    tags = [n.tags for n in elements]
    attributes = [n.attributes for n in elements]
    df = gpd.GeoDataFrame(dict(ids=ids, tags=tags, attributes=attributes),
                          geometry=points, crs=geo_settings.WSG84_CRS)
    return df if df.crs.is_exact_same(crs) else df.to_crs(crs)


def _search_elements_radius(point, radius, point_crs=None, element='node', crs=None, **kwargs):
    wsg84_crs = geo_settings.WSG84_CRS
    crs = crs or wsg84_crs
    if isinstance(point, gpd.GeoDataFrame):
        point_gdf = point
    else:
        point_crs = point_crs or wsg84_crs
        point_gdf = gpd.GeoDataFrame(geometry=[point] if isinstance(point, Point) else [Point(*point)], crs=point_crs)
    if not point_gdf.crs.is_exact_same(wsg84_crs):
        point_gdf = point_gdf.to_crs(wsg84_crs)
    bbox = point_gdf.buffer(radius).envelope.to_crs(geo_settings.WSG84_CRS).bounds
    bbox = f'{bbox.miny[0]:.3f}, {bbox.minx[0]:.3f}, {bbox.maxy[0]:.3f}, {bbox.maxx[0]:.3f}'
    return _search_elements(bbox, element=element, crs=crs, **kwargs)


def search_nodes_radius(point, radius, point_crs=None, crs=None, **kwargs):
    return _search_elements_radius(point, radius, point_crs=point_crs, element='node', crs=crs, **kwargs)


def search_ways_radius(point, radius, point_crs=None, crs=None, **kwargs):
    return _search_elements_radius(point, radius, point_crs=point_crs, element='ways', crs=crs, **kwargs)


def search_relations_radius(point, radius, point_crs=None, crs=None, **kwargs):
    return _search_elements_radius(point, radius, point_crs=point_crs, element='relations', crs=crs, **kwargs)


class Point2(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/coordinates/$defs/Point"

    def __init__(self, value=None, **opts):
        ObjectProtocol.__init__(self, value=value, **opts)

    def get_point(self):
        return _make_point_to_crs((self.longitude, self.latitude), point_crs=self.crs)

    def get_country(self):
        cn = self._dataValidated['addressCountry']
        from .territories import get_world
        world = get_world()
        world.countries
        pass

    def get_territory(self):
        pass
