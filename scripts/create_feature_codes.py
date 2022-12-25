# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

import inflection
import logging
import pathlib
import json

from ngoschema.decorators import assert_arg
from ngoschema.datatypes import Path
from ngoschema import settings, utils
from ngoschema.utils import file_link_format

logger = logging.getLogger(__name__)


def create_feature_codes(fc_file, fp_out):
    feature_classes = {
        'A': 'country, state, region, ...',
        'H': 'stream, lake, ...',
        'L': 'parks, area, ...',
        'P': 'city, village, ...',
        'R': 'road, railroad',
        'S': 'spot, building, farm',
        'T': 'mountain, hill, rock, ...',
        'U': 'undersea',
        'V': 'forest, heath, ...',
    }

    lines = []
    with open(str(fc_file), 'r') as fp:
        lines = fp.readlines()
    lines = [l.split('\t') for l in lines]

    feature_code_titles = {l[0]: l[1] for l in lines}
    feature_code_descriptions = {l[0]: l[2].strip() for l in lines}

    blank_line = ['\n']
    lines = ['# -*- coding: utf-8\n', 'import gettext\n', '_ = gettext.gettext\n'] + blank_line
    lines += ['FEATURE_CLASS_TITLES = {\n']
    lines += [f'    \'{k}\': _(\"{v}\"),\n' for k, v in feature_classes.items()]
    lines += ['}\n'] + blank_line + ['FEATURE_CODE_TITLES = {\n']
    lines += [f'    \'{k}\': _(\"{v}\"),\n' for k, v in feature_code_titles.items()]
    lines += ['}\n'] + blank_line + ['FEATURE_CODE_DESCRIPTIONS = {\n']
    lines += [f'    \'{k}\': _(\"{v}\"),\n' for k, v in feature_code_descriptions.items() if v]
    lines += ['}\n']

    with open(str(fp_out), 'w') as fp:
        fp.writelines(lines)

if __name__ == '__main__':
    fp_in = pathlib.Path(__file__).parent.parent.joinpath('ngogeo', 'static', 'geonames', 'featureCodes_en.txt')
    fp_out = pathlib.Path(__file__).parent.parent.joinpath('ngogeo', 'geonames', 'features.py')
    create_feature_codes(fp_in, fp_out)
