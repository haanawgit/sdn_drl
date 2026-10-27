
import numpy as np


class SDNEnvironment:
    """
    Simulated Software-Defined Network with three paths.
    The agent observes network congestion and chooses a path.
    """

    def __init__(self, num_paths=3, max_steps=200):
        self.num_paths = num_paths
        self.max_steps = max_steps

        # Different capacities and base delays for each path
        self.capacities = np.array([100.0, 140.0, 120.0])
        self.base_delays = np.array([10.0, 18.0, 14.0])

        self.reset()

    def reset(self):
        """Reset network traffic and return the initial state."""
        self.step_count = 0
        self.loads = np.random.uniform(15.0, 45.0, self.num_paths)
        self.total_delay = 0.0
        self.total_dropped = 0
        return self._get_state()

    def _get_state(self):
        """State contains each path's normalized load and delay."""
        utilization = self.loads / self.capacities
        delays = self.base_delays * (
            1.0 + 3.0 * np.maximum(utilization - 0.5, 0.0)
        )

        return np.concatenate([
            utilization.astype(np.float32),
            (delays / 50.0).astype(np.float32)
        ])

    def step(self, action):
        """
        Send traffic through the selected path.
        Returns: next_state, reward, done, information.
        """
        action = int(action)
        self.step_count += 1

        # New incoming traffic for this time step
        incoming = np.random.uniform(8.0, 25.0)

        # Other background traffic changes over time
        background = np.random.uniform(2.0, 12.0, self.num_paths)
        self.loads = np.maximum(self.loads - 12.0, 0.0)
        self.loads += background
        self.loads[action] += incoming

        utilization = self.loads / self.capacities
        selected_utilization = utilization[action]

        # Delay increases sharply as a path approaches its capacity
        delay = self.base_delays[action] * (
            1.0 + 4.0 * max(selected_utilization - 0.5, 0.0)
        )

        # Congestion penalty for exceeding path capacity
        overload = max(selected_utilization - 1.0, 0.0)
        packet_loss = min(overload, 1.0)

        # Congestion-aware reward: lower delay and packet loss are better
        reward = -(delay / 10.0) - (20.0 * packet_loss)

        # Penalize very high utilization to encourage balanced routing
        reward -= 2.0 * max(selected_utilization - 0.8, 0.0)

        self.total_delay += delay
        self.total_dropped += int(packet_loss > 0)

        done = self.step_count >= self.max_steps

        info = {
            "path": action,
            "delay": float(delay),
            "utilization": float(selected_utilization),
            "packet_loss": float(packet_loss),
        }

        return self._get_state(), float(reward), done, info

