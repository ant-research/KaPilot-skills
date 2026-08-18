#!/bin/bash

timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
file_path=$(realpath "$1")
line_number=$2
base_name=$(basename "$file_path")
stem="${base_name%.*}"
save_root_dir=$(realpath "$3")
result_fldr="$save_root_dir/spec-$stem/$line_number/$timestamp/"
mkdir -p "$result_fldr"
echo "$(realpath "$result_fldr")"