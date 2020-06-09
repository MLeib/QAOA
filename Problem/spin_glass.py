from typing import Callable, List

import dimod
import networkx as nx


def spin_glass(graph: nx.Graph, interaction_dist: Callable[[int], List[float]]) -> dimod.BinaryQuadraticModel:
    int_arr = interaction_dist(graph.size())
    bqm = dimod.BinaryQuadraticModel.empty(dimod.SPIN)
    for u, v in graph.edges():
        bqm.add_interaction(u, v, int_arr.pop())
    return bqm


def max_cut(graph: nx.Graph) -> dimod.BinaryQuadraticModel:
    def int_dist(size):
        return [1] * size
    return spin_glass(graph, int_dist)
