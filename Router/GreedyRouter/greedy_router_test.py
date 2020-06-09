from unittest import TestCase
import copy as cp

import networkx as nx
import cirq
import dimod

from Router.routing import Routing
from Router.mapping import Mapping
from Router.GreedyRouter.greedy_router import *
from Router.GreedyRouter.edge_coloring import find_edge_coloring

from Devices.quantum_hardware import Grid2dQPU


class TestGreedyRouter(TestCase):
    def setUp(self) -> None:
        self.bqm_arr = [dimod.generators.uniform(nx.random_regular_graph(4, 16), dimod.SPIN, low=0.5, high=1.0) for _ in range(10)]
        self.qpu = Grid2dQPU(4, 4)

    def test_int_pair_mapper(self):
        for bqm in self.bqm_arr:
            color_sets = find_edge_coloring(bqm.to_networkx_graph())
            mapping, int_layer = int_pair_mapper(self.qpu, bqm, color_sets[0])
            for color_pair in color_sets[0]:
                hard_qb0, hard_qb1 = mapping.log2hard[list(color_pair)[0]], mapping.log2hard[list(color_pair)[1]]
                self.assertTrue(self.qpu.graph.has_edge(hard_qb0, hard_qb1), msg='Mapping did not map pairs on adjacent sites of the qpu')

    def test_int_pair_distance(self):
        for bqm in self.bqm_arr:
            color_sets = find_edge_coloring(bqm.to_networkx_graph())
            for color_set in color_sets:
                mapping, int_layer = int_pair_mapper(self.qpu, bqm, color_set)
                route = Routing(bqm, self.qpu, mapping)
                self.assertEqual(0, int_pair_distance(route, color_set), msg='does not correctly calculate the total int_pair distance')

    def test_int_pair_distance_change(self):
        qpu = Grid2dQPU(2, 2)
        bqm = dimod.generators.randint(qpu.graph, dimod.SPIN)
        route = Routing(bqm, qpu)
        log_qb0 = route.mapping.hard2log[cirq.GridQubit(0, 0)]
        log_qb1 = route.mapping.hard2log[cirq.GridQubit(0, 1)]
        int_pairs = {frozenset((log_qb0, log_qb1))}
        swap = frozenset((cirq.GridQubit(0, 0), cirq.GridQubit(0, 1)))
        self.assertEqual(0, int_pair_distance_change(route, int_pairs, swap), msg='swap distance did change after swap on interaction pair')
        log_qb0 = route.mapping.hard2log[cirq.GridQubit(0, 0)]
        log_qb1 = route.mapping.hard2log[cirq.GridQubit(1, 1)]
        int_pairs = {frozenset((log_qb0, log_qb1))}
        swap = frozenset((cirq.GridQubit(0, 0), cirq.GridQubit(1, 0)))
        self.assertEqual(1, int_pair_distance_change(route, int_pairs, swap), msg='swap distance change is incorrect')
        log_qb0 = route.mapping.hard2log[cirq.GridQubit(0, 1)]
        log_qb1 = route.mapping.hard2log[cirq.GridQubit(1, 0)]
        int_pairs.add(frozenset((log_qb0, log_qb1)))
        self.assertEqual(2, int_pair_distance_change(route, int_pairs, swap), msg='swap distance change is incorrect')

    def test_execute_all_possible_int_gates(self):
        qpu = Grid2dQPU(2, 2)
        linear = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
        quadratic = {(0, 1): 1, (1, 2): 1, (2, 3): 1, (3, 0): 1}
        bqm = dimod.BinaryQuadraticModel(linear, quadratic, 0.0, dimod.SPIN)
        initial_mapping_dict = {cirq.GridQubit(0, 0): 0,
                           cirq.GridQubit(1, 0): 1,
                           cirq.GridQubit(0, 1): 2,
                           cirq.GridQubit(1, 1): 3}
        mapping = Mapping(qpu, bqm, partial_initial_mapping=initial_mapping_dict)
        int_pairs = {frozenset((0, 1)), frozenset((0, 2)), frozenset((2, 3))}
        route = Routing(bqm, qpu, initial_mapping=mapping)
        gate_executed = execute_all_possible_int_gates(route, int_pairs)
        self.assertTrue(gate_executed, msg='did not execute a single int gate even though log qubits are adjacent on the qpu')
        test = route.layers[-1].gates[cirq.GridQubit(0, 0)][cirq.GridQubit(1, 0)]['int'] and route.layers[-1].gates[cirq.GridQubit(0, 1)][cirq.GridQubit(1, 1)]['int']
        self.assertTrue(test, msg='did not execute maximal possible set of int gates')

    def test_decrease_int_pair_distance(self):
        for bqm in self.bqm_arr:
            color_sets = find_edge_coloring(bqm.to_networkx_graph())
            route = Routing(bqm, self.qpu)
            dist_before = int_pair_distance(route, color_sets[0])
            gate_executed = decrease_int_pair_distance(route, color_sets[0])
            dist_after = int_pair_distance(route, color_sets[0])
            if gate_executed:
                self.assertTrue(dist_before > dist_after, msg='even though swap gate was applied the int_pair_distance did not decrease')
            else:
                self.assertEqual(dist_before, dist_after, msg='int_pair_distance did change even though no swap was applied')

    def test_greedy_pair_mapper(self):
        qpu = Grid2dQPU(2, 2)
        linear = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
        quadratic = {(0, 1): 1, (1, 2): 1, (2, 3): 1, (3, 0): 1, (0, 2): 1, (1, 3): 1}
        bqm = dimod.BinaryQuadraticModel(linear, quadratic, 0.0, dimod.SPIN)
        int_pairs = {frozenset((0, 2)), frozenset((1, 3))}
        route = Routing(bqm, qpu)
        greedy_pair_mapper(route, int_pairs)
        for pair in int_pairs:
            self.assertFalse(route.remaining_interactions.has_edge(*pair),
                             msg='did not execute interaction given in int pairs')

    def test_randomized_greedy_pair_mapper(self):
        for bqm in self.bqm_arr:
            color_sets = find_edge_coloring(bqm.to_networkx_graph())
            route = Routing(bqm, self.qpu)
            greedy_pair_mapper(route, color_sets[0])
            for color_pair in color_sets[0]:
                self.assertFalse(route.remaining_interactions.has_edge(*color_pair), msg='did not execute interaction given in int pairs')

    def test_greedy_router(self):
        for bqm in self.bqm_arr:
            route = greedy_router(bqm, self.qpu)
            self.assertEqual(0, route.remaining_interactions.size(), msg='router did not finish all interactions')


