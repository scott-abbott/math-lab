"""Turn a layer's cross-section polygon into printable perimeter loops and
an infill region, using shapely for polygon offsetting."""
from typing import List
from shapely.geometry import Polygon, MultiPolygon, LinearRing


def _iter_polygons(geom):
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, MultiPolygon):
        for p in geom.geoms:
            if not p.is_empty:
                yield p
    elif isinstance(geom, Polygon):
        yield geom


def _rings_of(polygon: Polygon) -> List[LinearRing]:
    rings = [polygon.exterior]
    rings.extend(polygon.interiors)
    return rings


def compute_perimeters(geom, extrusion_width: float, num_perimeters: int):
    """Return list of loops (each a list of (x, y) points), ordered
    outermost-first, offset inward by half a line width per shell."""
    loops = []
    for i in range(num_perimeters):
        distance = extrusion_width / 2.0 + i * extrusion_width
        offset_geom = geom.buffer(-distance, join_style=2)  # mitre joins
        for poly in _iter_polygons(offset_geom):
            for ring in _rings_of(poly):
                loops.append(list(ring.coords))
    return loops


def compute_infill_region(geom, extrusion_width: float, num_perimeters: int):
    """Return the shapely geometry that should be filled with infill,
    i.e. the area inside the innermost perimeter."""
    inset = extrusion_width * num_perimeters
    if inset <= 0:
        return geom
    return geom.buffer(-inset, join_style=2)
