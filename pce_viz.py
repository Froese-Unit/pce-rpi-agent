"""
Standalone PCE visualizer. Replays a trial CSV as an animation of the two
avatars (+ their shadows and static objects) on the circular ring.

Usage:
    python pce_viz.py path/to/trial.csv
    python pce_viz.py --demo          # generate & show a synthetic trial

Reads the real PCE CSV columns: timestamp, pos0, pos1,
static_object_0, static_object_1, shadow_delta0, shadow_delta1,
motor_0_vibrate_software, motor_1_vibrate_software, button0, button1
"""
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

RING = 600
AVATAR_W = 20

def angle(x):
    """Map ring position 0..599 to an angle in radians."""
    return 2 * np.pi * (np.asarray(x) % RING) / RING

def make_demo_csv(path="demo_trial.csv", n=1500, hz=100):
    """Synthetic trial so the visualizer can be tested before real data exists."""
    t = np.linspace(0, n/hz, n)
    pos0 = (np.cumsum(np.random.uniform(-4, 4, n))) % RING
    pos1 = (300 + np.cumsum(np.random.uniform(-4, 4, n))) % RING
    s0, s1 = 150, 450
    def cdist(a, b):
        d = np.abs(a - b) % RING
        return np.minimum(d, RING - d)
    m0 = ((cdist(pos0, pos1) <= AVATAR_W) |
          (cdist(pos0, (pos1+150) % RING) <= AVATAR_W) |
          (cdist(pos0, s0) <= AVATAR_W)).astype(int)
    m1 = ((cdist(pos1, pos0) <= AVATAR_W) |
          (cdist(pos1, (pos0+150) % RING) <= AVATAR_W) |
          (cdist(pos1, s1) <= AVATAR_W)).astype(int)
    pd.DataFrame({
        "timestamp": t, "pos0": pos0, "pos1": pos1,
        "static_object_0": s0, "static_object_1": s1,
        "shadow_delta0": 150, "shadow_delta1": 150,
        "motor_0_vibrate_software": m0, "motor_1_vibrate_software": m1,
        "button0": 0, "button1": 0,
    }).to_csv(path, index_label="index")
    return path

def visualize(csv_path, speed=3):
    df = pd.read_csv(csv_path)
    n = len(df)
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"aspect": "equal"})
    ax.set_xlim(-1.4, 1.4); ax.set_ylim(-1.4, 1.4); ax.axis("off")
    # the ring
    ring = plt.Circle((0, 0), 1.0, fill=False, color="lightgray", lw=2)
    ax.add_patch(ring)

    def xy(pos, r=1.0):
        a = angle(pos)
        return r*np.cos(a), r*np.sin(a)

    sd0 = df["shadow_delta0"].iloc[0]
    sd1 = df["shadow_delta1"].iloc[0]

    # static objects (fixed) -- squares
    sx0, sy0 = xy(df["static_object_0"].iloc[0])
    sx1, sy1 = xy(df["static_object_1"].iloc[0])
    ax.scatter([sx0], [sy0], marker="s", s=180, c="tab:green", label="static 0", zorder=3)
    ax.scatter([sx1], [sy1], marker="s", s=180, c="darkgreen", label="static 1", zorder=3)

    # dynamic artists
    a0 = ax.scatter([], [], s=320, c="tab:blue", label="avatar 0 (participant)", zorder=5)
    a1 = ax.scatter([], [], s=320, c="tab:red",  label="avatar 1 (agent/partner)", zorder=5)
    sh0 = ax.scatter([], [], s=120, c="tab:blue", alpha=0.35, label="shadow 0", zorder=4)
    sh1 = ax.scatter([], [], s=120, c="tab:red",  alpha=0.35, label="shadow 1", zorder=4)
    title = ax.set_title("")
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)

    def update(frame):
        i = min(frame*speed, n-1)
        row = df.iloc[i]
        x0, y0 = xy(row["pos0"]); x1, y1 = xy(row["pos1"])
        a0.set_offsets([[x0, y0]]); a1.set_offsets([[x1, y1]])
        sh0.set_offsets([list(xy((row["pos0"]+sd0) % RING))])
        sh1.set_offsets([list(xy((row["pos1"]+sd1) % RING))])
        # grow the dot when its motor is firing (feeling contact)
        a0.set_sizes([700 if row["motor_0_vibrate_software"] else 320])
        a1.set_sizes([700 if row["motor_1_vibrate_software"] else 320])
        title.set_text(f"t = {row['timestamp']:.1f}s   "
                       f"motor0={int(row['motor_0_vibrate_software'])} "
                       f"motor1={int(row['motor_1_vibrate_software'])}")
        return a0, a1, sh0, sh1, title

    frames = n // speed + 1
    anim = FuncAnimation(fig, update, frames=frames, interval=20, blit=False)
    plt.show()
    return anim

if __name__ == "__main__":
    if "--demo" in sys.argv:
        p = make_demo_csv()
        print(f"wrote {p}; launching visualizer")
        visualize(p)
    elif len(sys.argv) > 1:
        visualize(sys.argv[1])
    else:
        print("usage: python pce_viz.py path/to/trial.csv   (or --demo)")
