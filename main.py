
import random
from collections import deque

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from environment import SDNEnvironment
from baselines import (
    round_robin_action,
    random_action,
    least_loaded_action,
)

# Make experiments reproducible
random.seed(42)
np.random.seed(42)
torch.manual_seed(42)

DEVICE = torch.device("cpu")


class DQN(nn.Module):
    """Neural network that estimates Q-values for each path."""

    def __init__(self, state_size=6, action_size=3):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(state_size, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, action_size),
        )

    def forward(self, state):
        return self.network(state)


class ReplayBuffer:
    """Stores past experiences for learning."""

    def __init__(self, capacity=10000):
        self.memory = deque(maxlen=capacity)

    def add(self, state, action, reward, next_state, done):
        self.memory.append(
            (state, action, reward, next_state, done)
        )

    def sample(self, batch_size):
        batch = random.sample(self.memory, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        return (
            torch.tensor(np.array(states), dtype=torch.float32),
            torch.tensor(actions, dtype=torch.int64),
            torch.tensor(rewards, dtype=torch.float32),
            torch.tensor(np.array(next_states), dtype=torch.float32),
            torch.tensor(dones, dtype=torch.float32),
        )

    def __len__(self):
        return len(self.memory)


class DQNAgent:
    def __init__(self, state_size=6, action_size=3):
        self.action_size = action_size
        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_min = 0.05
        self.epsilon_decay = 0.985
        self.batch_size = 64

        self.policy_net = DQN(state_size, action_size).to(DEVICE)
        self.target_net = DQN(state_size, action_size).to(DEVICE)
        self.target_net.load_state_dict(self.policy_net.state_dict())

        self.optimizer = optim.Adam(
            self.policy_net.parameters(), lr=0.001
        )
        self.loss_fn = nn.MSELoss()
        self.memory = ReplayBuffer()

    def act(self, state, training=True):
        # Explore sometimes; otherwise choose the highest Q-value
        if training and random.random() < self.epsilon:
            return random.randrange(self.action_size)

        with torch.no_grad():
            state_tensor = torch.tensor(
                state, dtype=torch.float32
            ).unsqueeze(0)
            q_values = self.policy_net(state_tensor)

        return int(torch.argmax(q_values, dim=1).item())

    def learn(self):
        if len(self.memory) < self.batch_size:
            return None

        states, actions, rewards, next_states, dones = (
            self.memory.sample(self.batch_size)
        )

        current_q = self.policy_net(states).gather(
            1, actions.unsqueeze(1)
        ).squeeze(1)

        with torch.no_grad():
            next_q = self.target_net(next_states).max(dim=1)[0]
            target_q = rewards + self.gamma * next_q * (1 - dones)

        loss = self.loss_fn(current_q, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return float(loss.item())

    def update_target(self):
        self.target_net.load_state_dict(self.policy_net.state_dict())


def train_agent(episodes=100):
    env = SDNEnvironment()
    agent = DQNAgent()
    episode_rewards = []
    losses = []

    print("\nTraining DQN agent...")

    for episode in range(episodes):
        state = env.reset()
        total_reward = 0.0

        for step in range(env.max_steps):
            action = agent.act(state)
            next_state, reward, done, info = env.step(action)

            agent.memory.add(
                state, action, reward, next_state, done
            )
            loss = agent.learn()

            if loss is not None:
                losses.append(loss)

            state = next_state
            total_reward += reward

            if done:
                break

        agent.epsilon = max(
            agent.epsilon_min,
            agent.epsilon * agent.epsilon_decay,
        )

        if (episode + 1) % 5 == 0:
            agent.update_target()

        episode_rewards.append(total_reward)

        if (episode + 1) % 10 == 0:
            print(
                f"Episode {episode + 1}/{episodes} | "
                f"Reward: {total_reward:.2f} | "
                f"Epsilon: {agent.epsilon:.3f}"
            )

    torch.save(agent.policy_net.state_dict(), "dqn_model.pth")
    print("Model saved as dqn_model.pth")

    return agent, episode_rewards, losses


def evaluate_policy(policy_name, agent=None, episodes=20):
    """Evaluate a routing policy without exploration."""
    env = SDNEnvironment()
    all_delays = []
    all_losses = []
    all_rewards = []
    all_utilizations = []

    for episode in range(episodes):
        state = env.reset()
        total_reward = 0.0

        for step in range(env.max_steps):
            if policy_name == "DQN":
                action = agent.act(state, training=False)
            elif policy_name == "Round Robin":
                action = round_robin_action(step, env.num_paths)
            elif policy_name == "Random":
                action = random_action(env.num_paths)
            elif policy_name == "Least Loaded":
                action = least_loaded_action(state, env.num_paths)
            else:
                raise ValueError(f"Unknown policy: {policy_name}")

            next_state, reward, done, info = env.step(action)

            all_delays.append(info["delay"])
            all_losses.append(info["packet_loss"])
            all_utilizations.append(info["utilization"])
            total_reward += reward
            state = next_state

            if done:
                break

        all_rewards.append(total_reward)

    return {
        "Algorithm": policy_name,
        "Average Delay (ms)": float(np.mean(all_delays)),
        "Packet Loss (%)": float(100 * np.mean(all_losses)),
        "Average Utilization (%)": float(
            100 * np.mean(all_utilizations)
        ),
        "Average Reward": float(np.mean(all_rewards)),
    }


if __name__ == "__main__":
    agent, rewards, losses = train_agent(episodes=100)

    print("\nEvaluating routing algorithms...")
    results = []

    for name in ["Round Robin", "Random", "Least Loaded", "DQN"]:
        result = evaluate_policy(
            name, agent=agent, episodes=20
        )
        results.append(result)
        print(
            f"{name:15} | "
            f"Delay: {result['Average Delay (ms)']:.2f} ms | "
            f"Packet Loss: {result['Packet Loss (%)']:.2f}% | "
            f"Reward: {result['Average Reward']:.2f}"
        )

    import csv

    with open("results.csv", "w", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=results[0].keys()
        )
        writer.writeheader()
        writer.writerows(results)

    print("\nResults saved to results.csv")
