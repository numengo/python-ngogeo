# -*- coding: utf-8 -*-

"""Main module NgoGeo """
from __future__ import absolute_import
from __future__ import unicode_literals

import requests
import zipfile
import pandas as pd
import geopandas as gpd
import shapely
from shapely.geometry import Point

from ngoschema.loaders import static_module_loader
from ngogeo import settings as geo_settings

# get geonames local folder
geonames_folder = static_module_loader.subfolder('ngogeo').joinpath(geo_settings.GEONAMES_STATIC_FOLDER)

# https://stackoverflow.com/a/20627316
pd.options.mode.chained_assignment = None  # default='warn'

# Adapted from https://stackoverflow.com/a/34499197
DATA_FIELDS = {
    'geonameid': int,
    'name': str,
    'asciiname': str,
    'alternatenames': str,
    'latitude': float,
    'longitude': float,
    'featureclass': str,
    'featurecode': str,
    'countrycode': str,
    'countrycode2': str,
    'admin1code': str,
    'admin2code': str,
    'admin3code': str,
    'admin4code': str,
    'population': float,
    'elevation': float,
    'dem': float,  # dem (digital elevation model)
    'timezone': str,
    'modificationdate': str
}


def load_geonames_gdf(filename, crs=None):
    gdir = geonames_folder.joinpath(filename)
    gct = gdir.joinpath(filename + '.txt')
    if not gct.exists():
        url = geo_settings.GEONAMES_DOWNLOAD_URL + filename + '.zip'
        r = requests.get(url)
        gcz = geonames_folder.joinpath(filename + '.zip')
        with gcz.open('wb') as f:
            # giving a name and saving it in any required format
            # opening the file in write mode
            f.write(r.content)
        # extract archive
        with zipfile.ZipFile(gcz, 'r') as zo:
            zo.extractall(str(geonames_folder.joinpath(filename)))
    df = pd.read_csv(
        gct, sep="\t", dtype=DATA_FIELDS, names=tuple(DATA_FIELDS), index_col='geonameid'
    )
    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(lon, lat) for lon, lat in zip(df["longitude"], df["latitude"])], # check the ordering of lon/lat
        crs="EPSG:4326"
    )
    return gdf if not crs or gdf.crs.is_exact_same(crs) else gdf.to_crs(crs)


def load_currencies():
    from pycountry import currencies
    return currencies


def load_languages():
    lg = geonames_folder.joinpath('iso-languagecodes.txt')
    assert lg.exists()
    with lg.open() as lgf:
        df = pd.read_csv(lgf, sep="\t")
    return df


def load_timezones():
    import pytz
    tz = geonames_folder.joinpath('timeZones.txt')
    with tz.open() as tzf:
        df = pd.read_csv(tzf, sep="\t")
    df.set_index('CountryCode', inplace=True)
    df['tz'] = df['TimeZoneId'].apply(pytz.timezone)
    return df


def load_cities(filename='cities5000', crs=None):
    assert filename in ['cities500', 'cities1000', 'cities5000', 'cities15000']
    return load_geonames_gdf(filename, crs)


def load_countries(with_shapes=True):
    ci = geonames_folder.joinpath('countryInfo.txt')
    assert ci.exists()
    with ci.open() as cif:
        names = ['ISO', 'ISO3', 'ISO-Numeric', 'fips', 'Country', 'Capital', 'Area(in sq km)', 'Population', 'Continent', 'tld', 'CurrencyCode', 'CurrencyName', 'Phone', 'Postal Code Format', 'Postal Code Regex', 'Languages', 'geonameid', 'neighbours', 'EquivalentFipsCode']
        df = df1 = pd.read_csv(cif, sep="\t", skiprows=50, names=names, dtype={'Area(in sq km)': float, 'Population': pd.Int64Dtype(), 'geonameid': pd.Int64Dtype()})
    if with_shapes:
        ss = geonames_folder.joinpath('shapes_simplified_low', 'shapes_simplified_low.json')
        with open(ss) as ssf:
            df2 = gpd.read_file(ssf)
            df2['geoNameId'] = df2['geoNameId'].astype(int)
        df = df2.merge(df1, left_on='geoNameId', right_on='geonameid').dropna(subset=['ISO'])
    df.set_index('ISO', inplace=True)
    return df

