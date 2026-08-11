# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The stubs which let a generated controller run without ROS2
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------

# The diagrams are written against the robot API and not against ROS2, so the tests of
# the generated code do not need ROS2 either. The modules the generated controller
# imports are replaced by the stubs below, and the controller then runs on pysm alone:
# no node is created, no service is called and no topic is subscribed.

import importlib
import sys
import types

API_MODULES = ('Debug', 'Navigation', 'Pump', 'Storage', 'Timer', 'Wheels')


class CallRecorder:
    # records the API calls a diagram makes and answers them with the set results

    def __init__(self):
        self.calls = []
        self.results = {}

    def result(self, call, value):
        # set the value an API method returns, e.g. result('Storage.next', [1, 2])
        self.results[call] = value

    def names(self):
        # the calls made so far, as Module.method strings
        return [name for name, _, _ in self.calls]

    def arguments(self, call):
        # the argument tuples of every call of the given API method
        return [args for name, args, _ in self.calls if name == call]


class FakeCaller:

    def __init__(self, module, recorder):
        self.__module = module
        self.__recorder = recorder

    def __getattr__(self, method):
        call = '{}.{}'.format(self.__module, method)

        def record(*args, **kwargs):
            self.__recorder.calls.append((call, args, kwargs))
            return self.__recorder.results.get(call)
        return record


class FakeBaseHSMController:
    # the base class of the generated controller, without the ROS2 node

    def __init__(self, object_name, obj_list, has_ticks=False, has_seconds=False,
                 has_minutes=False):
        self.object_name = object_name
        self.obj_list = tuple(obj_list)
        self.has_ticks = has_ticks
        self.has_seconds = has_seconds
        self.has_minutes = has_minutes
        self.terminated = False

    def dispatch_event(self, eventstr, arg):
        pass

    def terminate(self, *args):
        self.terminated = True


def install(package_dir):
    # replace rclpy and the controller runtime library by the stubs and return the
    # CallRecorder collecting the API calls of the diagram
    recorder = CallRecorder()

    rclpy = types.ModuleType('rclpy')
    rclpy.init = lambda *args, **kwargs: None
    rclpy.spin = lambda *args, **kwargs: None
    rclpy.try_shutdown = lambda *args, **kwargs: None
    executors = types.ModuleType('rclpy.executors')

    class ExternalShutdownException(Exception):
        pass

    executors.ExternalShutdownException = ExternalShutdownException
    rclpy.executors = executors
    sys.modules['rclpy'] = rclpy
    sys.modules['rclpy.executors'] = executors

    # the generated module is imported as hsm_controller.<name>, so the package of the
    # generated directory is put in place of the runtime library
    package = types.ModuleType('hsm_controller')
    package.__path__ = [package_dir]
    sys.modules['hsm_controller'] = package

    base = types.ModuleType('hsm_controller.base_hsm_controller')
    base.BaseHSMController = FakeBaseHSMController
    sys.modules['hsm_controller.base_hsm_controller'] = base
    package.base_hsm_controller = base

    for module in API_MODULES:
        name = 'hsm_controller.{}_caller'.format(module.lower())
        caller = types.ModuleType(name)
        setattr(caller, module, FakeCaller(module, recorder))
        sys.modules[name] = caller
        setattr(package, '{}_caller'.format(module.lower()), caller)

    return recorder


def remove():
    # drop the stubs, so the next test installs its own
    for name in list(sys.modules):
        if name == 'rclpy' or name.startswith('rclpy.') or name == 'hsm_controller' \
                or name.startswith('hsm_controller.'):
            del sys.modules[name]


def load_controller(package_dir, module_name):
    # import a generated controller module under the stubs and return its class
    path = '{}/hsm_controller'.format(package_dir)
    recorder = install(path)
    module = importlib.import_module('hsm_controller.{}'.format(module_name))
    classes = [getattr(module, name) for name in dir(module)
               if name.endswith('_HSMController')]
    assert len(classes) == 1, 'expected one controller class, got {}'.format(classes)
    return classes[0], recorder


def state_machine(controller):
    # the pysm state machine of a controller instance
    return getattr(controller, '_{}__sm'.format(type(controller).__name__))


def leaf_state(controller):
    # the name of the innermost active state
    return state_machine(controller).leaf_state.name
