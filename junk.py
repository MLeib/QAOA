import numpy as np
import matplotlib.pyplot as plt


x_vec = [0.5 * i for i in range(110)]
lin = [x for x in x_vec]
exp = [np.exp(0.1 * x) for x in x_vec]


plt.plot(x_vec, lin, x_vec, exp)
plt.show()