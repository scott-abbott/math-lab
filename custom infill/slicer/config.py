"""Print settings. All lengths are in mm, all temperatures in degrees C."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class PrintConfig:
    # --- Layers / extrusion ---
    layer_height: float = 0.2          # mm, height of each printed layer
    extrusion_width: float = 0.45      # mm, width of a single extruded line
    num_perimeters: int = 2            # number of perimeter (wall) loops
    infill_density: float = 0.2        # fraction 0..1 (0 = none, 1 = solid)

    # --- Hardware ---
    nozzle_diameter: float = 0.4       # mm
    filament_diameter: float = 1.75    # mm

    # --- Temperatures (degrees C) ---
    nozzle_temp: float = 200.0
    bed_temp: float = 60.0

    # --- Speeds (mm/s) ---
    print_speed: float = 40.0          # perimeters / infill
    first_layer_speed: float = 20.0
    travel_speed: float = 120.0

    # --- Retraction ---
    retraction_length: float = 1.0     # mm of filament
    retraction_speed: float = 35.0     # mm/s

    # --- Build plate ---
    bed_size_x: float = 220.0
    bed_size_y: float = 220.0

    # Where to center the model's XY footprint, in bed coordinates (mm).
    # Defaults (None) to the middle of the bed: (bed_size_x/2, bed_size_y/2).
    center_x: Optional[float] = None
    center_y: Optional[float] = None

    # --- Infill ---
    infill_angle: float = 45.0         # degrees, base direction of infill lines
    alternate_infill_angle: bool = True  # rotate 90 deg every other layer

    def __post_init__(self):
        if self.layer_height <= 0:
            raise ValueError("layer_height must be > 0")
        if self.extrusion_width <= 0:
            raise ValueError("extrusion_width must be > 0")
        if self.num_perimeters < 0:
            raise ValueError("num_perimeters must be >= 0")
        if not (0.0 <= self.infill_density <= 1.0):
            raise ValueError("infill_density must be between 0 and 1")
        if self.nozzle_diameter <= 0:
            raise ValueError("nozzle_diameter must be > 0")
        if self.filament_diameter <= 0:
            raise ValueError("filament_diameter must be > 0")

    @property
    def filament_area(self) -> float:
        """Cross-sectional area of the filament (mm^2)."""
        r = self.filament_diameter / 2.0
        return 3.141592653589793 * r * r

    @property
    def resolved_center_x(self) -> float:
        return self.center_x if self.center_x is not None else self.bed_size_x / 2.0

    @property
    def resolved_center_y(self) -> float:
        return self.center_y if self.center_y is not None else self.bed_size_y / 2.0
