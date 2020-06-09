from unittest import TestCase

import networkx as nx
from numpy.random import choice

from Router.mapping import Mapping
from Devices.quantum_hardware import Grid2dQPU
from Problem.spin_glass import max_cut


class TestMapping(TestCase):

    def setUp(self) -> None:
        self.qpu = Grid2dQPU(4, 6)
        problem_graph = nx.random_regular_graph(3, 24)
        self.problem = max_cut(problem_graph)
        self.mapping = Mapping(self.qpu, self.problem)

    def test_validity(self):
        self.assertSetEqual(set(self.problem.variables), set(self.mapping.log2hard.keys()),
                            msg='Not every logical variable is mapped')
        for log_qb in self.problem.variables:
            hardware_qb = self.mapping.log2hard[log_qb]
            self.assertEqual(log_qb, self.mapping.hard2log[hardware_qb],
                             msg='mapping is not consistent for hard_qb -> log_qb and log_qb -> hard_qb')

    def test_swap(self):
        hard_qbs = list(self.qpu.qubits())
        log_qbs = list(self.problem.variables)
        num_vars = len(log_qbs)
        for _ in range(10):
            pair = choice(num_vars, 2, replace=False)
            hard_qb0, hard_qb1 = hard_qbs[pair[0]], hard_qbs[pair[1]]
            log_qb0, log_qb1 = self.mapping.hard2log[hard_qb0], self.mapping.hard2log[hard_qb1]
            self.mapping.swap(frozenset((hard_qb0, hard_qb1)))
            self.test_validity()
            self.assertEqual(hard_qb0, self.mapping.log2hard[log_qb1])
            self.assertEqual(hard_qb1, self.mapping.log2hard[log_qb0])
        for _ in range(10):
            pair = choice(num_vars, 2, replace=False)
            log_qb0, log_qb1 = log_qbs[pair[0]], log_qbs[pair[1]]
            hard_qb0, hard_qb1 = self.mapping.log2hard[log_qb0], self.mapping.log2hard[log_qb1]
            self.mapping.swap(frozenset((log_qb0, log_qb1)))
            self.test_validity()
            self.assertEqual(log_qb0, self.mapping.hard2log[hard_qb1])
            self.assertEqual(log_qb1, self.mapping.hard2log[hard_qb0])



