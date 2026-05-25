#!/usr/bin/env python3
"""
R4-PREP step 2: add F.Cu + B.Cu GND copper pours per master directive.

Carries forward the v1.0 layout-v2 pattern (`run_outer_pours.py`):
  - GND pour on F.Cu over the full board (with USB diff-pair keepout)
  - GND pour on B.Cu over the full board (with USB diff-pair keepout)
  - USB diff-pair keepout: defines a rectangle on F.Cu+B.Cu where no
    copper pour fills (so the USB pair is a clean microstrip without
    a noisy GND fill underneath it crossing the diff-pair geometry)

Uses S-expr text injection (KiCad 9 SWIG segfaults when adding zones via
the pcbnew Python API — see v1.0 layout-v2 KICAD9_NOTES).

v1.1 USB pair location: USB-C J1 at (39.5, 65.85). USB_DM/USB_DP nets
route from J1 SMD pads (Y=61.8..62.53) south to MCU U1 PA11/PA12
(MCU center 41, 35). USB corridor is approximately X=37..43, Y=29..63.
"""

import os
import re
import uuid
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

BOARD_X0, BOARD_Y0 = 0.0, 0.0
BOARD_X1, BOARD_Y1 = 90.0, 70.0
EDGE_KEEPIN_MM = 0.30

# v1.1 USB-C J1 corridor: USB pads south of J1 (Y=61.8..62.53), trace
# south to MCU PA11/PA12 around (40, 35). Keepout corridor X=36.5..43.0
# (~6.5mm wide, covers both DM/DP traces with margin), Y=28..63.
USB_KEEPOUT = (36.5, 28.0, 43.0, 63.0)

# IMU island clean keepout: don't fill GND in the slot kerf area; the
# slot polygon on Edge.Cuts is what defines the milled area, but the
# zones shouldn't extend into the trace bundle bridge area either.
# Bridge gap on west side of island at X=62, Y=30..40 - keep GND pour
# RUNNING through here so the bridge traces have a return-path reference.


def main():
    brd = pcbnew.LoadBoard(PCB_PATH)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    gnd_code = nets["GND"].GetNetCode()
    print(f"GND net code: {gnd_code}")

    x0, y0 = BOARD_X0 + EDGE_KEEPIN_MM, BOARD_Y0 + EDGE_KEEPIN_MM
    x1, y1 = BOARD_X1 - EDGE_KEEPIN_MM, BOARD_Y1 - EDGE_KEEPIN_MM
    ux0, uy0, ux1, uy1 = USB_KEEPOUT

    with open(PCB_PATH) as f:
        content = f.read()

    zones = []
    for layer_name in ("F.Cu", "B.Cu"):
        zid = str(uuid.uuid4())
        zones.append(f"""	(zone
		(net {gnd_code})
		(net_name "GND")
		(layer "{layer_name}")
		(uuid "{zid}")
		(hatch edge 0.5)
		(connect_pads
			(clearance 0.3)
		)
		(min_thickness 0.20)
		(filled_areas_thickness no)
		(fill yes
			(thermal_gap 0.3)
			(thermal_bridge_width 0.3)
		)
		(polygon
			(pts
				(xy {x0:.4f} {y0:.4f}) (xy {x1:.4f} {y0:.4f}) (xy {x1:.4f} {y1:.4f}) (xy {x0:.4f} {y1:.4f})
			)
		)
	)
""")
    # USB keepout zones — F.Cu + B.Cu so USB-pair is microstrip with clean reference.
    for layer_name in ("F.Cu", "B.Cu"):
        kid = str(uuid.uuid4())
        zones.append(f"""	(zone
		(net 0)
		(net_name "")
		(layer "{layer_name}")
		(uuid "{kid}")
		(name "USB_keepout")
		(hatch edge 0.5)
		(connect_pads
			(clearance 0.0)
		)
		(min_thickness 0.20)
		(filled_areas_thickness no)
		(keepout
			(tracks allowed)
			(vias allowed)
			(pads allowed)
			(copperpour not_allowed)
			(footprints allowed)
		)
		(fill
			(thermal_gap 0.5)
			(thermal_bridge_width 0.5)
		)
		(polygon
			(pts
				(xy {ux0:.4f} {uy0:.4f}) (xy {ux1:.4f} {uy0:.4f}) (xy {ux1:.4f} {uy1:.4f}) (xy {ux0:.4f} {uy1:.4f})
			)
		)
	)
""")

    zones_text = "".join(zones)
    marker = "\t(embedded_fonts no)"
    idx = content.rfind(marker)
    if idx < 0:
        print("!! marker not found"); return
    new_content = content[:idx] + zones_text + content[idx:]
    with open(PCB_PATH, "w") as f:
        f.write(new_content)
    print(f"Added 2 GND pours (F.Cu, B.Cu) + 2 USB keepouts")


if __name__ == "__main__":
    main()
