# -*- coding: utf-8 -*-

"""Top-level package for NgoGeo."""

__author__ = """Cedric ROMAN"""
__email__ = 'roman@numengo.com'
__version__ = '0.1.0'

from simple_settings import LazySettings
settings = LazySettings('ngogeo.config.settings')

# PROTECTED REGION ID(ngogeo.init) ENABLED START
from ngoschema.loaders import register_module, register_locale_dir
import pycountry

register_module('ngogeo')
# pycountry provides locales for countries, languages, currencies
register_locale_dir('pycountry', 'locales')


from .ngogeo import *
__all__ = [
    'settings',
]
# PROTECTED REGION END
