import pandas as pd
import matplotlib.pyplot as plt

# Load the experimental results
df = pd.read_csv("results.csv")

# Display the exact results being plotted
print("\nEXPERIMENT RESULTS")
print(df.to_string(index=False))

# Plot 1: Average network delay
plt.figure(figsize=(9, 5))
plt.bar(df["Algorithm"], df["Average Delay (ms)"])
plt.ylabel("Average Delay (ms)")
plt.title("Comparison of Network Delay")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("delay_comparison.png", dpi=300)
plt.close()

# Plot 2: Packet loss
plt.figure(figsize=(9, 5))
plt.bar(df["Algorithm"], df["Packet Loss (%)"])
plt.ylabel("Packet Loss (%)")
plt.title("Comparison of Packet Loss")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("packet_loss_comparison.png", dpi=300)
plt.close()

# Plot 3: Average reward
plt.figure(figsize=(9, 5))
plt.bar(df["Algorithm"], df["Average Reward"])
plt.ylabel("Average Reward")
plt.title("Comparison of Average Reward")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("reward_comparison.png", dpi=300)
plt.close()

print("\nGraphs saved successfully:")
print("1. delay_comparison.png")
print("2. packet_loss_comparison.png")
print("3. reward_comparison.png")
