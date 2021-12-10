# -*- coding: utf-8 -*-

"""Main module NgoGeo """
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import dpath.util
import difflib
from collections import OrderedDict
from pprint import pprint
import pandas as pd
import geopandas as gpd
import shapely
import shapely.geometry
from shapely.geometry import Point, Polygon, MultiPoint

from .geonames import load_geonames_gdf, load_countries, load_cities, load_timezones, load_currencies, load_languages
from .postals import load_postals_gdf

# country info and subdivisions
import pycountry
from currencies import Currency

import overpy

from ngogeo import settings as geo_settings

api = overpy.Overpass()


def _make_point_to_crs(point, point_crs=None, dest_crs=None):
    if isinstance(point, gpd.GeoDataFrame):
        point_gdf = point
    else:
        point_gdf = gpd.GeoDataFrame(geometry=[point] if isinstance(point, Point) else [Point(*point)], crs=point_crs)
    dest_crs = dest_crs or point_gdf.crs
    if not point_gdf.crs.is_exact_same(dest_crs):
        point_gdf = point_gdf.to_crs(dest_crs)
    return point_gdf.geometry[0]


def _search_name(df, name, regex=False, **kwargs):
    """Returns the most likely result as a pandas Series"""
    # Make a copy of the dataset to preserve the original

    # Filter data by string queries before searching
    filters = {**kwargs}
    for key, val in filters.items():
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


def _search_radius(gdf, point, radius=10000, point_crs=None, regex=False, **kwargs):
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
        point_crs = point_crs or gdf.crs
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


class Territory:
    code: str
    name : str
    infos : pd.Series
    cities : gpd.GeoDataFrame
    postals : gpd.GeoDataFrame
    geonames : gpd.GeoDataFrame
    subdivisions: OrderedDict
    box: shapely.geometry.MultiPoint
    crs = geo_settings.DEFAULT_CRS

    def __init__(self, name, cities=None, postals=None, geonames=None, crs=None, parent=None, bound_from_cities=True):
        from shapely.geometry import Polygon
        self.name = name
        self.crs = crs = crs or self.crs
        self.cities = cities if cities is None or cities.crs.is_exact_same(crs) else cities.to_crs(crs)
        self.postals = postals if postals is None or postals.crs.is_exact_same(crs) else postals.to_crs(crs)
        self.geonames = geonames if geonames is None or geonames.crs.is_exact_same(crs) else geonames.to_crs(crs)
        self.subdivisions = OrderedDict()
        self.parent = parent
        self.box = None
        if bound_from_cities and cities is not None:
            cs = gpd.GeoSeries([MultiPoint(self.cities.geometry.to_list())], crs=crs)
            self.bnd = cs.convex_hull[0]
            self.box = self.bnd.minimum_rotated_rectangle.buffer(10000, resolution=4)
            bbox = cs.envelope.to_crs(geo_settings.WSG84_CRS).bounds
            self.bbox = f'{bbox.miny[0]:.3f}, {bbox.minx[0]:.3f}, {bbox.maxy[0]:.3f}, {bbox.maxx[0]:.3f}'

    def __str__(self):
        return f'<{self.__class__.__name__} {self.name}>'

    def search_geonames_name(self, name, regex=False, **kwargs):
        return _search_name(self.geonames, name, regex=regex, **kwargs)

    def search_city_name(self, name, regex=False, **kwargs):
        return _search_name(self.cities, name, regex=regex, **kwargs)

    def search_postal_code(self, codes, unique=False):
        if isinstance(codes, int):
            codes = str(codes)

        if isinstance(codes, str):
            codes = [codes]
            single_entry = True
        else:
            single_entry = False

        if not isinstance(codes, pd.DataFrame):
            codes = pd.DataFrame(codes, columns=["postal_code"])
        # normalize
        codes["postal_code"] = codes.postal_code.str.upper()
        response = pd.merge(
            codes, self.postals, on="postal_code", how="left"
        )
        if unique and single_entry:
            response = response.iloc[0]
        return response

    def search_nodes(self, **kwargs):
        return _search_elements(self.bbox, element='node', crs=self.crs, **kwargs)

    def search_ways(self, **kwargs):
        return _search_elements(self.bbox, element='ways', crs=self.crs, **kwargs)

    def search_areas(self, **kwargs):
        return _search_elements(self.bbox, element='areas', crs=self.crs, **kwargs)

    def search_relations(self, **kwargs):
        return _search_elements(self.bbox, element='relations', crs=self.crs, **kwargs)

    def search_geonames_radius(self, point, radius=10000, point_crs=None, regex=False, **kwargs):
        return _search_radius(self.geonames, point, radius=radius, point_crs=point_crs, regex=regex, **kwargs)

    def search_cities_radius(self, point, radius=10000, point_crs=None, regex=False, **kwargs):
        return _search_radius(self.cities, point, radius=radius, point_crs=point_crs, regex=regex, **kwargs)

    def search_postals_radius(self, point, radius=10000, point_crs=None, regex=False, **kwargs):
        return _search_radius(self.postals, point, radius=radius, point_crs=point_crs, regex=regex, **kwargs)

    def make_point_to_crs(self, point, point_crs=None, dest_crs=None):
        point_crs = point_crs or self.crs
        dest_crs = dest_crs or self.crs
        return _make_point_to_crs(point, point_crs=point_crs, dest_crs=dest_crs)

    def contains(self, point, point_crs=None, only_box=False):
        point = self.make_point_to_crs(point, point_crs)
        if self.box.intersects(point):
            return True if only_box else self.bnd.intersects(point)
        return False

    def locate(self, point, point_crs=None):
        point = self.make_point_to_crs(point, point_crs)
        if self.box.intersects(point):
            for s in self.subdivisions.values():
                if s.box.intersects(point):
                    l = s.locate(point)
                    if l:
                        return l
            return self


class Admin3(Territory):
    code = 'admin3'


class Admin2(Admin3):
    code = 'admin2'
    admin3: OrderedDict

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.admin3 = OrderedDict()


class Admin1(Admin2):
    code = 'admin1'
    admin2: OrderedDict

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.admin2 = OrderedDict()


class Country(Admin1):
    code = 'countrycode'
    admin1: OrderedDict

    def __init__(self, name, infos, **kwargs):
        super().__init__(name, bound_from_cities=False, **kwargs)
        self.infos = infos
        cs = gpd.GeoSeries([self.infos.geometry], crs=geo_settings.WSG84_CRS).to_crs(self.crs)
        ch = cs.explode().geometry.convex_hull
        self.bnd = ch.unary_union
        self.box = self.bnd.minimum_rotated_rectangle
        bbox = cs.envelope.to_crs(geo_settings.WSG84_CRS).bounds
        self.bbox = f'{bbox.miny[0]:.3f}, {bbox.minx[0]:.3f}, {bbox.maxy[0]:.3f}, {bbox.maxx[0]:.3f}'
        self.languages = [world.languages.get(alpha_2=c.split('-')[0]) for c in
                          infos['Languages'].split(',')]
        cc = infos['CurrencyCode']
        self.currency = world.currencies.get(alpha_3=cc)
        self.currency_fmt = Currency(cc)
        self.admin1 = OrderedDict()
        if self.cities is not None:
            for idx, row in self.cities.iterrows():
                if row['featurecode'] == 'PPLC':
                    self.capital = row
                    break

    def contains(self, point, point_crs=None):
        point = self.make_point_to_crs(point, point_crs)
        return self.bnd.contains(point) if self.box.contains(point) else False


class Continent(Territory):
    code = 'continent'
    countries: OrderedDict
    countries_gdf: gpd.GeoDataFrame
    crs = geo_settings.WSG84_CRS

    def __init__(self, *args, countries_gdf, **kwargs):
        super().__init__(*args, bound_from_cities=False, **kwargs)
        self.countries = OrderedDict()
        self.countries_gdf = countries_gdf
        if countries_gdf.geometry.any():
            # geometry is defined. we are normally served with a boundary geometry also EPSG:4326
            self.bnd = gpd.GeoSeries(countries_gdf['bnd'])
            self.box = self.bnd.unary_union.envelope

    def contains(self, point, point_crs=None):
        for cc, country in self.countries.items():
            if country.contains(point, point_crs):
                return True
        # box and boundaries come from countries and are in EPSG:4326
        point = self.make_point_to_crs(point, point_crs)
        return self.bnd.contains(point).any()

    def locate(self, point, point_crs=None):
        for cc, country in self.countries.items():
            if country.contains(point, point_crs):
                return country.locate(point, point_crs)
        point = self.make_point_to_crs(point, point_crs)
        for cc, bnd in self.bnd.iteritems():
            if bnd.contains(point):
                return cc


class World(Continent):
    code = 'world'
    continents: OrderedDict

    def __init__(self, city_file='cities5000', with_shapes=True, crs=None, **kwargs):
        import numpy as np
        cities = load_cities(city_file, crs=crs)
        countries_gdf = load_countries(with_shapes=with_shapes)
        if with_shapes:
            countries_bnd = countries_gdf.geometry.explode().convex_hull
            countries_gdf['bnd'] = gpd.GeoDataFrame(geometry=countries_bnd).dissolve('ISO')
        super().__init__('World', countries_gdf=countries_gdf, cities=cities, crs=crs, **kwargs)
        self.continents = continents = OrderedDict()
        for cc, countries_continent in countries_gdf.groupby('Continent'):
            cities_continent = cities[cities['countrycode'].isin(countries_continent.index.to_list())]
            continents[cc] = Continent(cc, countries_gdf=countries_continent, cities=cities_continent)
        self.languages = pycountry.languages # pycountry languages better than iso geonames
        self.currencies = load_currencies()
        self.tzs = load_timezones()

    def load_country(self, country_code, with_postals=True, with_geonames=False):
        ucc = country_code.upper()
        crs = self.crs
        world_countries_df = self.countries_gdf
        world_countries = self.countries
        world_continents = self.continents
        world_cities = self.cities
        country = world_countries.get(ucc)
        if country is None:
            country_infos = world_countries_df.loc[ucc]
            continent_code = country_infos['Continent']
            continent = world_continents[continent_code]
            country_cities = world_cities[world_cities['countrycode'] == ucc]
            country_postals = load_postals_gdf(ucc, crs=crs) if with_postals else None
            country_geonames = load_geonames_gdf(ucc, crs=crs) if with_geonames else None
            country = Country(country_infos['Country'], infos=country_infos, parent=continent,
                               cities=country_cities, postals=country_postals, geonames=country_geonames)
            continent.subdivisions[ucc] = continent.countries[ucc] = world_countries[ucc] = country
            by_admin1 = country_cities.groupby('admin1code')
            for a1, admin1_cities in by_admin1:
                admin1_geonames = country_geonames[country_geonames['admin1code'] == a1] if with_geonames else None
                admin1_postals = country_postals[country_postals['state_code'] == float(a1)] if with_postals else None
                admin1_aliases = admin1_postals['state_name'].unique() if with_postals else [a1]
                ca1 = Admin1(admin1_aliases[0], parent=country,
                             cities=admin1_cities, postals=admin1_postals, geonames=admin1_geonames)
                country.subdivisions[a1] = country.admin1[a1] = ca1
                by_admin2 = admin1_cities.groupby('admin2code')
                for a2, admin2_cities in by_admin2:
                    admin2_geonames = admin1_geonames[admin1_geonames['admin2code'] == a2] if with_geonames else None
                    admin2_postals = admin1_postals[admin1_postals['county_code'] == a2] if with_postals else None
                    admin2_aliases = admin2_postals['county_name'].unique() if with_postals else [a2]
                    ca2 = Admin2(admin2_aliases[0], parent=ca1,
                                 cities=admin2_cities, postals=admin2_postals, geonames=admin2_geonames)
                    ca1.subdivisions[a2] = ca1.admin2[a2] = country.admin2[a2] = ca2
                    by_admin3 = admin2_cities.groupby('admin3code')
                    for a3, admin3_cities in by_admin3:
                        admin3_geonames = admin2_geonames[admin2_geonames['admin3code'] == a3] if with_geonames else None
                        admin3_postals = admin2_postals[admin2_postals['community_code'] == a3] if with_postals else None
                        admin3_aliases = admin3_postals['community_name'].unique() if with_postals else [a3]
                        ca3 = Admin3(admin3_aliases[0], parent=ca2,
                                     cities=admin3_cities, postals=admin3_postals, geonames=admin3_geonames)
                        ca2.subdivisions[a3] = ca2.admin3[a3] = ca1.admin3[a3] = country.admin3[a3] = ca3
        return country


world = World()
