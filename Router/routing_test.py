from unittest import TestCase
import copy as cp

import cirq
import networkx as nx
import dimod
from numpy.random import choice

from Router.routing import Layer, Routing
from Router.mapping import Mapping
from Devices.quantum_hardware import Grid2dQPU


class TestLayer(TestCase):
    def setUp(self) -> None:
        qpu = Grid2dQPU(5, 4)
        self.layer = Layer(qpu)
        self.graph = qpu.graph
        matching = nx.maximal_matching(self.graph)
        while not nx.is_perfect_matching(self.graph, matching):
            self.graph = nx.random_regular_graph(4, 20)
            matching = nx.maximal_matching(self.graph)
        self.matching_gates = set()
        for gate in matching:
            self.matching_gates.add(frozenset(gate))

    def validity_test(self):
        for hard_qb in self.layer.gates.nodes():
            involved_in_gates = 0
            for neighbor in self.layer.gates.neighbors(hard_qb):
                if self.layer.gates[neighbor][hard_qb]['swap'] or self.layer.gates[neighbor][hard_qb]['int']:
                    involved_in_gates += 1
            if involved_in_gates > 1:
                return False
        return True

    def test_apply_gate(self):
        size = len(self.matching_gates) // 3
        for _ in range(size):
            self.layer.apply_int_gate(self.matching_gates.pop())
            self.assertTrue(self.validity_test(), msg="after adding int gate the layer was not valid any more")
        for _ in range(size):
            self.layer.apply_swap_gate(self.matching_gates.pop())
            self.assertTrue(self.validity_test(), msg="after adding swap gate the layer was not valid any more")
        for gate in self.matching_gates:
            self.layer.apply_swap_gate(gate)
            self.layer.apply_int_gate(gate)
            self.assertTrue(self.validity_test(), msg="after adding a combined swap-int gate the layer was not valid any more")

    def test_not_hardware_supported_gates(self):
        nodes = list(self.graph.nodes())
        for _ in range(100):
            gate = frozenset(choice(nodes, 2, replace=False))
            if not self.layer.gates.has_edge(*gate):
                self.assertFalse(self.layer.int_gate_applicable(gate), msg="does not recognize unsupported (by hardware) int gate")
                self.assertFalse(self.layer.swap_gate_applicable(gate), msg="does not recognize unsupported (by hardware) swap gate")

    def test_reject_gates_with_already_busy_qbs(self):
        self.layer.apply_int_gate(frozenset((cirq.GridQubit(1, 1), cirq.GridQubit(1, 2))))
        for neighbor in self.layer.gates.neighbors(cirq.GridQubit(1, 1)):
            gate = frozenset((neighbor, cirq.GridQubit(1, 1)))
            self.assertFalse(self.layer.int_gate_applicable(gate), msg="does not recognize invalid int gate on busy qubits")

    def test_invalid_application_of_double_int_gate(self):
        gate = frozenset((cirq.GridQubit(1, 1), cirq.GridQubit(1, 2)))
        self.layer.apply_int_gate(gate)
        self.assertFalse(self.layer.int_gate_applicable(gate), msg="does not recognize invalid int gate on busy qubits")

    def test_correct_handling_of_double_swap_gate(self):
        hard_qb0, hard_qb1 = cirq.GridQubit(1, 1), cirq.GridQubit(1, 2)
        gate = frozenset((hard_qb0, hard_qb1))
        self.layer.apply_swap_gate(gate)
        self.layer.apply_swap_gate(gate)
        self.assertFalse(self.layer.gates[hard_qb0][hard_qb1]['swap'], msg="did not delete swap operation after second application")


class TestRouting(TestCase):
    def setUp(self) -> None:
        gr = nx.grid_2d_graph(2, 2)
        gr.add_edge((0, 0), (1, 1))
        self.qpu = Grid2dQPU(2, 2)
        self.problem_instance = dimod.generators.random.uniform(gr, dimod.SPIN)
        init_map = {cirq.GridQubit(*loc): loc for loc in self.problem_instance.variables}
        self.initial_mapping = Mapping(self.qpu, self.problem_instance, initial_mapping=init_map)
        self.routing = Routing(self.problem_instance, self.qpu, cp.deepcopy(self.initial_mapping))

    def test_apply_swap(self) -> None:
        self.routing.apply_swap(frozenset((cirq.GridQubit(0, 0), cirq.GridQubit(1, 0))))
        self.assertEqual(self.initial_mapping.hard2log[cirq.GridQubit(0, 0)], self.routing.mapping.hard2log[cirq.GridQubit(1, 0)],
                         msg="application of swap gate did not update mapping")
        self.assertEqual(self.initial_mapping.hard2log[cirq.GridQubit(1, 0)], self.routing.mapping.hard2log[cirq.GridQubit(0, 0)],
                         msg="application of swap gate did not update mapping")
        self.assertTrue(self.routing.layers[0].gates[cirq.GridQubit(0, 0)][cirq.GridQubit(1, 0)]['swap'],
                      msg="did not add swap gate to layer")
        self.routing.apply_swap(frozenset((cirq.GridQubit(0, 1), cirq.GridQubit(1, 1))))
        self.assertEqual(self.initial_mapping.hard2log[cirq.GridQubit(0, 1)], self.routing.mapping.hard2log[cirq.GridQubit(1, 1)],
                         msg="application of swap gate did not update mapping")
        self.assertEqual(self.initial_mapping.hard2log[cirq.GridQubit(1, 1)], self.routing.mapping.hard2log[cirq.GridQubit(0, 1)],
                         msg="application of swap gate did not update mapping")
        self.assertTrue(self.routing.layers[0].gates[cirq.GridQubit(0, 1)][cirq.GridQubit(1, 1)]['swap'],
                      msg="did not add swap gate to layer")
        self.routing.apply_swap(frozenset((cirq.GridQubit(0, 0), cirq.GridQubit(0, 1))))
        self.assertTrue(self.routing.layers[1].gates[cirq.GridQubit(0, 0)][cirq.GridQubit(0, 1)]['swap'],
                      msg="did not add layer containing new swap gate")
        self.routing.draw()

    def test_apply_int(self) -> None:
        self.routing.apply_int(frozenset((cirq.GridQubit(0, 0), cirq.GridQubit(1, 0))))
        self.assertTrue(self.routing.layers[0].gates[cirq.GridQubit(0, 0)][cirq.GridQubit(1, 0)]['int'],
                      msg="did not add int gate to layer")
        self.assertFalse(self.routing.remaining_interactions.has_edge(cirq.GridQubit(0, 0), cirq.GridQubit(1, 0)),
                         msg='interaction has not been deleted from routing.remaining_interactions')
        self.routing.apply_int(frozenset((cirq.GridQubit(0, 1), cirq.GridQubit(1, 1))))
        self.assertTrue(self.routing.layers[0].gates[cirq.GridQubit(0, 1)][cirq.GridQubit(1, 1)]['int'],
                      msg="did not add int gate to layer")
        self.assertFalse(self.routing.remaining_interactions.has_edge(cirq.GridQubit(0, 1), cirq.GridQubit(1, 1)),
                         msg='interaction has not been deleted from routing.remaining_interactions')
        self.routing.apply_int(frozenset((cirq.GridQubit(0, 0), cirq.GridQubit(0, 1))))
        self.assertTrue(self.routing.layers[1].gates[cirq.GridQubit(0, 0)][cirq.GridQubit(0, 1)]['int'],
                      msg="did not add layer containing new int gate")
        self.assertFalse(self.routing.remaining_interactions.has_edge(cirq.GridQubit(0, 0), cirq.GridQubit(0, 1)),
                         msg='interaction has not been deleted from routing.remaining_interactions')








