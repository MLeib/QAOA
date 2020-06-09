from typing import Union, Any, Mapping, Generator, Tuple

import networkx as nx
import dimod

from QAOA.Problem import BaseProblem

class spinGlass(BaseProblem):

    def __init__(self, problem: Union[nx.Graph, dimod.BinaryQuadraticModel]):
        self.problem = problem
        if isinstance(problem, nx.Graph):
            self.size = problem.order()
            self.bqm = dimod.BinaryQuadraticModel.from_networkx_graph(problem, 'SPIN')
        elif isinstance(problem, dimod.BinaryQuadraticModel):
            assert problem.vartype is dimod.Vartype.SPIN, 'vartype of bqm must be SPIN'
            self.size = len(problem.linear)
            self.bqm = problem

    def energy(self, sample: Mapping[Any, bool]) -> float:

        return self.bqm.energy(sample)

    def interactions(self) -> Generator[Tuple[frozenset, float], None, None]:

        linear = self.bqm.linear
        linear = {frozenset([variable]): bias for variable, bias in linear.items()}
        quadratic = self.bqm.quadratic
        quadratic = {frozenset(variables): bias for variables, bias in quadratic.items()}
        ints = {**linear, **quadratic}

        generator = (frozenset(variables), bias for variables, bias in ints.items())

        return generator

