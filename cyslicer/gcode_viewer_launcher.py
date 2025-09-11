## gcode_viewer_launcher.py
import sys
from PyQt5 import QtWidgets
from stl_editor import STLEditor
from gcode_visualiser import parse_cylindrical_gcode

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gcode_viewer_launcher.py <gcode_file>")
        sys.exit(1)

    gcode_path = sys.argv[1]
    moves = parse_cylindrical_gcode(gcode_path)

    app = QtWidgets.QApplication([])
    viewer = STLEditor(stl_path="")  # Dummy STL
    viewer.load_gcode_path(moves)
    app.exec_()
