#!/bin/env bash

data_loc=data.loc.tgz
data_tgz=data.tgz
data_dir=experiments/data
data_tmp=temp/data

rm    -rf "$data_tmp"
mkdir -p  "$data_tmp"

[ -f "$data_tgz" ] && tar -C "$data_tmp" --skip-old-files -zxf "$data_tgz"
[ -f "$data_loc" ] && tar -C "$data_tmp" --skip-old-files -zxf "$data_loc"

tar -C "$data_dir" -zcvf "$data_loc" `ls "$data_dir"`

[ -f "$data_loc" ] && tar -C "$data_tmp" --skip-old-files -zxf "$data_loc"

rm  -rf "$data_tgz" "$data_loc"
tar -C "$data_tmp" -zcvf "$data_tgz" `ls "$data_tmp"`

rm    -rf "$data_dir" "$data_tmp"
mkdir -p  "$data_dir"

tar -C "$data_dir" -zxf "$data_tgz"

