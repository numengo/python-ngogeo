#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `ngogeo` package."""
from click.testing import CliRunner

from ngogeo.cli import main

# PROTECTED REGION ID(ngogeo.tests.test_ngogeo) ENABLED START
from ngogeo import ngogeo

def test_ngogeo():
    france = ngogeo.load_country('fr')
    assert france._name == 'France'


if __name__ == '__main__':
    # to run test file standalone
    test_ngogeo()

# PROTECTED REGION END
