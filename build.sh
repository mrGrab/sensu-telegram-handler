#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
NAME=sensu-telegram-handler

rm -rf dist
mkdir dist
tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner \
    --mode='u=rwX,go=rX' --exclude=__pycache__ -cf - bin |
    gzip -n -9 >"dist/${NAME}.tar.gz"
(cd dist && sha512sum "${NAME}.tar.gz" | tee "${NAME}_sha512-checksums.txt")
