#!/usr/bin/env bash
# chat-server をビルドする。出力は build/chat-server（llama.cpp を静的に含む 1 ファイル）。
#
#   LLAMA_SRC    llama.cpp のチェックアウト（既定 ~/projects/llama.cpp-src）
#   LLAMA_BUILD  llama.cpp の静的ビルド（既定 ../embeddings-server/build-llama を共用。無ければここで作る）
#   CLAY_ROOT    clay のチェックアウト（既定 ~/projects/clay）
#
# 作りは embeddings-server/build.sh と同じ（そちらのコメントも参照）:
# - run-server を使い、C の .o と .a をリンクするので、clay の build.sh + EXTRA_CFLAGS でビルドする
# - chatshim.h は -include で渡し、宣言は defextern で書く
# - RPATH /usr/lib/x86_64-linux-gnu は、ROCm の古い libdrm を Mesa RADV が掴まないための保険
set -euo pipefail
cd "$(dirname "$0")"
HERE=$PWD
LLAMA_SRC=${LLAMA_SRC:-$HOME/projects/llama.cpp-src}
LL=${LLAMA_BUILD:-$HERE/../embeddings-server/build-llama}
CLAY_ROOT=${CLAY_ROOT:-$HOME/projects/clay}

if [ ! -f "$LL/src/libllama.a" ] || [ ! -f "$LL/ggml/src/ggml-vulkan/libggml-vulkan.a" ]; then
  cmake -S "$LLAMA_SRC" -B "$LL" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=ON \
        -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_TOOLS=OFF -DLLAMA_BUILD_SERVER=OFF \
        -DLLAMA_CURL=OFF -DGGML_OPENMP=ON -DGGML_VULKAN=ON
  cmake --build "$LL" --target llama -j "$(nproc)"
fi

rm -rf build
mkdir -p build
clang -O2 -Wall -c -I"$LLAMA_SRC/include" -I"$LLAMA_SRC/ggml/include" chatshim.c -o build/chatshim.o

EXTRA_CFLAGS="-DCLAY_SERVER=threaded -lpthread -include $HERE/chatshim.h $HERE/build/chatshim.o \
  $LL/src/libllama.a $LL/ggml/src/libggml.a $LL/ggml/src/libggml-cpu.a $LL/ggml/src/ggml-vulkan/libggml-vulkan.a \
  $LL/ggml/src/libggml-base.a -lvulkan -lstdc++ -lgomp -Wl,--disable-new-dtags,-rpath,/usr/lib/x86_64-linux-gnu" \
  bash "$CLAY_ROOT/build.sh" chat/server.clay -o build/chat-server
echo "built: $HERE/build/chat-server (llama.cpp $(git -C "$LLAMA_SRC" rev-parse --short HEAD 2>/dev/null || echo '?'))"
