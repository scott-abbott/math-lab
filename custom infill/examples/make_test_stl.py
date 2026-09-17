"""Generate simple binary STL test files (no external mesh library needed)."""
import struct
import sys
import numpy as np


def write_binary_stl(path, triangles: np.ndarray):
    with open(path, "wb") as f:
        f.write(b"\x00" * 80)
        f.write(struct.pack("<I", len(triangles)))
        for tri in triangles:
            v0, v1, v2 = tri
            normal = np.cross(v1 - v0, v2 - v0)
            norm = np.linalg.norm(normal)
            if norm > 0:
                normal = normal / norm
            f.write(struct.pack("<3f", *normal))
            for v in tri:
                f.write(struct.pack("<3f", *v))
            f.write(struct.pack("<H", 0))


def box(sx, sy, sz, ox=0.0, oy=0.0, oz=0.0):
    """Axis-aligned box, size sx x sy x sz, min corner at (ox, oy, oz)."""
    x0, x1 = ox, ox + sx
    y0, y1 = oy, oy + sy
    z0, z1 = oz, oz + sz
    v = {
        "000": (x0, y0, z0), "100": (x1, y0, z0),
        "110": (x1, y1, z0), "010": (x0, y1, z0),
        "001": (x0, y0, z1), "101": (x1, y0, z1),
        "111": (x1, y1, z1), "011": (x0, y1, z1),
    }
    faces = [
        # bottom (normal -z)
        ("000", "010", "110"), ("000", "110", "100"),
        # top (normal +z)
        ("001", "101", "111"), ("001", "111", "011"),
        # front (normal -y)
        ("000", "100", "101"), ("000", "101", "001"),
        # back (normal +y)
        ("010", "011", "111"), ("010", "111", "110"),
        # left (normal -x)
        ("000", "001", "011"), ("000", "011", "010"),
        # right (normal +x)
        ("100", "110", "111"), ("100", "111", "101"),
    ]
    tris = [[v[a], v[b], v[c]] for a, b, c in faces]
    return np.array(tris, dtype=np.float64)


def cube(size=20.0):
    write_binary_stl("cube.stl", box(size, size, size))
    print("wrote cube.stl")


def hollow_box(size=20.0, wall=4.0, height=10.0):
    """A square tube: outer box with an inner box subtracted, open top/bottom
    would require boolean ops we don't have, so instead build a 'napkin ring'
    by hand: 4 outer walls + 4 inner walls + top + bottom annulus via triangles."""
    outer = size
    inner = size - 2 * wall
    ox0, oy0 = 0.0, 0.0
    ox1, oy1 = outer, outer
    ix0, iy0 = wall, wall
    ix1, iy1 = wall + inner, wall + inner
    z0, z1 = 0.0, height

    def quad(p0, p1, p2, p3):
        # two triangles, CCW as seen from outside given consistent winding
        return [[p0, p1, p2], [p0, p2, p3]]

    tris = []
    # outer walls (normal points outward)
    tris += quad((ox0, oy0, z0), (ox1, oy0, z0), (ox1, oy0, z1), (ox0, oy0, z1))  # -y
    tris += quad((ox1, oy0, z0), (ox1, oy1, z0), (ox1, oy1, z1), (ox1, oy0, z1))  # +x
    tris += quad((ox1, oy1, z0), (ox0, oy1, z0), (ox0, oy1, z1), (ox1, oy1, z1))  # +y
    tris += quad((ox0, oy1, z0), (ox0, oy0, z0), (ox0, oy0, z1), (ox0, oy1, z1))  # -x

    # inner walls (normal points inward, i.e. toward the hole -> reverse winding)
    tris += quad((ix0, iy0, z1), (ix1, iy0, z1), (ix1, iy0, z0), (ix0, iy0, z0))
    tris += quad((ix1, iy0, z1), (ix1, iy1, z1), (ix1, iy1, z0), (ix1, iy0, z0))
    tris += quad((ix1, iy1, z1), (ix0, iy1, z1), (ix0, iy1, z0), (ix1, iy1, z0))
    tris += quad((ix0, iy1, z1), (ix0, iy0, z1), (ix0, iy0, z0), (ix0, iy1, z0))

    # top annulus (z1), 4 trapezoids connecting outer corners to inner corners
    def annulus_ring(z, flip):
        r = []
        outer_pts = [(ox0, oy0, z), (ox1, oy0, z), (ox1, oy1, z), (ox0, oy1, z)]
        inner_pts = [(ix0, iy0, z), (ix1, iy0, z), (ix1, iy1, z), (ix0, iy1, z)]
        for i in range(4):
            o0, o1 = outer_pts[i], outer_pts[(i + 1) % 4]
            in0, in1 = inner_pts[i], inner_pts[(i + 1) % 4]
            if not flip:
                r += [[o0, o1, in1], [o0, in1, in0]]
            else:
                r += [[o0, in1, o1], [o0, in0, in1]]
        return r

    tris += annulus_ring(z1, flip=False)  # top, normal +z
    tris += annulus_ring(z0, flip=True)   # bottom, normal -z

    write_binary_stl("hollow_box.stl", np.array(tris, dtype=np.float64))
    print("wrote hollow_box.stl")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("cube", "all"):
        cube()
    if which in ("hollow", "all"):
        hollow_box()
