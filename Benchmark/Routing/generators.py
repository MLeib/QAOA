
from joblib import Memory
import networkx as nx
import dimod

data_cache = './Data'
mem = Memory(data_cache)


def regular_graph_bqm(degree: int, variable_count: int, copy_count: int):
    bqm_arr = []
    for _ in range(copy_count):
        problem_graph = nx.random_regular_graph(degree, variable_count)
        bqm_arr.append(dimod.generators.uniform(problem_graph, dimod.SPIN, low=0.5, high=1.0))
    return bqm_arr
regular_graph_bqm = mem.cache(regular_graph_bqm)
