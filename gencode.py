# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# HSM (CyberiadaML diagram)-to-Python conversion class
#
# Copyright (C) 2025-2026 Alexey Fedoseev <aleksey@fedoseev.net>
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

import importlib.util
import io
import os
import re
import shutil
import datetime

import CyberiadaML

GLOBAL_PARAM_LABEL = 'global parameters'
GLOBAL_PARAM_SEPARATOR = ':'
GLOBAL_PARAM_VERSION = 'version'
GLOBAL_PARAM_AUTHOR = 'author'
GLOBAL_PARAM_EMAIL = 'author e-mail'
GLOBAL_PARAM_LICENSE = 'license'
GLOBAL_PARAM_ALL = (GLOBAL_PARAM_VERSION, GLOBAL_PARAM_AUTHOR, GLOBAL_PARAM_EMAIL, GLOBAL_PARAM_LICENSE)

ROS2_HSM_MODULES_LABEL = 'ros2 hsm modules'

EMPTY_EVENT = ''
INIT_EVENT = 'INIT'

TEMPLATE_RE = re.compile(r'%%([^%]+)%%')


def shipped_dir(name):
    # the templates and the runtime library ship with the generator, so they are located
    # relative to this file and not relative to the current directory: the generator can
    # be run from anywhere. When the package is installed the sources are not next to the
    # script any more and the ament share directory is used instead.
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    if os.path.isdir(local):
        return local
    try:
        from ament_index_python.packages import get_package_share_directory
        return os.path.join(get_package_share_directory('hsm_generator'), name)
    except Exception:
        return local


TEMPLATES_DIR = shipped_dir('templates')
CONTROLLER_SCRIPT = 'hsm_controller.py'
SCRIPT_TARGET_DIR = 'hsm_controller'
SETUP_TARGET_DIR = '.'
TEMPLATES_EXTENSION = '.templ'
RESOURCES_DIR = 'resource'
RESOURCES = ['hsm_controller']

# the controller runtime library the generated package is built upon. The generator ships
# it and copies it into every package it generates, so the package is complete on its own.
LIBRARY_DIR = shipped_dir(SCRIPT_TARGET_DIR)
LIBRARY_FILES = ('__init__.py', 'base_hsm_controller.py', 'constants.py', 'service_utils.py',
                 'debug_caller.py', 'navigation_caller.py', 'pump_caller.py',
                 'storage_caller.py', 'timer_caller.py', 'wheels_caller.py')

# the CyberiadaML error classes derive from the built-in Exception and not from
# CyberiadaML.Exception, so catching the latter alone catches nothing
CYBERIADAML_EXCEPTIONS = tuple(
    getattr(CyberiadaML, name) for name in (
        'Exception', 'CybMLException', 'FileException', 'XMLException', 'FormatException',
        'ActionException', 'AssertException', 'MetainfoException', 'NotFoundException',
        'NotImplementedException', 'ParametersException')
    if hasattr(CyberiadaML, name))


def load_library_constants():
    # the runtime library is data the generator copies into the packages it generates and
    # not a module it imports: installing it here as hsm_controller would shadow the
    # generated package of the same name in the same workspace. The event names are
    # therefore read from the library file directly.
    path = os.path.join(LIBRARY_DIR, 'constants.py')
    spec = importlib.util.spec_from_file_location('hsm_controller_constants', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_library_constants = load_library_constants()
HSM_EVENTS = _library_constants.HSM_EVENTS
HSM_TICK_EVENT = _library_constants.HSM_TICK_EVENT
HSM_TICK_1S_EVENT = _library_constants.HSM_TICK_1S_EVENT
HSM_TICK_1M_EVENT = _library_constants.HSM_TICK_1M_EVENT
hsm_modules_with_dependencies = _library_constants.hsm_modules_with_dependencies

# the generated code is checked by the same linters as the framework sources
MAX_LINE_LENGTH = 120

# the API module calls of the diagram code, e.g. Navigation.move_to_point(1, 2). The string
# literals are removed before the match, so a module named inside a printed message is not
# taken for a call
MODULE_USAGE_RE = re.compile(r'\b({})\s*\.'.format('|'.join(sorted(HSM_EVENTS.keys()))))
STRING_LITERAL_RE = re.compile(r"'[^']*'|\"[^\"]*\"")
MATH_USAGE_RE = re.compile(r'\bmath\s*\.')


class ConvertorError(Exception):
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg

    def __str__(self):
        return self.msg


class ParserError(ConvertorError):
    def __init__(self, msg):
        ConvertorError.__init__(self, msg)


class GeneratorError(ConvertorError):
    def __init__(self, msg):
        ConvertorError.__init__(self, msg)


class CodeGenerator:

    VERSION = '1.0'  # generator version

    def __init__(self, graph_file, output_dir=SETUP_TARGET_DIR, force=False, quiet=False, **kwargs):
        self.__global_parameters = {}
        self.__hsm_modules = []
        # the math module is imported by the generated controller only when the
        # diagram code uses it
        self.__uses_math = False
        self.__sm_signals = {}
        # a transition without a trigger is treated as an error unless explicitly
        # allowed; has to be set before the graph is parsed
        self.__allow_empty_trans = kwargs.get('allow_empty_trans', False)
        # the default output directory reproduces the historical behaviour of writing
        # the package into the current directory
        self.__script_target_dir = os.path.join(output_dir, SCRIPT_TARGET_DIR)
        self.__setup_target_dir = output_dir
        self.__force = force
        self.__quiet = quiet

        self.__load_graph(graph_file, **kwargs)

        self.__template_handlers = {
            'AUTHOR_NAME': self.__global_parameters.get(GLOBAL_PARAM_AUTHOR, ''),
            'AUTHOR_EMAIL': self.__global_parameters.get(GLOBAL_PARAM_EMAIL, ''),
            'GENERATOR_INFO': self.__write_generator_info,
            'LICENSE': self.__global_parameters.get(GLOBAL_PARAM_LICENSE, ''),
            'SM_ENTRY_HANDLERS': self.__write_entries,
            'SM_EVENTS': self.__write_events,
            'SM_GUARDS': self.__write_guards,
            'SM_HAS_TICKS': (HSM_TICK_EVENT in self.__sm_signals) or (EMPTY_EVENT in self.__sm_signals),
            'SM_HAS_SECONDS': HSM_TICK_1S_EVENT in self.__sm_signals,
            'SM_HAS_MINUTES': HSM_TICK_1M_EVENT in self.__sm_signals,
            'SM_HSM_OBJECTS': ', '.join("'{}'".format(m) for m in self.__hsm_modules),
            'SM_MATH_IMPORT': 'import math' if self.__uses_math else '',
            'SM_HSM_IMPORTS': self.__write_hsm_imports,
            'SM_HSM_INITS': self.__write_hsm_inits,
            'SM_NAME': self.__sm_name,
            'SM_NAME_LO': self.__sm_name_lo,
            'SM_NAME_CAP': self.__sm_name_cap,
            'SM_STATES': self.__write_states,
            'SM_TRANSITIONS': self.__write_transitions,
            'VERSION': self.__global_parameters.get(GLOBAL_PARAM_VERSION, ''),
            'YEAR': datetime.date.today().year
        }

    def __load_graph(self, graph_file, **kwargs):
        try:
            self.__graph_file = graph_file

            # Read and parse GraphML file
            self.__doc = CyberiadaML.LocalDocument()
            self.__doc.open(graph_file, CyberiadaML.formatDetect, CyberiadaML.geometryFormatNone,
                            False, False, True)
            self.__graph = self.__doc.get_state_machines()[0]

            # State machine name
            self.__sm_name = self.__graph.get_name()
            self.__sm_name_lo = self.__sm_name.lower()
            self.__sm_name_cap = self.__sm_name[0].upper() + self.__sm_name[1:].lower()

            all_signals = {''}

            # Read global parameters from the standard comments
            for comment in self.__graph.find_elements_by_type(CyberiadaML.elementComment):
                text = comment.get_body()
                if text.lower().find(ROS2_HSM_MODULES_LABEL) == 0:
                    for i, line in enumerate(text.splitlines()):
                        if i == 0:
                            continue
                        line = line.strip()
                        if len(line) == 0:
                            continue
                        module = line
                        self.__hsm_modules.append(module)
                        if module not in HSM_EVENTS:
                            raise ParserError('The graph {} contains '.format(self.__graph_file) +
                                              'unknown module "{}"!\n'.format(module))
                        for s in HSM_EVENTS[module].values():
                            all_signals.add(s)
                elif text.lower().find(GLOBAL_PARAM_LABEL) == 0:
                    for i, line in enumerate(text.splitlines()):
                        if i == 0:
                            continue
                        line = line.strip()
                        if len(line) == 0:
                            continue
                        name, value = (s.strip() for s in line.split(GLOBAL_PARAM_SEPARATOR))
                        name = name.lower()
                        if name in GLOBAL_PARAM_ALL:
                            self.__global_parameters[name] = value

            # A module may imply other modules (Navigation implies Wheels). The implied
            # modules are added to the diagram's module list here, so their callers are
            # imported and initialized and their events are accepted as known signals.
            for module in hsm_modules_with_dependencies(self.__hsm_modules):
                if module not in self.__hsm_modules:
                    self.__hsm_modules.append(module)
                    for s in HSM_EVENTS[module].values():
                        all_signals.add(s)

            # Find initial pseudostate
            init_id = None
            self.__initial = None
            self.__initial_behavior = None
            for state in self.__graph.get_children():
                if state.get_type() == CyberiadaML.elementInitial:
                    if init_id is not None:
                        raise ParserError('The graph {} has more than one initial'.format(self.__graph_file) +
                                          'pseudostate on the top level!\n')
                    init_id = state.get_id()
            if init_id is None:
                raise ParserError('The graph {} has no initial pseudostate!\n'.format(self.__graph_file))

            # Read states and transitions
            uniq_states = set()
            self.__handlers = {}
            self.__transitions = []
            self.__local_transitions = []
            self.__final_states = len(self.__graph.find_elements_by_type(CyberiadaML.elementFinal)) > 0

            types = [CyberiadaML.elementTransition,
                     CyberiadaML.elementSimpleState,
                     CyberiadaML.elementCompositeState]
            for element in self.__graph.find_elements_by_types(types):
                if element.get_type() == CyberiadaML.elementTransition:
                    source_id = element.get_source_element_id()
                    if source_id == init_id:
                        target_id = element.get_target_element_id()
                        self.__initial = self.__graph.find_element_by_id(target_id)
                        self.__initial_behavior = element.get_action().get_behavior()
                        continue
                    source_state = self.__graph.find_element_by_id(source_id)
                    if source_state.get_type() == CyberiadaML.elementInitial:
                        continue
                    a = element.get_action()
                    if len(a.get_trigger()) == 0 and not self.__allow_empty_trans:
                        raise ParserError(
                            'The graph {} has state {} ({}->) with empty external transition!\n'.format(
                                self.__graph_file, element.get_id(), source_state.get_name()))
                    self.__check_trigger_and_behavior(element.get_id(), a.get_trigger(),
                                                      a.get_guard(), a.get_behavior())
                    if a.has_trigger():
                        signal_name = self.__parse_trigger(a.get_trigger())[0]
                        if signal_name not in all_signals:
                            raise ParserError('The graph {} has undefined event {}!\n'.format(self.__graph_file,
                                                                                              signal_name))
                        else:
                            self.__sm_signals[signal_name] = None
                    self.__transitions.append(element)
                else:
                    state_name = element.get_name()
                    if len(state_name) == 0:
                        raise ParserError(
                            'The graph {} has state {} with empty name!\n'.format(
                                self.__graph_file, element.get_id()))
                    if state_name.find(' ') >= 0:
                        raise ParserError(
                            'The graph {} has state {} with spaces in name "{}"!\n'.format(
                                self.__graph_file, element.get_id(), state_name))
                    full_name = self.__get_state_name(element)
                    if full_name in uniq_states:
                        raise ParserError(
                            'The graph {} has two states with the same qualfied name {}!\n'.format(
                                self.__graph_file, full_name))
                    uniq_states.add(full_name)
                    for a in element.get_actions():
                        if a.get_type() == CyberiadaML.actionTransition:
                            if len(a.get_trigger()) == 0:
                                raise ParserError(
                                    'The graph {} has state {} with empty trigger in int.trans.!\n'.format(
                                        self.__graph_file, element.get_id()))
                            self.__check_trigger_and_behavior(full_name, a.get_trigger(),
                                                              a.get_guard(), a.get_behavior())
                            if a.has_trigger():
                                signal_name = self.__parse_trigger(a.get_trigger())[0]
                                if signal_name not in all_signals:
                                    raise ParserError(
                                        'The graph {} has undefined event {}!\n'.format(
                                            self.__graph_file, signal_name))
                                else:
                                    self.__sm_signals[signal_name] = None
                            self.__local_transitions.append(element)
                        else:
                            if full_name not in self.__handlers:
                                self.__handlers[full_name] = {}
                            if a.get_type() == CyberiadaML.actionEntry:
                                entry = 'enter'
                            else:
                                assert a.get_type() == CyberiadaML.actionExit
                                entry = 'exit'
                            if entry not in self.__handlers[full_name]:
                                handler_name = 'on_st_{}_{}'.format(full_name, entry)
                                self.__handlers[full_name][entry] = 'self.' + handler_name
                            self.__check_trigger_and_behavior(full_name, None, None, a.get_behavior())

            # Find the initial state
            if self.__initial is None:
                raise ParserError('The game graph {} has no initial state!\n'.format(self.__graph_file))
            self.__initial_states = {}
            # init_parent = self.__initial.get_parent()
            # if init_parent.get_type() != CyberiadaML.elementSM:
            #     self.__initial_states[init_parent.get_id()] = self.__initial.get_id()
            for element in self.__graph.find_elements_by_type(CyberiadaML.elementInitial):
                if element.get_id() in self.__initial_states:
                    continue
                for t in self.__transitions:
                    if t.get_source_element_id() == element.get_id():
                        parent = element.get_parent()
                        self.__initial_states[parent.get_id()] = element.get_target_element_id()
                        break
            for element in self.__graph.find_elements_by_type(CyberiadaML.elementCompositeState):
                if element.get_id() in self.__initial_states:
                    continue
                self.__initial_states[element.get_id()] = element.get_children()[0].get_id()

            for s in self.__sm_signals.keys():
                self.__sm_signals[s] = s[0].upper() + s[1:].lower()

        except CYBERIADAML_EXCEPTIONS as e:
            raise ParserError('CyberiadaML {}: {}\n'.format(e.__class__.__name__, e))

    def __check_trigger_and_behavior(self, context, trigger, guard, behavior):
        # the diagram may call only the API modules it declares: an undeclared module is
        # not imported into the generated controller and fails when the state is entered
        for text in (guard, behavior):
            if not text:
                continue
            text = STRING_LITERAL_RE.sub('', text)
            if MATH_USAGE_RE.search(text):
                self.__uses_math = True
            for module in MODULE_USAGE_RE.findall(text):
                if module not in self.__hsm_modules:
                    raise ParserError('The graph {} uses the module {} in {}, '
                                      'but does not declare it!\n'.format(self.__graph_file,
                                                                          module, context))

    @classmethod
    def __w(cls, f, s):
        f.write(s)

    @classmethod
    def __w4(cls, f, s):
        f.write(' ' * 4 + s)

    @classmethod
    def __w8(cls, f, s):
        f.write(' ' * 8 + s)

    @classmethod
    def __w12(cls, f, s):
        f.write(' ' * 12 + s)

    def __write_assignment(self, f, var, call, parts):
        line = '{} = {}({})'.format(var, call, ', '.join(parts))
        if len(line) + 8 <= MAX_LINE_LENGTH:
            self.__w8(f, line + '\n')
        else:
            self.__write_call(f, '{} = {}'.format(var, call), parts)

    def __write_call(self, f, call, parts):
        line = '{}({})'.format(call, ', '.join(parts))
        if len(line) + 8 <= MAX_LINE_LENGTH:
            self.__w8(f, line + '\n')
            return
        # the qualified state names are long, so the arguments go one per line
        self.__w8(f, '{}(\n'.format(call))
        for i, part in enumerate(parts):
            tail = ',' if i + 1 < len(parts) else ')'
            self.__w12(f, part + tail + '\n')

    def __insert_template(self, f, template, filename):
        if template not in self.__template_handlers:
            raise GeneratorError(
                'Cannot insert template "{}" in file {}: template not found!\n'.format(template, filename))
        handler = self.__template_handlers[template]
        if callable(handler):
            handler(f)
        else:
            self.__w(f, str(handler))

    def __apply_template(self, template_file, target_file):
        with open(template_file) as templ:
            with open(target_file, 'w') as f:
                for line in templ.readlines():
                    line = line.rstrip()
                    # a template standing alone on its line writes whole lines of its own,
                    # so it controls the line breaks: an empty one writes nothing at all
                    # and one ending with a line break does not get a second one
                    alone = TEMPLATE_RE.fullmatch(line) is not None
                    buf = io.StringIO()
                    while len(line) > 0:
                        match = TEMPLATE_RE.search(line)
                        if match:
                            re_start, re_end = match.span()
                            template = match.group(1)
                            self.__w(buf, line[0:re_start])
                            self.__insert_template(buf, template, template_file)
                            line = line[re_end:]
                        else:
                            self.__w(buf, line)
                            break
                    text = buf.getvalue()
                    if alone and len(text) == 0:
                        continue
                    if not text.endswith('\n'):
                        text += '\n'
                    f.write(text)

    def __write_generator_info(self, f):
        self.__w(f, '# The SM class {} based on {} file\n'.format(self.__sm_name_cap, self.__graph_file))
        self.__w(f, '# Generated by HSM-to-ROS2 script version {}'.format(self.VERSION))

    @classmethod
    def __get_state_name(cls, state):
        return state.get_qualified_name().replace('::', '_').replace('-', '_')

    @classmethod
    def __parse_trigger(cls, trigger):
        if trigger.find('(') > 0:
            idx1 = trigger.find('(')
            idx2 = trigger.find(')')
            return trigger[0:idx1], trigger[idx1+1:idx2]
        return trigger, None

    def __write_hsm_imports(self, f):
        for module in self.__hsm_modules:
            self.__w(f, 'import hsm_controller.{lm}_caller\n'.format(lm=module.lower()))
        self.__w(f, '\n')
        for module in self.__hsm_modules:
            self.__w(f, '{} = None\n'.format(module))

    def __write_hsm_inits(self, f):
        for module in self.__hsm_modules:
            self.__w8(f, 'global {}\n'.format(module))
            self.__w8(f, '{m} = hsm_controller.{lm}_caller.{m}\n'.format(
                lm=module.lower(), m=module))
        self.__w(f, '\n')

    @classmethod
    def __transition_name(cls, source_name, target_name, event_name):
        # the qualified names of the two states repeat the path of their common parent,
        # which makes the handler names of a deep diagram longer than a source line
        common = ''
        for part in source_name.split('_'):
            candidate = common + part + '_'
            if not target_name.startswith(candidate):
                break
            common = candidate
        return '{}_TO_{}_{}'.format(source_name, target_name[len(common):], event_name)

    def __write_entry_handler(self, f, state_name, entry, behavior):
        handler_name = 'on_st_{}_{}'.format(state_name, entry)
        self.__w(f, '\n')
        self.__w4(f, 'def {}(self, *_):\n'.format(handler_name))
        # self.__w4(f, 'def {}(self, state, event):\n'.format(handler_name))
        for line in behavior.split('\n'):
            self.__w8(f, line.rstrip() + '\n')

    def __write_entries_recursively(self, f, state):
        for a in state.get_actions():
            if a.get_type() == CyberiadaML.actionEntry:
                self.__write_entry_handler(f, self.__get_state_name(state), 'enter', a.get_behavior())
            elif a.get_type() == CyberiadaML.actionExit:
                self.__write_entry_handler(f, self.__get_state_name(state), 'exit', a.get_behavior())
        for ch in state.get_children():
            if ch.get_type() in (CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState):
                self.__write_entries_recursively(f, ch)

    def __write_entries(self, f):
        self.__w4(f, '# Entry & Exit Handlers:\n')
        for ch in self.__graph.get_children():
            if ch.get_type() in (CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState):
                self.__write_entries_recursively(f, ch)

    @classmethod
    def __write_guard_handler(cls, f, trigger_name, condition, argument):
        handler_name = "is_{}".format(trigger_name)
        cls.__w(f, '\n')
        # pysm calls the handlers with (state, event), so both have to be named here:
        # a trigger carrying an argument reads it from the event below
        cls.__w4(f, "def {}(self, state, event):\n".format(handler_name))
        if argument:
            cls.__w8(f, '{} = event.cargo["value"]\n'.format(argument))
        cls.__w8(f, 'return ({})\n'.format(condition))

    @classmethod
    def __write_trigger_action(cls, f, trigger_name, behavior, argument):
        handler_name = "on_{}".format(trigger_name)
        cls.__w(f, '\n')
        # see __write_guard_handler: the (state, event) signature is what pysm calls
        cls.__w4(f, 'def {}(self, state, event):\n'.format(handler_name))
        if argument:
            cls.__w8(f, '{} = event.cargo["value"]\n'.format(argument))
        for line in behavior.split('\n'):
            cls.__w8(f, line.rstrip() + '\n')

    def __write_guards_recursively(self, f, state):
        handlers = {}
        # internal triggers
        for a in state.get_actions():
            if a.get_type() == CyberiadaML.actionTransition:
                name, argument = self.__parse_trigger(a.get_trigger())
                trigger_name = '{}_{}'.format(self.__get_state_name(state), name)
                if trigger_name not in handlers:
                    handlers[trigger_name] = 1
                else:
                    handlers[trigger_name] += 1
                    trigger_name += '_{}'.format(handlers[trigger_name])
                if a.has_guard():
                    self.__write_guard_handler(f, trigger_name, a.get_guard(), argument)
                if a.has_behavior():
                    self.__write_trigger_action(f, trigger_name, a.get_behavior(), argument)

        # external triggers
        for t in self.__transitions:
            if t.get_source_element_id() != state.get_id():
                continue
            target = self.__graph.find_element_by_id(t.get_target_element_id())
            if target.get_type() == CyberiadaML.elementFinal:
                target_name = 'terminate'
            else:
                target_name = self.__get_state_name(target)
            a = t.get_action()
            if a.has_trigger():
                name, argument = self.__parse_trigger(a.get_trigger())
            else:
                name, argument = HSM_TICK_EVENT, None
            trigger_name = self.__transition_name(self.__get_state_name(state),
                                                  target_name, name)
            if trigger_name not in handlers:
                handlers[trigger_name] = 1
            else:
                handlers[trigger_name] += 1
                trigger_name += '_{}'.format(handlers[trigger_name])
            if a.has_guard():
                self.__write_guard_handler(f, trigger_name, a.get_guard(), argument)
            if a.has_behavior():
                self.__write_trigger_action(f, trigger_name, a.get_behavior(), argument)

        for ch in state.get_children():
            if ch.get_type() in (CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState):
                self.__write_guards_recursively(f, ch)

    def __write_guards(self, f):
        self.__w(f, '\n')
        self.__w4(f, "# Transition Conditions and Actions:\n")
        if self.__initial_behavior:
            self.__write_trigger_action(f, "initial", self.__initial_behavior, None)
        for ch in self.__graph.get_children():
            if ch.get_type() in (CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState):
                self.__write_guards_recursively(f, ch)
        self.__w(f, '\n')

    def __write_handlers(self, f, state_name):
        if state_name not in self.__handlers:
            return
        items = list(self.__handlers[state_name].items())
        self.__w8(f, 'st_{}.handlers = '.format(state_name) + '{\n')
        for i, (event, handler) in enumerate(items):
            tail = ',' if i + 1 < len(items) else '}'
            self.__w12(f, '"{}": {}{}\n'.format(event, handler, tail))

    def __write_states(self, f):
        self.__w8(f, '# Hierarchical States:\n')
        self.__w8(f, 'st_initial = pysm.State("initial")\n')
        self.__w8(f, 'self.__sm.add_state(st_initial, initial=True)\n')
        if self.__final_states:
            self.__w8(f, 'st_terminate = pysm.State("terminate")\n')
            self.__w8(f, 'self.__sm.add_state(st_terminate)\n')
            self.__w8(f, 'st_terminate.handlers = {"enter": self.terminate}\n')
        for ch in self.__graph.get_children():
            if ch.get_type() in (CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState):
                # the initial state of the state machine itself is st_initial, which the
                # INIT transition leaves for the state the initial pseudostate points at:
                # marking that state as initial as well is rejected by pysm
                self.__write_states_recursively(f, ch, 'self.__sm', False)

    def __write_states_recursively(self, f, state, parent_var, initial):
        state_name = self.__get_state_name(state)
        state_var = 'st_{}'.format(state_name)
        if state.get_type() == CyberiadaML.elementCompositeState:
            sm_class = "StateMachine"
        else:
            sm_class = "State"
        self.__write_assignment(f, state_var, 'pysm.{}'.format(sm_class),
                                ['"{}"'.format(state_name)])
        parts = [state_var]
        if initial:
            parts.append('initial=True')
        self.__write_call(f, '{}.add_state'.format(parent_var), parts)
        self.__write_handlers(f, state_name)
        if state.get_type() == CyberiadaML.elementCompositeState:
            initial_id = self.__initial_states[state.get_id()]
            for ch in state.get_children():
                if ch.get_type() in (CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState):
                    self.__write_states_recursively(f, ch, state_var, ch.get_id() == initial_id)

    def __write_events(self, f):
        self.__w8(f, '# Events:\n\n')
        self.__w8(f, 'InitEvent = pysm.Event("{}")\n'.format(INIT_EVENT))
        for s, v in self.__sm_signals.items():
            self.__w8(f, '{} = "{}"\n'.format(v, s))
            self.__w8(f, '{ev}Event = pysm.Event({ev})\n'.format(ev=v))
        entries = ['"{}": InitEvent'.format(INIT_EVENT)]
        entries += ['"{}": {}Event'.format(s, v) for s, v in self.__sm_signals.items()]
        self.__w8(f, 'self.__events = {\n')
        for i, entry in enumerate(entries):
            tail = ',' if i + 1 < len(entries) else '}'
            self.__w12(f, entry + tail + '\n')

    def __write_transitions(self, f):
        self.__w8(f, '# Internal transitions:\n')
        for state in self.__local_transitions:
            handlers = {}
            for a in state.get_actions():
                if a.get_type() == CyberiadaML.actionTransition:
                    state_name = self.__get_state_name(state)
                    name, _ = self.__parse_trigger(a.get_trigger())
                    trigger_name = '{}_{}'.format(state_name, name)
                    if trigger_name not in handlers:
                        handlers[trigger_name] = 1
                    else:
                        handlers[trigger_name] += 1
                        trigger_name += '_{}'.format(handlers[trigger_name])
                    parts = ['st_{}'.format(self.__get_state_name(state)),
                             'None',
                             'events=[{}]'.format(self.__sm_signals[name])]
                    if a.has_guard():
                        parts.append('condition=self.is_{}'.format(trigger_name))
                    if a.has_behavior():
                        parts.append('action=self.on_{}'.format(trigger_name))
                    parent = state.get_parent()
                    if parent.get_type() == CyberiadaML.elementSM:
                        owner = 'self.__sm'
                    else:
                        owner = 'st_{}'.format(self.__get_state_name(parent))
                    self.__write_call(f, '{}.add_transition'.format(owner), parts)

        self.__w(f, '\n')
        self.__w8(f, '# External transitions:\n')
        parts = ['st_initial',
                 'st_{}'.format(self.__get_state_name(self.__initial)),
                 'events=["{}"]'.format(INIT_EVENT)]
        if self.__initial_behavior:
            parts.append('action=self.on_initial')
        self.__write_call(f, 'self.__sm.add_transition', parts)

        # external triggers
        handlers = {}
        for t in self.__transitions:
            source = self.__graph.find_element_by_id(t.get_source_element_id())
            source_name = self.__get_state_name(source)
            if source_name not in handlers:
                handlers[source_name] = {}
            target = self.__graph.find_element_by_id(t.get_target_element_id())
            if target.get_type() == CyberiadaML.elementFinal:
                target_name = 'terminate'
            else:
                target_name = self.__get_state_name(target)
            a = t.get_action()
            if a.has_trigger():
                name, _ = self.__parse_trigger(a.get_trigger())
            else:
                name, _ = HSM_TICK_EVENT, None
            trigger_name = self.__transition_name(source_name, target_name, name)
            if trigger_name not in handlers:
                handlers[trigger_name] = 1
            else:
                handlers[trigger_name] += 1
                trigger_name += '_{}'.format(handlers[trigger_name])
            parts = ['st_{}'.format(source_name),
                     'st_{}'.format(target_name),
                     'events=[{}]'.format(self.__sm_signals[name])]
            if a.has_guard():
                parts.append('condition=self.is_{}'.format(trigger_name))
            if a.has_behavior():
                parts.append('action=self.on_{}'.format(trigger_name))
            parent = source.get_parent()
            if parent.get_type() == CyberiadaML.elementSM:
                owner = 'self.__sm'
            else:
                owner = 'st_{}'.format(self.__get_state_name(parent))
            self.__write_call(f, '{}.add_transition'.format(owner), parts)

    def __write_library(self):
        # the generated controller imports the runtime library as hsm_controller.*, so the
        # library is copied into the generated package and the package builds on its own
        target_dir = self.__script_target_dir
        os.makedirs(target_dir, exist_ok=True)
        for name in LIBRARY_FILES:
            source_file = os.path.join(LIBRARY_DIR, name)
            if not os.path.isfile(source_file):
                raise GeneratorError('The library file {} is missing\n'.format(source_file))
            target_file = os.path.join(target_dir, name)
            if not self.__quiet:
                print('Writing {} as {}'.format(name, target_file))
            shutil.copyfile(source_file, target_file)

    def generate_code(self):
        controller_template = CONTROLLER_SCRIPT + TEMPLATES_EXTENSION
        # sorted() keeps the reported order stable between runs
        for tmpl in sorted(os.listdir(TEMPLATES_DIR)):
            tmpl_file = os.path.join(TEMPLATES_DIR, tmpl)
            if not tmpl.endswith(TEMPLATES_EXTENSION) or not os.path.isfile(tmpl_file):
                continue
            if tmpl == controller_template:
                target_dir = self.__script_target_dir
                target_file = os.path.join(target_dir, self.__sm_name_lo + '.py')
                # the controller carries the diagram behavior, so an existing one is
                # never silently replaced
                if os.path.exists(target_file) and not self.__force:
                    raise GeneratorError('The file {} already exists; '.format(target_file) +
                                         'use --force to overwrite it\n')
            else:
                target_dir = self.__setup_target_dir
                target_file = os.path.join(target_dir,
                                           tmpl[:-len(TEMPLATES_EXTENSION)])
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            if not self.__quiet:
                print('Writing {} as {}'.format(tmpl, target_file))
            self.__apply_template(tmpl_file, target_file)
        self.__write_library()
        target_dir = os.path.join(self.__setup_target_dir, RESOURCES_DIR)
        os.makedirs(target_dir, exist_ok=True)
        for r in RESOURCES:
            target_file = os.path.join(target_dir, r)
            if not self.__quiet:
                print('Writing {} as {}'.format(r, target_file))
            f = open(target_file, 'w')
            f.close()
