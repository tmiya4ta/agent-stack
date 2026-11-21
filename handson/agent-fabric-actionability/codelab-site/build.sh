#!/bin/sh
# codelab/actionability.md から HTML を作り直して src/main/resources/web に置く
set -e
cd "$(dirname "$0")"
rm -rf src/main/resources/web
node "${CODELAB_GEN:-$HOME/demos/codelab-generator/dist/codelab.js}" ../codelab/actionability.md -f html -o src/main/resources/web
