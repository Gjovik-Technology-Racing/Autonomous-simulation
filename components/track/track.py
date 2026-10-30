"""Read an ASCII grid and convert its single S-to-E path into a smooth road centreline.

No Panda3D dependency: this module only produces coordinates in metres.
"""

from pathlib import Path
import numpy as np


class Track:
    ALLOWED = {".", "X", "S", "E"}

    def __init__(
        self,
        file: str | Path,
        cell_size_m: float,
        width_m: float,
        mesh_resolution_m: float = 0.5,
        corner_rounding: float = 0.45,
        line_width_m: float = 0.12,
    ):
        self.file = Path(file)
        self.cell_size_m = float(cell_size_m)
        self.width_m = float(width_m)
        self.mesh_resolution_m = float(mesh_resolution_m)
        self.corner_rounding = float(corner_rounding)
        self.line_width_m = float(line_width_m)

        if self.cell_size_m <= 0 or self.width_m <= 0 or self.mesh_resolution_m <= 0:
            raise ValueError("cell_size_m, width_m and mesh_resolution_m must be positive.")
        if not 0 <= self.corner_rounding < 0.5:
            raise ValueError("corner_rounding must be in [0, 0.5).")
        if not 0 < self.line_width_m < self.width_m / 2:
            raise ValueError("line_width_m must be positive and smaller than half the road width.")

        self.grid = self._read_grid()
        self.cells = self._ordered_cells()
        self.grid_centres_m = np.array([self._cell_to_xy(cell) for cell in self.cells])
        self.centerline_m = self._build_centerline(self.grid_centres_m)
        self.length_m = float(np.linalg.norm(np.diff(self.centerline_m, axis=0), axis=1).sum())

        # Positive normal is left of the direction from S to E.
        tangent = np.gradient(self.centerline_m, axis=0)
        lengths = np.linalg.norm(tangent, axis=1)
        self.normals = np.column_stack((-tangent[:, 1], tangent[:, 0])) / lengths[:, None]

    def _read_grid(self) -> list[str]:
        if not self.file.is_file():
            raise FileNotFoundError(f"Track file not found: {self.file}")
        rows = [line.strip().upper() for line in self.file.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not rows or any(len(row) != len(rows[0]) for row in rows):
            raise ValueError("Grid must be nonempty and all rows must have equal length.")
        for r, row in enumerate(rows):
            invalid = set(row) - self.ALLOWED
            if invalid:
                raise ValueError(f"Unexpected symbols on row {r + 1}: {sorted(invalid)}")
        if sum(row.count("S") for row in rows) != 1 or sum(row.count("E") for row in rows) != 1:
            raise ValueError("Grid must contain exactly one S and one E.")
        return rows

    def _ordered_cells(self) -> list[tuple[int, int]]:
        passable = {
            (row, col): value
            for row, line in enumerate(self.grid)
            for col, value in enumerate(line)
            if value in "SXE"
        }
        start = next(cell for cell, value in passable.items() if value == "S")
        finish = next(cell for cell, value in passable.items() if value == "E")
        neighbours = {}
        for r, c in passable:
            neighbours[r, c] = [
                adjacent
                for adjacent in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
                if adjacent in passable
            ]

        for cell, linked in neighbours.items():
            required = 1 if cell in (start, finish) else 2
            if len(linked) != required:
                raise ValueError(
                    f"Invalid track at grid cell {cell}: expected {required} connections, "
                    f"found {len(linked)}. Use a single 4-connected, unbranched S-to-E path."
                )

        ordered = [start]
        previous = None
        current = start
        while current != finish:
            candidates = [cell for cell in neighbours[current] if cell != previous]
            if len(candidates) != 1 or candidates[0] in ordered:
                raise ValueError("Track contains a loop or ambiguous path.")
            previous, current = current, candidates[0]
            ordered.append(current)

        if len(ordered) != len(passable):
            raise ValueError("Track contains disconnected cells.")
        return ordered

    def _cell_to_xy(self, cell: tuple[int, int]) -> tuple[float, float]:
        r, c = cell
        height, width = len(self.grid), len(self.grid[0])
        return (
            (c - (width - 1) / 2) * self.cell_size_m,
            ((height - 1) / 2 - r) * self.cell_size_m,
        )

    def _build_centerline(self, points: np.ndarray) -> np.ndarray:
        # Round grid corners with quadratic Bezier segments, then uniformly resample.
        control = [points[0]]
        for i in range(1, len(points) - 1):
            previous, vertex, following = points[i - 1], points[i], points[i + 1]
            arriving = vertex - previous
            leaving = following - vertex
            if np.allclose(arriving / np.linalg.norm(arriving), leaving / np.linalg.norm(leaving)) or self.corner_rounding == 0:
                control.append(vertex)
                continue

            before = vertex - arriving * self.corner_rounding
            after = vertex + leaving * self.corner_rounding
            control.append(before)
            # Sample the Bezier densely enough before final equal-distance resampling.
            count = max(8, int(np.ceil(2 * self.cell_size_m * self.corner_rounding / self.mesh_resolution_m)))
            for t in np.linspace(0, 1, count + 1)[1:]:
                control.append((1 - t) ** 2 * before + 2 * (1 - t) * t * vertex + t**2 * after)
        control.append(points[-1])

        control = np.asarray(control)
        distances = np.linalg.norm(np.diff(control, axis=0), axis=1)
        keep = np.r_[True, distances > 1e-9]
        control = control[keep]
        cumulative = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(control, axis=0), axis=1))]
        total = cumulative[-1]
        samples = np.r_[np.arange(0, total, self.mesh_resolution_m), total]
        return np.column_stack([
            np.interp(samples, cumulative, control[:, 0]),
            np.interp(samples, cumulative, control[:, 1]),
        ])

    def offset_curve(self, signed_offset_m: float) -> np.ndarray:
        """Return a curve parallel to the centreline (+left, -right)."""
        return self.centerline_m + self.normals * signed_offset_m

    @property
    def bounds_m(self) -> tuple[float, float, float, float]:
        left, right = self.offset_curve(self.width_m / 2), self.offset_curve(-self.width_m / 2)
        points = np.vstack((left, right))
        return (float(points[:, 0].min()), float(points[:, 0].max()),
                float(points[:, 1].min()), float(points[:, 1].max()))
