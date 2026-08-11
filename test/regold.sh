#!/bin/sh
# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# Record the reference output of the code generator
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# -----------------------------------------------------------------------------
#
# Run this after an intended change of the conversion or of the templates, then review
# the difference of the reference files as a part of the patch. The ROS 2 workspace with
# the built hsm_interfaces package has to be sourced.

set -e

TEST_DIR=$(cd "$(dirname "$0")" && pwd)
GENERATOR_DIR=$(dirname "$TEST_DIR")
GOLDEN_DIR="$TEST_DIR/golden"
WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

mkdir -p "$GOLDEN_DIR"

for diagram in "$TEST_DIR"/diagrams/valid/*.graphml "$GENERATOR_DIR"/examples/*.graphml; do
    name=$(basename "$diagram" .graphml)
    package="$WORK_DIR/$name"
    python3 "$GENERATOR_DIR/hsm_generator.py" "$diagram" -o "$package" -q
    module=$(ls "$package"/hsm_controller/*.py | while read -r f; do
        base=$(basename "$f")
        if [ ! -f "$GENERATOR_DIR/hsm_controller/$base" ]; then echo "$f"; fi
    done)
    # the year of the run is not a property of the conversion
    sed -e 's/^# Copyright (C) [0-9][0-9][0-9][0-9] /# Copyright (C) YEAR /' \
        "$module" > "$GOLDEN_DIR/$name.py.expected"
    echo "recorded $name"
done
