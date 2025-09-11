import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
import pyvista as pv
import subprocess
import sys

from pathlib import Path
from stl_utils import unwrap_and_repair_stl
from slicer_utils import slice_stl_with_prusaslicer
from gcode_utils import modify_gcode
from stl_editor import STLEditor
from gcode_visualiser import parse_cylindrical_gcode, plot_gcode_plotly


def browse_and_view_gcode():
    file_path = filedialog.askopenfilename(
        filetypes=[("G-code files", "*.gcode"), ("All files", "*.*")],
        title="Select a G-code file"
    )
    if not file_path:
        return

    try:
        moves = parse_cylindrical_gcode(file_path)
        plot_gcode_plotly(moves)
    except Exception as e:
        messagebox.showerror("G-code Viewer Error", f"Failed to view G-code:\n{e}")

# Define keys and their labels
PARAM_KEYS = {
    "temperature": "Nozzle Temperature (C)",
    "bed_temperature": "Bed Temperature (C)",
    "perimeter_speed": "Print Speed (mm/s)",
    "layer_height": "Layer Height (mm)",
    "fan_always_on": "Cooling Fan Always On (1/0)",
    "retract_length": "Retraction Length (mm)",
    "retract_speed": "Retraction Speed (mm/s)",
    "fill_density": "Infill Density (%)",
    "first_layer_height": "First Layer Height (mm)",
    "extrusion_multiplier": "Extrusion Multiplier"
}

REVERSE_KEYS = {v: k for k, v in PARAM_KEYS.items()}

entries = {}

def update_prusa_config(json_path, ini_path, output_path=None):
    import json

    EXCLUDE_KEYS = {"stl_file","ini_file", "bed_radius"}

    with open(json_path, 'r') as f:
        new_params = json.load(f)

    with open(ini_path, 'r') as f:
        lines = f.readlines()

    updated_config = {}
    for line in lines:
        if '=' in line and not line.strip().startswith('#'):
            key, value = line.split('=', 1)
            updated_config[key.strip()] = value.strip()

    # Update only relevant keys
    for key, new_value in new_params.items():
        if key in EXCLUDE_KEYS:
            continue
        updated_config[key] = str(new_value)

    updated_lines = [f"{key} = {value}\n" for key, value in updated_config.items()]

    if not output_path:
        output_path = ini_path

    with open(output_path, 'w') as f:
        f.writelines(updated_lines)

    print(f"Config updated and saved to: {output_path}")


def browse_ini():
    path = filedialog.askopenfilename(
        filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
        title="Select a config.ini file"
    )
    if path:
        ini_path_var.set(path)
        load_config_into_fields(path)

def load_config_into_fields(path):
    try:
        with open(path, 'r') as f:
            lines = f.readlines()

        config_dict = {}
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                config_dict[key.strip()] = value.strip()

        for param_key, label in PARAM_KEYS.items():
            if param_key in config_dict:
                entries[label].delete(0, tk.END)
                entries[label].insert(0, config_dict[param_key])

    except Exception as e:
        messagebox.showerror("Error", f"Failed to read config file:\n{e}")
def slice_and_process():
    try:
        # Step 1: Save parameters first
        save_parameters()

        # Step 2: Load parameters
        base_dir = Path(__file__).resolve().parent
        user_params_path = base_dir / "user_parameters.json"
        with open(user_params_path, 'r') as f:
            params = json.load(f)

        stl_path = Path(params["stl_file"])
        bed_radius = float(params["bed_radius"])

        stl_name = stl_path.stem.lower().replace(" ", "_")
        stl_dir = base_dir / "stl"
        gcode_dir = base_dir / "gcode"
        temp_dir = base_dir / "temp"
        config_path = Path(params["ini_file"])
        prusaslicer_path = Path(r"C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer.exe")

        unwrapped_stl = stl_dir / f"unwrapped_{stl_name}.stl"
        raw_gcode = gcode_dir / f"unwrapped_{stl_name}.gcode"
        updated_gcode = gcode_dir / f"{stl_name}_updated.gcode"

        gcode_dir.mkdir(exist_ok=True)
        temp_dir.mkdir(exist_ok=True)

        # Step 3: Run the slicing pipeline
        unwrap_and_repair_stl(stl_path, unwrapped_stl, debug_temp_path=temp_dir)
        update_prusa_config(user_params_path, config_path)
        slice_stl_with_prusaslicer(prusaslicer_path, config_path, unwrapped_stl, raw_gcode)
        modify_gcode(raw_gcode, updated_gcode, radius=bed_radius)

        from tkinter import messagebox
        messagebox.showinfo("Success", f"Slicing complete!\nOutput: {updated_gcode}")

    except Exception as e:
        from tkinter import messagebox
        messagebox.showerror("Slicing Error", f"An error occurred during slicing:\n{e}")

def preview_stl(file_path):
    try:
        

        mesh = pv.read(file_path)
        plotter = pv.Plotter(title="STL Preview")
        plotter.add_mesh(mesh, color="lightgray", show_edges=True)
        plotter.show()
    except Exception as e:
        messagebox.showerror("STL Preview Error", f"Could not render STL:\n{e}")


def browse_stl():
    file_path = filedialog.askopenfilename(
        filetypes=[("STL files", "*.stl")],
        title="Select an STL file"
    )
    if file_path:
        stl_var.set(file_path)
        preview_button["state"] = "normal"


def save_parameters():
    try:
        params = {
            "stl_file": stl_var.get(),
            "ini_file" : ini_path_var.get(),
            "bed_radius": float(entries["Bed Radius (mm)"].get())
        }

        for label, entry in entries.items():
            key = REVERSE_KEYS.get(label)
            if key:
                val = entry.get()
                if key in ["layer_height", "retract_length", "retract_speed", "extrusion_multiplier", "first_layer_height"]:
                    params[key] = float(val)
                elif key in ["temperature", "bed_temperature", "perimeter_speed", "fan_always_on"]:
                    params[key] = int(val)
                else:
                    params[key] = val

        with open("user_parameters.json", "w") as f:
            json.dump(params, f, indent=4)

        messagebox.showinfo("Success", "Parameters saved to 'user_parameters.json'")
    except Exception as e:
        messagebox.showerror("Error", f"Could not save parameters:\n{e}")


def on_stl_saved(new_path):
    stl_var.set(new_path)
    messagebox.showinfo("STL Saved", f"STL saved and updated:\n{new_path}")

def launch_stl_editor():
    stl_file = stl_var.get()
    if not stl_file:
        messagebox.showerror("No STL File", "Please select an STL file first.")
        return

    try:
        subprocess.Popen([sys.executable, "-m", "stl_editor_launcher", stl_file])
    except Exception as e:
        messagebox.showerror("STL Editor Error", f"Failed to launch editor:\n{e}")


# GUI Setup
root = tk.Tk()
root.title("3D Printing Parameters")

stl_var = tk.StringVar()
ini_path_var = tk.StringVar()
# Load INI Section
tk.Label(root, text="Config INI File:").grid(row=0, column=0, sticky="e")
ini_entry = tk.Entry(root, textvariable=ini_path_var, width=50)
ini_entry.grid(row=0, column=1)
tk.Button(root, text="Browse", command=browse_ini).grid(row=0, column=2, padx=5)

# Parameter Input Fields
start_row = 1
for i, label in enumerate(PARAM_KEYS.values()):
    tk.Label(root, text=label).grid(row=start_row + i, column=0, sticky="e")
    entry = tk.Entry(root)
    entry.grid(row=start_row + i, column=1)
    entries[label] = entry

# STL File Picker
tk.Label(root, text="STL File").grid(row=start_row + len(PARAM_KEYS), column=0, sticky="e")
stl_entry = tk.Entry(root, textvariable=stl_var, width=40)
stl_entry.grid(row=start_row + len(PARAM_KEYS), column=1)
tk.Button(root, text="Browse", command=browse_stl).grid(row=start_row + len(PARAM_KEYS), column=2)

# Bed Radius Input
tk.Label(root, text="Bed Radius (mm)").grid(row=start_row + len(PARAM_KEYS) + 1, column=0, sticky="e")
bed_radius_entry = tk.Entry(root)
bed_radius_entry.grid(row=start_row + len(PARAM_KEYS) + 1, column=1)
entries["Bed Radius (mm)"] = bed_radius_entry

# Save Button and Slice Button
tk.Button(root, text="Save Parameters", command=save_parameters).grid(
    row=start_row + len(PARAM_KEYS) + 2, column=0, pady=10
)

tk.Button(root, text="Slice", command=slice_and_process).grid(
    row=start_row + len(PARAM_KEYS) + 2, column=1, pady=10
)
preview_button = tk.Button(root, text="Edit STL", state="disabled", command=launch_stl_editor)
preview_button.grid(row=start_row + len(PARAM_KEYS), column=3, padx=5)

tk.Button(root, text="View G-code", command=browse_and_view_gcode).grid(
    row=start_row + len(PARAM_KEYS) + 2, column=2, pady=10
)


root.mainloop()

def launch_gui():
    import tkinter as tk
    from tkinter import messagebox

    try:
        root = tk.Tk()
        root.title("3D Printing Parameters")
        globals()["root"] = root  # Make root accessible to others

        # Your GUI code continues from here (the one you already have)
        # Replace the previous `root = tk.Tk()` in your script with `root = globals()["root"]`
        # So this works nicely when launched from another script

        # [PASTE your GUI layout code here]

        root.mainloop()
    except Exception as e:
        messagebox.showerror("GUI Error", f"Failed to open GUI:\n{e}")

