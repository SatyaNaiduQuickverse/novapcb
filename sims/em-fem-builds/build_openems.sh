#!/usr/bin/env bash
# OpenEMS source build — userspace, with apt-installed prereqs.
# Build chain: fparser (apt) → CSXCAD → openEMS → python_openEMS wrapper
# Target install prefix: ~/local/openems/
set -euo pipefail

PREFIX=~/local/openems
SRC=~/local/src/em-fem-builds
JOBS=2

mkdir -p "$PREFIX" "$SRC"
cd "$SRC"

echo "[openems] cloning CSXCAD + openEMS"
[ -d CSXCAD ]  || git clone --depth 1 https://github.com/thliebig/CSXCAD.git
[ -d openEMS ] || git clone --depth 1 https://github.com/thliebig/openEMS.git

echo "[openems] building CSXCAD"
cd "$SRC/CSXCAD"
mkdir -p build && cd build
cmake -DCMAKE_INSTALL_PREFIX="$PREFIX" \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_RPATH="$PREFIX/lib" \
      ..
make -j$JOBS
make install

echo "[openems] building openEMS"
cd "$SRC/openEMS"
mkdir -p build && cd build
cmake -DCMAKE_INSTALL_PREFIX="$PREFIX" \
      -DCMAKE_BUILD_TYPE=Release \
      -DCSXCAD_ROOT_DIR="$PREFIX" \
      -DCMAKE_INSTALL_RPATH="$PREFIX/lib" \
      ..
make -j$JOBS
make install

echo "[openems] building python_openEMS wrapper"
cd "$SRC/openEMS/python"
# pip install via user site so we don't need root
LD_LIBRARY_PATH="$PREFIX/lib" CFLAGS="-I$PREFIX/include" \
LDFLAGS="-L$PREFIX/lib -Wl,-rpath,$PREFIX/lib" \
  pip install --user .

echo "[openems] DONE. Binaries at $PREFIX/bin"
ls -la "$PREFIX/bin" "$PREFIX/lib" | head -10
