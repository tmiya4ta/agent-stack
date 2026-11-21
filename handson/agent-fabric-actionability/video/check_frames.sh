#!/bin/sh
# 仕上げた Lab ごとの動画 (out/final/*.mp4) から 2 秒ごとにコマを取り、Windows の OCR で kurita などの文字が写っていないか調べる
# ディスクを食わないよう、1 本ずつ取り出して調べたら消す
# 使い方: ./check_frames.sh <ffmpeg.exe> [パターン]
FF="$1"; PAT="${2:-kurita|Kurita}"
HERE="$(cd "$(dirname "$0")" && pwd)"
sed "s/kurita|kur1ta|Kurita/$PAT/" "$HERE/ocr.ps1" > "$HERE/out/ocr-run.ps1"
for v in "$HERE"/out/final/*.mp4; do
  case "$(basename "$v")" in actionability-*) continue;; esac  # Lab の動画をつないだだけなので調べない
  d="$HERE/out/frames"; rm -rf "$d"; mkdir -p "$d"
  "$FF" -loglevel error -i "$v" -vf fps=0.5 "$d/%04d.png"
  powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$HERE/out/ocr-run.ps1")" -dir "$(cygpath -w "$d")" 2>&1 | grep HIT | sed "s|^|$(basename "$v") |"
  rm -rf "$d"
done
echo checked
