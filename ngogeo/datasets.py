# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import pandas as pd
import geopandas as gpd
import numpy as np

from ngoschema.protocols import with_metaclass, SchemaMetaclass, ObjectProtocol
from ngoschema.models.datasets import DataframeSubset

from .point_search import _search_radius


class GeoDataframeSubset(with_metaclass(SchemaMetaclass)):
    _id = r"https://numengo.org/ngogeo#/$defs/datasets/$defs/GeoDataframeSubset"

    def get_subset(self):
        df = DataframeSubset.get_subset(self)
        if df is not None:
            df = df if isinstance(df, gpd.GeoDataFrame) else gpd.GeoDataFrame(df)
            if not df.crs or not df.crs.is_exact_same(self.crs):
                df.to_crs(self.crs, inplace=True)
        return df

    def get__dataframe(self):
        gdf = self.subset
        return pd.DataFrame(gdf) if gdf is not None else None

    def search_radius(self, point, radius=10000, point_crs=None, regex=False, **kwargs):
        subset = self.subset
        if subset is not None:
            return _search_radius(subset, point, radius=10000, point_crs=None, regex=False, **kwargs)
