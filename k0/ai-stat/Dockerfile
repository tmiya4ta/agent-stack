# stat-models のイメージ (embed.hash512.stat と llm.tfidf.stat)。実行ファイルは build.sh が mulay build で作る
# (mulay の templates/stat-models を、DataWeave ごとネイティブにした 1 つのファイル。JVM も mulay 本体も要らない)。
# 手元 (Debian sid、glibc 2.43) でビルドした実行ファイルを、同じ sid の slim で動かす。要るのは OpenSSL 3、zlib、zstd (と tini)。
FROM debian:sid-slim
RUN apt-get update && apt-get install -y --no-install-recommends libssl3t64 zlib1g libzstd1 ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*
COPY build/stat-models /usr/local/bin/stat-models
USER 65534:65534
EXPOSE 8080
# tini を PID 1 にする (SIGTERM を子に渡す)
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/stat-models"]
