# The HSM ROS2 Plugin of CyberiadaPro

The `hsm-ros2` plugin makes CyberiadaPro the IDE of HSM-ROS2: it checks a diagram,
generates the `hsm_controller` ROS 2 package and builds it with colcon. The plugin is
written against the editor's plugin interface, level 1 (`docs/PLUGIN-API.md` of
CyberiadaHSM-Editor): the editor runs a program per action and takes back the result the
action declares.

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
|  build             |         |  hsm_generator | CMD  |  exec
+--------------------+         +-----------------------+------+
   ^  ^  ^                                                    |
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

## Actions

| id | result | command after `ros2_env` | exit_ok | timeout |
|---|---|---|---|---|
| `check` | `diagnostics` | `hsm_generator ${input} --check --json ${diagnostics}` | 0, 1 | 60 s |
| `generate` | `files` (`outdir: ws`) | `hsm_generator ${input} -o ${outdir}/src/hsm_controller -f -q` | 0 | 60 s |
| `build` | `log` | `--cd ${param:ws} colcon build --packages-select hsm_controller` | 0 | none |

* The actions read `${input}`, the editor's snapshot with the unsaved edits; none of them
  needs the document saved.
* `generate` overwrites the controller (`-f`): the editor is the place the diagram is
  edited, so regenerating is the normal cycle. One workspace holds one `hsm_controller`,
  so a second diagram needs a workspace of its own.
* `generate` fills the missing `platformLanguage` metainformation with `Python`.
* All three are on the plugin toolbar.

## Parameters

| id | type | scope | default | used by |
|---|---|---|---|---|
| `setup` | `file` | `persistent` | `/opt/ros/jazzy/setup.bash` | all |
| `ws` | `dir`, `create`, `required` | `document` | `${document_dir}/ros2_ws` | generate, build |

`setup` is the ROS 2 setup script that provides `hsm_generator` and `hsm_interfaces`.
For a source build it is `<ros2_ws>/install/setup.bash`, which chains the underlay;
`--install-editor-plugin` sets it to the workspace it is run from. An empty value sources
nothing and relies on the environment the editor was started in.

## The adapter

```
ros2_env --setup FILE [--cd DIR] hsm_generator ARGS...
ros2_env --setup FILE [--cd DIR] COMMAND ARGS...
```

1. sources `FILE` when it is not empty;
2. with `--cd`, enters `DIR` (creating it) and sources `DIR/install/setup.bash` if present;
3. `hsm_generator` is resolved as `$HSM_GENERATOR` (pinned by the installer), then
   `../hsm_generator.py` of a source tree, then `ros2 run hsm_generator hsm_generator`;
4. execs the command, so its exit code is the action's exit code.

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
| `unknown-module` | the comment | `ros2 hsm modules` names an unknown module |
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
| `cyberiadaml` | | the file is not read as a CyberiadaML diagram |
| `generator` | | the package is not written (exit 2-4) |

## Install

| How | Where the editor finds it |
|---|---|
| `colcon build` of this package | `install/hsm_generator/share/hsm_generator/editor-plugin` — add it with `--plugin-path` or `CYBERIADA_PRO_PLUGIN_PATH` |
| `hsm_generator --install-editor-plugin [DIR]` | `DIR/hsm-ros2`, by default the user folder `~/.local/share/Cyberiada/CyberiadaPro/plugins/hsm-ros2` |

The installer copies the folder and pins `HSM_GENERATOR` and the `setup` default to the
generator and the ROS 2 environment it runs from.

## Test

```
colcon test --packages-select hsm_generator --pytest-args -m unit
CyberiadaPro --batch examples/turtle-square.graphml --plugin-path editor-plugin/.. \
    --run-plugin hsm-ros2:check --dump-plugin
```

`test/test_check.py` covers `--check`/`--json`, `test/test_editor_plugin.py` the
descriptor, the adapter and, when the editor is found, a batch run of every action.
