#!/usr/bin/env bash

FILE_NAME=${PWD##*/}

tar -czf ${FILE_NAME}.tar.gz bin
sha512sum ${FILE_NAME}.tar.gz | tee ${PWD##*/}_sha512-checksums.txt
