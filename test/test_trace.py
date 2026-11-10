# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The trace of the controller: the diagram ids and the step messages
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

import importlib
import sys

import hsmd
import hsmd.session
import pytest

import hsm_stubs
from conftest import diagrams, examples

pytestmark = pytest.mark.unit

VALID = diagrams('valid')
EXAMPLES = examples()


def last_step(node, now=0.0):
    # the message of the controller's last step, as the tracer publishes it
    trace = importlib.import_module('hsm_controller.trace')
    outcomes, error = node.steps[-1]
    message = trace.step_message(hsmd.session, hsm_stubs.dispatcher(node), outcomes,
                                 node.records, now, node.elements, error)
    del node.records[:]
    return message


def test_the_elements_name_the_states_and_the_transitions(controller):
    node, _ = controller(VALID['nested'])
    module = sys.modules[type(node).__module__]
    assert node.elements is module.ELEMENTS
    assert module.ELEMENTS == {
        'outer': 'nOuter', 'outer_middle': 'nMiddle', 'outer_middle_inner': 'nInner',
        'outer_middle_inner2': 'nInner2', 'outer_sibling': 'nSibling',
        'e0': 'e0', 'e1': 'e1', 'e2': 'e2', 'e3': 'e3', 'e4': 'e4'}


def test_the_start_is_a_step(controller):
    node, _ = controller(VALID['nested'])
    assert last_step(node) == {'time': 0.0, 'history': [], 'fired': ['e0', 'e1', 'e2'],
                               'active': ['nOuter', 'nMiddle', 'nInner'], 'finished': False}


def test_an_event_is_a_step_with_its_history(controller):
    node, _ = controller(VALID['minimal'])
    last_step(node)
    node.dispatch_event('TIMER_TICK', None)
    assert last_step(node, 1.25) == {
        'time': 1.25, 'fired': ['e1'], 'active': ['nB'], 'finished': False,
        'history': [{'event': 'TIMER_TICK', 'time': 1.25, 'origin': 'system',
                     'outcome': 'fired', 'fired': ['e1']}]}


def test_a_tick_firing_nothing_is_no_step(controller):
    node, _ = controller(VALID['minimal'])
    node.dispatch_event('TIMER_TICK', None)
    last_step(node)
    node.dispatch_event('TIMER_TICK', None)
    assert last_step(node) is None
    node.dispatch_event('MOVE_COMPLETED', None)
    assert last_step(node)['history'][0]['outcome'] == hsmd.DROPPED


def test_an_internal_transition_marks_its_state(controller):
    node, _ = controller(EXAMPLES['move-along-traj'], {'Storage.points': [[1.0, 2.0]]})
    last_step(node)
    node.dispatch_event('POINT_PASSED', None)
    message = last_step(node)
    assert message['fired'] == ['n2::n0::n0']
    assert message['history'][0]['fired'] == ['n2::n0::n0']


def test_a_completion_comes_from_the_model_and_an_error_ends_the_trace(controller):
    node, _ = controller(VALID['minimal'])
    trace = importlib.import_module('hsm_controller.trace')
    completion = hsmd.Outcome(hsmd.Event(''), [])
    message = trace.step_message(hsmd.session, hsm_stubs.dispatcher(node), [completion], [],
                                 0.5, node.elements, 'the code failed')
    assert message['history'][0]['origin'] == 'model'
    assert (message['finished'], message['error']) == (True, 'the code failed')
