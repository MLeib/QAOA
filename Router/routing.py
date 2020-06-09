from typing import Set, Type, List
import copy as cp

import cirq
import dimod
import networkx as nx
import matplotlib.pyplot as plt

from Router.mapping import Mapping
from Devices.quantum_hardware import QPU


class Layer:
    def __init__(self, qpu: Type[QPU], int_gates: Set[frozenset] = [], swap_gates: Set[frozenset] = []):
        self.qpu = qpu
        self.gates = nx.Graph()
        for hard_qb0, hard_qb1 in self.qpu.graph.edges():
            self.gates.add_edge(hard_qb0, hard_qb1, swap=False, int=False)
        for gate in int_gates:
            if self.int_gate_applicable(gate):
                self.apply_int_gate(gate)
            else:
                print(f'INT-Gate {gate} cannot be applied in layer')
        for gate in swap_gates:
            if self.swap_gate_applicable(gate):
                self.apply_swap_gate(gate)
            else:
                print(f'SWAP-Gate {gate} cannot be applied in layer')

    def qbs_not_involved_in_other_gate(self, gate: frozenset) -> bool:
        hard_qb0, hard_qb1 = list(gate)
        for neighbor in self.gates.neighbors(hard_qb0):
            if neighbor != hard_qb1:
                if self.gates[neighbor][hard_qb0]['swap'] or self.gates[neighbor][hard_qb0]['int']:
                    return False
        for neighbor in self.gates.neighbors(hard_qb1):
            if neighbor != hard_qb0:
                if self.gates[neighbor][hard_qb1]['swap'] or self.gates[neighbor][hard_qb1]['int']:
                    return False
        return True

    def int_gate_applicable(self, gate: frozenset) -> bool:
        if not self.qpu.has_edge(gate):
            return False
        hard_qb0, hard_qb1 = list(gate)
        if self.gates[hard_qb0][hard_qb1]['int']:
            return False
        return self.qbs_not_involved_in_other_gate(gate)

    def apply_int_gate(self, gate: frozenset) -> None:
        if self.int_gate_applicable(gate):
            hard_qb0, hard_qb1 = list(gate)
            self.gates[hard_qb0][hard_qb1]['int'] = True

    def swap_gate_applicable(self, gate:  frozenset) -> bool:
        if not self.qpu.has_edge(gate):
            return False
        return self.qbs_not_involved_in_other_gate(gate)

    def apply_swap_gate(self, gate: frozenset) -> None:
        if self.swap_gate_applicable(gate):
            hard_qb0, hard_qb1 = list(gate)
            self.gates[hard_qb0][hard_qb1]['swap'] = not self.gates[hard_qb0][hard_qb1]['swap']

    def draw(self, mapping: Mapping=None, ax=None, show: bool=True):
        gate_lists = {'y': [], 'b': [], 'g': []}
        for hard_qb0, hard_qb1 in self.gates.edges():
            swap_b, int_b = self.gates[hard_qb0][hard_qb1]['swap'], self.gates[hard_qb0][hard_qb1]['int']
            if swap_b and int_b:
                gate_lists['y'].append((hard_qb0, hard_qb1))
            elif swap_b:
                gate_lists['b'].append((hard_qb0, hard_qb1))
            elif int_b:
                gate_lists['g'].append((hard_qb0, hard_qb1))

        if mapping is None:
            self.qpu.draw(gate_lists=gate_lists, ax=ax, show=show)
        else:
            self.qpu.draw(gate_lists=gate_lists, mapping=mapping, ax=ax, show=show)


class Routing:
    def __init__(self, problem_instance: dimod.BinaryQuadraticModel, qpu: Type[QPU], initial_mapping: Mapping = None):
        self.problem = problem_instance
        self.remaining_interactions = problem_instance.to_networkx_graph()
        self.qpu = qpu
        if initial_mapping is None:
            self.initial_mapping = Mapping(self.qpu, self.problem)
        else:
            self.initial_mapping = initial_mapping
        self.mapping = cp.deepcopy(self.initial_mapping)
        self.layers = [Layer(self.qpu)]

    def apply_swap(self, gate: frozenset, attempt_int: bool = False):
        assert self.qpu.has_edge(gate), 'SWAP gate not supported on hardware graph'

        def internal_apply_swap(layer_index: int):
            self.layers[layer_index].apply_swap_gate(gate)
            self.mapping.swap(gate)
            if attempt_int:
                log_qb0, log_qb1 = self.mapping.hard2log(list(gate)[0]), self.mapping.hard2log(list(gate)[1])
                if self.remaining_interactions.has_edge(log_qb0, log_qb1):
                    self.apply_int(gate)

        if not self.layers[-1].swap_gate_applicable(gate):
            self.layers.append(Layer(self.qpu))
            internal_apply_swap(-1)
        else:
            if len(self.layers) == 1:
                internal_apply_swap(-1)
            else:
                for layer_index in range(len(self.layers)-1, 0, -1):
                    if not self.layers[layer_index - 1].swap_gate_applicable(gate):
                        internal_apply_swap(layer_index)
                        break
                    elif layer_index == 1:
                        internal_apply_swap(0)

    def apply_int(self, gate: frozenset):
        assert self.qpu.has_edge(gate), 'INT gate not supported on hardware graph'
        log_qb0, log_qb1 = self.mapping.hard2log[list(gate)[0]], self.mapping.hard2log[list(gate)[1]]
        assert self.remaining_interactions.has_edge(log_qb0, log_qb1), 'int gate does not process any remaining interaction'

        if not self.layers[-1].int_gate_applicable(gate):
            self.layers.append(Layer(self.qpu))
            self.layers[-1].apply_int_gate(gate)
            self.remaining_interactions.remove_edge(log_qb0, log_qb1)
        else:
            if len(self.layers) == 1:
                self.layers[-1].apply_int_gate(gate)
                self.remaining_interactions.remove_edge(log_qb0, log_qb1)
            else:
                for layer_index in range(len(self.layers)-1, 0, -1):
                    if not self.layers[layer_index - 1].int_gate_applicable(gate):
                        self.layers[layer_index].apply_int_gate(gate)
                        self.remaining_interactions.remove_edge(log_qb0, log_qb1)
                        break

    def draw(self):
        layer_count = len(self.layers)
        if layer_count > 1:
            layer_batches = [self.layers[x:x+9] for x in range(0, len(self.layers), 9)]
            mapping = cp.deepcopy(self.initial_mapping)
            layer_index = 0
            for layers in layer_batches:
                fig, axs = plt.subplots(3, 3, subplot_kw={'clip_on': False, 'frame_on': False})
                for layer in layers:
                    row = (layer_index % 9) // 3
                    column = (layer_index % 9) % 3
                    layer.draw(mapping=mapping, ax=axs[row, column], show=False)
                    axs[row, column].set_axis_off()
                    axs[row, column].autoscale_view()
                    axs[row, column].set_title(f'Layer {layer_index }')
                    mapping.update(layer)
                    layer_index += 1
                plt.show()
        else:
            self.layers[0].draw(mapping=self.initial_mapping)

    def build_cirq(self, betas, gammas):

        circuit = cirq.Circuit()
        swap_gate = cirq.SWAP
        layers = self.layers

        for gamma, beta in zip(gammas, betas):
            for layer in self.layers:
                gate_list = []
                for gate_qbs in layer['swap']:
                    gate_list.append(swap_gate(*gate_qbs))
                circuit.append(gate_list)

                gate_list = []
                for gate_qbs in layer['int']:
                    log_qb0 = self.hard2log[gate_qbs[0]]
                    log_qb1 = self.hard2log[gate_qbs[1]]
                    weight = self.logical_graph.edges[log_qb0, log_qb1]['weight']
                    gate_list.append(gates.Rzz(gamma * weight).on(*gate_qbs))
                circuit.append(gate_list)
            layers.reverse()
            cirq.Rx(2 * beta).on_each(*self.hardware_graph.nodes)







