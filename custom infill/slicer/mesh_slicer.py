"""Slice a triangle mesh into 2D cross-section polygons at a set of Z heights.

Approach:
  1. For each layer Z, intersect every triangle that straddles the plane
     with that plane, producing a set of undirected line segments.
  2. Chain the segments end-to-end (matching coincident endpoints) into
     closed loops. Each loop is either an outer boundary or a hole.
  3. Build a shapely polygon per loop, then combine all loops for a layer
     with a symmetric-difference (even-odd / XOR) sweep ordered by area.
     This correctly resolves outer-boundary-vs-hole nesting without
     needing to trust triangle winding order.
"""
from typing import List, Dict, Tuple
import numpy as np
from shapely.geometry import Polygon

Point2 = Tuple[float, float]

_ROUND_DECIMALS = 6  # coordinate matching tolerance (~0.001 micron at mm scale)


def compute_layer_z_values(triangles: np.ndarray, layer_height: float) -> List[float]:
    z_min = triangles[:, :, 2].min()
    z_max = triangles[:, :, 2].max()
    n_layers = max(1, int(np.ceil((z_max - z_min) / layer_height)))
    # Sample at the mid-height of each layer to avoid landing exactly on
    # vertex/edge Z coordinates (flat top/bottom faces, etc.)
    return [z_min + layer_height * (i + 0.5) for i in range(n_layers)]


def _triangle_plane_segment(tri: np.ndarray, z: float):
    """Return the (p0, p1) XY intersection segment of a triangle with
    plane Z=z, or None if the triangle doesn't cross the plane."""
    d = tri[:, 2] - z
    # Nudge any vertex that lies (numerically) exactly on the plane so we
    # never have to special-case a zero.
    eps = 1e-9
    d = np.where(np.abs(d) < eps, eps, d)

    pts = []
    edges = ((0, 1), (1, 2), (2, 0))
    for a, b in edges:
        da, db = d[a], d[b]
        if (da > 0) != (db > 0):
            t = da / (da - db)
            p = tri[a] + t * (tri[b] - tri[a])
            pts.append((p[0], p[1]))

    if len(pts) == 2:
        return pts[0], pts[1]
    return None


def _key(p: Point2) -> Point2:
    return (round(p[0], _ROUND_DECIMALS), round(p[1], _ROUND_DECIMALS))


def _chain_segments(segments: List[Tuple[Point2, Point2]]) -> List[List[Point2]]:
    """Chain undirected segments (matching endpoints) into closed loops."""
    adjacency: Dict[Point2, List[Point2]] = {}
    for p, q in segments:
        kp, kq = _key(p), _key(q)
        if kp == kq:
            continue  # degenerate zero-length segment
        adjacency.setdefault(kp, []).append(kq)
        adjacency.setdefault(kq, []).append(kp)

    visited_edges = set()
    loops: List[List[Point2]] = []

    for start in list(adjacency.keys()):
        for first_next in list(adjacency.get(start, [])):
            edge = frozenset((start, first_next))
            if edge in visited_edges:
                continue

            # Walk a fresh loop starting with this edge until we return to
            # `start`, or get stuck (open/non-manifold contour -> discard).
            loop = [start]
            prev, current = start, first_next
            visited_edges.add(edge)
            closed = False
            while True:
                if current == start:
                    closed = True
                    break
                loop.append(current)
                neighbors = adjacency.get(current, [])
                nxt = None
                for cand in neighbors:
                    e = frozenset((current, cand))
                    if e not in visited_edges and cand != prev:
                        nxt = cand
                        break
                if nxt is None:
                    for cand in neighbors:  # allow doubling back if forced
                        e = frozenset((current, cand))
                        if e not in visited_edges:
                            nxt = cand
                            break
                if nxt is None:
                    break  # dead end; abandon this partial chain
                visited_edges.add(frozenset((current, nxt)))
                prev, current = current, nxt

            if closed and len(loop) >= 3:
                loops.append(loop)
    return loops


def slice_layer(triangles: np.ndarray, z: float) -> List[List[Point2]]:
    """Return the closed XY loops formed by intersecting the mesh with Z=z."""
    z_lo = triangles[:, :, 2].min(axis=1)
    z_hi = triangles[:, :, 2].max(axis=1)
    candidates = np.nonzero((z_lo < z) & (z_hi > z))[0]

    segments = []
    for idx in candidates:
        seg = _triangle_plane_segment(triangles[idx], z)
        if seg is not None:
            segments.append(seg)

    return _chain_segments(segments)


def loops_to_polygon(loops: List[List[Point2]]):
    """Combine raw loops into a shapely (Multi)Polygon, resolving holes via
    an even-odd sweep so winding direction doesn't matter."""
    polys = []
    for loop in loops:
        if len(loop) < 3:
            continue
        poly = Polygon(loop)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty or poly.area == 0:
            continue
        polys.append(poly)

    if not polys:
        return None

    polys.sort(key=lambda p: p.area, reverse=True)
    result = polys[0]
    for poly in polys[1:]:
        result = result.symmetric_difference(poly)
    if result.is_empty:
        return None
    return result
