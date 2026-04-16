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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------

import sys
import os
import traceback
import re
import datetime

import CyberiadaML

from hsm_controller.constants import HSM_EVENTS, HSM_TICK_EVENT, HSM_TICK_1S_EVENT, HSM_TICK_1M_EVENT

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

TEMPLATES_DIR = 'templates'
CONTROLLER_SCRIPT = 'hsm_controller.py'
SCRIPT_TARGET_DIR = 'hsm_controller'
SETUP_TARGET_DIR = '.'
TEMPLATES_EXTENSION = '.templ'

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

    VERSION = '1.0' # generator version

    def __init__(self, graph_file, **kwargs):
        self.__global_parameters = {}
        self.__hsm_modules = []
        self.__sm_signals = {}

        self.__load_graph(graph_file, **kwargs)

        self.__template_handlers = {
            'AUTHOR_NAME': self.__global_parameters[GLOBAL_PARAM_AUTHOR] if GLOBAL_PARAM_AUTHOR in self.__global_parameters else '',
            'AUTHOR_EMAIL': self.__global_parameters[GLOBAL_PARAM_EMAIL] if GLOBAL_PARAM_EMAIL in self.__global_parameters else '',
            'GENERATOR_INFO': self.__write_generator_info,
            'LICENSE': self.__global_parameters[GLOBAL_PARAM_LICENSE] if GLOBAL_PARAM_LICENSE in self.__global_parameters else '',
            'SM_ENTRY_HANDLERS': self.__write_entries,
            'SM_EVENTS': self.__write_events,
            'SM_GUARDS': self.__write_guards,
            'SM_HAS_TICKS': (HSM_TICK_EVENT in self.__sm_signals) or (EMPTY_EVENT in self.__sm_signals),
            'SM_HAS_SECONDS': HSM_TICK_1S_EVENT in self.__sm_signals,
            'SM_HAS_MINUTES': HSM_TICK_1M_EVENT in self.__sm_signals,
            'SM_HSM_OBJECTS': ', '.join(map(lambda m: "'{}'".format(m), self.__hsm_modules)),
            'SM_HSM_IMPORTS': self.__write_imports,
            'SM_NAME': self.__sm_name,
            'SM_NAME_LO': self.__sm_name_lo,
            'SM_NAME_CAP': self.__sm_name_cap,
            'SM_STATES': self.__write_states,
            'SM_TRANSITIONS': self.__write_transitions,
            'VERSION': self.__global_parameters[GLOBAL_PARAM_VERSION] if GLOBAL_PARAM_VERSION in self.__global_parameters else '',
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

            all_signals = set([''])
            
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
                        name, value = map(lambda s: s.strip(), line.split(GLOBAL_PARAM_SEPARATOR))
                        name = name.lower()
                        if name in GLOBAL_PARAM_ALL:
                            self.__global_parameters[name] = value

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
            uniq_states = set([])
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
                        raise ParserError('The graph {} has state {} ({}->) with empty external transition!\n'.format(self.__graph_file,
                                                                                                                      element.get_id(),
                                                                                                                      source_state.get_name()))
                    self.__check_trigger_and_behavior(element.get_id(), a.get_trigger(), a.get_guard(), a.get_behavior())
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
                        raise ParserError('The graph {} has state {} with empty name!\n'.format(self.__graph_file,
                                                                                                element.get_id()))
                    if state_name.find(' ') >= 0:
                        raise ParserError('The graph {} has state {} with spaces in name "{}"!\n'.format(self.__graph_file,
                                                                                                         element.get_id(),
                                                                                                         state_name))
                    full_name = self.__get_state_name(element)
                    if full_name in uniq_states:
                        raise ParserError('The graph {} has two states with the same qualfied name {}!\n'.format(self.__graph_file,
                                                                                                                 full_name))
                    uniq_states.add(full_name)
                    for a in element.get_actions():
                        if a.get_type() == CyberiadaML.actionTransition:
                            if len(a.get_trigger()) == 0:
                                raise ParserError('The graph {} has state {} with empty trigger in int.trans.!\n'.format(self.__graph_file,
                                                                                                                         element.get_id()))
                            self.__check_trigger_and_behavior(full_name, a.get_trigger(), a.get_guard(), a.get_behavior())
                            if a.has_trigger():
                                signal_name = self.__parse_trigger(a.get_trigger())[0]
                                if signal_name not in all_signals:
                                    raise ParserError('The graph {} has undefined event {}!\n'.format(self.__graph_file,
                                                                                              signal_name))
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

        except CyberiadaML.Exception as e:
            raise ParserError('Unexpected CyberiadaML exception: {}\n{}\n'.format(e.__class__,
                                                                                  traceback.format_exc()))
    def __check_trigger_and_behavior(self, context, trigger, guard, behavior):
        pass

    @classmethod
    def __w(cls, f, s):
        f.write(s)
    @classmethod
    def __w4(cls, f, s):
        f.write(' ' * 4 + s)
    @classmethod
    def __w8(cls, f, s):
        f.write(' ' * 8 + s)

    def __insert_template(self, f, template, filename):
        if template not in self.__template_handlers:
            raise GeneratorError('Cannot insert template "{}" in file {}: template not found!\n'.format(template, filename))
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
                    while len(line) > 0:
                        match = TEMPLATE_RE.search(line)
                        if match:
                            re_start, re_end = match.span()
                            template = match.group(1)
                            self.__w(f, line[0:re_start])
                            self.__insert_template(f, template, template_file)
                            line = line[re_end:]
                        else:
                            self.__w(f, line)
                            break
                    self.__w(f, '\n')

    def __write_generator_info(self, f):
        self.__w(f, '# The SM class {} based on {} file\n'.format(self.__sm_name_cap, self.__graph_file))
        self.__w(f, '# Generated by HSM-to-ROS2 script version {}'.format(self.VERSION))

    @classmethod
    def __get_state_name(cls, state):
        return state.get_qualified_name().replace('::', '_')
    @classmethod
    def __parse_trigger(cls, trigger):
        if trigger.find('(') > 0:
            idx1 = trigger.find('(')
            idx2 = trigger.find(')')
            return trigger[0:idx1], trigger[idx1+1:idx2]
        return trigger, None

    def __write_imports(self, f):
        for module in self.__hsm_modules:
            self.__w(f, 'import hsm_controller.{lm}_caller.{m} as {m}\n'.format(lm=module.lower(),
                                                                            m=module))
        self.__w(f, '\n')

    def __write_entry_handler(self, f, state_name, entry, behavior):
        handler_name = 'on_st_{}_{}'.format(state_name, entry)
        self.__w(f, '\n')
        self.__w4(f, 'def {}(self, *_):\n'.format(handler_name))
        # self.__w4(f, 'def {}(self, state, event):\n'.format(handler_name))
        for line in behavior.split('\n'):
            self.__w8(f, line + '\n')

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
        self.__w(f, '\n')
        self.__w4(f, '# Entry & Exit Handlers:\n')
        for ch in self.__graph.get_children():
            if ch.get_type() in (CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState):
                self.__write_entries_recursively(f, ch)

    @classmethod
    def __write_guard_handler(cls, f, trigger_name, condition, argument):
        handler_name = "is_{}".format(trigger_name)
        cls.__w(f, '\n')
        # cls.__w4(f, "def {}(self, state, event):\n".format(handler_name))
        cls.__w4(f, "def {}(self, *_):\n".format(handler_name))
        if argument:
            cls.__w8(f, '{} = event.cargo["value"]\n'.format(argument))
        cls.__w8(f, 'return ({})\n'.format(condition))

    @classmethod
    def __write_trigger_action(cls, f, trigger_name, behavior, argument):
        handler_name = "on_{}".format(trigger_name)
        cls.__w(f, '\n')
        # cls.__w4(f, 'def {}(self, state, event):\n'.format(handler_name))
        cls.__w4(f, 'def {}(self, *_):\n'.format(handler_name))
        if argument:
            cls.__w8(f, '{} = event.cargo["value"]\n'.format(argument))
        for line in behavior.split('\n'):
            cls.__w8(f, line + '\n')

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
                name, argument = TICK_EVENT, None
            trigger_name = '{}_TO_{}_{}'.format(self.__get_state_name(state),
                                                target_name,
                                                name)
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

    def __write_handlers(self, f, state_name):
        if state_name not in self.__handlers:
            return
        handlers_str = map(lambda i: '"{}": {}'.format(*i), self.__handlers[state_name].items())
        self.__w8(f, 'st_{}.handlers = '.format(state_name) +
                  '{' + ', '.join(handlers_str) + '}\n')

    def __write_states(self, f):
        self.__w(f, '\n')
        self.__w8(f, '# Hierarchical States:\n')
        self.__w8(f, 'st_initial = pysm.State("initial")\n')
        self.__w8(f, 'self.__sm.add_state(st_initial, initial=True)\n')
        if self.__final_states:
            self.__w8(f, 'st_terminate = pysm.State("terminate")\n')
            self.__w8(f, 'self.__sm.add_state(st_terminate)\n')
            self.__w8(f, 'st_terminate.handlers = {"enter": self.terminate}\n')
        for ch in self.__graph.get_children():
            if ch.get_type() in (CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState):
                self.__write_states_recursively(f, ch, 'self.__sm', ch.get_id() == self.__initial.get_id())

    def __write_states_recursively(self, f, state, parent_var, initial):
        state_name = self.__get_state_name(state)
        state_var = 'st_{}'.format(state_name)
        if state.get_type() == CyberiadaML.elementCompositeState:
            sm_class = "StateMachine"
        else:
            sm_class = "State"
        self.__w8(f, '{} = pysm.{}("{}")\n'.format(state_var, sm_class, state_name))
        self.__w8(f, '{}.add_state({}{})\n'.format(parent_var, state_var,
                                                   ', initial=True' if initial else ''))
        self.__write_handlers(f, state_name)
        if state.get_type() == CyberiadaML.elementCompositeState:
            initial_id = self.__initial_states[state.get_id()]
            for ch in state.get_children():
                if ch.get_type() in (CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState):
                    self.__write_states_recursively(f, ch, state_var, ch.get_id() == initial_id)

    def __write_events(self, f):
        self.__w(f, '\n')
        self.__w8(f, '# Events:\n\n')
        self.__w8(f, 'InitEvent = pysm.Event("{}")\n'.format(INIT_EVENT))
        for s, v in self.__sm_signals.items():
            self.__w8(f, '{} = "{}"\n'.format(v, s))
            self.__w8(f, '{ev}Event = pysm.Event({ev})\n'.format(ev=v))
        signals_str = map(lambda i: '"{}": {}Event'.format(*i), self.__sm_signals.items())
        self.__w8(f, 'self.__events = {{"{}": InitEvent, {}}}\n'.format(INIT_EVENT, ', '.join(signals_str)))

    def __write_transitions(self, f):
        self.__w(f, '\n')
        self.__w8(f, '# Internal transitions:\n\n')
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
                    self.__w8(f, '{}.add_transition({})\n'.format(owner, ', '.join(parts)))

        self.__w(f, '\n')
        self.__w8(f, '# External transitions:\n\n')
        parts = ['st_initial',
                 'st_{}'.format(self.__get_state_name(self.__initial)),
                 'events=["{}"]'.format(INIT_EVENT)]
        if self.__initial_behavior:
            parts.append('action=self.on_initial')
        self.__w8(f, 'self.__sm.add_transition({})\n'.format(', '.join(parts)))

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
                name, _ = TICK_EVENT, None
            trigger_name = '{}_TO_{}_{}'.format(source_name,
                                                target_name,
                                                name)
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
            self.__w8(f, '{}.add_transition({})\n'.format(owner, ', '.join(parts)))

    def generate_code(self):
        for tmpl in os.listdir(TEMPLATES_DIR):
            tmpl_file = os.path.join(TEMPLATES_DIR, tmpl)
            if tmpl.find(TEMPLATES_EXTENSION) <= 0 or not os.path.isfile(tmpl_file):
                continue
            if tmpl.find(CONTROLLER_SCRIPT) == 0:
                target_file = os.path.join(SCRIPT_TARGET_DIR, self.__sm_name_lo + '.py')
            else:
                target_file = os.path.join(SETUP_TARGET_DIR, tmpl.replace(TEMPLATES_EXTENSION, ''))
            print('Writing {} as {}'.format(tmpl, target_file))
            self.__apply_template(tmpl_file, target_file)
