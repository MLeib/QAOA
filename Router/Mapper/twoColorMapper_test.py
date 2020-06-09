from unittest import TestCase

import networkx as nx
import dimod

from Devices.quantum_hardware import Grid2dQPU

from Router.Mapper.twoColorMapper import *
from Router.GreedyRouter.edge_coloring import find_edge_coloring


class TestTwoColorMapper(TestCase):
    def setUp(self) -> None:
        self.test_bqms = [dimod.generators.uniform(nx.random_regular_graph(4, 36), dimod.SPIN, low=0.5, high=1.0) for _ in range(40)]
        self.qpu = Grid2dQPU(6, 6)

    def test_decompose_into_chains(self):
        for bqm in self.test_bqms:
            problem_graph = bqm.to_networkx_graph()
            color_sets = find_edge_coloring(problem_graph)
            color_sets = sorted(color_sets, key=lambda color_set: len(color_set), reverse=True)
            int_gate_count = len(color_sets[0]) + len(color_sets[1])
            chains, loops = decompose_into_chains(bqm)
            alternate_int_gate_count = 0
            for chain in chains:
                alternate_int_gate_count += len(chain) - 1
            for loop in loops:
                alternate_int_gate_count += len(loop)
            self.assertEqual(int_gate_count, alternate_int_gate_count, msg='not the entire color-set got decomposed')
            #Check if no node has been assigned twice
            node_set = set()
            node_sum = 0
            for chain in chains:
                self.assertTrue(len(chain) > 1, msg='chain found with a single element')
                node_set.update(chain)
                node_sum += len(chain)
            for loop in loops:
                self.assertTrue(len(loop) > 1, msg='loop found with single element')
                node_set.update(loop)
                node_sum += len(loop)
            self.assertEqual(node_sum, len(node_set), msg="At least a node has been assigned at least twice")
            #Check if all nodes in the chains and nodes are actually adjacent to each other in the problem_graph
            for chain in chains:
                for log_qb0, log_qb1 in zip(chain[:-1], chain[1:]):
                    self.assertTrue(problem_graph.has_edge(log_qb0, log_qb1),
                                    msg="adjacent nodes in chain are not adjacent in problem_graph")
            for loop in loops:
                for log_qb0, log_qb1 in zip(loop[:-1], loop[1:]):
                    self.assertTrue(problem_graph.has_edge(log_qb0, log_qb1),
                                    msg="adjacent nodes in loop are not adjacent in problem_graph")
                self.assertTrue(problem_graph.has_edge(loop[-1], loop[0]),
                                msg="first and last node of loop are not adjacent in problem_graph")

    def test_embed_chain(self):
        for bqm in self.test_bqms:
            chains, loops = decompose_into_chains(bqm)
            qpu_graph = self.qpu.graph
            for chain in chains:
                embedding = embed_chain(chain, qpu_graph.copy())
                rev_embedding = {log_qb: hard_qb for hard_qb, log_qb in embedding.items()}
                for log_qb0, log_qb1 in zip(chain[:-1], chain[1:]):
                    self.assertTrue(qpu_graph.has_edge(rev_embedding[log_qb0], rev_embedding[log_qb1]))

    def test_twoColorMapper(self):
        for bqm in self.test_bqms:
            mapping, int_layers = twoColorMapper(bqm, self.qpu)
            int_gate_count = [len(int_layers[0]), len(int_layers[1])]
            for layer_ind, int_layer in enumerate(int_layers):
                qbs_set = set()
                for int_gate in int_layer:
                    qbs_set.add(list(int_gate)[0])
                    qbs_set.add(list(int_gate)[1])
                self.assertEqual(2 * int_gate_count[layer_ind], len(qbs_set), msg='int_layer involves at least one qubit twice')
            int_partners = 0
            problem_graph = bqm.to_networkx_graph()
            for hard_qb0, hard_qb1 in self.qpu.graph.edges():
                log_qb0, log_qb1 = mapping.hard2log[hard_qb0], mapping.hard2log[hard_qb1]
                if problem_graph.has_edge(log_qb0, log_qb1):
                    int_partners += 1
            self.assertTrue(int_partners >= int_gate_count[0] + int_gate_count[1],
                            msg='twoColorMapper did not map as many logical qubits next to each other as advertised')







