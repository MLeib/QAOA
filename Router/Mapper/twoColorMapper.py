from typing import Type
import matplotlib.pyplot as plt

import dimod
import networkx as nx

from Router.GreedyRouter.edge_coloring import find_edge_coloring
from Devices.quantum_hardware import QPU
from Router.mapping import Mapping


def decompose_into_chains(problem_instance: dimod.BinaryQuadraticModel):
    problem_graph = problem_instance.to_networkx_graph()
    for log_qb in problem_graph:
        problem_graph.add_node(log_qb, endnode=False)
    problem_size = len(problem_graph)
    color_sets = find_edge_coloring(problem_graph)
    color_sets = sorted(color_sets, key=lambda color_set: len(color_set), reverse=True)
    for log_qb0, log_qb1 in problem_graph.edges():
        if frozenset((log_qb0, log_qb1)) in color_sets[0]:
            color0 = problem_graph[log_qb0][log_qb1]['color']
            break
    for log_qb0, log_qb1 in problem_graph.edges():
        if frozenset((log_qb0, log_qb1)) in color_sets[1]:
            color1 = problem_graph[log_qb0][log_qb1]['color']
            break
    def filter_edge(log_qb0, log_qb1) -> bool:
        if problem_graph[log_qb0][log_qb1]['color'] == color0:
            return True
        elif problem_graph[log_qb0][log_qb1]['color'] == color1:
            return True
        else:
            return False

    twocolor_graph = nx.subgraph_view(problem_graph, filter_edge=filter_edge)
    components = [twocolor_graph.subgraph(c).copy() for c in nx.connected_components(twocolor_graph)]
    chains, loops = [], []
    for component in components:
        deg = 3
        for node in component:
            if component.degree(node) < deg:
                node0 = node
                deg = component.degree(node)
        for neighbor in component.neighbors(node0):
            node1 = neighbor
            break
        lst = [node0, node1]
        for _ in range(len(component)-2):
            for neighbor in component.neighbors(node1):
                if neighbor is not node0:
                    node0 = node1
                    node1 = neighbor
                    lst.append(node1)
                    break
        if deg == 1:
            chains.append(lst)
        elif deg == 2:
            loops.append(lst)

    return chains, loops


def embed_chain(chain, hardware_graph: nx.Graph):
    current_deg = len(hardware_graph)
    for node in hardware_graph:
        deg = hardware_graph.degree(node)
        if deg < current_deg:
            current_node = node
    embedding = {current_node: chain[0]}
    for log_qb in chain[1:]:
        current_deg = len(hardware_graph)
        for neighbor in hardware_graph.neighbors(current_node):
            deg = hardware_graph.degree(neighbor)
            if deg < current_deg:
                new_node = neighbor
                current_deg = deg
        embedding[new_node] = log_qb
        hardware_graph.remove_node(current_node)
        current_node = new_node
        new_node = None
    hardware_graph.remove_node(current_node)
    return embedding


def twoColorMapper(problem_instance: dimod.BinaryQuadraticModel, qpu: Type[QPU]):
    chains, loops = decompose_into_chains(problem_instance)
    concatenated_chains = []
    for chain in chains:
        concatenated_chains .extend(chain)
    for loop in loops:
        concatenated_chains.extend(loop)
    embedding = {}
    hardware_chain = list(qpu.embedded_chain())[:len(concatenated_chains)]
    for hard_qb, log_qb in zip(hardware_chain, concatenated_chains):
        embedding[hard_qb] = log_qb
    mapping = Mapping(qpu, problem_instance, embedding)
    int_layer0 = []
    int_layer1 = []
    for chain in chains:
        for log_qb0, log_qb1 in zip(chain[::2], chain[1::2]):
            hard_qb0, hard_qb1 = mapping.log2hard[log_qb0], mapping.log2hard[log_qb1]
            int_layer0.append(frozenset((hard_qb0, hard_qb1)))
        for log_qb0, log_qb1 in zip(chain[1::2], chain[2::2]):
            hard_qb0, hard_qb1 = mapping.log2hard[log_qb0], mapping.log2hard[log_qb1]
            int_layer1.append(frozenset((hard_qb0, hard_qb1)))
    for loop in loops:
        for log_qb0, log_qb1 in zip(loop[::2], loop[1::2]):
            hard_qb0, hard_qb1 = mapping.log2hard[log_qb0], mapping.log2hard[log_qb1]
            int_layer0.append(frozenset((hard_qb0, hard_qb1)))
        for log_qb0, log_qb1 in zip(loop[1::2], loop[2::2]):
            hard_qb0, hard_qb1 = mapping.log2hard[log_qb0], mapping.log2hard[log_qb1]
            int_layer1.append(frozenset((hard_qb0, hard_qb1)))

    return mapping, [int_layer0, int_layer1]



