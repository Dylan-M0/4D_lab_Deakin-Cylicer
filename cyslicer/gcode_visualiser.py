import re
import math
import plotly.graph_objects as go

g1_re = re.compile(r'G1\b')
coord_re = re.compile(r'([BYZE])(-?\d+\.?\d*)')


# Assumed regex patterns
g1_re = re.compile(r'^\s*G1\b')  # Match lines starting with G1
coord_re = re.compile(r'([BYZE])([-+]?[0-9]*\.?[0-9]+)')  # Extract B, Y, Z, E values

def parse_cylindrical_gcode(file_path):
    moves = []
    B = Y = Z = E = 0.0

    with open(file_path, 'r') as f:
        for line in f:
            if not g1_re.match(line):
                continue
            if ';' in line:
                line = line.split(';')[0]

            parts = dict(coord_re.findall(line))
            prev_B, prev_Y, prev_Z, prev_E = B, Y, Z, E
            B = float(parts.get('B', B))
            Y = float(parts.get('Y', Y))
            Z = float(parts.get('Z', Z))
            E = float(parts.get('E', E))

            # Determine number of steps if B changes significantly
            delta_B = B - prev_B
            steps = max(1, int(abs(delta_B) / 3.0))
            
            for step in range(1, steps + 1):
                # Interpolated parameters
                interp_B = prev_B + (delta_B * step / steps)
                interp_theta = math.radians(interp_B)

                # Linear interpolation for Z, Y, and E
                interp_Z = prev_Z + (Z - prev_Z) * step / steps
                interp_Y = prev_Y + (Y - prev_Y) * step / steps
                interp_E = prev_E + (E - prev_E) * step / steps

                # Previous step (either actual prev or last interpolated)
                if step == 1:
                    prev_theta = math.radians(prev_B)
                    prev_r = prev_Z
                    prev_y = prev_Y
                else:
                    prev_theta = math.radians(prev_B + (delta_B * (step - 1) / steps))
                    prev_r = prev_Z + (Z - prev_Z) * (step - 1) / steps
                    prev_y = prev_Y + (Y - prev_Y) * (step - 1) / steps

                x0 = prev_r * math.cos(prev_theta)
                z0 = prev_r * math.sin(prev_theta)
                y0 = prev_y

                x1 = interp_Z * math.cos(interp_theta)
                z1 = interp_Z * math.sin(interp_theta)
                y1 = interp_Y

                extruding = interp_E > prev_E + (E - prev_E) * (step - 1) / steps
                moves.append(((x0, y0, z0), (x1, y1, z1), extruding))

    return moves


def plot_gcode_plotly(moves):
    lines_extrude = {'x': [], 'y': [], 'z': []}
    lines_travel = {'x': [], 'y': [], 'z': []}

    for start, end, extruding in moves:
        target = lines_extrude if extruding else lines_travel
        for coord in [start, end]:
            target['x'].append(coord[0])
            target['y'].append(coord[1])
            target['z'].append(coord[2])
        for k in target:
            target[k].append(None)  # separate lines

    # Axis scaling
    all_coords = [c for c in zip(lines_extrude['x'] + lines_travel['x'],
                                 lines_extrude['y'] + lines_travel['y'],
                                 lines_extrude['z'] + lines_travel['z']) if None not in c]
    if not all_coords:
        return

    xs, ys, zs = zip(*all_coords)
    center = [(max(v) + min(v)) / 2 for v in (xs, ys, zs)]
    max_range = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) / 2

    layout = go.Layout(
        title="G-code Viewer (Plotly)",
        scene=dict(
            xaxis=dict(range=[center[0] - max_range, center[0] + max_range], title="X"),
            yaxis=dict(range=[center[1] - max_range, center[1] + max_range], title="Y"),
            zaxis=dict(range=[center[2] - max_range, center[2] + max_range], title="Z"),
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=1)
        )
    )

    fig = go.Figure(layout=layout)

    fig.add_trace(go.Scatter3d(
        x=lines_extrude['x'], y=lines_extrude['y'], z=lines_extrude['z'],
        mode='lines', name='Extruding',
        line=dict(color='red', width=2)
    ))

    fig.add_trace(go.Scatter3d(
        x=lines_travel['x'], y=lines_travel['y'], z=lines_travel['z'],
        mode='lines', name='Travel',
        line=dict(color='gray', width=1)
    ))

    fig.show()
