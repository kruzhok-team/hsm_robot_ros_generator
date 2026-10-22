# The Comments of an HSM-ROS2 Diagram

A diagram is a CyberiadaML-GraphML document (PNST 1044-2025). Besides the states and the
transitions the generator reads three kinds of formal comments: the metainformation of the
document, the API modules the diagram uses and the expectations of a test run. Every other
comment is left to the reader of the diagram.

```
 the diagram                               the generated package
 ───────────────────────────────           ─────────────────────────────────────────
 CGML_META  version/ author/        ─────▶  package.xml, setup.py, the header of <sm>.py
            contact/ license/
            platform/ HSM-ROS2
 CGML_COMPONENT Navigation          ─────▶  the callers of the modules (+ the implied ones,
 type/ Navigation                           Navigation -> Wheels), their known events
 ROS2 HSM Test                      ─────▶  nothing; the test run of hsm_robot_test and
 MOVE_COMPLETED x4 within 60                the test action of the editor plugin
```

## The metainformation

The standard `CGML_META` comment (6.9 of the standard) gives the package parameters:

| Parameter | Goes to |
|---|---|
| `version` | the version of the package |
| `author` | the author and the maintainer |
| `contact` | the e-mail of the author and the maintainer |
| `license` | the license of the package (a parameter of the platform) |
| `platform`, `platformLanguage` | `HSM-ROS2`, `Python`: the editor plugin |

## The modules

An API module is a component of the diagram (10.3 of the standard), one comment a module.
The identifier of the component is the name of the module, the one the code calls:

```xml
<node id="cNavigation">
  <data key="dNote">formal</data>
  <data key="dName">CGML_COMPONENT Navigation</data>
  <data key="dData">type/ Navigation</data>
</node>
```

```
entry/
Navigation.move_to_point(1, 2)

MOVE_COMPLETED/
```

The events of a module keep their names (`MOVE_COMPLETED`, not `Navigation.MOVE_COMPLETED`).
The modules are listed in `hsm_robot_ros_api/docs/hsm_robot_api.md`.

| Rule | The problem |
|---|---|
| `unknown-module` | the type is not an API module |
| `component-id` | the identifier is not the type: `CGML_COMPONENT nav` with `type/ Navigation` |
| `component-type` | no `type` parameter |
| `component-syntax` | a line of the body is not a `name/ value` parameter |
| `duplicate-module` | the module is declared twice |
| `undeclared-module` | the code calls a module the diagram does not declare |

## The test expectations

A formal comment named `ROS2 HSM Test`, one rule a line (`docs/editor_plugin.md`, The
expectations comment):

```xml
<node id="nTest">
  <data key="dNote">formal</data>
  <data key="dName">ROS2 HSM Test</data>
  <data key="dData">MOVE_COMPLETED x4 within 60
never COLLISION_DETECTED</data>
</node>
```

## The yEd diagrams

The older diagrams carry the same data in informal comments, the key on the first line of
the body. The generator still reads them; the metainformation wins over the legacy
parameters:

| Informal comment | Its CGML form |
|---|---|
| `Global Parameters` with `Version:`, `Author:`, `Author e-mail:`, `License:` | `CGML_META` with `version/`, `author/`, `contact/`, `license/` |
| `ROS2 HSM Modules` with a module a line | a `CGML_COMPONENT` a module |
| `ROS2 HSM Test` with a rule a line | the formal `ROS2 HSM Test` |

The keys ignore case, underscores, extra spaces and a trailing colon. Saving a yEd diagram
in CyberiadaPro keeps the informal comments; replace them with the formal ones.
