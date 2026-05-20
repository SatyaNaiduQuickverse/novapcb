"""
novapcb SKiDL common setup — KiCad 9 default, library paths, helpers.

Every sheet module imports `setup()` and calls it once before declaring parts.
The top-level generate.py also calls setup() before importing sheet modules.
"""

import os
import skidl


def setup():
    """Configure SKiDL for KiCad 9 + /usr/share/kicad/symbols/."""
    skidl.set_default_tool(skidl.KICAD9)
    syms = "/usr/share/kicad/symbols"
    if syms not in skidl.lib_search_paths["kicad9"]:
        skidl.lib_search_paths["kicad9"].append(syms)
    # Suppress the KICAD*_SYMBOL_DIR env warnings — we set the path explicitly.
    os.environ.setdefault("KICAD9_SYMBOL_DIR", syms)


# Footprint shorthand strings reused across sheets. Centralized so a
# package-family change updates everywhere at once.
FP_R_0402 = "Resistor_SMD:R_0402_1005Metric"
FP_C_0402 = "Capacitor_SMD:C_0402_1005Metric"
FP_C_0805 = "Capacitor_SMD:C_0805_2012Metric"  # bulk
FP_FB_0402 = "Inductor_SMD:L_0402_1005Metric"  # ferrite bead shares 0402 footprint
FP_XTAL_3225 = "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm"  # 8 MHz HSE
