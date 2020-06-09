# first line: 10
def regular_graph_bqm(degree: int, variable_count: int):
    problem_graph = nx.random_regular_graph(degree, variable_count)
    return dimod.generators.randint(problem_graph, dimod.SPIN)
