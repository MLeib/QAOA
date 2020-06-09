from typing import Dict, List
import matplotlib.pyplot as plt
import itertools

import cirq
import networkx as nx

#from Router.mapping import Mapping


class QPU:
    def __init__(self, hardware_graph: nx.Graph(), hardware_layout: Dict):
        self.graph = hardware_graph
        self.layout = hardware_layout

    def draw(self, mapping=None, gate_lists: Dict[str, List[tuple]] = None, ax=None, show: bool = True, **kwargs):
        nx.draw_networkx_edges(self.graph, pos=self.layout, with_labels=False, ax=ax, **kwargs)
        if gate_lists is not None:
            for color, gates in gate_lists.items():
                edge_list = [tuple(gate) for gate in gates]
                nx.draw_networkx_edges(self.graph, self.layout, ax=ax, edgelist=edge_list, width=6.0, edge_color=color)
        if mapping is not None:
            labels = {hard_qb: mapping.hard2log[hard_qb] for hard_qb in self.graph.nodes()}
            nx.draw_networkx_labels(self.graph, self.layout, ax=ax, labels=labels)
            nx.draw_networkx_nodes(self.graph, pos=self.layout, ax=ax)
        else:
            nx.draw_networkx_nodes(self.graph, pos=self.layout, ax=ax)
        if show:
            plt.show()

    def qubits(self):
        return self.graph.nodes()

    def has_edge(self, gate: frozenset):
        return self.graph.has_edge(*gate)


class Grid2dQPU(QPU):
    def __init__(self, num_rows: int, num_columns: int):
        self.num_rows = num_rows
        self.num_columns = num_columns
        grid_2d = nx.grid_2d_graph(num_columns, num_rows)
        hardware_graph = nx.Graph()
        for u, v in grid_2d.edges():
            hardware_graph.add_edge(cirq.GridQubit(*u), cirq.GridQubit(*v))
        hardware_layout = {node: [node.row, node.col] for node in hardware_graph.nodes()}
        super().__init__(hardware_graph, hardware_layout)

    def embedded_chain(self):
        for row_ind in range(self.num_rows):
            if row_ind % 2 == 0:
                for column_ind in range(self.num_columns):
                    yield cirq.GridQubit(row_ind, column_ind)
            else:
                for column_ind in range(self.num_columns - 1, -1, -1):
                    yield cirq.GridQubit(row_ind, column_ind)

    # def loop_embedding(self):
    #     num_rows_even = self.num_rows % 2 == 0
    #     num_columns_even = self.num_columns % 2 == 0
    #     if not (num_rows_even or num_columns_even):
    #         raise NotImplementedError
    #
    #     if num_rows_even:
    #         for row_ind in range(self.num_rows / 2):
    #             if row_ind % 2 == 0:
    #             else:




class LineQPU(QPU):
    def __init__(self, length: int):
        path = nx.path_graph(length)
        hardware_graph = nx.Graph()
        for u, v in path.edges():
            hardware_graph.add_edge(cirq.LineQubit(u), cirq.LineQubit(v))
        hardware_layout = {node: node.x for node in hardware_graph.nodes()}
        super().__init__(hardware_graph, hardware_layout)


class XmonQPU(QPU):
    def __init__(self, device: cirq.google.XmonDevice):
        device_qubits = sorted(device.qubits)
        edges = [(a, b) for a, b in itertools.combinations(device_qubits, 2)
                 if a.is_adjacent(b)]
        hardware_graph = nx.Graph(edges)
        hardware_layout = nx.kamada_kawai_layout(hardware_graph)
        super().__init__(hardware_graph, hardware_layout)

