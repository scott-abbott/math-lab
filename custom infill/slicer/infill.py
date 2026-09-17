"""Generate infill toolpaths from a user-supplied pattern function f(x).

The pattern function has the signature:

    f(x: float) -> float

and describes the shape of a single infill line as it sweeps across the
part in a local coordinate frame: for a line based at local y = base_y,
the actual local y at a given local x is `base_y + f(x)`.

f(x) = 0.0 everywhere gives ordinary straight-line infill. Passing e.g.
`lambda x: 0.4 * math.sin(x / 3.0)` gives wavy/sinusoidal infill; a
triangle-wave or square-wave function gives zigzag infill, etc. See
patterns.py for ready-made examples.
"""
import math
from typing import Callable, List, Tuple
import numpy as np
from shapely.geometry import LineString, MultiLineString, GeometryCollection
from shapely.affinity import rotate as shapely_rotate

Point2 = Tuple[float, float]
PatternFn = Callable[[float], float]


def straight_line_pattern(x: float) -> float:
    """Default infill pattern: plain straight lines."""
    return 0.0


def _rotate_point(p: Point2, angle_rad: float) -> Point2:
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    x, y = p
    return (x * c - y * s, x * s + y * c)


def _extract_lines(geom) -> List[List[Point2]]:
    """Flatten any shapely intersection result down to a list of polylines."""
    out = []
    if geom is None or geom.is_empty:
        return out
    if isinstance(geom, LineString):
        if geom.length > 0:
            out.append(list(geom.coords))
    elif isinstance(geom, (MultiLineString, GeometryCollection)):
        for g in geom.geoms:
            out.extend(_extract_lines(g))
    return out


def generate_infill(
    region,
    extrusion_width: float,
    density: float,
    pattern: PatternFn = straight_line_pattern,
    angle_deg: float = 45.0,
    sample_step: float = 0.5,
) -> List[List[Point2]]:
    """Fill `region` (a shapely Polygon/MultiPolygon) with infill lines.

    Returns a list of polylines (each a list of (x, y) points) in the
    original coordinate frame, ready to be extruded.
    """
    if region is None or region.is_empty or density <= 0:
        return []

    line_spacing = extrusion_width / density

    # Work in a frame rotated so infill lines are horizontal, so the
    # pattern function only ever needs to reason about a simple 1D sweep.
    angle_rad = math.radians(angle_deg)
    local_region = shapely_rotate(region, -angle_deg, origin=(0, 0), use_radians=False)

    minx, miny, maxx, maxy = local_region.bounds
    if maxx <= minx or maxy <= miny:
        return []

    n_lines = max(1, int(math.floor((maxy - miny) / line_spacing)) + 1)
    n_samples = max(2, int(math.ceil((maxx - minx) / sample_step)) + 1)
    xs = np.linspace(minx, maxx, n_samples)

    polylines: List[List[Point2]] = []
    for i in range(n_lines):
        base_y = miny + (i + 0.5) * line_spacing
        if base_y > maxy:
            break
        coords = [(x, base_y + pattern(x)) for x in xs]
        line = LineString(coords)
        clipped = line.intersection(local_region)
        for seg in _extract_lines(clipped):
            # rotate back to the global frame
            global_seg = [_rotate_point(p, angle_rad) for p in seg]
            polylines.append(global_seg)

    return polylines
