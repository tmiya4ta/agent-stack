# max-oms のイメージ (マックス証券の注文。約定を Anypoint MQ に送る)。実行ファイルは build.sh が mulay build で作る
# (max/core を DataWeave ごとネイティブにした 1 つのファイル)。手元 (Debian sid) でビルドしたものを同じ sid の slim で動かす。
FROM debian:sid-slim
RUN apt-get update && apt-get install -y --no-install-recommends libssl3t64 zlib1g libzstd1 ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*
COPY build/max-oms /usr/local/bin/max-oms
USER 65534:65534
EXPOSE 8083
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/max-oms"]
