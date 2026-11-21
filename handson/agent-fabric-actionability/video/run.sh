#!/bin/sh
# 使い方: ./run.sh [start <lab> | stop]   または   ./run.sh <<'JS' ... JS  (標準入力の JS を実行する)
case "$1" in
  start) curl -s -X POST "http://127.0.0.1:9334/start?lab=$2"; echo; exit;;
  stop)  curl -s -X POST http://127.0.0.1:9334/stop; echo; exit;;
esac
curl -s --max-time ${T:-300} -X POST --data-binary @- http://127.0.0.1:9334/run
echo
