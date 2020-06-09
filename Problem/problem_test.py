import unittest
from typing import Mapping, Any

from numpy.random import rand
import networkx as nx
import dimod


def random_problem_graph(variable_count: int=10, edge_prob: float=0.3) -> nx.Graph:
    gr = nx.fast_gnp_random_graph(variable_count, edge_prob)
    random_arr = list(rand(gr.size()))
    for u, v in gr.edges():
        gr[u][v]['bias'] = random_arr.pop()
    return gr


def random_problem_bqm(variable_count: int=10, edge_prob: float=0.3) -> dimod.BinaryQuadraticModel:
    gr = random_problem_graph(variable_count, edge_prob)
    bqm = dimod.BinaryQuadraticModel.from_networkx_graph(gr)
    return bqm


def energy_from_graph(sample: Mapping[Any, bool], graph: nx.Graph) -> float:
    energy = 0
    for u, v in graph.edges():
        energy += graph[u][v]['bias'] * (1 if sample[u] else -1) * (1 if sample[v] else -1)


class Test_spinGlass(unittest.TestCase):
    def setUp(self) -> None:
        self.problem_graph = random_problem_graph(10, 0.3)
        self.problem_bqm = dimod.BinaryQuadraticModel.from_networkx_graph(gr)

    def test_energy(self):













