"""Top-level orchestration: STL file -> G-code file."""
from typing import Optional

from .config import PrintConfig
from .stl_reader import load_stl
from .mesh_slicer import compute_layer_z_values, slice_layer, loops_to_polygon
from .geometry import compute_perimeters, compute_infill_region
from .infill import generate_infill, straight_line_pattern, PatternFn
from .gcode import GCodeWriter


def _center_mesh_on_bed(triangles, cfg: PrintConfig):
    xs = triangles[:, :, 0]
    ys = triangles[:, :, 1]
    zs = triangles[:, :, 2]
    cx = (xs.min() + xs.max()) / 2.0
    cy = (ys.min() + ys.max()) / 2.0
    z_shift = -zs.min()
    x_shift = cfg.resolved_center_x - cx
    y_shift = cfg.resolved_center_y - cy
    triangles = triangles.copy()
    triangles[:, :, 0] += x_shift
    triangles[:, :, 1] += y_shift
    triangles[:, :, 2] += z_shift
    return triangles


def slice_stl_to_gcode(
    stl_path: str,
    output_path: str,
    config: PrintConfig,
    infill_pattern: PatternFn = straight_line_pattern,
    progress_callback: Optional[callable] = None,
) -> None:
    triangles = load_stl(stl_path)
    if triangles.shape[0] == 0:
        raise ValueError("STL contains no triangles")

    triangles = _center_mesh_on_bed(triangles, config)

    layer_zs = compute_layer_z_values(triangles, config.layer_height)

    writer = GCodeWriter(config)
    writer.header()

    for i, z in enumerate(layer_zs):
        top_z = (i + 1) * config.layer_height
        writer.start_layer(i, top_z)

        loops = slice_layer(triangles, z)
        polygon = loops_to_polygon(loops)
        if polygon is None or polygon.is_empty:
            if progress_callback:
                progress_callback(i, len(layer_zs))
            continue

        perimeter_loops = compute_perimeters(
            polygon, config.extrusion_width, config.num_perimeters
        )
        for loop in perimeter_loops:
            writer.print_polyline(loop, closed=True)

        infill_region = compute_infill_region(
            polygon, config.extrusion_width, config.num_perimeters
        )
        angle = config.infill_angle
        if config.alternate_infill_angle and (i % 2 == 1):
            angle += 90.0

        infill_lines = generate_infill(
            infill_region,
            config.extrusion_width,
            config.infill_density,
            pattern=infill_pattern,
            angle_deg=angle,
        )
        for line in infill_lines:
            writer.print_polyline(line, closed=False)

        if progress_callback:
            progress_callback(i, len(layer_zs))

    writer.footer()
    writer.write(output_path)
