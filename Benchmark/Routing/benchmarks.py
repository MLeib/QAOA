
import numpy as np
import matplotlib.pyplot as plt

from Benchmark.Routing.generators import regular_graph_bqm
from Devices.quantum_hardware import Grid2dQPU
from Router.GreedyRouter.greedy_router import greedy_router


def greedy_router_benchmark():
    data = {n**2: regular_graph_bqm(4, n**2, 20) for n in range(3, 7)}
    layer_count_avg = np.zeros(len(data))
    layer_count_20perc = np.zeros(len(data))
    layer_count_80perc = np.zeros(len(data))
    i = -1
    for size, data_point in data.items():
        print(size)
        i += 1
        qpu = Grid2dQPU(int(np.sqrt(size)), int(np.sqrt(size)))
        layer_counts = np.zeros(len(data_point))
        for bqm_index, bqm in enumerate(data_point):
            route = greedy_router(bqm, qpu)
            assert route.remaining_interactions.size() == 0, 'routing not finished with success'
            layer_counts[bqm_index] = len(route.layers)
        layer_count_avg[i] = np.mean(layer_counts)
        layer_count_20perc[i] = np.percentile(layer_counts, 20)
        layer_count_80perc[i] = np.percentile(layer_counts, 80)
    sys_size = np.zeros(len(data))
    for ind, sze in enumerate(data):
        sys_size[ind] = sze
    plt.plot(sys_size, layer_count_avg, color='blue')
    plt.fill_between(sys_size, layer_count_20perc, layer_count_80perc, facecolor='blue', alpha=0.5)
    plt.show()
    data = np.column_stack((sys_size, layer_count_avg, layer_count_20perc, layer_count_80perc))
    header = 'system size, layer count average, layer count 20th percentile, layer count 80th percentile'
    np.savetxt('./Data/results/greedy_router_v2.dat', data, header=header)


greedy_router_benchmark()
