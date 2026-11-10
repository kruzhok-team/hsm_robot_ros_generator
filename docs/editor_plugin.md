# The HSM ROS2 Plugin of CyberiadaPro

The `hsm-ros2` plugin makes CyberiadaPro the IDE of HSM-ROS2: it checks a diagram,
generates the `hsm_controller` ROS 2 package, builds it with colcon and tests the diagram
with the fake robot. The plugin is
written against the editor's plugin interface (`docs/PLUGIN-API.md` of
CyberiadaHSM-Editor): the editor runs a program per action and takes back the result the
action declares; the conditions of the actions grey out what cannot run, and the test runs
as an observed session that marks the running controller on the diagram.

| | |
|---|---|
| id | `hsm-ros2` |
| name | `HSM ROS2`, in Russian `ROS2 ПРИМС` |
| folder | `editor-plugin/` of this repository |
| platforms | Linux with ROS 2 Jazzy |

## Architecture

```
 CyberiadaPro                      editor-plugin/                 ROS 2 environment
+--------------------+  argv   +-----------------------+ source  +---------------------+
| Plugins > HSM ROS2 |-------->| ros2_env (bash)       |-------->| ${param:setup}      |
|  check             |         |  --setup FILE         |         | [WS/install/setup]  |
|  generate          |         |  [--cd WS]            |         +---------------------+
|  build             |         |  hsm_generator |      |  exec
|  test              |         |  --ros-exec PKG EXE | |
+--------------------+         |  CMD                  |------+
   ^  ^  ^  ^                  +-----------------------+      |
   |  |  |  |  diagnostics.json  hsm_robot_test IN --json DIAG ...  <--+ test
   |  |  |  +---------------------------------------------------------+
   |  |  |  diagnostics.json   hsm_generator.py IN --check --json DIAG  <--+ check
   |  |  +-----------------------------------------------------------------+
   |  |     files of WS        hsm_generator.py IN -o WS/src/hsm_controller -f  <--+ generate
   |  +--------------------------------------------------------------------------+
   |        stdout/stderr      colcon build --packages-select hsm_controller (in WS)  <--+ build
   +------------------------------------------------------------------------------------+

 WS = ${param:ws}:   WS/src/hsm_controller/   the generated package
                     WS/build, WS/install, WS/log   colcon
```

The editor never sources a ROS 2 setup: it is usually started from the desktop. The
generator needs one (it reads the event tables through `hsm_interfaces`), and so does
colcon, so every action goes through the `ros2_env` adapter.
The descriptor names `bash` as the interpreter, so the adapter needs no executable bit.
The `hsm-turtle` plugin (`turtle_driver/docs/editor_plugin.md`) runs its actions through this
adapter as well, found in the share directory of this package.

## Actions

| id | result | command after `ros2_env` | exit_ok | timeout |
|---|---|---|---|---|
| `check` | `diagnostics` | `hsm_generator ${input} --check --json ${diagnostics}` | 0, 1 | 60 s |
| `generate` | `files` (`outdir: ws`) | `hsm_generator ${input} -o ${outdir}/src/hsm_controller -f -q` | 0 | 60 s |
| `build` | `log` | `--cd ${param:ws} colcon build --packages-select hsm_controller` | 0 | none |
| `test` | `diagnostics` | `--ros-exec hsm_tests hsm_robot_test ${input} --json ${diagnostics} --duration ... --pose ... --scan ... [--real-time]` | 0, 1 | none |
| `test-live` (session) | `diagnostics` | the `test` command and `--session` | 0, 1 | none |

* The actions read `${input}`, the editor's snapshot; but every action that generates,
  builds or runs needs the diagram saved (see Conditions), so the snapshot is the file.
* `generate` overwrites the controller (`-f`): the editor is the place the diagram is
  edited, so regenerating is the normal cycle. One workspace holds one `hsm_controller`,
  so a second diagram needs a workspace of its own; regenerating with `-f` removes the
  controller module of the diagram generated there before.
* `generate` and `test` fill the missing `platformLanguage` metainformation with `Python`
  and save it (`save`), so the document stays clean.
* `test` runs the diagram against the fake robot of `hsm_robot_ros_tests` (the
  `hsm_robot_test` runner, `docs/hsm_robot_testing.md` §10 there) and reports every failed
  expectation of the `ROS2 HSM Test` comment; its output is the timeline of the events and
  the `Debug.print` lines of the diagram. It needs the `hsm_tests` package and the HSM
  dispatcher `hsmd` (`python3-hsm-dispatcher`) the generated controller runs on in the
  `setup` environment. Cancel stops the whole run.
* `test-live` is the same run as an observed session (see The session); it `replaces`
  `test`, so an editor with the sessions shows it instead, and an older editor and
  `--run-plugin hsm-ros2:test` keep the one-shot run.
* All of them are on the plugin toolbar.

## Conditions

| action | `when` |
|---|---|
| `check` | `sm`, `!fa` |
| `generate`, `test`, `test-live` | `saved`, `sm`, `!fa`, `initial`, `meta:platformLanguage=Python` |
| `build` | `saved` |

The descriptor `requires` `bash`, the interpreter. `ros2` and `colcon` are not in
`requires`: they come from the `setup` script and not from the editor's `PATH`, so
`ros2_env` checks them in the run. `check` stays open on unsaved edits and reports a
missing initial state as a finding. A diagram without `platformLanguage` passes the
`meta:` token: the action fills it.

## The session

`test-live` runs `hsm_robot_test --session`: the editor and the runner talk JSON-RPC
(`docs/PLUGIN-API.md`, Sessions, kind `observed`), and the controller reports its steps on
a topic the runner listens to (see The trace). The user's input is the parameter dialog
before the run and Stop.

```
 CyberiadaPro (document locked)        hsm_robot_test --session         ROS 2, random domain
+--------------------------------+   +----------------------------+  +---------------------+
| canvas: the active states,     |<--| state {status, text,       |  | API nodes           |
|         the fired transitions  |   |        active, fired}      |  | fake robot          |
| session tab: status, text,     |<--| history {time, event,      |  |                     |
|   one history row per event    |   |   origin, outcome, fired}  |  | hsm_controller      |
|   [Stop] ---- shutdown ------->|-->| stops the nodes, writes    |  |  trace:=true        |
| output tab: the timeline,      |<--|   the diagnostics, exits   |<-|  /hsm_ros_trace     |
|   Debug.print, the errors      |log+----------------------------+  +---------------------+
+--------------------------------+
```

| Phase | `state` | canvas | `history` |
|---|---|---|---|
| the nodes start | `waiting`, "starting the nodes" | — | — |
| the controller started | `running`, the time | the initial configuration | — |
| an event handled | `running`, the time, the rules that hold | the active states, the fired transitions | the event, `origin` `system`, the outcome, the fired transitions; a completion `model` |
| the end: the duration, every rule holds, the controller ends | `finished`, the verdict | the last configuration | — |

The run ends as the one-shot `test` does and writes the same diagnostics file; Stop ends it
earlier, as Cancel does.

## The trace

The controller publishes its steps when its parameter `trace` is true (false by default):

| | |
|---|---|
| topic | `/hsm_ros_trace` (`TRACE_TOPIC`), `std_msgs/String`, reliable, transient local, the depth `message_queue_length` |
| a message | one JSON object per step: the start, and every event the controller handles with the completions it causes |
| ids | the element ids of the diagram: `ELEMENTS` of the generated module maps every model id the trace reports to its diagram id (a transition keeps its `id=`); an initial transition the generator adds has no element and is left out |

```json
{"time": 12.43, "history": [{"event": "MOVE_COMPLETED", "time": 12.43, "origin": "system",
 "outcome": "fired", "fired": ["e5"]}], "fired": ["e5"], "active": ["n1", "n4"],
 "finished": false}
```

* `time` is seconds from the start of the controller; `history` holds the rows of the
  editor's `history` (`hsmd.session.history_row`), `origin` `model` for a completion and
  `system` for an event of the API; `fired` every transition of the step, the initial ones
  included; `active` the configuration after the step; `error` the error that stopped the
  machine.
* A tick (`TIMER_TICK`) that fires nothing is no step.
* An internal transition marks its state; the trace needs `hsmd.session.history_row`
  (hsm-dispatcher-py after 0.2.0), else the controller logs an error and runs untraced.

## Parameters

| id | type | scope | default | used by |
|---|---|---|---|---|
| `setup` | `file` | `persistent` | `/opt/ros/jazzy/setup.bash` | all |
| `ws` | `dir`, `create`, `required` | `document` | `${document_dir}/ros2_ws` | generate, build |
| `duration` | `int`, min 1 | `document` | 30 | test: the run limit, s |
| `x`, `y`, `theta` | `double` | `document` | 0 | test: the start pose of the robot |
| `scan_forward`, `scan_right`, `scan_elsewhere` | `double` | `document` | 10.0 | test: the distances the scan reports, 10 m is free space |
| `realtime` | `bool` | `document` | false | test: run the timers at their real periods |

`setup` is the ROS 2 setup script that provides `hsm_generator` and `hsm_interfaces`.
For a source build it is `<ros2_ws>/install/setup.bash`, which chains the underlay;
`--install-editor-plugin` sets it to the workspace it is run from. An empty value sources
nothing and relies on the environment the editor was started in.

## The adapter

```
ros2_env --setup FILE [--cd DIR] hsm_generator ARGS...
ros2_env --setup FILE [--cd DIR] --ros-exec PACKAGE EXECUTABLE ARGS...
ros2_env --setup FILE [--cd DIR] COMMAND ARGS...
```

1. sources `FILE` when it is not empty;
2. with `--cd`, enters `DIR` (creating it) and sources `DIR/install/setup.bash` if present;
3. `--ros-exec` resolves `$(ros2 pkg prefix PACKAGE)/lib/PACKAGE/EXECUTABLE`. Unlike
   `ros2 run`, which keeps the program as its child, the program replaces the adapter, so
   the editor's Cancel (SIGTERM) reaches it;
4. `hsm_generator` is resolved as `$HSM_GENERATOR` (pinned by the installer), then
   `../hsm_generator.py` of a source tree, then `--ros-exec hsm_generator hsm_generator`;
5. execs the command, so its exit code is the action's exit code.

| exit | meaning |
|---|---|
| 5 | a usage error, a setup or a directory that is missing |
| other | the command's own |

## Diagnostics

`hsm_generator --check` parses the diagram and writes nothing; `--json FILE` writes the
editor's diagnostics file in both modes: `[]` for a clean diagram, otherwise one entry
`{severity: "error", rule, message, element?}`. The generator stops at the first error, so
a check reports one finding at a time.

| rule | element | the problem |
|---|---|---|
| `unknown-module` | the comment | a `CGML_COMPONENT` (or `ROS2 HSM Modules`) names an unknown module |
| `component-id` | the comment | a `CGML_COMPONENT` identifier is not its type |
| `component-type` | the comment | a `CGML_COMPONENT` without `type/` |
| `component-syntax` | the comment | a `CGML_COMPONENT` line is not `name/ value` |
| `duplicate-module` | the comment | a module declared twice |
| `undeclared-module` | the state or transition | the code calls a module not declared |
| `two-initial` | the second initial | two initial pseudostates on the top level |
| `no-initial` | | no initial pseudostate on the top level |
| `no-initial-state` | | the initial pseudostate leads nowhere |
| `empty-transition` | the transition | an external transition without a trigger |
| `empty-trigger` | the state | an internal transition without a trigger |
| `undefined-event` | the transition or state | a trigger names an unknown event |
| `empty-name` | the state | a state without a name |
| `spaced-name` | the state | a state name with spaces |
| `duplicate-name` | the state | two states with the same qualified name |
| `empty-composite` | the state | a composite state without substates |
| `test-rule` | the comment | a line of `ROS2 HSM Test` is not a rule or names an unknown event |
| `cyberiadaml` | | the file is not read as a CyberiadaML diagram |
| `generator` | | the package is not written (exit 2-4) |

The `test` action writes the same file: `[]` when the run passes, otherwise an entry per
failed expectation, rule `test-failed`, pointing at the `ROS2 HSM Test` comment, or rule
`test-controller` when the controller ends with an error, e.g. an error of the diagram
code which stops the dispatcher (the controller exits with 1). A diagram the generator rejects
gets the generator's finding. A node of the framework which fails to start fails the
action itself.

## The expectations comment

A diagram states what a test run has to see in the formal comment named `ROS2 HSM Test`
(`docs/diagram_comments.md`), one rule a line:

```
MOVE_COMPLETED
MOVE_COMPLETED x4 within 60
POINT_PASSED within 10
never COLLISION_DETECTED
```

| line | holds when |
|---|---|
| `EVENT [xN] [within S]` | the robot reports `EVENT` at least `N` times (1) within `S` s (the run duration) of the controller start |
| `never EVENT` | the robot does not report `EVENT` while the run lasts |

The events are the API event names (`hsm_controller/constants.py`); `#` starts a remark.
The run stops when every positive rule holds. A diagram without the comment gets a smoke
run: it passes when the controller is still running, or has ended with 0, after the
duration. The comment changes nothing in the generated code; `--check` validates it.

## Install

| How | Where the editor finds it |
|---|---|
| `colcon build` of this package | `install/hsm_generator/share/hsm_generator/editor-plugin` — add it with `--plugin-path` or `CYBERIADA_PRO_PLUGIN_PATH` |
| `hsm_generator --install-editor-plugin [DIR]` | `DIR/hsm-ros2`, by default the user folder `~/.local/share/Cyberiada/CyberiadaPro/plugins/hsm-ros2` |
| the `ros-jazzy-hsm-generator` .deb | the system folder: `/usr/share/cyberiada-pro/plugins/hsm-ros2`, a link to `/opt/ros/jazzy/share/hsm_generator/editor-plugin` (`packaging/debian/links`) |

The installer copies the folder and pins `HSM_GENERATOR` and the `setup` default to the
generator and the ROS 2 environment it runs from.
`hsmplugin.install` takes the plugin id, so the other plugins of the framework install the same way.

## Test

```
colcon test --packages-select hsm_generator --pytest-args -m unit
CyberiadaPro --batch examples/turtle-square.graphml --plugin-path editor-plugin/.. \
    --run-plugin hsm-ros2:check --dump-plugin
```

`test/test_check.py` covers `--check`/`--json` and the expectations comment,
`test/test_editor_plugin.py` the descriptor, the conditions, the session block, the
adapter and, when the editor is found, a batch run; `test/test_trace.py` the ids of the
generated module and the trace messages. The `test` and `test-live` actions are tested
with their runner in `hsm_robot_ros_tests`.
