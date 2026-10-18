FROM debian:bookworm-slim
ARG GNUCOBOL_VER=3.2
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl xz-utils libgmp-dev libdb-dev libncurses-dev \
      libxml2-dev libjson-c-dev python3 ca-certificates \
 && curl -fsSL https://ftp.gnu.org/gnu/gnucobol/gnucobol-${GNUCOBOL_VER}.tar.xz | tar xJ -C /tmp \
 && cd /tmp/gnucobol-${GNUCOBOL_VER} && ./configure --with-db && make -j"$(nproc)" && make install && ldconfig \
 && rm -rf /tmp/gnucobol-* /var/lib/apt/lists/*
# TODO(phase 2): add GixSQL (Postgres) for EXEC SQL programs
ENV COB_LIBRARY_PATH=/work/out/legacy/lib \
    COB_FILE_PATH=/work/out/legacy/data
WORKDIR /work
