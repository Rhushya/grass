"""Tests for interactive map helpers and layers."""

import json
import sys

import pytest

from grass.jupyter.interactivemap import Vector


class _FakeRenderer:
    def __init__(self, filename):
        self._filename = filename

    def render_vector(self, _name):
        return self._filename


class _FakeMap:
    def __init__(self):
        self.layers = []

    def add(self, layer):
        self.layers.append(layer)


class _FakeGeoJSON:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _FakeIpyLeafletModule:
    GeoJSON = _FakeGeoJSON


def test_vector_add_to_folium_generates_html_output(tmp_path):
    """Vector can be added to folium map and exported as HTML output."""
    folium = pytest.importorskip("folium", reason="folium package not available")

    geojson = tmp_path / "point.json"
    geojson.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
                        "properties": {"name": "origin"},
                    }
                ],
            }
        )
    )

    vector = Vector("point", renderer=_FakeRenderer(geojson))
    map_object = folium.Map(location=[0.0, 0.0], zoom_start=3)
    vector.add_to(map_object)

    output = tmp_path / "vector_map.html"
    map_object.save(output)

    content = output.read_text(encoding="utf-8")
    assert output.exists()
    assert output.stat().st_size > 0
    assert "FeatureCollection" in content
    assert "origin" in content


def test_vector_opacity_style_is_reused_across_multiple_maps(tmp_path, monkeypatch):
    """Vector opacity is translated to style without mutating layer kwargs."""
    geojson = tmp_path / "point.json"
    geojson.write_text(json.dumps({"type": "FeatureCollection", "features": []}))

    monkeypatch.setitem(sys.modules, "ipyleaflet", _FakeIpyLeafletModule)

    vector = Vector(
        "point",
        renderer=_FakeRenderer(geojson),
        opacity=0.6,
        style={"color": "red"},
    )

    first_map = _FakeMap()
    vector.add_to(first_map)

    second_map = _FakeMap()
    vector.add_to(second_map)

    for layer in [first_map.layers[0], second_map.layers[0]]:
        assert layer.kwargs["style"] == {"color": "red", "opacity": 0.6}
        assert "opacity" not in layer.kwargs
        assert layer.kwargs["name"] == "point"
        assert layer.kwargs["data"] == {
            "type": "FeatureCollection",
            "features": [],
        }

    # Original user-provided style remains unchanged.
    assert vector._layer_kwargs == {"opacity": 0.6, "style": {"color": "red"}}
