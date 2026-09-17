#!/usr/bin/env python
"""CLI entry point: slice an STL file into a G-code file.

Examples
--------
Basic slice with defaults:
    python main.py part.stl part.gcode

Custom perimeters / infill density / layer height:
    python main.py part.stl part.gcode --layer-height 0.15 \\
        --perimeters 3 --infill-density 0.3

Built-in wavy infill pattern:
    python main.py part.stl part.gcode --infill-pattern sine

Your own infill pattern function f(x) -> y, loaded from a .py file:
    python main.py part.stl part.gcode \\
        --infill-pattern-file my_pattern.py --infill-pattern-func my_wave
"""
import argparse
import importlib.util
import sys
import time

from slicer.config import PrintConfig
from slicer.engine import slice_stl_to_gcode
from slicer.infill import straight_line_pattern
from slicer.patterns import PATTERNS


def load_pattern_from_file(path: str, func_name: str):
    spec = importlib.util.spec_from_file_location("user_infill_pattern", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, func_name):
        raise SystemExit(f"'{func_name}' not found in {path}")
    return getattr(module, func_name)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="A simple STL -> G-code slicer with custom infill patterns. "
        "All lengths in mm, all temperatures in degrees C.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("input_stl", help="Path to the input STL file")
    p.add_argument("output_gcode", help="Path to write the output G-code file")

    geo = p.add_argument_group("Layers / extrusion")
    geo.add_argument("--layer-height", type=float, default=0.2, help="mm (default: 0.2)")
    geo.add_argument("--extrusion-width", type=float, default=0.45,
                      help="width of a single extruded line, mm (default: 0.45)")
    geo.add_argument("--perimeters", type=int, default=2, dest="num_perimeters",
                      help="number of perimeter shells (default: 2)")
    geo.add_argument("--infill-density", type=float, default=0.2,
                      help="0.0-1.0 (default: 0.2)")
    geo.add_argument("--infill-angle", type=float, default=45.0,
                      help="base infill direction in degrees (default: 45)")
    geo.add_argument("--no-alternate-infill-angle", action="store_false",
                      dest="alternate_infill_angle",
                      help="don't rotate infill 90 degrees every other layer")

    hw = p.add_argument_group("Hardware")
    hw.add_argument("--nozzle-diameter", type=float, default=0.4, help="mm (default: 0.4)")
    hw.add_argument("--filament-diameter", type=float, default=1.75, help="mm (default: 1.75)")
    hw.add_argument("--bed-size-x", type=float, default=220.0, help="mm (default: 220)")
    hw.add_argument("--bed-size-y", type=float, default=220.0, help="mm (default: 220)")
    hw.add_argument("--center-x", type=float, default=None,
                     help="mm, where to center the model's X footprint "
                          "(default: middle of the bed, bed-size-x / 2)")
    hw.add_argument("--center-y", type=float, default=None,
                     help="mm, where to center the model's Y footprint "
                          "(default: middle of the bed, bed-size-y / 2)")

    temp = p.add_argument_group("Temperatures (degrees C)")
    temp.add_argument("--nozzle-temp", type=float, default=200.0, help="default: 200")
    temp.add_argument("--bed-temp", type=float, default=60.0, help="default: 60")

    speed = p.add_argument_group("Speeds (mm/s) and retraction")
    speed.add_argument("--print-speed", type=float, default=40.0)
    speed.add_argument("--first-layer-speed", type=float, default=20.0)
    speed.add_argument("--travel-speed", type=float, default=120.0)
    speed.add_argument("--retraction-length", type=float, default=1.0, help="mm")
    speed.add_argument("--retraction-speed", type=float, default=35.0, help="mm/s")

    infill = p.add_argument_group("Infill pattern")
    infill.add_argument("--infill-pattern", choices=sorted(PATTERNS.keys()),
                         default="lines",
                         help="built-in infill pattern function f(x) (default: lines)")
    infill.add_argument("--infill-pattern-file", default=None,
                         help="path to a .py file defining a custom f(x) function")
    infill.add_argument("--infill-pattern-func", default="infill",
                         help="name of the function inside --infill-pattern-file "
                              "(default: 'infill')")

    return p


def main(argv=None):
    args = build_arg_parser().parse_args(argv)

    config = PrintConfig(
        layer_height=args.layer_height,
        extrusion_width=args.extrusion_width,
        num_perimeters=args.num_perimeters,
        infill_density=args.infill_density,
        nozzle_diameter=args.nozzle_diameter,
        filament_diameter=args.filament_diameter,
        nozzle_temp=args.nozzle_temp,
        bed_temp=args.bed_temp,
        print_speed=args.print_speed,
        first_layer_speed=args.first_layer_speed,
        travel_speed=args.travel_speed,
        retraction_length=args.retraction_length,
        retraction_speed=args.retraction_speed,
        bed_size_x=args.bed_size_x,
        bed_size_y=args.bed_size_y,
        center_x=args.center_x,
        center_y=args.center_y,
        infill_angle=args.infill_angle,
        alternate_infill_angle=args.alternate_infill_angle,
    )

    if args.infill_pattern_file:
        pattern_fn = load_pattern_from_file(args.infill_pattern_file, args.infill_pattern_func)
    else:
        pattern_fn = PATTERNS.get(args.infill_pattern, straight_line_pattern)

    start = time.time()

    def progress(layer_i, total_layers):
        pct = 100.0 * (layer_i + 1) / total_layers
        sys.stdout.write(f"\rSlicing layer {layer_i + 1}/{total_layers} ({pct:5.1f}%)")
        sys.stdout.flush()

    slice_stl_to_gcode(
        args.input_stl, args.output_gcode, config,
        infill_pattern=pattern_fn, progress_callback=progress,
    )

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.1f}s -> {args.output_gcode}")


if __name__ == "__main__":
    main()
