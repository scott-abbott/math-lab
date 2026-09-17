"""Visualize one layer of a generated G-code file (travel vs extrude moves)."""
import re
import sys
import matplotlib.pyplot as plt


def parse_layer(path, layer_num):
    lines = open(path).read().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(f"; LAYER:{layer_num} "))
    end = next(
        (i for i, l in enumerate(lines[start + 1:], start + 1) if l.startswith("; LAYER:")),
        len(lines),
    )
    return lines[start:end]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "cube_custom.gcode"
    layer_num = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    block = parse_layer(path, layer_num)

    x = y = 0.0
    segments_extrude = []
    segments_travel = []
    for line in block:
        m = re.search(r"X([-\d.]+)\s*Y([-\d.]+)", line)
        if not m:
            continue
        nx, ny = float(m.group(1)), float(m.group(2))
        is_extrude = line.startswith("G1") and " E" in line
        if line.startswith("G0"):
            segments_travel.append(((x, y), (nx, ny)))
        elif is_extrude:
            segments_extrude.append(((x, y), (nx, ny)))
        x, y = nx, ny

    fig, ax = plt.subplots(figsize=(6, 6))
    for (x0, y0), (x1, y1) in segments_travel:
        ax.plot([x0, x1], [y0, y1], color="lightgray", linewidth=0.5, linestyle="--")
    for (x0, y0), (x1, y1) in segments_extrude:
        ax.plot([x0, x1], [y0, y1], color="steelblue", linewidth=1.2)
    ax.set_aspect("equal")
    ax.set_title(f"{path} - layer {layer_num}")
    out = f"layer_{layer_num}_preview.png"
    fig.savefig(out, dpi=150)
    print("wrote", out)


if __name__ == "__main__":
    main()
