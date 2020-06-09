import networkx as nx
import matplotlib.pyplot as plt


def ec_is_valid(graph):

    for _, nbrsdict in graph.adjacency():
        color_lst = []
        for eattr in nbrsdict.values():
            if 'color' in eattr:
                if eattr['color'] not in color_lst:
                    color_lst.append(eattr['color'])
                else:
                    return False

    return True


def ec_is_complete(graph):

    for _, _, eattr in graph.edges.data('color'):
        if eattr is None:
            return False

    return True


def plot_edge_coloring(graph, pos, color_palette=None, default_color='#00000000'):

    if color_palette is None:
        color_palette = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'w']

    edge_color_arr = []
    for edge in graph.edges():
        if 'color' in graph[edge[0]][edge[1]]:
            edge_color_arr.append(color_palette[graph[edge[0]][edge[1]]['color']])
        else:
            edge_color_arr.append(default_color)

    nx.draw_networkx(graph, pos, edge_color=edge_color_arr)


def colors_on_node(graph, node):

    color_arr = {}

    for neighbor in graph.neighbors(node):
        if 'color' in graph.edges[node, neighbor]:
            color_arr[graph.edges[node, neighbor]['color']] = neighbor

    return color_arr


def color_is_free_on(graph, node, color):

    for neighbor in graph.neighbors(node):
        if 'color' in graph.edges[node, neighbor]:
            if color is graph.edges[node, neighbor]['color']:
                return False

    return True


def free_colors(graph, node, color_palette):

    return color_palette - colors_on_node(graph, node).keys()


def find_maximal_fan(graph, node1, node2, color_palette):

    fan = [node2]

    found = True

    while found is True:
        found = False
        for color in free_colors(graph, fan[-1], color_palette):
            if color in colors_on_node(graph, node1).keys():
                if colors_on_node(graph, node1)[color] not in fan:
                    fan.append(colors_on_node(graph, node1)[color])
                    found = True
                    break

    return fan


def find_and_invert_cdpath(graph, node, c, d):

    current_color = c
    other_color = d
    path = [node]

    #Find
    while current_color in colors_on_node(graph, path[-1]).keys():
        path.append(colors_on_node(graph, path[-1])[current_color])
        current_color, other_color = other_color, current_color

    #if len(path) > 1:
    #    print(f"non-zero path of length {len(path)} found")

    #Invert
    for current_node, next_node in zip(path[:-1], path[1:]):
        if graph.edges[current_node, next_node]['color'] is c:
            graph.edges[current_node, next_node]['color'] = d
        else:
            graph.edges[current_node, next_node]['color'] = c


def rotate_fan(graph, node, fan, color):

    for node1, node2 in zip(fan[:-1], fan[1:]):
        graph.edges[node, node1]['color'] = graph.edges[node, node2]['color']

    #if color not in free_colors(graph, node, color_palette):
    #    print('color not free on root node')
    #if color not in free_colors(graph, fan[-1], color_palette):
    #    print('color not free on fan node')

    graph.edges[node, fan[-1]]['color'] = color


def color_edge(graph, node1, node2, color_palette):

    fan = find_maximal_fan(graph, node1, node2, color_palette)
    c_color = free_colors(graph, node1, color_palette).pop()
    d_color = free_colors(graph, fan[-1], color_palette).pop()
    find_and_invert_cdpath(graph, node1, d_color, c_color)
    #print(f"After inverting cdpath coloring is {ec_is_valid(graph)}")

    reduced_fan = []
    for node in fan:
        if d_color not in free_colors(graph, node, color_palette):
            reduced_fan.append(node)
        else:
            reduced_fan.append(node)
            break


    rotate_fan(graph, node1, reduced_fan, d_color)
    #print(f"After rotating fan, coloring is {ec_is_valid(graph)}")
    #plot_edge_coloring(graph, ex_pos)
    #plt.show()

def find_edge_coloring(graph):

    graph_degree = max([graph.degree(node) for node in graph])
    color_palette = tuple(range(graph_degree + 1))
    for edge in graph.edges():
        color_edge(graph, edge[0], edge[1], color_palette)

    color_sets = [set() for _ in range(graph_degree + 1)]
    for u, v, color in graph.edges.data('color'):
        color_sets[color].add(frozenset((u,v)))

    return color_sets