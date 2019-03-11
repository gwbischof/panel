from __future__ import absolute_import, division, unicode_literals

import sys

import numpy as np

from bokeh.models import ColumnDataSource

from ..models import VegaPlot
from .base import PaneBase


def ds_as_cds(dataset):
    """
    Converts Vega dataset into Bokeh ColumnDataSource data
    """
    if len(dataset) == 0:
        return {}
    data = {k: [] for k, v in dataset[0].items()}
    for item in dataset:
        for k, v in item.items():
            data[k].append(v)
    data = {k: np.asarray(v) for k, v in data.items()}
    return data


class Vega(PaneBase):
    """
    Vega panes allow rendering Vega plots and traces.

    For efficiency any array objects found inside a Figure are added
    to a ColumnDataSource which allows using binary transport to sync
    the figure on bokeh server and via Comms.
    """

    priority = 0.8

    _updates = True

    @classmethod
    def is_altair(cls, obj):
        if 'altair' in sys.modules:
            import altair as alt
            return isinstance(obj, alt.vegalite.v2.api.Chart)
        return False

    @classmethod
    def applies(cls, obj):
        if isinstance(obj, dict) and 'vega' in obj.get('$schema', '').lower():
            return True
        return cls.is_altair(obj)

    @classmethod
    def _to_json(cls, obj):
        if isinstance(obj, dict):
            json = dict(obj)
            json['data'] = dict(json['data'])
            return json
        return obj.to_dict()

    def _get_sources(self, json, sources):
        for name, data in json.pop('datasets', {}).items():
            if name in sources:
                continue
            columns = set(data[0]) if data else []
            if self.is_altair(self.object):
                import altair as alt
                if (not isinstance(self.object.data, alt.Data) and
                    columns == set(self.object.data)):
                    data = ColumnDataSource.from_df(self.object.data)
                else:
                    data = ds_as_cds(data)
                sources[name] = ColumnDataSource(data=data)
            else:
                sources[name] = ColumnDataSource(data=ds_as_cds(data))
        data = json.get('data', {}).pop('values', {})
        if data:
            sources['data'] = ColumnDataSource(data=ds_as_cds(data))

    def _get_model(self, doc, root=None, parent=None, comm=None):
        sources = {}
        if self.object is None:
            json = None
        else:
            json = self._to_json(self.object)
            json['data'] = dict(json['data'])
            self._get_sources(json, sources)
        model = VegaPlot(data=json, data_sources=sources)
        if root is None:
            root = model
        self._models[root.ref['id']] = (model, parent)
        return model

    def _update(self, model):
        if self.object is None:
            json = self._to_json(self.object)
            self._get_sources(json, model.data_sources)
        else:
            json = None
        model.data = json

