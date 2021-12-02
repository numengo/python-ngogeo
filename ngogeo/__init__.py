# -*- coding: utf-8 -*-

"""Top-level package for NgoGeo."""

__author__ = """Cedric ROMAN"""
__email__ = 'roman@numengo.com'
__version__ = '0.1.0'

from simple_settings import LazySettings
settings = LazySettings('ngogeo.config.settings', 'NGOGEO_.environ')

# PROTECTED REGION ID(ngogeo.init) ENABLED START
from ngoschema.loaders import register_module
register_module('ngogeo')

from .ngogeo import *
__all__ = [
    'settings',
]
# PROTECTED REGION END
