# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import pytz
from collections import namedtuple, OrderedDict
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, MultiPoint

# country info and subdivisions
import pycountry
import country_converter as coco

from ngoschema.protocols import with_metaclass, SchemaMetaclass
from ngogeo import settings as geo_settings


from .point_search import _make_point_to_crs, _search_elements, _search_name, _search_radius
from .geonames.loaders import load_geonames_gdf, load_countries, load_cities, load_timezones
from .postals import load_postals_gdf
from .datasets import DataframeSubset, GeoDataframeSubset

WSG84_CRS = EPSG4326_CRS = geo_settings.WSG84_CRS
DEFAULT_CRS = geo_settings.DEFAULT_CRS
DEFAULT_RADIUS_SEARCH = geo_settings.DEFAULT_RADIUS_SEARCH
WORLD_CITIES_FILE = geo_settings.WORLD_CITIES_FILE
WORLD_WITH_SHAPE = geo_settings.WORLD_WITH_SHAPE
WORLD_WITH_CITIES = geo_settings.WORLD_WITH_CITIES
COUNTRY_WITH_POSTALS = geo_settings.COUNTRY_WITH_POSTALS
COUNTRY_WITH_GEONAMES = geo_settings.COUNTRY_WITH_GEONAMES


class SearchBox(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/SearchBox"

    def search_around(self, element=None, **kwargs):
        return _search_elements(self.bbox, element=element, crs=self.crs, **kwargs)

    def search_nodes_around(self, **kwargs):
        return self.search_around(element='node', **kwargs)

    def search_ways_around(self, **kwargs):
        return self.search_around(element='ways', **kwargs)

    def search_areas_around(self, **kwargs):
        return self.search_around(element='areas', **kwargs)

    def search_relations_around(self, **kwargs):
        return self.search_around(element='relations', **kwargs)


class Territory(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/Territory"
    _lazyLoading = True

    def __init__(self, *args, crs=None, **opts):
        crs = crs or geo_settings.DEFAULT_CRS
        super().__init__(*args, crs=crs, **opts)

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self.admin_code}] {self.name}>'

    def __str__(self):
        return f'<{self.__class__.__name__} [{self.admin_code}] {self.name}>'

    def get_bnd(self):
        return self.cs.convex_hull[0] if self.cs is not None else None

    def get_box(self):
        return self.bnd.minimum_rotated_rectangle.buffer(DEFAULT_RADIUS_SEARCH, resolution=4) if self.bnd else None

    def get_bbox(self):
        if self.cs is not None:
            bbox = self.cs.envelope.to_crs(geo_settings.WSG84_CRS).bounds
            return f'{bbox.miny[0]:.3f}, {bbox.minx[0]:.3f}, {bbox.maxy[0]:.3f}, {bbox.maxx[0]:.3f}'

    def make_point_to_crs(self, point, point_crs=None, dest_crs=None):
        if hasattr(point, '_crs'):
            point_crs = point_crs or point._crs
        point_crs = point_crs or WSG84_CRS
        dest_crs = dest_crs or self.crs
        return _make_point_to_crs(point, point_crs=point_crs, dest_crs=dest_crs)

    def contains(self, point, point_crs=None, only_box=False):
        point = self.make_point_to_crs(point, point_crs, dest_crs=self.crs)
        if self.box.intersects(point):
            return True if only_box else self.bnd.intersects(point)
        return False

    def locate(self, point, point_crs=None):
        point = self.make_point_to_crs(point, point_crs, dest_crs=self.crs)
        if self.box.intersects(point):
            if 'subdivisions' in self._propertiesAllowed:
                for s in self.subdivisions:
                    if s.box is not None and s.box.intersects(point):
                        l = s.locate(point)
                        if l:
                            return l
            return self

    def _create_parent_df_subset(self, name, subkeys, ids, cls=None, **opts):
        cls = cls or DataframeSubset
        if self.parent:
            parent_df = self.parent[name]
            df = parent_df.subset if isinstance(parent_df, DataframeSubset) else parent_df
            if df is not None:
                return cls(dataframe=df, subkeys=subkeys, ids=ids, **opts)

    def _create_parent_gdf_subset(self, name, subkeys, ids):
        return self._create_parent_df_subset(name, subkeys, ids, cls=GeoDataframeSubset, crs=self.crs)


class CitiesTerritory(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/CitiesTerritory"

    def set_bound_from_cities(self, value):
        if self.subdivisions:
            for s in self.subdivisions:
                s.bound_from_cities = value

    def get_cities_ids(self):
        return [self.admin_code]

    def get_cs(self):
        cities_gdf = self.cities_gdf
        cities_gdf = cities_gdf.subset if isinstance(cities_gdf, GeoDataframeSubset) else cities_gdf
        if self.bound_from_cities and self.cities_gdf is not None:
            return gpd.GeoSeries([MultiPoint(cities_gdf.geometry.to_list())], crs=self.crs)

    def get_cities_gdf(self):
        return self._create_parent_gdf_subset('cities_gdf', subkeys=self.cities_subkeys, ids=self.cities_ids)

    def search_cities_name(self, name, regex=False, **kwargs):
        cities_gdf = self.cities_gdf
        cities_gdf = cities_gdf.subset if isinstance(cities_gdf, GeoDataframeSubset) else cities_gdf
        return _search_name(cities_gdf, name, regex=regex, **kwargs)

    def search_cities_around(self, point, radius=DEFAULT_RADIUS_SEARCH, point_crs=None, regex=False, **kwargs):
        cities_gdf = self.cities_gdf
        cities_gdf = cities_gdf.subset if isinstance(cities_gdf, GeoDataframeSubset) else cities_gdf
        return _search_radius(cities_gdf, point, radius=radius, point_crs=point_crs, regex=regex, **kwargs)


class PostalsTerritory(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/PostalsTerritory"

    def get_postals_gdf(self):
        return self._create_parent_gdf_subset('postals_gdf', subkeys=self.postals_subkeys, ids=self.postals_ids)

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
        postals_gdf = self.postals_gdf
        postals_gdf = postals_gdf.subset if isinstance(postals_gdf, GeoDataframeSubset) else postals_gdf

        codes["postal_code"] = codes.postal_code.str.upper()
        response = pd.merge(
            codes, postals_gdf, on="postal_code", how="left"
        )
        if unique and single_entry:
            response = response.iloc[0]
            return response
        else:
            return response

    def search_postals_around(self, point, radius=DEFAULT_RADIUS_SEARCH, point_crs=None, regex=False, **kwargs):
        postals_gdf = self.postals_gdf
        postals_gdf = postals_gdf.subset if isinstance(postals_gdf, GeoDataframeSubset) else postals_gdf
        if postals_gdf is not None:
            gdf = _search_radius(postals_gdf, point, radius=radius, point_crs=point_crs, regex=regex, **kwargs)
            return gdf


class GeonamesTerritory(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/GeonamesTerritory"

    def get_geonames_ids(self):
        return [self.admin_code]

    def get_geonames_gdf(self):
        return self._create_parent_gdf_subset('geonames_gdf', subkeys=self.geonames_subkeys, ids=self.geonames_ids)

    def search_geonames_around(self, point, radius=DEFAULT_RADIUS_SEARCH, point_crs=None, regex=False, **kwargs):
        geonames_gdf = self.geonames_gdf
        geonames_gdf = geonames_gdf.subset if isinstance(geonames_gdf, GeoDataframeSubset) else geonames_gdf
        if geonames_gdf is not None:
            gdf = _search_radius(geonames_gdf, point, radius=radius, point_crs=point_crs, regex=regex, **kwargs)
            return gdf

    def search_geonames_name(self, name, regex=False, **kwargs):
        geonames_gdf = self.geonames_gdf
        geonames_gdf = geonames_gdf.subset if isinstance(geonames_gdf, GeoDataframeSubset) else geonames_gdf
        if geonames_gdf is not None:
            gdf = _search_name(geonames_gdf, name, regex=regex, **kwargs)
            return gdf


class Admin3(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/Admin3"
    cities_subkeys = 'admin3code'
    postals_subkeys = 'community_code'
    geonames_subkeys = 'admin3code'

    def get_postals_gdf(self):
        a2_postals = self.parent.postals_gdf
        if a2_postals is not None:
            admin_code = self.admin_code
            try:
                a3_community_code = f'{float(admin_code):.1f}'
            except Exception as er:
                a3_community_code = admin_code
            a3_postals = a2_postals[a2_postals['community_code'].isin([a3_community_code, admin_code])]
            if not len(a3_postals):
                a3_cities = self.cities_gdf.subset
                a3_cities_postals = a3_cities.merge(a2_postals, left_on='name', right_on='place_name', copy=True)
                a3s = a3_cities_postals.admin3code.value_counts()
                if len(a3s):
                    a3_community_code = a3s.index[0]
                    a3_postals = a2_postals[a2_postals['community_code'] == a3_community_code]
        return a3_postals

    def get_name(self):
        admin3_postals = self.postals_gdf
        if admin3_postals is not None:
            admin3_aliases = admin3_postals['community_name'].unique()
            if admin3_aliases:
                return admin3_aliases[0]
        return self.admin_code

    def locate_cities_around(self, point, radius=DEFAULT_RADIUS_SEARCH, point_crs=None, regex=False, **kwargs):
        cities = self.search_cities_around(point, radius=radius, point_crs=point_crs, regex=regex, **kwargs)
        cities_distance = cities.pop('distance')
        ret = [(cities_distance[i], City(geoname=row, parent=self, crs=self.crs)) for i, row in cities.iterrows()]
        return ret

    def locate_city(self, name=None, postal_code=None):
        postal = self.search_postal_code(postal_code, unique=True) if postal_code else None
        geo_kwargs = OrderedDict()
        if len(postal):
            if name is None:
                name = postal.place_name
                # only set admin3, others will filter down to the same
            geo_kwargs['admin3code'] = postal.community_code
        if name:
            cities = self.search_cities_name(name, featureclass='P', **geo_kwargs)
            if not len(cities):
                cities = self.search_geonames_name(name, featureclass='P', **geo_kwargs)
            if len(cities):
                cities = [City(geoname=row, crs=self.crs, parent=self) for i, row in cities.iterrows()]
                return cities[0] if len(cities) == 1 else cities


class Admin2(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/Admin2"
    cities_subkeys = 'admin2code'
    postals_subkeys = 'county_code'
    geonames_subkeys = 'admin2code'

    def get_postals_gdf(self):
        a1_postals = self.parent.postals_gdf
        if a1_postals is not None:
            admin_code = self.admin_code
            try:
                a2_county_code = f'{int(admin_code)}'
            except Exception as er:
                a2_county_code = admin_code
            a2_postals = a1_postals[a1_postals['county_code'].isin([a2_county_code, admin_code])]
            if not len(a2_postals):
                a2_cities = self.cities_gdf.subset
                a2_cities_postals = a2_cities.merge(a1_postals, left_on='name', right_on='place_name', copy=True)
                a2s = a2_cities_postals.admin2code.value_counts()
                if len(a2s):
                    a2_county_code = a2s.index[0]
                    a2_postals = a1_postals[a1_postals['county_code'] == a2_county_code]
            return a2_postals

    def get_name(self):
        a2_postals = self.postals_gdf
        if a2_postals is not None:
            admin2_aliases = a2_postals['county_name'].unique()
            if len(admin2_aliases):
                return admin2_aliases[0]
        return self.admin_code

    def get_admin3(self):
        if self.cities_gdf:
            cities_subset = self.cities_gdf.subset
            subkey = Admin3.cities_subkeys.ptype.default()[0]
            admin3_codes = cities_subset[subkey].unique()
            return [Admin3(admin3_code=c, admin2_code=self.admin2_code, admin1_code=self.admin1_code, parent=self)
                    for c in admin3_codes]


class Admin1(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/Admin1"
    cities_subkeys = 'admin1code'
    postals_subkeys = 'state_code'
    geonames_subkeys = 'admin1code'

    def get_postals_gdf(self):
        cy_postals = self.country.postals_gdf
        if cy_postals is not None:
            a1_cities = self.cities_gdf.subset
            a1_cities_postals = a1_cities.merge(cy_postals, left_on='name', right_on='place_name', copy=True)
            a1_postal = a1_cities_postals.state_code.value_counts().index[0]
            a1_postals = cy_postals[cy_postals['state_code'] == a1_postal]
            return a1_postals

    def get_name(self):
        a1_postals = self.postals_gdf
        if a1_postals is not None:
            a1_aliases = a1_postals['state_name'].unique()
            return a1_aliases[0]
        return self.admin_code

    def get_admin2(self):
        if self.cities_gdf:
            cities_subset = self.cities_gdf.subset
            subkey = Admin2.cities_subkeys.ptype.default()[0]
            admin2_codes = cities_subset[subkey].unique()
            return [Admin2(admin2_code=c, admin1_code=self.admin1_code, parent=self)
                    for c in admin2_codes]

    def get_admin3(self):
        ret = []
        for a2 in self.admin2:
            ret += list(a2.admin3)
        return ret


class Country(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/Country"
    cities_subkeys = 'countrycode'
    geonames_subkeys = 'countrycode'

    def __init__(self, *args, infos=None, **kwargs):
        if infos is not None:
            kwargs.update(infos.dropna().to_dict())
            kwargs['infos'] = infos
        super().__init__(*args, bound_from_cities=False, **kwargs)

    def get_name(self):
        return self.admin_code if self.infos is None else self.infos['Country']

    def get_admin1(self):
        if self.cities_gdf:
            cities_subset = self.cities_gdf.subset
            subkey = Admin1.cities_subkeys.ptype.default()[0]
            admin1_codes = cities_subset[subkey].unique()
            return [Admin1(admin1_code=c, parent=self)
                    for c in admin1_codes]

    def get_admin2(self):
        ret = []
        for a1 in self.admin1:
            ret += list(a1.admin2)
        return ret

    def get_countries_ids(self):
        return [self.continent_code]

    def get_capital(self):
        cities = self.cities_gdf
        if cities is not None:
            for idx, row in cities.iterrows():
                if row['featurecode'] == 'PPLC':
                    return row

    def get_cs(self):
        infos = self.infos
        if infos is not None and infos.geometry is not None:
            # cs is used for bnd and box of countries which are in WSG84_CRS
            return gpd.GeoSeries([infos.geometry], crs=geo_settings.WSG84_CRS)

    def get_bnd(self):
        cs = self.cs
        if cs is not None:
            ch = cs.explode().geometry.convex_hull
            return ch.unary_union

    def get_languages(self):
        # hack: world.languages return an external db which doesn t behave as a dict
        # conversion possible through protected member fields
        world = get_world()
        languages = [world.languages.get(alpha_2=c.split('-')[0])
                     for c in self.infos['Languages'].split(',')]
        return [l._fields for l in languages if l]

    def contains(self, point, point_crs=None):
        # box and boundaries come from countries and are in EPSG:4326 (=WSG84_CRS)
        point = self.make_point_to_crs(point, point_crs, dest_crs=WSG84_CRS)
        if self.box is not None:
            if self.box.contains(point):
                return True
        return False

    def locate(self, point, point_crs=None):
        # box and boundaries come from countries and are in EPSG:4326 (=WSG84_CRS)
        p = self.make_point_to_crs(point, point_crs, dest_crs=WSG84_CRS)
        if self.box.intersects(p):
            for a1 in self.admin1:
                l = a1.locate(point, point_crs)
                if l is not None:
                    return l
            return self

    def get_currency(self):
        # hack: world.currencies return an external db which doesn t behave as a dict
        # conversion possible through protected member fields
        return get_world().currencies.get(alpha_3=self.infos['CurrencyCode'])._fields

    def get_currency_fmt(self):
        from currencies import Currency
        return Currency(self.infos['CurrencyCode'])

    def get_timezone_details(self):
        tzs = get_world().timezones
        return pytz.timezone(tzs['TimeZoneId'][self.country_code])

    def get_geonames_gdf(self):
        if self.with_geonames:
            return load_geonames_gdf(self.country_code, crs=self.crs)

    def get_postals_gdf(self):
        if self.with_postals:
            return load_postals_gdf(self.country_code, crs=self.crs)


class Continent(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/Continent"

    def get_cities_gdf(self):
        countries_gdf = self.countries_gdfs.subset
        world_cities = self.world.cities_gdf
        country_codes = countries_gdf.index.to_list()
        return world_cities[world_cities['countrycode'].isin(country_codes)]

    def get_countries_gdfs(self):
        return self._create_parent_gdf_subset('countries_gdf', subkeys='Continent', ids=[self.continent_code])

    def get_countries(self):
        countries_gdf = self.countries_gdfs.subset
        return [Country(country_code=ucc, infos=countries_gdf.loc[ucc], parent=self)
                for ucc in countries_gdf.index]

    def get_bnd(self):
        countries_gdf = self.countries_gdfs.subset
        if hasattr(countries_gdf, 'geometry') and countries_gdf.geometry.any():
            return gpd.GeoSeries(countries_gdf['bnd'])

    def get_box(self):
        return self.bnd.unary_union.envelope if self.bnd is not None else None

    def contains(self, point, point_crs=None):
        if self.bnd is not None:
            # box and boundaries come from countries and are in EPSG:4326 (=WSG84_CRS)
            p = self.make_point_to_crs(point, point_crs, dest_crs=WSG84_CRS)
            return self.bnd.contains(p).any()
        for country in self.countries:
            if country.contains(point, point_crs):
                return True

    def locate(self, point, point_crs=None):
        for country in self.countries:
            if country.contains(point, point_crs):
                return country.locate(point, point_crs)

    def locate_country(self, point, point_crs=None):
        if hasattr(self, 'bnd'):
            p = self.make_point_to_crs(point, point_crs, dest_crs=WSG84_CRS)
            for cc, bnd in self.bnd.iteritems():
                if bnd.contains(p):
                    return cc
        for country in self.countries:
            if country.contains(point, point_crs):
                return country.admin_code


class World(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/World"

    def __init__(self, *args,
                 cities_file=WORLD_CITIES_FILE,
                 with_shapes=WORLD_WITH_SHAPE,
                 with_cities=WORLD_WITH_CITIES,
                 crs=geo_settings.WSG84_CRS,
                 **kwargs):
        super().__init__(*args, name='World', cities_file=cities_file,
                         with_cities=with_cities, with_shapes=with_shapes, crs=crs, **kwargs)

    def get_countries_gdf(self):
        countries_gdf = load_countries(with_shapes=self.with_shapes)
        if self.with_shapes:
            countries_bnd = countries_gdf.geometry.explode().convex_hull
            countries_gdf['bnd'] = gpd.GeoDataFrame(geometry=countries_bnd).dissolve('ISO')
        return countries_gdf

    def get_cities_gdf(self):
        if self.with_cities:
            return load_cities(self.cities_file, crs=self.crs)

    def get_continents(self):
        continent_codes = self.countries_gdf['Continent'].dropna().unique()
        return [Continent(continent_code=cc, parent=self, crs=self.crs)
                for cc in continent_codes]

    def get_countries(self):
        continents_countries = [list(c.countries) for c in self.continents]
        return sum(continents_countries)

    def get_timezones(self):
        return load_timezones()

    def get_currencies(self):
        from pycountry import currencies
        return currencies

    def get_ip_country(self):
        if self.with_ip_country:
            from .ip_utils import IpUtilsCountry
            return IpUtilsCountry()

    def get_ip_city(self):
        if self.with_ip_city:
            from .ip_utils import IpUtilsCity
            return IpUtilsCity()

    def locate_ip_country(self, ip):
        res = None
        if self.ip_country is not None:
            res = self.ip_country.country(ip)
        elif self.ip_city is not None:
            res = self.ip_city.city(ip)
        if res is not None:
            return self.continents.get(continent_code=res.continent.code).countries.get(country_code=res.country.iso_code)

    def locate_ip_city(self, ip):
        if self.ip_city:
            res = self.ip_city.city(ip)
            if res:
                country = cur = self.continents.get(continent_code=res.continent.code).countries.get(country_code=res.country.iso_code)
                for s in res.subdivisions:
                    if cur.subdivisions:
                        cur = cur.subdivisions.get(name=s.name)
                return cur.locate_city(name=res.city.name,
                                       postal_code=res.postal.code)

    def get_languages(self):
        return pycountry.languages # pycountry languages better than iso geonames

    def get_country(self, country_code):
        for continent in self.continents:
            c = continent.countries.get(country_code=country_code)
            if c:
                return c

    def locate(self, point, point_crs=None):
        for continent in self.continents:
            if continent.contains(point, point_crs):
                return continent.locate(point, point_crs)

    def locate_country(self, point, point_crs=None):
        for continent in self.continents:
            if continent.contains(point, point_crs):
                return continent.locate_country(point, point_crs)

    def find_by_name(self, name, exclude_prefix=None):
        country_code = coco.convert(names=name, to='ISO2', not_found=None, enforce_list=False, exclude_prefix=exclude_prefix)
        return self.get_country(country_code)


class Geoname(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/Geoname"
    _lazyLoading = True

    def __init__(self, *args, geoname=None, **kwargs):
        if geoname is not None:
            kwargs.update(geoname.dropna().to_dict())
            kwargs['geoname'] = geoname
        super().__init__(*args, **kwargs)

    def set_geoname(self, geoname):
        for k, v in geoname.dropna().to_dict().items():
            self._set_dataValidated(k, v)

    def get_country(self):
        cur = self.parent
        while cur is not None:
            if isinstance(cur, Country):
                return cur
            cur = cur.parent

    def get_admin1(self):
        return self.country.admin1.get(admin_code=self.admin1code)

    def get_admin2(self):
        return self.admin1.admin2.get(admin_code=self.admin2code)

    def get_admin3(self):
        return self.admin2.admin3.get(admin_code=self.admin3code)

    def get_featureclass_description(self):
        from .geonames.features import FEATURE_CLASS_TITLES
        fcs = self.featureclass
        return FEATURE_CLASS_TITLES[fcs] if fcs else None

    def get_featurecode_description(self):
        from .geonames.features import FEATURE_CODE_DESCRIPTIONS
        fcs = self.featureclass
        fc = self.featurecode
        return FEATURE_CODE_DESCRIPTIONS[f'{fcs}.{fc}'] if fcs and fc else None

    def get_featurecode_title(self):
        from .geonames.features import FEATURE_CODE_TITLES
        fcs = self.featureclass
        fc = self.featurecode
        return FEATURE_CODE_TITLES.get(f'{fcs}.{fc}') if fcs and fc else None

    def locate_cities_around(self, admin_level=3, **kwargs):
        admin = self[f'admin{admin_level}']
        return admin.locate_cities_around(self.location, point_crs=self.crs, **kwargs)

    def search_cities_around(self, admin_level=3, **kwargs):
        admin = self[f'admin{admin_level}']
        return admin.search_cities_around(self.location, point_crs=self.crs, **kwargs)

    def search_postals_around(self, admin_level=3, **kwargs):
        admin = self[f'admin{admin_level}']
        return admin.search_postals_around(self.location, point_crs=self.crs, **kwargs)

    def search_geonames_around(self, admin_level=3, **kwargs):
        admin = self[f'admin{admin_level}']
        return admin.search_geonames_around(self.location, point_crs=self.crs, **kwargs)

    def get_bbox(self):
        buff = self.gdf.buffer(self.radius or DEFAULT_RADIUS_SEARCH).to_crs(geo_settings.WSG84_CRS)
        bbox = buff.bounds.iloc[0]
        return f'{bbox.miny:.3f}, {bbox.minx:.3f}, {bbox.maxy:.3f}, {bbox.maxx:.3f}'

    def get_timezone_details(self):
        tz = self.timezone
        return pytz.timezone(tz) if tz else None

    def get_location(self):
        return _make_point_to_crs((self.longitude, self.latitude), point_crs=WSG84_CRS, dest_crs=self.crs)

    def get_gdf(self):
        gdf = gpd.GeoDataFrame([self.geoname], geometry=[self.location], crs=self.crs)
        return gdf

    def distance_km(self, other):
        from geopandas import GeoDataFrame
        unique = True
        if isinstance(other, Geoname):
            other_loc = other.location
            other_loc = _make_point_to_crs(other_loc, point_crs=other.crs, dest_crs=self.crs)
        elif isinstance(other, Point):
            other_loc = other
            other_loc = _make_point_to_crs(other_loc, point_crs=other._crs or WSG84_CRS, dest_crs=self.crs)
        elif isinstance(other, GeoDataFrame):
            unique = False
            if not other.crs.is_exact_same(self.crs):
                other = other.to_crs(self.crs)
            other_loc = other.geometry
        res = list(self.gdf.geometry.distance(other_loc) / 1000.)
        return res[0] if unique else res


class City(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/territories/$defs/City"

    def get_postalInfo(self):
        postals = self.admin3.postals_gdf
        postals = postals[postals['place_name'] == self.name]
        if len(postals):
            postalInfo = postals.iloc[0]
            for k, v in postalInfo.dropna().to_dict().items():
                self._set_dataValidated(k, v)
            return postalInfo

    def get_gdf(self):
        gdf = gpd.GeoDataFrame([self.geoname], geometry=[self.location], crs=self.crs)
        return gdf


_world_dbs = {}
_WorldCfg = namedtuple("WorldConfig", "cities_file with_shapes with_cities")


def get_world(cities_file=WORLD_CITIES_FILE, with_shapes=WORLD_WITH_SHAPE, with_cities=WORLD_WITH_CITIES):
    global _world_dbs
    cfg = _WorldCfg(cities_file, with_shapes, with_cities)
    if cfg not in _world_dbs:
        _world_dbs[cfg] = World(**cfg._asdict())
    return _world_dbs[cfg]
