#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `ngogeo` package."""
from click.testing import CliRunner

from ngogeo.cli import cli

# PROTECTED REGION ID(ngogeo.tests.test_ngogeo) ENABLED START
from ngogeo import territories


def test_ip_utils_country():
    from ngogeo.ip_utils import IpUtilsCountry
    country = IpUtilsCountry().country('92.184.108.14')
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
    world = territories.get_world()
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
    world = territories.get_world()
    france = world.load_country('FR', with_geonames=False)
    g = gpd.GeoDataFrame(geometry=[france.infos.geometry], crs="EPSG:4326")
    g.plot()
    plt.show()
    g = gpd.GeoDataFrame(geometry=[world.countries_gdf.loc['RU'].geometry.convex_hull], crs="EPSG:4326")
    g = gpd.GeoDataFrame(geometry=[world.countries_gdf.loc['RU'].geometry], crs="EPSG:4326")
    g.plot()
    plt.show()


def test_boundaries():
    world = territories.get_world()
    # ip tests
    assert world.locate_ip_country('92.184.108.14') is None
    world.with_ip_city = True
    ip_country = world.locate_ip_country('92.184.108.14')
    ip_country.with_postals = True
    ip_country.with_geonames = True
    ip_city = world.locate_ip_city('92.184.108.14')
    postal = ip_city.postal
    from ngogeo.territories import Postal
    p = Postal(postal=postal, parent=ip_country)
    p.admin3
    ip_city_admin = ip_city.admin3
    ip_city.timezone_details
    # before loading france, locate only according to world shapes
    point = world.make_point_to_crs((4.04255, 46.04378), point_crs='EPSG:4326')
    loc = ip_city.location
    d = ip_city.distance_km(point)
    assert world.locate_country(point).country_code == 'FR'
    france = world.get_country('FR')
    france.with_postals = True
    france.bound_from_cities = True
    france.with_geonames = True
    #gg0 = len(france.geonames_gdf)
    #gg1 = len(france.admin1[0].geonames_gdf.subset)
    #gg2 = len(france.admin1[0].admin2[0].geonames_gdf.subset)
    #gg3 = len(france.admin1[0].admin2[0].admin3[0].geonames_gdf.subset)
    #cg0 = len(france.cities_gdf.subset)
    #cg1 = len(france.admin1[0].cities_gdf.subset)
    #cg2 = len(france.admin1[0].admin2[0].cities_gdf.subset)
    #cg3 = len(france.admin1[0].admin2[0].admin3[0].cities_gdf.subset)
    #admin1 = france.admin1
    admin2 = france.admin2
    #admin3 = france.admin3
    #a1n = admin1[0].name
    #a2n = admin2[0].name
    #a3n = admin3[0].name
    # check if point located in france is in europe and not in africa
    assert world.continents.get(continent_code='EU').contains(point)
    assert world.continents.get(continent_code='AF').contains(point) is not True
    # load country
    #france = world.load_country('FR', with_geonames=False)
    # project point in country crs
    point = world.make_point_to_crs(point, point_crs='EPSG:4326')
    assert france.contains(point)
    # find administrative zone
    loc = france.locate(point)
    # check that point is found in Loire department and not in Haute Savoie
    # (boundaries of subdivisions defined by city points of department)
    h_savoie = france.admin2.get(admin_code='74')
    assert not h_savoie.contains(point)
    loire = france.admin2.get(admin_code='42')
    assert loire.contains(point)
    assert loc.parent == loire
    # search for cities and postal codes 3km around point in administrative zone
    point_cities = loc.search_cities_around(point, 3000)
    point_postals = loc.search_postals_around(point, 3000)
    assert point_cities.name.iloc[0] == 'Riorges'
    assert point_postals.place_name.iloc[0] == 'Riorges'
    res = loc.search_nodes_around(amenity='drinking_water')
    assert len(res)
    es = ip_city.search_nodes_around(amenity='drinking_water')

    # find and load spain
    spain = world.find_by_name('spain')
    spain.with_postals = True
    spain.postals_gdf
    assert len(spain.postals_gdf)


def test_perf():
    world = territories.get_world()
    print('======= start loading =======')
    spain = world.find_by_name('spain')
    portugal = world.find_by_name('portugal')
    germany = world.find_by_name('germany')
    print('======= end loading =======')
    assert germany


if __name__ == '__main__':
    test_ip_utils_country()
    test_ip_utils_city()
    # to run test file standalone
    test_boundaries()
    #test_perf()
    #test_plot()
    #test_ngogeo()
    #test_geoplot()

# PROTECTED REGION END
