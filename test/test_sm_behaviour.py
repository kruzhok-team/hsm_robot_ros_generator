# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The behaviour of the state machine the generator builds
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

import pytest

import hsm_stubs
from conftest import controller_module, diagrams, examples, generate

VALID = diagrams('valid')
EXAMPLES = examples()


@pytest.fixture
def controller(tmp_path):
    # generate a diagram and return its controller, driven without ROS2. The results
    # of the API calls are set before the controller is built, because the entry actions
    # of the initial state run while it is being built
    counter = []

    def _controller(diagram, results=None):
        counter.append(diagram)
        package = generate(diagram, tmp_path / 'pkg{}'.format(len(counter)))
        cls, recorder = hsm_stubs.load_controller(package, controller_module(package))
        for call, value in (results or {}).items():
            recorder.result(call, value)
        return cls(), recorder
    yield _controller
    hsm_stubs.remove()


def test_initial_state_is_entered(controller):
    node, recorder = controller(VALID['minimal'])
    assert hsm_stubs.leaf_state(node) == 'first'
    # the entry action of the initial state runs while the controller is built
    assert recorder.names() == ['Debug.println']
    assert recorder.arguments('Debug.println') == [('first',)]


def test_event_moves_to_the_next_state(controller):
    node, _ = controller(VALID['minimal'])
    node.dispatch_event('TIMER_TICK', None)
    assert hsm_stubs.leaf_state(node) == 'second'


def test_unknown_event_is_ignored(controller):
    node, _ = controller(VALID['minimal'])
    node.dispatch_event('MOVE_COMPLETED', None)
    assert hsm_stubs.leaf_state(node) == 'first'


def test_ring_returns_to_the_first_state(controller):
    node, recorder = controller(VALID['cycle_ring'])
    assert hsm_stubs.leaf_state(node) == 'one'
    for expected in ('two', 'three', 'one'):
        node.dispatch_event('TIMER_TICK', None)
        assert hsm_stubs.leaf_state(node) == expected
    # every state is entered again on the second turn
    assert recorder.arguments('Debug.println') == [('one',), ('two',), ('three',), ('one',)]


def test_self_transition_re_enters_the_state(controller):
    node, recorder = controller(VALID['cycle_self'])
    assert hsm_stubs.leaf_state(node) == 'looping'
    node.dispatch_event('TIMER_TICK', None)
    assert hsm_stubs.leaf_state(node) == 'looping'
    # a transition to the state itself leaves it and enters it again
    assert recorder.arguments('Debug.println') == [('enter',), ('leave',), ('enter',)]


def test_transition_leaves_and_re_enters_a_composite(controller):
    node, _ = controller(VALID['cycle_composite'])
    assert hsm_stubs.leaf_state(node) == 'outer_inside'
    node.dispatch_event('TIMER_TICK', None)
    assert hsm_stubs.leaf_state(node) == 'outer_outside'
    node.dispatch_event('TIMER_TICK_1S', None)
    assert hsm_stubs.leaf_state(node) == 'outer_inside'


def test_nested_states_are_entered_to_the_deepest_level(controller):
    node, _ = controller(VALID['nested'])
    assert hsm_stubs.leaf_state(node) == 'outer_middle_inner'
    node.dispatch_event('TIMER_TICK', None)
    assert hsm_stubs.leaf_state(node) == 'outer_middle_inner2'
    # the transition of the enclosing composite fires from the state inside it
    node.dispatch_event('TIMER_TICK_1S', None)
    assert hsm_stubs.leaf_state(node) == 'outer_sibling'


def test_event_argument_reaches_the_action(controller):
    node, recorder = controller(VALID['timer_elapsed'])
    node.dispatch_event('TIMER_ELAPSED', 'wakeup')
    assert hsm_stubs.leaf_state(node) == 'awake'
    # the transition action prints the argument the event carried
    assert ('wakeup',) in recorder.arguments('Debug.println')


def test_guard_selects_the_transition(controller):
    node, recorder = controller(VALID['storage'], {'Storage.has_data': True})
    node.dispatch_event('TIMER_ELAPSED', None)
    assert hsm_stubs.leaf_state(node) == 'read'
    # while the storage has data the diagram stays in the reading state
    node.dispatch_event('TIMER_TICK', None)
    assert hsm_stubs.leaf_state(node) == 'read'
    recorder.result('Storage.has_data', False)
    node.dispatch_event('TIMER_TICK', None)
    assert hsm_stubs.leaf_state(node) == 'done'


def test_tick_flags_follow_the_events_used(controller):
    node, _ = controller(VALID['timer_ticks'])
    assert (node.has_ticks, node.has_seconds, node.has_minutes) == (True, True, True)
    plain, _ = controller(VALID['minimal'])
    assert (plain.has_ticks, plain.has_seconds, plain.has_minutes) == (True, False, False)


def test_declared_modules_reach_the_base_controller(controller):
    node, _ = controller(VALID['pump'])
    assert node.obj_list == ('Debug', 'Pump', 'Timer')
    assert node.object_name == 'pump_control_hsm_controller'


def test_navigation_implies_wheels(controller):
    node, _ = controller(EXAMPLES['turtle-square'])
    # the diagram declares Debug and Navigation only
    assert node.obj_list == ('Debug', 'Navigation', 'Wheels')


def test_example_cycles_through_the_square(controller):
    node, recorder = controller(EXAMPLES['turtle-square'])
    assert hsm_stubs.leaf_state(node) == 'turtle_square_four_corners_top_left'
    for expected in ('top_right', 'bottom_right', 'bottom_left', 'top_left'):
        node.dispatch_event('MOVE_COMPLETED', None)
        assert hsm_stubs.leaf_state(node) == 'turtle_square_four_corners_' + expected
    assert len(recorder.arguments('Navigation.move_to_point')) == 5


def test_example_guard_reads_the_storage(controller):
    node, recorder = controller(EXAMPLES['move-along-traj'],
                                {'Storage.next': (1.0, 2.0), 'Storage.has_data': True})
    node.dispatch_event('MOVE_COMPLETED', None)
    # with data left the diagram keeps moving to the next point
    assert recorder.arguments('Navigation.move_to_point')[-1] == (1.0, 2.0)


def test_deep_example_resolves_transitions_across_composites(controller):
    node, _ = controller(EXAMPLES['right_hand_maze_solver'])
    assert hsm_stubs.leaf_state(node) == 'right_hand_maze_solver_solver_go_farward_0'
    node.dispatch_event('COLLISION_WARNING', None)
    assert hsm_stubs.leaf_state(node) == 'right_hand_maze_solver_solver_stop_02'
    node.dispatch_event('STOP_COMPLETED', None)
    assert hsm_stubs.leaf_state(node) == 'right_hand_maze_solver_solver_left_turn_turn_left_2'
