# AI-Based Intelligent Load Balancing in SDN Using DQN

## Project Overview

This project implements a prototype for intelligent load balancing in Software-Defined Networking (SDN) using a Deep Q-Network (DQN).

The system selects among three parallel network paths using a six-feature state representation. The DQN produces three Q-values, and the selected action maps to an inter-switch port.

The project includes:
- A Python simulation for evaluating load-balancing strategies.
- A DQN model implemented using PyTorch.
- An SDN controller using OS-Ken.
- A Mininet topology with Open vSwitch and OpenFlow 1.3.
- Comparison results for Round Robin, Random, Least Loaded, and DQN.

## Objectives

- Implement DQN-based path selection.
- Create a multi-path SDN topology.
- Install forwarding rules through an SDN controller.
- Compare the proposed approach against conventional load-balancing strategies.
- Verify controller-directed forwarding in Mininet.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Simulation and controller implementation |
| PyTorch | DQN neural network |
| NumPy | Numerical computations |
| Matplotlib | Result visualization |
| OS-Ken | SDN controller |
| Mininet | Virtual network emulation |
| Open vSwitch | Software-based packet forwarding |
| OpenFlow 1.3 | Controller-to-switch communication |

## Project Structure

The project directory contains the following key files:

```text
SDN-DRL/
├── main.py
├── environment.py
├── baselines.py
├── visualize.py
├── dqn_model.pth
├── results.csv
├── adaptive_controller.py
├── adaptive_controller_dqn.py
├── multipath_topology.py
├── l2_switch.py
├── requirements.txt
├── delay_comparison.png
├── packet_loss_comparison.png
├── reward_comparison.png
└── final_evidence/
    ├── s1_flows_verified.txt
    └── s2_flows_verified.txt
```

The exact files present may vary with the final project version. Include only files that actually exist in your submitted folder.

## Network Topology

The network contains:
- Host h1 connected to switch s1.
- Host h2 connected to switch s2.
- Three parallel links between s1 and s2.
- Host-facing port 1 on each switch.
- Inter-switch ports 2, 3, and 4.

### DQN Action Mapping

| Action | Selected port |
|---|---|
| 0 | Port 2 |
| 1 | Port 3 |
| 2 | Port 4 |

The neural network accepts six input features and returns three Q-values.

## Setup

Activate the existing virtual environment from the project directory:

```bash
cd /mnt/c/Users/sahaa/OneDrive/Desktop/SDN-DRL
source .venv/bin/activate
```

The recorded development environment used WSL Ubuntu. OS-Ken was available from the system Python package directory.

Do not reinstall dependencies if the existing environment already works.

## Running the Simulation

Run the simulation:

```bash
python main.py
```

Generate the comparison visualizations:

```bash
python visualize.py
```

These commands assume the scripts use their default settings. If the local version requires additional arguments, check the script or its help output.

The simulation results are recorded in `results.csv`, and the visualization script generates comparison graphs.

## Running the Live SDN Demonstration

### Step 1: Start the controller

Open a WSL terminal:

```bash
cd /mnt/c/Users/sahaa/OneDrive/Desktop/SDN-DRL
source .venv/bin/activate
PYTHONPATH=/usr/lib/python3/dist-packages python -m os_ken.cmd.manager adaptive_controller_dqn.py
```

The controller should load the DQN model and wait for switch connections.

### Step 2: Start Mininet

Open a second WSL terminal:

```bash
sudo mn --custom multipath_topology.py --topo multipath --switch ovs,protocols=OpenFlow13 --controller=remote,ip=127.0.0.1,port=6653
```

### Step 3: Test connectivity

At the Mininet prompt, run:

```text
pingall
```

You can also test the two hosts directly:

```text
h1 ping -c 10 h2
```

Record the actual ping summary, including transmitted packets, received packets, and packet loss.

### Step 4: Inspect forwarding rules

From another WSL terminal, run:

```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
sudo ovs-ofctl -O OpenFlow13 dump-flows s2
```

The captured flow-table evidence in `final_evidence/` showed port-4 forwarding rules on both switches. The matching flow entries displayed 23 packets at the time of capture.

### Step 5: Clean up

Exit the Mininet CLI before running:

```bash
sudo mn -c
```

## Recorded Simulation Results

The following values are from the recorded `results.csv` file.

| Strategy | Delay (ms) | Packet Loss (%) | Average Utilization (%) | Reward |
|---|---:|---:|---:|---:|
| Round Robin | 29.54 | 8.12 | 75.20 | -974.09 |
| Random | 46.98 | 24.41 | 105.98 | -2072.72 |
| Least Loaded | 27.43 | 2.98 | 70.62 | -700.61 |
| DQN | 31.48 | 4.05 | 79.58 | -833.14 |

**Result interpretation:** Least Loaded performed best across the four recorded metrics in this simulation. DQN improved on Random and Round Robin in packet loss but did not outperform Least Loaded overall.

These figures are simulation results, not live Mininet measurements.

## Live Demonstration Findings

During the live test:
- The DQN controller selected port 4.
- The controller requested forwarding rules on s1 and s2.
- The flow tables showed traffic forwarding through port 4.
- The relevant matching entries displayed 23 packets at the time of capture.

These findings verify controller-directed forwarding. They do not independently establish the live ping success rate or demonstrate that congestion caused the path selection.

## Limitations

- The topology is small and contains only two switches.
- The live state representation may differ from the simulation training state.
- The selected-path handling is a prototype and is not robust per-flow routing.
- Results may change with different traffic patterns and random seeds.
- The recorded results do not show DQN outperforming every baseline.

## Future Enhancements

- Align training and live state representations.
- Maintain separate path selections for individual flows.
- Evaluate more traffic patterns and random seeds.
- Measure live delay and packet loss directly.
- Improve congestion monitoring and controller scalability.

## Conclusion

This project demonstrates a DQN-based path-selection prototype integrated with an SDN controller. The simulation compares it with conventional load-balancing strategies, while the Mininet demonstration verifies forwarding-rule installation.

The recorded simulation favored Least Loaded overall. Further work is required to improve the learned policy's performance and evaluate its behavior under a broader range of network conditions.
