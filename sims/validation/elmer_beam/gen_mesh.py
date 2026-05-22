#!/usr/bin/env python3
"""Cantilever beam mesh for Elmer structural validation.

Refined NX=200, NY=20 (4000 Q1 quads) to defeat shear-locking on bending.
Geometry: L=1.0m × h=0.05m, b=0.01m thickness (plane stress).
Boundaries: 1=bottom, 2=right (tip load), 3=top, 4=left (clamped).
"""
import os
NX, NY = 200, 20
LX, LY = 1.0, 0.05
OUT = os.path.join(os.path.dirname(__file__), "mesh")
os.makedirs(OUT, exist_ok=True)
nx, ny = NX+1, NY+1
n_nodes = nx * ny

with open(f"{OUT}/mesh.nodes", "w") as f:
    for j in range(ny):
        for i in range(nx):
            f.write(f"{j*nx + i + 1} -1 {i*LX/NX:.8f} {j*LY/NY:.8f} 0.0\n")

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
