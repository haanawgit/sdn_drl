
import numpy as np


def round_robin_action(step, num_paths=3):
    """Select paths in a repeating order: 0, 1, 2, 0, 1, 2..."""
    return step % num_paths


def random_action(num_paths=3):
    """Choose a path randomly."""
    return int(np.random.randint(0, num_paths))


def least_loaded_action(state, num_paths=3):
    """
    Choose the path with the lowest observed utilization.
    The first num_paths values in state are path utilizations.
    """
    utilization = state[:num_paths]
    return int(np.argmin(utilization))
