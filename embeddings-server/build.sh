#!/usr/bin/env bash
# embeddings-server をビルドする。出力は build/embeddings-server（llama.cpp を静的に含む 1 ファイル）。
#
#   LLAMA_SRC  llama.cpp のチェックアウト（既定 ~/projects/llama.cpp-src）
#   CLAY_ROOT  clay のチェックアウト（既定 ~/projects/clay）
#
# - run-server を使う clay アプリは `clay build` ではなく clay の build.sh + -DCLAY_SERVER=threaded で
#   ビルドする（サーバの実装がコンパイル時に選ばれるため。zeta の build-server-app.sh と同じ）。
# - llama.cpp は build-llama/ に静的ライブラリとしてビルドし（CPU + Vulkan、-DGGML_NATIVE=ON）、実行ファイルに
#   焼き込む。llama.cpp-src 側を作り直しても、動いているサーバが別の版の .so を掴むことはない。
#   llama.cpp を更新したときは build-llama/ を消してから実行する。
# - Vulkan のドライバ（Mesa RADV）は実行時に libvulkan から読まれる。/etc/ld.so.conf.d/20-amdgpu.conf
#   （ROCm の amdgpu-install が置く）が /opt/amdgpu の古い libdrm_amdgpu を先に見せていて、RADV がそれを
#   掴むと VK_ERROR_INITIALIZATION_FAILED で GPU が見えなくなる。そのため実行ファイルに
#   DT_RPATH（--disable-new-dtags。RUNPATH と違って間接的に読まれるライブラリにも効く）で
#   /usr/lib/x86_64-linux-gnu を持たせ、システムの libdrm を先に見つけさせる。
# - embshim.h は -include で渡す。clay の (c-include ..) は "..." 形式のローカルヘッダを扱えず、
#   (c/..) の型調べも -I なしで走るので、宣言は defextern + 強制 include にしている。
set -euo pipefail
cd "$(dirname "$0")"
HERE=$PWD
LLAMA_SRC=${LLAMA_SRC:-$HOME/projects/llama.cpp-src}
CLAY_ROOT=${CLAY_ROOT:-$HOME/projects/clay}

if [ ! -f build-llama/src/libllama.a ] || [ ! -f build-llama/ggml/src/ggml-vulkan/libggml-vulkan.a ]; then
  cmake -S "$LLAMA_SRC" -B build-llama -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=ON \
        -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_TOOLS=OFF -DLLAMA_BUILD_SERVER=OFF \
        -DLLAMA_CURL=OFF -DGGML_OPENMP=ON -DGGML_VULKAN=ON
  cmake --build build-llama --target llama -j "$(nproc)"
fi

rm -rf build
mkdir -p build

clang -O2 -Wall -c -I"$LLAMA_SRC/include" -I"$LLAMA_SRC/ggml/include" embshim.c -o build/embshim.o

LL=$HERE/build-llama
EXTRA_CFLAGS="-DCLAY_SERVER=threaded -lpthread -include $HERE/embshim.h $HERE/build/embshim.o \
  $LL/src/libllama.a $LL/ggml/src/libggml.a $LL/ggml/src/libggml-cpu.a $LL/ggml/src/ggml-vulkan/libggml-vulkan.a \
  $LL/ggml/src/libggml-base.a -lvulkan -lstdc++ -lgomp -Wl,--disable-new-dtags,-rpath,/usr/lib/x86_64-linux-gnu" \
  bash "$CLAY_ROOT/build.sh" emb/server.clay -o build/embeddings-server
echo "built: $HERE/build/embeddings-server (llama.cpp $(git -C "$LLAMA_SRC" rev-parse --short HEAD 2>/dev/null || echo '?'))"
