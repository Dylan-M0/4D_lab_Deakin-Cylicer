import subprocess
from pathlib import Path

def slice_stl_with_prusaslicer(prusaslicer_path, config_path, stl_path, output_path):
    cmd = [
        str(prusaslicer_path),
        "--slice",
        "--load", str(config_path),
        "--output", str(output_path),
        str(stl_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Slicing failed.\nSTDERR:", result.stderr)
    else:
        print("Slicing succeeded:", output_path)
