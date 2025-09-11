import subprocess
import os
from pathlib import Path

config_ini     = Path(r"C:\Users\moslem\Documents\cy_slicer\my_snapmaker_config.ini")
stl_file       = Path(r"C:\Users\moslem\Documents\cy_slicer\STL\unwrapped_sample 01.stl")
gcode_output   = Path(r"C:\Users\moslem\Documents\cy_slicer\gcode\unwrapped_sample 01.gcode")
prusaslicer_exe = Path(r"C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer.exe")

def slice_stl_with_prusaslicer(
    prusaslicer_path,
    config_ini_path,
    stl_path,
    output_gcode_path
):
    # Build the command
    cmd = [
        prusaslicer_path,
        "--slice",
        "--load", str(config_ini_path),
        "--output", str(output_gcode_path),
        str(stl_path)
    ]



    # Run the command
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Check result
    if result.returncode == 0:
        print(" Slicing completed successfully.")
        print(f"Generated G-code: {output_gcode_path}")
    else:
        print(" Slicing failed.")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

# === Example usage ===




slice_stl_with_prusaslicer(
    prusaslicer_exe,
    config_ini,
    stl_file,
    gcode_output
)
