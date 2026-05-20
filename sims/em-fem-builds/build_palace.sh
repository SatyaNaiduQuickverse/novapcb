#!/usr/bin/env bash
# Palace source build (AWS Labs Palace — 3D FEM EM solver).
# Uses apt-installed libmfem-dev + libmumps-dev + libsuitesparse-dev + libmetis-dev +
# libpetsc-real-dev + libslepc-real-dev + libscalapack-mpi-dev + libopenmpi-dev +
# libnlopt-dev — Palace's CMake build auto-detects these.
# Target install prefix: ~/local/palace/
set -euo pipefail

PREFIX=~/local/palace
SRC=~/local/src/em-fem-builds
JOBS=2

mkdir -p "$PREFIX" "$SRC"
cd "$SRC"

echo "[palace] cloning Palace"
[ -d palace ] || git clone --depth 1 https://github.com/awslabs/palace.git

cd "$SRC/palace"
# Use the CMake "superbuild" but tell it to use system MFEM + system MUMPS + system METIS
# + system PETSc + system SuiteSparse instead of downloading + building its own.
mkdir -p build && cd build

cmake \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=ON \
  -DPALACE_BUILD_EXTERNAL_DEPS=OFF \
  -DPALACE_WITH_MFEM=ON -DMFEM_DIR=/usr/lib/aarch64-linux-gnu/cmake/MFEM \
  -DPALACE_WITH_MUMPS=ON \
  -DPALACE_WITH_SUITESPARSE=ON \
  -DPALACE_WITH_METIS=ON \
  -DPALACE_WITH_SCALAPACK=ON \
  -DPALACE_WITH_OPENMP=ON \
  -DCMAKE_INSTALL_RPATH="$PREFIX/lib" \
  ..

make -j$JOBS
make install

echo "[palace] DONE. Binary at $PREFIX/bin/palace"
ls -la "$PREFIX/bin" 2>/dev/null | head -5
