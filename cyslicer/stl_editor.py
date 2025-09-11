from PyQt5 import QtWidgets, QtCore
from pyvistaqt import QtInteractor
import pyvista as pv
import numpy as np
from pathlib import Path
import json


class STLEditor(QtWidgets.QMainWindow):
    def __init__(self, stl_path, callback_on_save=None):
        super().__init__()
        self.setWindowTitle("STL Editor")

        self.original_path = Path(stl_path)
        self.callback_on_save = callback_on_save

        self.mesh = pv.read(str(self.original_path))
        if self.mesh.n_points == 0:
            raise ValueError("STL file has no points.")

        center = np.array(self.mesh.center)
        self.mesh.translate(-center, inplace=True)
        self.transformed_mesh = self.mesh.copy()

        # === Main widget layout ===
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QHBoxLayout()
        central_widget.setLayout(layout)

        # === Left: Controls ===
        self.controls = self.build_controls()
        layout.addLayout(self.controls, stretch=1)

        # === Right: 3D Viewer ===
        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter.interactor, stretch=3)

        # Setup viewer
        self.plotter.set_background("white")
        self.actor = self.plotter.add_mesh(self.transformed_mesh, color="lightgray", show_edges=True)
        self.plotter.show_grid()
        self.plotter.view_isometric()
        self.plotter.reset_camera()

        self.show()

    def build_controls(self):
        layout = QtWidgets.QVBoxLayout()

        # --- Scale ---
        layout.addWidget(QtWidgets.QLabel("Scale"))
        self.sx = QtWidgets.QDoubleSpinBox(value=1.0); self.sx.setPrefix("X: "); self.sx.setRange(0.01, 10.0)
        self.sy = QtWidgets.QDoubleSpinBox(value=1.0); self.sy.setPrefix("Y: "); self.sy.setRange(0.01, 10.0)
        self.sz = QtWidgets.QDoubleSpinBox(value=1.0); self.sz.setPrefix("Z: "); self.sz.setRange(0.01, 10.0)
        layout.addWidget(self.sx); layout.addWidget(self.sy); layout.addWidget(self.sz)
        layout.addWidget(self._btn("Apply Scale", self.apply_scale))

        # --- Translate ---
        layout.addWidget(QtWidgets.QLabel("Translate"))
        self.tx = QtWidgets.QDoubleSpinBox(value=0); self.tx.setPrefix("X: "); self.tx.setRange(-1000, 1000)
        self.ty = QtWidgets.QDoubleSpinBox(value=0); self.ty.setPrefix("Y: "); self.ty.setRange(-1000, 1000)
        self.tz = QtWidgets.QDoubleSpinBox(value=0); self.tz.setPrefix("Z: "); self.tz.setRange(-1000, 1000)
        layout.addWidget(self.tx); layout.addWidget(self.ty); layout.addWidget(self.tz)
        layout.addWidget(self._btn("Apply Translation", self.apply_translation))

        # --- Rotate ---
        layout.addWidget(QtWidgets.QLabel("Rotate"))
        self.axis_selector = QtWidgets.QComboBox()
        self.axis_selector.addItems(["X", "Y", "Z"])
        self.angle_spin = QtWidgets.QDoubleSpinBox(value=0); self.angle_spin.setSuffix("°"); self.angle_spin.setRange(-360, 360)
        layout.addWidget(self.axis_selector); layout.addWidget(self.angle_spin)
        layout.addWidget(self._btn("Apply Rotation", self.apply_rotation))

        # --- Other controls ---
        layout.addWidget(self._btn("Reset", self.reset_transform))
        layout.addWidget(self._btn("Save STL", self.save_stl))

        layout.addStretch()
        return layout

    def _btn(self, label, func):
        btn = QtWidgets.QPushButton(label)
        btn.clicked.connect(func)
        return btn

    def apply_scale(self):
        factors = [self.sx.value(), self.sy.value(), self.sz.value()]
        self.transformed_mesh.scale(factors, inplace=True)
        self.update_view()

    def apply_translation(self):
        vec = [self.tx.value(), self.ty.value(), self.tz.value()]
        self.transformed_mesh.translate(vec, inplace=True)
        self.update_view()

    def apply_rotation(self):
        axis = self.axis_selector.currentText().lower()
        angle = self.angle_spin.value()
        vec = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[axis]
        self.transformed_mesh.rotate_vector(vec, angle, point=(0, 0, 0), inplace=True)
        self.update_view()

    def reset_transform(self):
        self.transformed_mesh = self.mesh.copy()
        self.update_view()

    def update_view(self):
        self.plotter.clear()
        self.plotter.add_mesh(self.transformed_mesh, color="lightgray", show_edges=True)

        #  Re-add helper visuals
        self.plotter.show_axes()
        self.plotter.show_grid(color='lightgray')

        self.plotter.view_isometric()
        self.plotter.reset_camera()
        self.plotter.render()


    def save_stl(self):
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save STL", str(self.original_path), "STL Files (*.stl)"
        )
        if save_path:
            self.transformed_mesh.save(save_path)
            self.update_json_and_notify(Path(save_path))

    def update_json_and_notify(self, new_stl_path):
        json_path = Path(__file__).parent / "user_parameters.json"
        if json_path.exists():
            with open(json_path) as f:
                data = json.load(f)
            data["stl_file"] = str(new_stl_path)
            with open(json_path, "w") as f:
                json.dump(data, f, indent=4)

        if self.callback_on_save:
            self.callback_on_save(str(new_stl_path))
    def load_gcode_path(self, moves):
        self.plotter.clear()
        for start, end, extruding in moves:
            line = pv.Line(start, end)
            color = "red" if extruding else "gray"
            width = 2 if extruding else 1
            self.plotter.add_mesh(line, color=color, line_width=width)

        self.plotter.show_axes()
        self.plotter.show_grid()
        self.plotter.view_isometric()
        self.plotter.reset_camera()
        self.plotter.render()
