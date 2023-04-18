#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, os.path
import geoip2.database
import ipaddress

from ngoschema.loaders import static_module_loader

from ngogeo import settings as geo_settings

geolite2_folder = static_module_loader.subfolder('ngogeo').joinpath(geo_settings.GEOLITE2_STATIC_FOLDER)


class IpUtilsFile:
    _version = geo_settings.GEOLITE2_VERSION
    _db_fn = None

    def __init__(self):
        fn = geolite2_folder.joinpath(f'{self._db_fn}_{self._version}', f'{self._db_fn}.mmdb')
        self._reader = geoip2.database.Reader(str(fn.resolve()))

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._reader.close()


class IpUtilsCountry(IpUtilsFile):
    _db_fn = 'GeoLite2-Country'

    def country(self, ip):
        return self._reader.country(ip)


class IpUtilsCity(IpUtilsCountry):
    _db_fn = 'GeoLite2-City'

    def city(self, ip):
        return self._reader.city(ip)
