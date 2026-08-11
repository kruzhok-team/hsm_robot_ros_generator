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

## Requirements

* Python 3.x
* ROS 2
* ROS 2 HSM robot API - https://github.com/kruzhok-team/hsm-robot-ros-api
* ROS 2 HSM robot API interfaces - https://github.com/kruzhok-team/hsm-robot-ros-interfaces
* pysm: the Python implementation of the hierarchical state machines
* Python binding for the CyberiadaML library - https://github.com/kruzhok-team/libcyberiadamlpp-py
* Editor to draw CyberiadaML diagrams like yEd, https://github.com/kruzhok-team/lapki-client or https://github.com/dralex/CyberiadaHSM-Editor
