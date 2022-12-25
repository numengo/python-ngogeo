# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

import os
import re
import inflection
import logging
import pathlib
import requests

from ngoschema.decorators import assert_arg
from ngoschema.datatypes import Path
from ngoschema import settings, utils
from ngoschema.utils import file_link_format
from ngoschema.utils.jinja2 import default_jinja2_env

logger = logging.getLogger(__name__)


def create_amenities_codes(fp_out, dir_img_out):

    url = 'https://wiki.openstreetmap.org/wiki/Key:amenity'

    response = requests.get(url)

    from lxml import etree
    root = etree.fromstring(response.content)
    n = root.find('.//table[@class="wikitable"]')
    trs = n.find('tbody').findall('tr')

    if not dir_img_out.exists():
        logger.info('CREATE DIRECTORY %s.', file_link_format(str(dir_img_out)))
        os.makedirs(str(dir_img_out))

    amenity_titles = {}
    amenity_descriptions = {}
    amenity_icons = {}

    for tr in trs:
        tr_id = tr.get('id')
        try:
            name = etree.tostring(tr.findall('td')[1], encoding='utf-8', method='text').decode('utf-8').strip()
            comment = etree.tostring(tr.findall('td')[3], encoding='unicode-escape', method='text').decode('utf-8').strip('\\n')
            amenity_titles[name] = inflection.titleize(name)
            amenity_descriptions[name] = comment
            icon = tr.findall('td')[4].find('.//a')
            if icon is not None:
                icon_src = icon.get('href')
                fn = icon_src.split(':')[-1]
                amenity_icons[name] = fn
                img_fp = dir_img_out.joinpath(fn)
                if not img_fp.exists():
                    response = requests.get('https://wiki.openstreetmap.org' + icon_src)
                    logger.info('CREATE IMAGE %s.', file_link_format(str(img_fp)))
                    with img_fp.open('wb') as fp:
                        fp.write(response.content)
        except IndexError as er:
            pass
        except Exception as er:
            print(er)

    template_str = """
# -*- coding: utf-8
import gettext
_ = gettext.gettext

AMENITY_TITLES = {
{% for k, v in amenity_titles.items() %}
    '{{k}}': _("{{v}}"), 
{% endfor -%}
}

AMENITY_DESCRIPTIONS = {
{% for k, v in amenity_descriptions.items() %}
    '{{k}}': _("{% filter escape %}{{v}}{% endfilter %}"), 
{% endfor -%}
}

AMENITY_ICONS = {
{% for k, v in amenity_icons.items() %}
    '{{k}}': '{{v}}', 
{% endfor -%}
}

"""
    template = default_jinja2_env().from_string(template_str)
    stream = template.render(amenity_titles=amenity_titles,
                             amenity_descriptions=amenity_descriptions,
                             amenity_icons=amenity_icons)

    logger.info('CREATE FILE %s.', file_link_format(str(fp_out)))
    with open(str(fp_out), 'w') as fp:
        fp.writelines(stream)


if __name__ == '__main__':
    fp_out = pathlib.Path(__file__).parent.parent.joinpath('ngogeo', 'geonames', 'amenities.py')
    dir_img_out = pathlib.Path(__file__).parent.parent.joinpath('ngogeo', 'static', 'img', 'amenities')
    create_amenities_codes(fp_out, dir_img_out)
