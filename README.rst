========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |appveyor| |requires|
        | |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/python-ngogeo/badge/?style=flat
    :target: https://readthedocs.org/projects/python-ngogeo
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/numengo/python-ngogeo.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/numengo/python-ngogeo

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/numengo/python-ngogeo?branch=master&svg=true
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/numengo/python-ngogeo

.. |requires| image:: https://requires.io/github/numengo/python-ngogeo/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/numengo/python-ngogeo/requirements/?branch=master

.. |codecov| image:: https://codecov.io/github/numengo/python-ngogeo/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/numengo/python-ngogeo

.. |version| image:: https://img.shields.io/pypi/v/ngogeo.svg
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/ngogeo

.. |commits-since| image:: https://img.shields.io/github/commits-since/numengo/python-ngogeo/v0.1.0.svg
    :alt: Commits since latest release
    :target: https://github.com/numengo/python-ngogeo/compare/v0.1.0...master

.. |wheel| image:: https://img.shields.io/pypi/wheel/ngogeo.svg
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/ngogeo

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/ngogeo.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/ngogeo

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/ngogeo.svg
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/ngogeo


.. end-badges

Geo tools

* Free software: GNU General Public License v3

Installation
============

::

    pip install ngogeo

Settings are managed using
`simple-settings <https://raw.githubusercontent.com/drgarcia1986/simple-settings>`__
and can be overriden with configuration files (cfg, yaml, json) or with environment variables
prefixed with NGOGEO_.

Documentation
=============

https://python-ngogeo.readthedocs.io/

Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
