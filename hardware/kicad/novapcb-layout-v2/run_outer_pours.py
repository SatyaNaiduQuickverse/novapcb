#!/usr/bin/env python3
"""Add F.Cu + B.Cu GND copper pours per master 2026-05-21 root-cause fix.

Pours flood unused outer-layer area, net=GND. USB_DM/USB_DP get a
clearance keepout (we add a rule_area / keepout zone over the USB
corridor) so the pair stays a microstrip and 94.4Ω geometry holds.

Adapted from run_planes.py (uses S-expr injection due to KiCad 9 SWIG
zone segfault).
"""
import os, re, uuid
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")

# Board outline: 0,0 to 80,60 mm (80×60 board)
BOARD_X0, BOARD_Y0 = 0.0, 0.0
BOARD_X1, BOARD_Y1 = 80.0, 60.0
EDGE_KEEPIN_MM = 0.30

# USB diff-pair keepout zone — covers the corridor where USB_DM/USB_DP
# routes on F.Cu near U5→U1 (~X=47..52, Y=24..50)
USB_KEEPOUT = (46.5, 22.5, 53.5, 50.5)  # x0,y0,x1,y1


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
        # GND pour zone with USB-pair-vicinity clearance bumped by per-net rule
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
    # USB keepout zone — F.Cu only (USB pair on F.Cu+B.Cu, but the
    # microstrip impedance is defined by L1↔L2 reference which holds at
    # F.Cu; we keep B.Cu pour cleared too for symmetric stripline ref)
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
