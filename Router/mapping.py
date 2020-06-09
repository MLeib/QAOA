from typing import Type

import networkx as nx
import dimod

from Devices.quantum_hardware import QPU


class Mapping:
    def __init__(self, qpu: Type[QPU], problem: dimod.BinaryQuadraticModel, partial_initial_mapping: dict = None):
        if problem.vartype is dimod.BINARY:
            problem.change_vartype(dimod.SPIN)
            print('changed vartype of problem definition from BINARY to SPIN')

        self.log_qbs = set(problem.variables)
        self.hard_qbs = set(qpu.qubits())

        assert len(self.hard_qbs) == len(self.log_qbs), 'number of hardware qubits does not match number of logical qubits'

        if partial_initial_mapping is None:
            self.hard2log = {hard_qb: log_qb for hard_qb, log_qb in zip(self.hard_qbs, self.log_qbs)}
            self.log2hard = {log_qb: hard_qb for log_qb, hard_qb in zip(self.log_qbs, self.hard_qbs)}
        else:
            assert len(set(partial_initial_mapping.values())) == len(partial_initial_mapping.values()), 'partial_initial_mapping is not bijective'
            if len(partial_initial_mapping) < len(self.log_qbs):
                remaining_hard_qbs = self.hard_qbs - set(partial_initial_mapping.keys())
                remaining_log_qbs = self.log_qbs - set(partial_initial_mapping.values())
                initial_mapping = partial_initial_mapping
                for hard_qb, log_qb in zip(remaining_hard_qbs, remaining_log_qbs):
                    initial_mapping[hard_qb] = log_qb
            else:
                initial_mapping = partial_initial_mapping

            self.hard2log = initial_mapping
            self.log2hard = {log_qb: hard_qb for hard_qb, log_qb in self.hard2log.items()}

    def swap(self, gate: frozenset):
        qb0, qb1 = list(gate)
        if qb0 in self.hard_qbs:
            assert qb1 in self.hard_qbs, 'impossible to swap hardware with logical qubit'
            self.hard2log[qb0], self.hard2log[qb1] = self.hard2log[qb1], self.hard2log[qb0]
            self.log2hard = {log_qb: hard_qb for hard_qb, log_qb in self.hard2log.items()}
        else:
            assert qb1 in self.log_qbs, 'impossible to swap hardware with logical qubit'
            self.log2hard[qb0], self.log2hard[qb1] = self.log2hard[qb1], self.log2hard[qb0]
            self.hard2log = {hard_qb: log_qb for log_qb, hard_qb in self.log2hard.items()}

    def update(self, layer):
        for hard_qb0, hard_qb1 in layer.gates.edges():
            if layer.gates[hard_qb0][hard_qb1]['swap']:
                self.swap(frozenset((hard_qb0, hard_qb1)))



