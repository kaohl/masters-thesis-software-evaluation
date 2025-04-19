#!/bin/env bash

x="$1"
f="$1.tgz"

if [ ! -d "$x" ]; then
    echo "The specified directory does not exist: '$x'"
    exit 1
fi

if [ -f "$f" ]; then
    echo "The output file already exists: '$f'"
    exit 1
fi

tar -zcvf "$f" --exclude=workspaces "$x"

