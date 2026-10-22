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

import collections
import importlib.util
import io
import os
import re
import shutil
import datetime

import CyberiadaML

GLOBAL_PARAM_VERSION = 'version'
GLOBAL_PARAM_AUTHOR = 'author'
GLOBAL_PARAM_EMAIL = 'author e-mail'
GLOBAL_PARAM_LICENSE = 'license'
GLOBAL_PARAM_ALL = (GLOBAL_PARAM_VERSION, GLOBAL_PARAM_AUTHOR, GLOBAL_PARAM_EMAIL, GLOBAL_PARAM_LICENSE)
# the package parameters in the CGML_META of the document (PNST 1044, 6.9)
META_PARAMETERS = {'version': GLOBAL_PARAM_VERSION, 'author': GLOBAL_PARAM_AUTHOR,
                   'contact': GLOBAL_PARAM_EMAIL, 'license': GLOBAL_PARAM_LICENSE}
META_NAME = 'CGML_META'

# an API module used by the diagram: CGML_COMPONENT <Module> with type/ <Module> (10.3)
COMPONENT_PREFIX = 'CGML_COMPONENT '
PARAMETER_SEPARATOR = '/'
PARAMETER_TYPE = 'type'

# the keys of the convention comments: the name of a formal comment or the first line of
# an informal one; the first two are the legacy yEd forms of CGML_META and CGML_COMPONENT
GLOBAL_PARAM_LABEL = 'global parameters'
GLOBAL_PARAM_SEPARATOR = ':'
ROS2_HSM_MODULES_LABEL = 'ros2 hsm modules'
# the expectations of a test run of the diagram, one rule per line
ROS2_HSM_TEST_LABEL = 'ros2 hsm test'

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

# EVENT [xN] [within S] | never EVENT; '#' starts a remark
TEST_RULE_RE = re.compile(r'^(?:(?P<never>never)\s+(?P<forbidden>\w+)|(?P<event>\w+)'
                          r'(?:\s+x(?P<count>\d+))?(?:\s+within\s+(?P<within>\d+(?:\.\d+)?))?)$')
TEST_RULE_REMARK = '#'
TestRule = collections.namedtuple('TestRule', 'event count within never line')


class ConvertorError(Exception):
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg

    def __str__(self):
        return self.msg


class ParserError(ConvertorError):
    # the rule and the element id let the editor point at the problem
    def __init__(self, msg, rule=None, element=None):
        ConvertorError.__init__(self, msg)
        self.rule = rule
        self.element = element


class GeneratorError(ConvertorError):
    def __init__(self, msg):
        ConvertorError.__init__(self, msg)


def comment_key(text):
    # the key ignores case, underscores, extra spaces and a trailing colon
    return ' '.join(text.replace('_', ' ').strip().rstrip(':').lower().split())


def parse_parameters(body):
    # the name/value blocks of a formal comment (PNST 1044, 6.9, 10.3.1); None when
    # a line is not a parameter
    parameters = {}
    name = None
    for line in body.split('\n'):
        if not line.strip():
            name = None
            continue
        if name is None:
            if PARAMETER_SEPARATOR not in line:
                return None
            name, value = line.split(PARAMETER_SEPARATOR, 1)
            name = name.strip()
            parameters[name] = value.strip()
        else:
            parameters[name] += '\n' + line
    return parameters


def api_event_names():
    # the events any module of the API reports, whether the diagram declares it or not
    return {name for events in HSM_EVENTS.values() for name in events.values()}


def parse_test_rules(text, element=None):
    # the rules of a 'ROS2 HSM Test' comment, its content only; within is None for
    # the whole run
    rules = []
    known = api_event_names()
    for line in text.splitlines():
        line = line.split(TEST_RULE_REMARK, 1)[0].strip()
        if not line:
            continue
        match = TEST_RULE_RE.match(line)
        if match is None:
            raise ParserError('The test rule "{}" is not EVENT [xN] [within S] '
                              'or never EVENT!\n'.format(line), 'test-rule', element)
        never = match.group('never') is not None
        event = match.group('forbidden') if never else match.group('event')
        if event not in known:
            raise ParserError('The test rule "{}" names the unknown event {}!\n'.format(line, event),
                              'test-rule', element)
        count = int(match.group('count') or 1)
        if count < 1:
            raise ParserError('The test rule "{}" expects no event; use never!\n'.format(line),
                              'test-rule', element)
        within = float(match.group('within')) if match.group('within') else None
        rules.append(TestRule(event, count, within, never, line))
    return rules


class CodeGenerator:

    VERSION = '1.0'  # generator version

    def __init__(self, graph_file, output_dir=SETUP_TARGET_DIR, force=False, quiet=False, **kwargs):
        self.__global_parameters = {}
        self.__hsm_modules = []
        # the math module is imported by the generated controller only when the
        # diagram code uses it
        self.__uses_math = False
        self.__sm_signals = {}
        self.__test_rules = []
        self.__test_comment = None
        # (element id, event) of every trigger and (element id, text) of every guard and
        # behavior, for the checks of the platforms
        self.__triggers = []
        self.__code = []
        # a transition without a trigger is treated as an error unless explicitly
        # allowed; has to be set before the graph is parsed
        self.__allow_empty_trans = kwargs.get('allow_empty_trans', False)
        # the default output directory reproduces the historical behaviour of writing
        # the package into the current directory
        self.__script_target_dir = os.path.join(output_dir, SCRIPT_TARGET_DIR)
        self.__setup_target_dir = output_dir
        self.__force = force
        self.__quiet = quiet

        self.__machine = None
        self.__load_graph(graph_file, **kwargs)

        self.__template_handlers = {
            'AUTHOR_NAME': self.__global_parameters.get(GLOBAL_PARAM_AUTHOR, ''),
            'AUTHOR_EMAIL': self.__global_parameters.get(GLOBAL_PARAM_EMAIL, ''),
            'GENERATOR_INFO': self.__write_generator_info,
            'LICENSE': self.__global_parameters.get(GLOBAL_PARAM_LICENSE, ''),
            'SM_FUNCTIONS': self.__write_functions,
            'SM_HAS_TICKS': HSM_TICK_EVENT in self.__sm_signals,
            'SM_HAS_SECONDS': HSM_TICK_1S_EVENT in self.__sm_signals,
            'SM_HAS_MINUTES': HSM_TICK_1M_EVENT in self.__sm_signals,
            'SM_HSM_OBJECTS': ', '.join("'{}'".format(m) for m in self.__hsm_modules),
            'SM_MATH_IMPORT': 'import math' if self.__uses_math else '',
            'SM_HSM_IMPORTS': self.__write_hsm_imports,
            'SM_HSM_INITS': self.__write_hsm_inits,
            'SM_MACHINE': self.__write_machine,
            'SM_NAME': self.__sm_name,
            'SM_NAME_LO': self.__sm_name_lo,
            'SM_NAME_CAP': self.__sm_name_cap,
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

            # the events of the declared modules
            all_signals = {''}.union(*(HSM_EVENTS[m].values() for m in self.__read_comments()))

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
                                          'pseudostate on the top level!\n', 'two-initial', state.get_id())
                    init_id = state.get_id()
            if init_id is None:
                raise ParserError('The graph {} has no initial pseudostate!\n'.format(self.__graph_file),
                                  'no-initial')

            # Read states and transitions
            uniq_states = set()
            self.__transitions = []

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
                        if self.__initial_behavior:
                            self.__code.append((element.get_id(), self.__initial_behavior))
                        continue
                    source_state = self.__graph.find_element_by_id(source_id)
                    if source_state.get_type() == CyberiadaML.elementInitial:
                        continue
                    a = element.get_action()
                    if len(a.get_trigger()) == 0 and not self.__allow_empty_trans:
                        raise ParserError(
                            'The graph {} has state {} ({}->) with empty external transition!\n'.format(
                                self.__graph_file, element.get_id(), source_state.get_name()),
                            'empty-transition', element.get_id())
                    self.__check_trigger_and_behavior(element.get_id(), element.get_id(), a.get_trigger(),
                                                      a.get_guard(), a.get_behavior())
                    if a.has_trigger():
                        signal_name = self.__parse_trigger(a.get_trigger())[0]
                        if signal_name not in all_signals:
                            raise ParserError('The graph {} has undefined event {}!\n'.format(self.__graph_file,
                                                                                              signal_name),
                                              'undefined-event', element.get_id())
                        else:
                            self.__sm_signals[signal_name] = None
                    else:
                        # an allowed transition without a trigger waits for the next tick
                        self.__sm_signals[HSM_TICK_EVENT] = None
                    self.__transitions.append(element)
                else:
                    state_name = element.get_name()
                    if len(state_name) == 0:
                        raise ParserError(
                            'The graph {} has state {} with empty name!\n'.format(
                                self.__graph_file, element.get_id()),
                            'empty-name', element.get_id())
                    if state_name.find(' ') >= 0:
                        raise ParserError(
                            'The graph {} has state {} with spaces in name "{}"!\n'.format(
                                self.__graph_file, element.get_id(), state_name),
                            'spaced-name', element.get_id())
                    full_name = self.__get_state_name(element)
                    if full_name in uniq_states:
                        raise ParserError(
                            'The graph {} has two states with the same qualified name {}!\n'.format(
                                self.__graph_file, full_name),
                            'duplicate-name', element.get_id())
                    uniq_states.add(full_name)
                    for a in element.get_actions():
                        if a.get_type() == CyberiadaML.actionTransition:
                            if len(a.get_trigger()) == 0:
                                raise ParserError(
                                    'The graph {} has state {} with empty trigger in int.trans.!\n'.format(
                                        self.__graph_file, element.get_id()),
                                    'empty-trigger', element.get_id())
                            self.__check_trigger_and_behavior(full_name, element.get_id(), a.get_trigger(),
                                                              a.get_guard(), a.get_behavior())
                            if a.has_trigger():
                                signal_name = self.__parse_trigger(a.get_trigger())[0]
                                if signal_name not in all_signals:
                                    raise ParserError(
                                        'The graph {} has undefined event {}!\n'.format(
                                            self.__graph_file, signal_name),
                                        'undefined-event', element.get_id())
                                else:
                                    self.__sm_signals[signal_name] = None
                        else:
                            self.__check_trigger_and_behavior(full_name, element.get_id(), None, None,
                                                              a.get_behavior())

            # Find the initial state
            if self.__initial is None:
                raise ParserError('The graph {} has no initial state!\n'.format(self.__graph_file),
                                  'no-initial-state')
            self.__initial_states = {}
            # init_parent = self.__initial.get_parent()
            # if init_parent.get_type() != CyberiadaML.elementSM:
            #     self.__initial_states[init_parent.get_id()] = self.__initial.get_id()
            # the transitions leaving an initial pseudostate are not collected with the
            # others, so the whole graph is searched here
            all_transitions = self.__graph.find_elements_by_type(CyberiadaML.elementTransition)
            for element in self.__graph.find_elements_by_type(CyberiadaML.elementInitial):
                parent = element.get_parent()
                if parent.get_id() in self.__initial_states:
                    continue
                for t in all_transitions:
                    if t.get_source_element_id() == element.get_id():
                        self.__initial_states[parent.get_id()] = t.get_target_element_id()
                        break
            for element in self.__graph.find_elements_by_type(CyberiadaML.elementCompositeState):
                if element.get_id() in self.__initial_states:
                    continue
                # a composite without an initial pseudostate starts with its first state;
                # the pseudostates of the other kinds are not states to start from
                states = [ch for ch in element.get_children()
                          if ch.get_type() in (CyberiadaML.elementSimpleState,
                                               CyberiadaML.elementCompositeState)]
                if not states:
                    raise ParserError('The graph {} has the empty composite state {}!\n'.format(
                        self.__graph_file, element.get_name()), 'empty-composite', element.get_id())
                self.__initial_states[element.get_id()] = states[0].get_id()

        except CYBERIADAML_EXCEPTIONS as e:
            raise ParserError('CyberiadaML {}: {}\n'.format(e.__class__.__name__, e), 'cyberiadaml')

    def __read_comments(self):
        # the package parameters, the API modules and the test rules of the diagram; the
        # modules are returned in the order of their declaration
        for name, key in META_PARAMETERS.items():
            value = self.__doc.meta().get_string(name)
            if value:
                self.__global_parameters[key] = value
        legacy = {}
        comments = [(c, comment_key(c.get_name()), c.get_body())
                    for c in self.__graph.find_elements_by_type(CyberiadaML.elementFormalComment)]
        for c in self.__graph.find_elements_by_type(CyberiadaML.elementComment):
            first, _, rest = c.get_body().partition('\n')
            comments.append((c, comment_key(first), rest))
        for comment, key, body in comments:
            name = comment.get_name() if comment.get_type() == CyberiadaML.elementFormalComment else ''
            if name.startswith(COMPONENT_PREFIX):
                self.__read_component(comment, name[len(COMPONENT_PREFIX):].strip(), body)
            elif key == ROS2_HSM_MODULES_LABEL:
                for line in body.splitlines():
                    if line.strip():
                        self.__add_module(line.strip(), comment)
            elif key == ROS2_HSM_TEST_LABEL:
                self.__test_comment = comment.get_id()
                self.__test_rules = parse_test_rules(body, comment.get_id())
            elif key == GLOBAL_PARAM_LABEL:
                for line in body.splitlines():
                    if GLOBAL_PARAM_SEPARATOR in line:
                        name, value = (t.strip() for t in line.split(GLOBAL_PARAM_SEPARATOR, 1))
                        if name.lower() in GLOBAL_PARAM_ALL:
                            legacy[name.lower()] = value
        # the legacy comment fills only what the metainformation leaves out
        for key, value in legacy.items():
            self.__global_parameters.setdefault(key, value)
        return self.__hsm_modules

    def __read_component(self, comment, ident, body):
        parameters = parse_parameters(body)
        if parameters is None:
            raise ParserError('The graph {} has the component {} with a line that is not '
                              'a name/ value parameter!\n'.format(self.__graph_file, ident),
                              'component-syntax', comment.get_id())
        if PARAMETER_TYPE not in parameters:
            raise ParserError('The graph {} has the component {} without a type!\n'.format(
                self.__graph_file, ident), 'component-type', comment.get_id())
        module = parameters[PARAMETER_TYPE]
        self.__add_module(module, comment)
        # the module is one per robot and the diagram code calls it by its name
        if ident != module:
            raise ParserError('The graph {} names the {} component {}; an API module is '
                              'named after its type!\n'.format(self.__graph_file, module, ident),
                              'component-id', comment.get_id())

    def __add_module(self, module, comment):
        if module not in HSM_EVENTS:
            raise ParserError('The graph {} contains unknown module "{}"!\n'.format(
                self.__graph_file, module), 'unknown-module', comment.get_id())
        if module in self.__hsm_modules:
            raise ParserError('The graph {} declares the module {} twice!\n'.format(
                self.__graph_file, module), 'duplicate-module', comment.get_id())
        self.__hsm_modules.append(module)

    def test_rules(self):
        # the expectations of a test run and the id of the comment holding them
        return self.__test_rules, self.__test_comment

    def usage(self):
        # the modules (with the implied ones), the triggers and the code of the diagram
        return list(self.__hsm_modules), list(self.__triggers), list(self.__code)

    def __check_trigger_and_behavior(self, context, element_id, trigger, guard, behavior):
        if trigger:
            self.__triggers.append((element_id, self.__parse_trigger(trigger)[0]))
        # the diagram may call only the API modules it declares: an undeclared module is
        # not imported into the generated controller and fails when the state is entered
        for text in (guard, behavior):
            if not text:
                continue
            self.__code.append((element_id, text))
            text = STRING_LITERAL_RE.sub('', text)
            if MATH_USAGE_RE.search(text):
                self.__uses_math = True
            for module in MODULE_USAGE_RE.findall(text):
                if module not in self.__hsm_modules:
                    raise ParserError('The graph {} uses the module {} in {}, '
                                      'but does not declare it!\n'.format(self.__graph_file,
                                                                          module, context),
                                      'undeclared-module', element_id)

    @classmethod
    def __w(cls, f, s):
        f.write(s)

    @classmethod
    def __w8(cls, f, s):
        f.write(' ' * 8 + s)

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
        # only the name of the diagram file is written: the path it was generated from is
        # a property of the machine which ran the generator and not of the controller
        self.__w(f, '# The SM class {} based on the {} diagram\n'.format(
            self.__sm_name_cap, os.path.basename(self.__graph_file)))
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

    @classmethod
    def __unique(cls, names, name):
        # the second handler of the same name gets the suffix _2 and so on
        names[name] = names.get(name, 0) + 1
        return name if names[name] == 1 else '{}_{}'.format(name, names[name])

    @classmethod
    def __pseudostate_id(cls, parent_name, kind, number=1):
        # the pseudostates of the machine are named by their kind, of a composite after it
        ident = kind if parent_name is None else '{}.{}'.format(parent_name, kind)
        return ident if number == 1 else '{}_{}'.format(ident, number)

    def __function(self, name, code, argument=None, guard=False):
        # a piece of the diagram code as a function of the module: hsmd calls it without
        # arguments in the module globals, the event it processes is the global event
        lines = ['', '', 'def {}():'.format(name)]
        if argument:
            lines.append(' ' * 4 + '{} = event.value'.format(argument))
        if guard:
            lines.append(' ' * 4 + 'return ({})'.format(code.strip()))
        else:
            lines += [(' ' * 4 + line).rstrip() for line in code.rstrip().split('\n')]
        self.__functions += lines
        return name

    def __reaction_args(self, action, trigger_name, argument):
        args = []
        if action.has_guard():
            args.append('guard=' + self.__function('is_' + trigger_name, action.get_guard(), argument, True))
        if action.has_behavior():
            args.append('action=' + self.__function('on_' + trigger_name, action.get_behavior(), argument))
        return args

    @classmethod
    def __call_lines(cls, indent, call, args, end):
        # call(args)end on one line, or the arguments one per line
        line = '{}{}({}){}'.format(indent, call, ', '.join(args), end)
        if len(line) <= MAX_LINE_LENGTH or len(args) < 2:
            return [line]
        lines = [indent + call + '(']
        for i, arg in enumerate(args):
            lines.append(indent + ' ' * 4 + arg + (',' if i + 1 < len(args) else ')' + end))
        return lines

    @classmethod
    def __nested_lines(cls, indent, call, args, groups, end):
        # a declaration with the lists of the nested declarations, one item a line:
        # call(args, key=[ items ], key=[ items ])end; a group is (key, items(indent))
        if not groups:
            return cls.__call_lines(indent, call, args, end)
        first = indent + call + '(' + ', '.join(args) + ', ' + groups[0][0] + '=['
        lines = []
        if len(first) > MAX_LINE_LENGTH:
            # the long head goes one argument per line, the items one level deeper
            lines = [indent + call + '('] + [indent + ' ' * 4 + arg + ',' for arg in args]
            for key, items in groups:
                lines.append(indent + ' ' * 4 + key + '=[')
                lines += items(indent + ' ' * 8)
                lines.append(indent + ' ' * 4 + '],')
            lines[-1] = indent + ' ' * 4 + '])' + end
            return lines
        for i, (key, items) in enumerate(groups):
            head = indent + call + '(' + ', '.join(args) + ', ' if i == 0 else indent + '], '
            lines.append(head + key + '=[')
            lines += items(indent + ' ' * 4)
        return lines + [indent + '])' + end]

    def __vertex_id(self, element):
        if element.get_type() == CyberiadaML.elementFinal:
            return self.__final_ids[element.get_id()]
        return self.__get_state_name(element)

    def __initial_lines(self, parent, parent_name, indent):
        # one initial pseudostate in every machine and composite: the one of the diagram
        # or, when it has none, the one leading to its first state
        ident = self.__pseudostate_id(parent_name, 'initial')
        if parent_name is None:
            target, behavior = self.__initial, self.__initial_behavior
        else:
            target = self.__graph.find_element_by_id(self.__initial_states[parent.get_id()])
            behavior = None
        args = [repr(ident), repr(self.__vertex_id(target))]
        if behavior:
            name = 'initial' if parent_name is None else '{}_initial'.format(parent_name)
            args.append('action=' + self.__function('on_' + name, behavior))
        self.__initial_transitions.append(args)
        return [indent + 'hsmd.Initial(id={!r}),'.format(ident)]

    def __children_lines(self, parent, parent_name, indent):
        lines = self.__initial_lines(parent, parent_name, indent)
        finals = 0
        for ch in parent.get_children():
            if ch.get_type() == CyberiadaML.elementFinal:
                finals += 1
                ident = self.__pseudostate_id(parent_name, 'final', finals)
                self.__final_ids[ch.get_id()] = ident
                lines.append(indent + 'hsmd.Final(id={!r}),'.format(ident))
        for ch in parent.get_children():
            if ch.get_type() in (CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState):
                lines += self.__state_lines(ch, indent)
        return lines

    def __state_lines(self, state, indent):
        state_name = self.__get_state_name(state)
        args = [repr(state.get_name())]
        if state_name != state.get_name():
            args.append('id={!r}'.format(state_name))
        names = {}
        internal = []
        for kind, entry in ((CyberiadaML.actionEntry, 'enter'), (CyberiadaML.actionExit, 'exit')):
            handlers = [self.__function(self.__unique(names, 'on_st_{}_{}'.format(state_name, entry)),
                                        a.get_behavior())
                        for a in state.get_actions() if a.get_type() == kind]
            if handlers:
                key = 'entry' if entry == 'enter' else 'exit'
                args.append('{}={}'.format(key, handlers[0] if len(handlers) == 1 else
                                           '[' + ', '.join(handlers) + ']'))
        for a in state.get_actions():
            if a.get_type() == CyberiadaML.actionTransition:
                name, argument = self.__parse_trigger(a.get_trigger())
                trigger_name = self.__unique(names, '{}_{}'.format(state_name, name))
                internal.append([repr(name)] + self.__reaction_args(a, trigger_name, argument))
        groups = []
        if internal:
            groups.append(('internal', lambda i: [line for on in internal
                                                  for line in self.__call_lines(i, 'hsmd.On', on, ',')]))
        if state.get_type() == CyberiadaML.elementCompositeState:
            groups.append(('states', lambda i: self.__children_lines(state, state_name, i)))
        return self.__nested_lines(indent, 'hsmd.State', args, groups, ',')

    def __transition_lines(self, indent):
        # the transitions of the initial pseudostates are collected with the states
        lines = [line for args in self.__initial_transitions
                 for line in self.__call_lines(indent, 'hsmd.Transition', args, ',')]
        names = {}
        for t in self.__transitions:
            source_name = self.__get_state_name(self.__graph.find_element_by_id(t.get_source_element_id()))
            target = self.__graph.find_element_by_id(t.get_target_element_id())
            target_name = 'terminate' if target.get_type() == CyberiadaML.elementFinal else \
                self.__get_state_name(target)
            a = t.get_action()
            if a.has_trigger():
                name, argument = self.__parse_trigger(a.get_trigger())
            else:
                # an allowed transition without a trigger waits for the next tick
                name, argument = HSM_TICK_EVENT, None
            trigger_name = self.__unique(names, self.__transition_name(source_name, target_name, name))
            args = [repr(source_name), repr(self.__vertex_id(target)), repr(name)]
            args += self.__reaction_args(a, trigger_name, argument)
            lines += self.__call_lines(indent, 'hsmd.Transition', args, ',')
        return lines

    def __build_machine(self):
        # the functions of the diagram code and the hsmd declaration of the machine
        if self.__machine is not None:
            return
        self.__functions = []
        self.__initial_transitions = []
        self.__final_ids = {}
        # the states go first: they name the pseudostates the transitions refer to
        self.__machine = self.__nested_lines('', 'machine = hsmd.Machine', [repr(self.__sm_name)],
                                             [('states', lambda i: self.__children_lines(self.__graph, None, i)),
                                              ('transitions', self.__transition_lines)], '')

    def __write_functions(self, f):
        self.__build_machine()
        for line in self.__functions:
            self.__w(f, line + '\n')

    def __write_machine(self, f):
        self.__build_machine()
        self.__w(f, '\n\n')
        for line in self.__machine:
            self.__w(f, line + '\n')

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

    def __remove_other_controllers(self):
        # the setup files declare the controller of this diagram only, so with force the
        # controller another diagram left in the package is removed as dead code
        target_dir = self.__script_target_dir
        if not self.__force or not os.path.isdir(target_dir):
            return
        own = self.__sm_name_lo + '.py'
        for name in sorted(os.listdir(target_dir)):
            if name.endswith('.py') and name not in LIBRARY_FILES and name != own:
                if not self.__quiet:
                    print('Removing the controller {}'.format(name))
                os.remove(os.path.join(target_dir, name))

    def generate_code(self):
        controller_template = CONTROLLER_SCRIPT + TEMPLATES_EXTENSION
        self.__remove_other_controllers()
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
