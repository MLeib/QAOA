import abc
from typing import Mapping, Any, Generator, Tuple


class BaseProblem(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def energy(self, sample: Mapping[Any, bool]) -> float:
        pass

    @abc.abstractmethod
    def interactions(self) -> Generator[Tuple[frozenset, float], None, None]:
        pass