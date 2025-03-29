#!/bin/env bash

data_tgz=data.tgz
data_dir=experiments/data


if [ -f "$data_tgz" ]; then
    echo "Please manually remove '$data_tgz', if your intention is to re-create it using this script."
    exit 1
fi

tar -C "$data_dir" -zcvf "$data_tgz" `ls "$data_dir"`

