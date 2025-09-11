import sys
from PyQt5.QtWidgets import QApplication
from stl_editor import STLEditor

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m stl_editor_launcher <stl_file>")
        sys.exit(1)

    stl_path = sys.argv[1]
    app = QApplication(sys.argv)
    editor = STLEditor(stl_path)
    sys.exit(app.exec_())
