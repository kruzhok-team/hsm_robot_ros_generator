# The HSM diagrams to ROS2 Node code generator

The HSM graphml-to-Python convertor and the simple HAL based on ROS2 library.

The code is distributed under the GNU Lesser General Public License (version 3).

## Usage

    python3 hsm_generator.py <diagram.graphml> -o <output directory>

The output directory is required, so that the generator never writes over its own sources.

    python3 hsm_generator.py <diagram.graphml> --check [--json <diagnostics.json>]

checks the diagram only and writes nothing; `--json` writes the findings as the
diagnostics file of the CyberiadaPro editor.

## Editor plugin

The `editor-plugin` directory is the `hsm-ros2` plugin of CyberiadaPro ("HSM ROS2"): it
checks the diagram, generates the package into a colcon workspace, builds it and tests the
diagram against the fake robot of `hsm_robot_ros_tests`. Install
it into the user plugin folder of the editor from a sourced workspace:

    ros2 run hsm_generator hsm_generator --install-editor-plugin

The plugin is described in `docs/editor_plugin.md`.

The generated controller declares the state machine as an `hsmd.Machine` and runs it on
the Python HSM dispatcher `hsmd` (hsm-dispatcher-py); the events of the API modules are
sent to the dispatcher, and the node is closed when the machine reaches its final state or
an error of the diagram code stops the dispatcher:

    graphml --gencode.py--> hsm_controller/<sm>.py: the diagram code functions
                                                    machine = hsmd.Machine(...)
                                                    <Sm>_HSMController(BaseHSMController)
    ROS topics --> BaseHSMController --dispatch_event--> hsmd.Dispatcher.send(EVENT, value=arg)

This repository is the `hsm_generator` ROS 2 package: the convertor (`gencode.py`,
`hsm_generator.py`), the templates, and the controller runtime library of the
`hsm_controller` directory the generated package is built upon. The generated package is a
separate package named `hsm_controller`.

## Tests

    colcon test --packages-select hsm_generator
    colcon test --packages-select hsm_generator --pytest-args -m unit    # without the linters

These are the L1 tier of the framework. The tests convert the diagrams of the
`test/diagrams` directory and the examples, and check the code the generator produces: the
package it writes is complete and builds, the generated code passes the linters, the state
machine it builds behaves as the diagram says, and an invalid diagram is reported instead
of being converted. The generated controller is driven with `rclpy` and the runtime library
replaced by the stubs of `test/hsm_stubs.py`, so no ROS 2 node is created and no service is
called. The behaviour tests need `hsmd` importable.

The `test/golden` directory holds the reference output of every diagram. After an
intended change of the conversion or of the templates, record it again and review the
difference as a part of the patch:

    ./test/regold.sh

A diagram dropped into `test/diagrams/valid/` is enrolled by itself and needs its reference
recorded; a diagram added to `test/diagrams/invalid/` also needs an entry in the `REPORTED`
dictionary of `test_errors.py`, naming the phrase its report has to contain. Both rules, and
the fixtures, are described in §3 of `docs/howto_write_a_test.md` of the testing project -
https://github.com/kruzhok-team/hsm_robot_ros_tests.

## Requirements

* Python 3.x
* ROS 2
* ROS 2 HSM robot API - https://github.com/kruzhok-team/hsm-robot-ros-api
* ROS 2 HSM robot API interfaces - https://github.com/kruzhok-team/hsm-robot-ros-interfaces
* hsm-dispatcher-py: the Python HSM dispatcher `hsmd`, needed where the generated controller
  runs - https://github.com/kruzhok-team/hsm-dispatcher-py (its Debian package
  `python3-hsm-dispatcher` or `pip install`)
* Python binding for the CyberiadaML library - https://github.com/kruzhok-team/libcyberiadamlpp-py
* Editor to draw CyberiadaML diagrams like yEd, https://github.com/kruzhok-team/lapki-client or https://github.com/dralex/CyberiadaHSM-Editor
