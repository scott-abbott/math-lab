"""Minimal STL loader (binary + ASCII), no external mesh library required.

Returns triangles as an (N, 3, 3) numpy array of float64 vertex coordinates,
in mm, matching whatever units the STL file itself was authored in.
"""
import struct
import numpy as np


def load_stl(path: str) -> np.ndarray:
    with open(path, "rb") as f:
        header = f.read(80)
        rest = f.read()

    # Binary STL: 80 byte header, 4 byte uint triangle count, then
    # 50 bytes per triangle (12 floats + 2 byte attribute).
    if len(rest) >= 4:
        (tri_count,) = struct.unpack("<I", rest[:4])
        expected_len = 4 + tri_count * 50
        if expected_len == len(rest):
            return _load_binary(rest, tri_count)

    # Fall back to ASCII STL (re-read as text; header bytes are part of it).
    with open(path, "r", errors="ignore") as f:
        text = f.read()
    if "facet" in text.lower():
        return _load_ascii(text)

    raise ValueError(f"Could not parse '{path}' as binary or ASCII STL")


def _load_binary(data: bytes, tri_count: int) -> np.ndarray:
    triangles = np.empty((tri_count, 3, 3), dtype=np.float64)
    offset = 4
    for i in range(tri_count):
        # skip normal (12 bytes), read 3 vertices (36 bytes), skip attr (2 bytes)
        chunk = data[offset + 12: offset + 12 + 36]
        verts = struct.unpack("<9f", chunk)
        triangles[i, 0] = verts[0:3]
        triangles[i, 1] = verts[3:6]
        triangles[i, 2] = verts[6:9]
        offset += 50
    return triangles


def _load_ascii(text: str) -> np.ndarray:
    triangles = []
    verts = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("vertex"):
            parts = line.split()
            verts.append([float(parts[1]), float(parts[2]), float(parts[3])])
            if len(verts) == 3:
                triangles.append(verts)
                verts = []
    if not triangles:
        raise ValueError("No triangles found in ASCII STL")
    return np.array(triangles, dtype=np.float64)
