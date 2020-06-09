from typing import Set, Type
from functools import lru_cache
from copy import copy

import networkx as nx
import dimod

from Router.routing import Layer, Routing
from Router.GreedyRouter import edge_coloring
from Router.mapping import Mapping
from Devices.quantum_hardware import QPU
from Router.Mapper.twoColorMapper import twoColorMapper


def int_pair_mapper(qpu: Type[QPU], problem_instance: dimod.BinaryQuadraticModel, interaction_pairs):
    hardware_graph = qpu.graph.copy()
    mapping_dict = {}
    unmapped_log_qbs = list(problem_instance.variables)
    int_layer = set()

    for interaction_pair in interaction_pairs:
        hard_qb0, hard_qb1 = list(hardware_graph.edges)[0]
        int_layer.add(frozenset((hard_qb0, hard_qb1)))
        mapping_dict[hard_qb0] = list(interaction_pair)[0]
        mapping_dict[hard_qb1] = list(interaction_pair)[1]
        hardware_graph.remove_nodes_from([hard_qb0, hard_qb1])
        unmapped_log_qbs.remove(list(interaction_pair)[0])
        unmapped_log_qbs.remove(list(interaction_pair)[1])

    for hard_qb, log_qb in zip(hardware_graph, unmapped_log_qbs):
        mapping_dict[hard_qb] = log_qb

    return Mapping(qpu, problem_instance, mapping_dict), int_layer


def int_pair_distance(routing: Routing, int_pairs: Set[frozenset]) -> int:
    r = 0
    for pair in int_pairs:
        hard_qb0, hard_qb1 = routing.mapping.log2hard[list(pair)[0]], routing.mapping.log2hard[list(pair)[1]]
        r += len(nx.shortest_path(routing.qpu.graph, hard_qb0, hard_qb1)) - 2
    return r


def int_pair_distance_change(routing: Routing, int_pairs: Set[frozenset], swap: frozenset) -> int:
    dist_before = int_pair_distance(routing, int_pairs)
    routing.apply_swap(swap)
    dist_after = int_pair_distance(routing, int_pairs)
    routing.apply_swap(swap)
    return dist_before - dist_after


def execute_all_possible_int_gates(routing: Routing, int_pairs: Set[frozenset]) -> bool:
    int_graph = nx.Graph()
    gate_executed = False
    for int_pair in int_pairs:
        hard_qb0 = routing.mapping.log2hard[list(int_pair)[0]]
        hard_qb1 = routing.mapping.log2hard[list(int_pair)[1]]
        if routing.qpu.graph.has_edge(hard_qb0, hard_qb1):
            if routing.layers[-1].int_gate_applicable(frozenset((hard_qb0, hard_qb1))):
                int_graph.add_edge(hard_qb1, hard_qb0)
                gate_executed = True
    matching = nx.maximal_matching(int_graph)
    for match in matching:
        gate = frozenset(match)
        log_qb0 = routing.mapping.hard2log[list(match)[0]]
        log_qb1 = routing.mapping.hard2log[list(match)[1]]
        int_pair = frozenset((log_qb0, log_qb1))
        routing.apply_int(gate)
        int_pairs.remove(int_pair)
    return gate_executed


def decrease_int_pair_distance(routing: Routing, int_pairs: Set[frozenset]) -> bool:
    gate_executed = False
    for _ in range(routing.qpu.graph.size()):
        no_swap_gate_executed = True
        swap1_gate = None
        for hard_qb0, hard_qb1 in routing.qpu.graph.edges():
            swap_gate = frozenset((hard_qb0, hard_qb1))
            if routing.layers[-1].swap_gate_applicable(swap_gate):
                diff = int_pair_distance_change(routing, int_pairs, swap_gate)
                if diff == 2:
                    routing.apply_swap(swap_gate)
                    gate_executed = True
                    no_swap_gate_executed = False
                elif diff == 1:
                    swap1_gate = swap_gate
        if no_swap_gate_executed:
            if swap1_gate is not None:
                routing.apply_swap(swap1_gate)
                gate_executed = True
                continue
            else:
                break
    return gate_executed


def fallback_routine(routing: Routing, int_pairs: Set[frozenset]) -> None:
    @lru_cache(maxsize=None)
    def deterministic_pair(int_pairs):
        int_pairs_copy = copy(set(int_pairs))
        return int_pairs_copy.pop()
    det_pair = deterministic_pair(frozenset(int_pairs))
    hard_qb0 = routing.mapping.log2hard[list(det_pair)[0]]
    hard_qb1 = routing.mapping.log2hard[list(det_pair)[1]]
    shortest_path = nx.shortest_path(routing.qpu.graph, hard_qb0, hard_qb1)
    routing.apply_swap(frozenset(shortest_path[:2]))


def greedy_pair_mapper(routing: Routing, int_pairs: Set[frozenset]) -> None:
    for i in range(len(routing.problem.variables)):
        #print(i)
        gate_executed = execute_all_possible_int_gates(routing, int_pairs)
        if len(int_pairs) > 0:
            if int_pair_distance(routing, int_pairs) > 0:
                gate_executed = gate_executed or decrease_int_pair_distance(routing, int_pairs)
                if not gate_executed:
                    #print('fallback')
                    fallback_routine(routing, int_pairs)
            routing.layers.append(Layer(routing.qpu))
        else:
            break


def greedy_router(problem_instance: dimod.BinaryQuadraticModel, qpu: Type[QPU]):

    #find edge coloring for problem graph
    #color_sets = edge_coloring.find_edge_coloring(problem_instance.to_networkx_graph())
    #color_sets = sorted(color_sets, key=lambda color_set: len(color_set), reverse=True)

    # find initial mapping and execute interaction gates
    #initial_mapping, int_layer = int_pair_mapper(qpu, problem_instance, color_sets[0])
    initial_mapping, int_layers = twoColorMapper(problem_instance, qpu)
    route = Routing(problem_instance, qpu, initial_mapping=initial_mapping)
    int_count = 0
    for int_layer in int_layers:
        for int_gate in int_layer:
            int_count += 1
            route.apply_int(int_gate)
    print(int_count)

    # find valid edge coloring
    #route = Routing(problem_instance, qpu)
    color_sets = edge_coloring.find_edge_coloring(route.remaining_interactions)
    color_sets = sorted(color_sets, key=lambda color_set: len(color_set), reverse=True)

    #finish remaining layers of color sets
    for color_set in color_sets:
        greedy_pair_mapper(route, color_set)

    return route


