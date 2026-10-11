# llm-openai-emu のイメージ。実行ファイルは手元で build.sh が作る (clay はイメージに入れない)。
# 手元 (Debian sid、glibc 2.43) でビルドした実行ファイルを、同じ sid の slim で動かす。要るのは OpenSSL 3、zlib、zstd。
FROM debian:sid-slim
RUN apt-get update && apt-get install -y --no-install-recommends libssl3t64 zlib1g libzstd1 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY build/llm-openai-emu /usr/local/bin/llm-openai-emu
USER 65534:65534
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/llm-openai-emu"]
