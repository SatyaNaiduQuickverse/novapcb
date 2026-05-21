"""
novapcb SKiDL common setup — KiCad 9 default, library paths, helpers.

Every sheet module imports `setup()` and calls it once before declaring parts.
The top-level generate.py also calls setup() before importing sheet modules.
"""

import os
import skidl


def _virtual_part_footprint_handler(part):
    """SKiDL's default empty-footprint handler errors when a Part has no footprint.
    PWR_FLAG (and similar netlist-only virtual symbols) intentionally have no
    physical footprint; silently accept them. Real parts with empty footprints
    still error — fall through to default behavior.

    See hardware/kicad/KICAD9_NOTES.md SKiDL gotchas section for context.
    """
    if getattr(part, "name", "") == "PWR_FLAG":
        return  # netlist-only virtual symbol; no PCB footprint by design
    # Default: error (preserves the "real part missing footprint" check)
    from skidl.logger import active_logger
    active_logger.raise_(
        ValueError,
        f"No footprint for {part.name}/{part.ref} added at "
        f"{getattr(part, 'creation_loc', '?')}."
    )


def setup():
    """Configure SKiDL for KiCad 9 + /usr/share/kicad/symbols/ + PWR_FLAG handler."""
    skidl.set_default_tool(skidl.KICAD9)
    syms = "/usr/share/kicad/symbols"
    if syms not in skidl.lib_search_paths["kicad9"]:
        skidl.lib_search_paths["kicad9"].append(syms)
    # Local project library (easyeda2kicad-pulled parts: BMI088 C194919,
    # LSM6DSV16XTR C5267406). Added v1.1 redundancy re-spin 2026-05-21
    # per master directive — verified-symbol path over training-data guesses.
    local_lib = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
    if local_lib not in skidl.lib_search_paths["kicad9"]:
        skidl.lib_search_paths["kicad9"].append(local_lib)
    # Suppress the KICAD*_SYMBOL_DIR env warnings — we set the path explicitly.
    os.environ.setdefault("KICAD9_SYMBOL_DIR", syms)
    # Override SKiDL's empty-footprint handler so PWR_FLAGs don't error.
    skidl.empty_footprint_handler = _virtual_part_footprint_handler


def n(name):
    """Singleton-net fetcher — returns the shared Net for `name`.

    Multiple sheets call this for the same rail (e.g. '+3V3'); they all get
    the SAME Net instance. Without this, `Net('+3V3')` in mcu_3a + `Net('+3V3')`
    in power_3b create TWO different nets ('+3V3' and '+3V3_1') with the same
    intended name but no electrical connection — silent topology bug.

    `Net.fetch()` is SKiDL's official lookup-or-create-by-name API.
    See `hardware/kicad/KICAD9_NOTES.md` (Phase 3b lesson).
    """
    return skidl.Net.fetch(name)


# Footprint shorthand strings reused across sheets. Centralized so a
# package-family change updates everywhere at once.
FP_R_0402 = "Resistor_SMD:R_0402_1005Metric"
FP_C_0402 = "Capacitor_SMD:C_0402_1005Metric"
FP_C_0805 = "Capacitor_SMD:C_0805_2012Metric"  # bulk
FP_FB_0402 = "Inductor_SMD:L_0402_1005Metric"  # ferrite bead shares 0402 footprint
FP_XTAL_3225 = "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm"  # 8 MHz HSE
