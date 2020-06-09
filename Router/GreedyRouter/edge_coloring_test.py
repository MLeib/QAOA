import networkx as nx
import matplotlib.pyplot as plt

from qaoa_experiment.routing.edge_color_routing import edge_coloring



#Matplotlib colors {'b', 'g', 'r', 'c', 'm', 'y', 'k', 'w'}
#color_palette = {'g', 'r', 'c', 'm', 'y', 'k'}
ex_graph = nx.random_regular_graph(3, 10)
ex_pos = nx.spring_layout(ex_graph)

color_sets = edge_coloring.find_edge_coloring(ex_graph)

print(color_sets)
edge_coloring.plot_edge_coloring(ex_graph, ex_pos)
plt.show()

#for ind, edge in enumerate(ex_graph.edges()):
#    color_edge(ex_graph, edge[0], edge[1], color_palette)

#print(ec_is_valid(ex_graph))
#print(ec_is_complete(ex_graph))

#for nd1, nd2, color in ex_graph.edges.data('color'):
#    print(f"edge {nd1},{nd2} has color: {color}")

