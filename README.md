# The HSM diagrams to ROS2 Node code generator

The HSM graphml-to-Python convertor and the simple HAL based on ROS2 library.

The code is distributed under the GNU Lesser General Public License (version 3).

## Usage

    python3 hsm_generator.py <diagram.graphml> -o <output directory>

The output directory is required, so that the generator never writes over its own sources.

This repository is the `hsm_generator` ROS 2 package: the convertor (`gencode.py`,
`hsm_generator.py`), the templates, and the controller runtime library of the
`hsm_controller` directory the generated package is built upon. The generated package is a
separate package named `hsm_controller`.

## Tests

    colcon test --packages-select hsm_generator

The tests convert the diagrams of the `test/diagrams` directory and the examples, and
check the code the generator produces: the package it writes is complete and builds, the
generated code passes the linters, the state machine it builds behaves as the diagram
says, and an invalid diagram is reported instead of being converted. The generated
controller is driven with `rclpy` and the runtime library replaced by the stubs of
`test/hsm_stubs.py`, so no ROS 2 node is created and no service is called.

The `test/golden` directory holds the reference output of every diagram. After an
intended change of the conversion or of the templates, record it again and review the
difference as a part of the patch:

    ./test/regold.sh

## Requirements

* Python 3.x
* ROS 2
* ROS 2 HSM robot API - https://github.com/kruzhok-team/hsm-robot-ros-api
* ROS 2 HSM robot API interfaces - https://github.com/kruzhok-team/hsm-robot-ros-interfaces
* pysm: the Python implementation of the hierarchical state machines
* Python binding for the CyberiadaML library - https://github.com/kruzhok-team/libcyberiadamlpp-py
* Editor to draw CyberiadaML diagrams like yEd, https://github.com/kruzhok-team/lapki-client or https://github.com/dralex/CyberiadaHSM-Editor
