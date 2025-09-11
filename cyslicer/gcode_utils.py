import re
import math
from pathlib import Path

def modify_gcode(input_path, output_path, radius=20.0):
    with open(input_path, 'r') as f:
        lines = f.readlines()

    MINX, MINY = float('inf'), float('inf')
    MAX_X = -1
    for line in lines:
        if line.startswith('G1') and 'X' in line and 'Y' in line:
            x_match = re.search(r'X([-+]?[0-9]*\.?[0-9]+)', line)
            y_match = re.search(r'Y([-+]?[0-9]*\.?[0-9]+)', line)
            if x_match: MINX = min(MINX, float(x_match.group(1)))
            if x_match: MAX_X = max(MAX_X, float(x_match.group(1)))
            if y_match: MINY = min(MINY, float(y_match.group(1)))
    #print(f"min of x is : {MINX}")
    #print(f"max of x is : {MAX_X}")
    
    transform_active = False
    updated_lines = []
    layer_h = 0.2
    z_val = radius + layer_h
    #print(f"first z_val is: {z_val}")
    new_line = f"G0 X0 Y0 Z{radius:.3f} ; updated Z by +100\n"
    updated_lines.append(new_line)
    for line in lines:
        stripped = line.strip()

        if re.search(r'\b(M140|G28|M190)\b', stripped, re.IGNORECASE):
            updated_lines.append(';' + line if not line.startswith(';') else line)
            continue

        if re.search(r'lift nozzle', stripped, re.IGNORECASE):
            updated_lines.append(';' + line)
            z_match = re.search(r'\bZ([-+]?[0-9]*\.?[0-9]+)', line)
            if z_match:
                z_val = float(z_match.group(1)) + 100
                new_line = f"G0 X0 Y0 Z{z_val:.3f} ; updated Z by +100\n"
                updated_lines.append(new_line)
            continue

        if 'Wait for Hotend Temperature' in stripped:
            updated_lines.append(line)
            updated_lines.append("G0 X0 Y0 F3000\n")
            continue

        if ';LAYER_CHANGE' in stripped:
            transform_active = True

        if transform_active and line.startswith(('G0', 'G1')):
            cmd = line[:2].strip()
            x = re.search(r'X([-+]?[0-9]*\.?[0-9]+)', line)
            y = re.search(r'Y([-+]?[0-9]*\.?[0-9]+)', line)
            z = re.search(r'Z([-+]?[0-9]*\.?[0-9]+)', line)
            f = re.search(r'F([-+]?[0-9]*\.?[0-9]+)', line)
            e = re.search(r'E([-+]?[0-9]*\.?[0-9]+)', line)

            parts = [cmd]
            if f: parts.append(f"F{f.group(1)}")
            if x:
                b_val = ((float(x.group(1)) - MINX) / ((z_val + radius) * 2 * math.pi-1.6)) * 360
                parts.append(f"B{b_val:.5f}")
            if y:
                parts.append(f"Y{float(y.group(1)) - MINY:.5f}")
            if z:
                z_val = float(z.group(1))
                parts.append(f"Z{z_val + radius:.5f}")
            if e: parts.append(f"E{e.group(1)}")

            updated_lines.append(" ".join(parts) + "\n")
        else:
            updated_lines.append(line)

    with open(output_path, 'w') as f:
        f.writelines(updated_lines)

    print(f"Modified G-code saved to: {output_path}")
