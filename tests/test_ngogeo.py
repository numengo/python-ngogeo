#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `ngogeo` package."""
from click.testing import CliRunner

from ngogeo.cli import cli

# PROTECTED REGION ID(ngogeo.tests.test_ngogeo) ENABLED START
from ngogeo import ngogeo


def test_ip_utils_country():
    from ngogeo.ip_utils import ip_country
    country = ip_country.country('92.184.108.14')
    assert country


def test_ip_utils_city():
    from ngogeo.ip_utils import IpUtilsCity
    ip_city = IpUtilsCity()
    city = ip_city.city('92.184.108.14')
    assert city


def test_geoplot():
    import geoplot
    import geoplot.crs as gcrs
    import geopandas as gpd
    import matplotlib.pyplot as plt
    data = gpd.read_file(
        "https://raw.githubusercontent.com/holtzy/The-Python-Graph-Gallery/master/static/data/france.geojson")
    p = geoplot.polyplot(data, projection=gcrs.AlbersEqualArea(), edgecolor='darkgrey', facecolor='lightgrey', linewidth=.3,
                     figsize=(12, 8))
    plt.show()
    assert p


def test_ngogeo():
    import time
    import geoplot
    import geoplot.crs as gcrs
    import geopandas as gpd
    import matplotlib.pyplot as plt
    import pyproj
    import json
    from io import StringIO
    tw0 = time.time()
    world = ngogeo.World()
    tw1 = time.time()
    dtw = tw1 - tw0
    print('load World', dtw)
    tfr0 = time.time()
    france = world.load_country('FR', with_geonames=False)
    tfr1 = time.time()
    dtfr = tfr1 - tfr0
    print('load France', dtfr)
    loire = france.admin2['42']
    hsavoie = france.admin2['74']
    g = gpd.GeoDataFrame(geometry=[france.infos.geometry], crs=france.crs)
    g.plot()
    plt.show()
    #p = geoplot.polyplot(g, projection=gcrs.AlbersEqualArea(), edgecolor='darkgrey', facecolor='lightgrey', linewidth=.3,
    #                 figsize=(12, 8))
    #plt.show()

    ts0 = time.time()
    r1 = france.search_city_name('Riorges')
    ts1 = time.time()
    r2 = france.search_postal_code('42153')
    ts2 = time.time()
    r3 = loire.search_city_name('Riorges')
    ts3 = time.time()
    dts01 = ts1 - ts0
    dts12 = ts2 - ts1
    dts23 = ts3 - ts2
    print('search riorges in france', dts01)
    print('search 42153 in france', dts12)
    print('search riorges in loire', dts23)
    tr0 = time.time()
    cr = loire.search_cities_radius(r3.geometry, 10000, point_crs=france.crs)
    tr1 = time.time()
    dtr = tr1 - tr0
    print('search cities around in roanne', dtr)
    print(cr)


def test_plot():
    import geopandas as gpd
    import matplotlib.pyplot as plt
    world = ngogeo.world
    france = world.load_country('FR', with_geonames=False)
    g = gpd.GeoDataFrame(geometry=[france.infos.geometry], crs="EPSG:4326")
    g.plot()
    plt.show()
    g = gpd.GeoDataFrame(geometry=[world.countries_gdf.loc['RU'].geometry.convex_hull], crs="EPSG:4326")
    g = gpd.GeoDataFrame(geometry=[world.countries_gdf.loc['RU'].geometry], crs="EPSG:4326")
    g.plot()
    plt.show()


def test_boundaries():
    world = ngogeo.world
    # before loading france, locate only according to world shapes
    point = world.make_point_to_crs((4.04255, 46.04378), point_crs='EPSG:4326')
    assert world.locate(point) == 'FR'
    # check if point located in france is in europe and not in africa
    assert world.continents['EU'].contains(point)
    assert world.continents['AF'].contains(point) is not True
    # load country
    france = world.load_country('FR', with_geonames=False)
    # project point in country crs
    point = world.make_point_to_crs(point, point_crs='EPSG:4326', dest_crs=france.crs)
    assert france.contains(point)
    # find administrative zone
    loc = france.locate(point)
    # check that point is found in Loire department and not in Haute Savoie
    # (boundaries of subdivisions defined by city points of department)
    h_savoie = france.admin2['74']
    assert not h_savoie.contains(point)
    loire = france.admin2['42']
    assert loire.contains(point)
    assert loc.parent == loire
    # search for cities and postal codes 3km around point in administrative zone
    point_cities = loc.search_cities_radius(point, 3000)
    point_postals = loc.search_postals_radius(point, 3000)
    assert point_cities.name.iloc[0] == 'Riorges'
    assert point_postals.place_name.iloc[0] == 'Riorges'


if __name__ == '__main__':
    # to run test file standalone
    test_boundaries()
    #test_plot()
    #test_ngogeo()
    #test_geoplot()
    #test_ip_utils_country()
    #test_ip_utils_city()

# PROTECTED REGION END
