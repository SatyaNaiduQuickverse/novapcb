#!/usr/bin/env bash
# Elmer FEM source build (ElmerSolver minimal for thermal/electrostatic).
# Uses apt-installed libmumps-dev + libmetis-dev + libsuitesparse-dev +
# libopenmpi-dev + libscalapack-mpi-dev. We skip ElmerGUI (no Qt
# dependency needed for headless FEA) — ElmerSolver alone is sufficient.
# Target install prefix: ~/local/elmer/
set -euo pipefail

PREFIX=~/local/elmer
SRC=~/local/src/em-fem-builds
JOBS=2

mkdir -p "$PREFIX" "$SRC"
cd "$SRC"

echo "[elmer] cloning elmerfem"
[ -d elmerfem ] || git clone --depth 1 https://github.com/ElmerCSC/elmerfem.git

cd "$SRC/elmerfem"
mkdir -p build && cd build

# Headless minimal — ElmerSolver + ElmerGrid (mesh tools) only. NO Qt/ElmerGUI.
cmake \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_BUILD_TYPE=Release \
  -DWITH_MPI=ON \
  -DWITH_OpenMP=ON \
  -DWITH_LUA=OFF \
  -DWITH_ElmerIce=OFF \
  -DWITH_Mumps=OFF \
  -DWITH_Hypre=OFF \
  -DWITH_Trilinos=OFF \
  -DWITH_NETCDF=OFF \
  -DWITH_GridDataReader=ON \
  -DWITH_ScatteredDataInterpolator=OFF \
  -DWITH_ELMERGUI=OFF \
  -DWITH_QWT=OFF \
  -DCMAKE_INSTALL_RPATH="$PREFIX/lib" \
  ..

make -j$JOBS
make install

echo "[elmer] DONE. Binaries at $PREFIX/bin"
ls -la "$PREFIX/bin" 2>/dev/null | head -10
