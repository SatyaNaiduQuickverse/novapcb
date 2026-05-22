#!/usr/bin/env python3
"""Generate Elmer-native 2D mesh for the thermal validation.

100mm × 10mm rectangle, 100×10 quad elements, 4 distinct boundary tags.
ElmerGrid native `.grd` syntax does NOT generate boundary elements for a
single-body rectangle, so we hand-write `mesh.boundary` with 4 IDs:
  1 = bottom (y=0), 2 = right (x=100), 3 = top (y=10), 4 = left (x=0)
"""
import os
NX, NY = 100, 10
LX, LY = 100.0, 10.0
OUT = os.path.join(os.path.dirname(__file__), "mesh2")
os.makedirs(OUT, exist_ok=True)
nx, ny = NX+1, NY+1
n_nodes = nx * ny

with open(f"{OUT}/mesh.nodes", "w") as f:
    for j in range(ny):
        for i in range(nx):
            f.write(f"{j*nx + i + 1} -1 {i*LX/NX:.6f} {j*LY/NY:.6f} 0.0\n")

with open(f"{OUT}/mesh.elements", "w") as f:
    eid = 1
    for j in range(NY):
        for i in range(NX):
            n00 = j*nx + i + 1; n10 = j*nx + (i+1) + 1
            n11 = (j+1)*nx + (i+1) + 1; n01 = (j+1)*nx + i + 1
            f.write(f"{eid} 1 404 {n00} {n10} {n11} {n01}\n"); eid += 1

bnd, bid = [], 1
for i in range(NX):
    bnd.append(f"{bid} 1 {i + 1} 0 202 {i + 1} {i + 2}"); bid += 1
for j in range(NY):
    bnd.append(f"{bid} 2 {j*NX + NX} 0 202 {j*nx + NX + 1} {(j+1)*nx + NX + 1}"); bid += 1
for i in range(NX):
    bnd.append(f"{bid} 3 {(NY-1)*NX + i + 1} 0 202 {NY*nx + i + 1} {NY*nx + i + 2}"); bid += 1
for j in range(NY):
    bnd.append(f"{bid} 4 {j*NX + 1} 0 202 {j*nx + 1} {(j+1)*nx + 1}"); bid += 1

with open(f"{OUT}/mesh.boundary", "w") as f:
    for line in bnd: f.write(line + "\n")
with open(f"{OUT}/mesh.header", "w") as f:
    f.write(f"{n_nodes} {NX*NY} {len(bnd)}\n2\n202 {len(bnd)}\n404 {NX*NY}\n")
print(f"Wrote {OUT}: {n_nodes} nodes, {NX*NY} quads, {len(bnd)} bnd edges")
