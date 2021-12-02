# -*- coding: utf-8 -*-

"""Main module NgoGeo """
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import urllib.request as request
import zipfile
import dpath.util
import difflib
from collections import OrderedDict
from pprint import pprint

# a lot of data (long, lat, admin regions, population), search by name
import geonames

# https://pgeocode.readthedocs.io/en/latest/overview.html
# only for postal code, but very efficient
import pgeocode

# country info and subdivisions
import pycountry


class Territory:
    _humans_code = {}
    _subdivisions = {}
    _pk = None
    _name = None
    _postal = None
    _geocities = None
    _geonames = None

    def __init__(self, pk, name, postal=None, geocities=None, geonames=None):
        self._pk = pk
        self._name = name
        self._postal = postal
        self._geocities = geocities
        self._geonames = geonames
        self._humans_code[name] = pk
        self._subdivisions = OrderedDict()

    def __str__(self):
        return f'{self.__class__.__name__}({self._name} [{self._pk}])'

    def by_name(self, name):
        if name in self._humans_code:
            pk = self._humans_code[name]
            return self._subdivisions[pk]
        return self.search_name(name)

    def by_code(self, pk):
        return self._subdivisions[pk]

    def search_name(self, name, converter=None, regex=False, **kwargs):
        """Returns the most likely result as a pandas Series"""
        # Make a copy of the dataset to preserve the original
        data = self._geonames.data

        # Filter data by string queries before searching
        filters = {**kwargs}
        for key, val in filters.items():
            data = data[
                data[key].str.contains(val, case=False, regex=regex, na=False)
            ]

        # Use difflib to find matches
        diffs = difflib.get_close_matches(name, data['name'].tolist(), n=1, cutoff=0)
        matches = data[data['name'] == diffs[0]]

        for index, result in matches.iterrows():
            certainty = difflib.SequenceMatcher(None, result['name'], name).ratio()

            # Convert result if converter specified
            if converter:
                result = converter(result)

            result['certainty'] = certainty
            yield result

    def search_postal_code(self, codes):
        return self._postal.query_postal_code(codes)


class County(Territory):

    def __init__(self, pk, name, postal=None, geocities=None, geonames=None):
        Territory.__init__(self, pk, name, postal=postal, geocities=geocities, geonames=geonames)
        self._communities = self._subdivisions = OrderedDict()


Arrondissement = County


class Region(Territory):

    def __init__(self, pk, name, postal=None, geocities=None, geonames=None):
        Territory.__init__(self, pk, name, postal=postal, geocities=geocities, geonames=geonames)
        self._counties = self._subdivisions = OrderedDict()

        humans_code = self._humans_code
        admin2codes = geocities['admin2code'].dropna().unique()
        for cc in admin2codes:
            geocities_admin2 = geocities.loc[geocities['admin2code'] == cc]
            postal_admin2 = postal.loc[postal['county_code'] == cc]

            admin2_aliases = postal_admin2['county_name'].unique()
            for a in admin2_aliases:
                humans_code[a] = cc
            kk = admin2_aliases[0]

            self._counties[cc] = county = County(cc, kk, postal=postal_admin2, geocities=geocities_admin2, geonames=geonames)

            admin3codes = geocities_admin2['admin3code'].dropna().unique()
            for ccc in admin3codes:
                geocities_admin3 = geocities_admin2.loc[geocities_admin2['admin3code'] == ccc]
                postal_admin3 = postal_admin2.loc[postal_admin2['community_code'] == ccc]

                admin3_aliases = postal_admin3['community_name'].unique()
                for a in admin3_aliases:
                    humans_code[a] = ccc
                kkk = admin3_aliases[0]

                county._subdivisions[ccc] = Territory(ccc, kkk, postal=postal_admin3, geocities=geocities_admin3, geonames=geonames)


class Country(Territory):

    def __init__(self, country_code='fr'):
        ucc = country_code.upper()
        # load pycountry https://github.com/flyingcircusio/pycountry#countries-iso-3166
        self._pyctry = ctry = pycountry.countries.get(alpha_2=ucc)
        # country postal informations
        nomi = pgeocode.Nominatim(country_code)
        postal = nomi._data_frame
        # all country information
        gn = geonames.GeoNames(open(f'/Users/cedric/Downloads/{ucc}/{ucc}.txt', 'r'))
        geocities = gn.data.loc[gn.data['featureclass']=='P']
        geocities = geocities.sort_values('population', ascending=False)

        Territory.__init__(self, ucc, ctry.name, postal=postal, geocities=geocities, geonames=geonames)
        self._regions = self._subdivisions = OrderedDict()
        #self._counties = counties = OrderedDict()
        humans_code = self._humans_code

        # http://www.geonames.org/export/codes.html
        # P: city, village, ...
        admin1codes = geocities['admin1code'].dropna().unique()
        for c in admin1codes:
            #subdivisions[c] = OrderedDict()
            geocities_admin1 = geocities.loc[geocities['admin1code'] == c]
            postal_admin1 = postal.loc[postal['state_code'] == float(c)]

            admin1_aliases = postal_admin1['state_name'].unique()
            for a in admin1_aliases:
                humans_code[a] = c
            k = admin1_aliases[0]

            self._regions[c] = Region(c, k, postal=postal_admin1, geocities=geocities_admin1, geonames=gn)


world = {}


def load_country(country_code):
    world[country_code] = c = Country(country_code)
    return c
