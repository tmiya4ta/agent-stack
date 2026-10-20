# aisearch-server のイメージ (k0 の ai-search.azure.emu)。実行ファイルは手元で build.sh が作る (clay はイメージに入れない)。
# 手元 (Debian sid、glibc 2.43) でビルドした実行ファイルを、同じ sid の slim で動かす。要るのは OpenSSL 3、zlib、zstd (と tini)。
FROM debian:sid-slim
RUN apt-get update && apt-get install -y --no-install-recommends libssl3t64 zlib1g libzstd1 ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*
COPY build/aisearch-server /usr/local/bin/aisearch-server
USER 65534:65534
EXPOSE 8080
# tini を PID 1 にする。Clay のサーバーが PID 1 だと SIGTERM を受けず、Pod の入れ替えで 30 秒待たされる
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/aisearch-server"]
