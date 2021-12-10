# -*- coding: utf-8 -*-

"""Main module NgoGeo """
from __future__ import absolute_import
from __future__ import unicode_literals

import urllib.request as request
import requests
import zipfile
import pandas as pd
import geopandas as gpd
import shapely
from shapely.geometry import Point

from ngoschema.loaders import static_module_loader
from ngogeo import settings as geo_settings

postal_folder = static_module_loader.subfolder('ngogeo').joinpath(geo_settings.POSTAL_STATIC_FOLDER)

# https://stackoverflow.com/a/20627316
pd.options.mode.chained_assignment = None  # default='warn'

# Adapted from https://stackoverflow.com/a/34499197
DATA_FIELDS = [
    "country_code",
    "postal_code",
    "place_name",
    "state_name",
    "state_code",
    "county_name",
    "county_code",
    "community_name",
    "community_code",
    "latitude",
    "longitude",
    "accuracy",
]


def load_postals_gdf(filename, unique=True, crs=None):
    gdir = postal_folder.joinpath(filename)
    gct = gdir.joinpath(filename + '.txt')
    gcti = gct.with_name(filename + '-index.txt')
    if not gct.exists():
        url = geo_settings.POSTAL_DOWNLOAD_URL + filename + '.zip'
        r = requests.get(url)
        gcz = postal_folder.joinpath(filename + '.zip')
        with gcz.open('wb') as f:
            # giving a name and saving it in any required format
            # opening the file in write mode
            f.write(r.content)
        # extract archive
        with zipfile.ZipFile(gcz, 'r') as zo:
            zo.extractall(str(gdir))
        # open separated with tabs
        df = pd.read_csv(gct, sep="\t", dtype={"postal_code": str}, names=DATA_FIELDS)
        # save it with standard sep ,
        df.to_csv(gct, index=None)
        # group postal codes
        df_unique_cp_group = df.groupby("postal_code")
        df_unique = df_unique_cp_group[["latitude", "longitude"]].mean()
        valid_keys = set(DATA_FIELDS).difference(
            ["place_name", "lattitude", "longitude", "postal_code"]
        )
        df_unique["place_name"] = df_unique_cp_group["place_name"].apply(
            lambda x: ", ".join([str(el) for el in x])
        )
        for key in valid_keys:
            df_unique[key] = df_unique_cp_group[key].first()
        df_unique = df_unique.reset_index()[DATA_FIELDS]
        df_unique.to_csv(gcti, index=None)

    df = pd.read_csv(gcti if unique else gct, dtype={"postal_code": str, "longitude": float, "latitude": float})
    if unique:
        df = df.set_index('postal_code')
    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(lon,lat) for lon,lat in zip(df["longitude"], df["latitude"])], # check the ordering of lon/lat
        crs="EPSG:4326"
    )
    return gdf.to_crs(crs) if crs else gdf
