"""
PCE visualizer

Usage:
    python pce_viz.py path/to/trial.csv
    python pce_viz.py path/to/trial.csv --speed 5
"""
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

RING = 600
AVATAR_W = 20

def angle(x):
    return 2 * np.pi * (np.asarray(x) % RING) / RING

def xy(pos, r=1.0):
    a = angle(pos)
    return r*np.cos(a), r*np.sin(a)

def visualize(csv_path, speed=4, trail=40):
    df = pd.read_csv(csv_path)
    n = len(df)

    # detect click ONSET events (0 -> 1 transitions), not held frames
    b0 = df["button0"].to_numpy()
    b1 = df["button1"].to_numpy()
    onset0 = np.where((b0[1:] == 1) & (b0[:-1] == 0))[0] + 1
    onset1 = np.where((b1[1:] == 1) & (b1[:-1] == 0))[0] + 1
    print(f"Trial has {len(df)} rows, ~{df['timestamp'].iloc[-1]:.0f}s")
    print(f"P0 clicked {len(onset0)} time(s); P1 clicked {len(onset1)} time(s)")

    sd0 = df["shadow_delta0"].iloc[0]
    sd1 = df["shadow_delta1"].iloc[0]

    fig = plt.figure(figsize=(13, 7))
    axR = fig.add_subplot(1, 2, 1, aspect="equal")   # the ring
    axS = fig.add_subplot(1, 2, 2)                     # position-vs-time strip

    # ---- ring panel ----
    axR.set_xlim(-1.4, 1.4); axR.set_ylim(-1.4, 1.4); axR.axis("off")
    axR.add_patch(plt.Circle((0, 0), 1.0, fill=False, color="lightgray", lw=2))
    sx0, sy0 = xy(df["static_object_0"].iloc[0])
    sx1, sy1 = xy(df["static_object_1"].iloc[0])
    axR.scatter([sx0],[sy0], marker="s", s=160, c="tab:green", zorder=3, label="static 0")
    axR.scatter([sx1],[sy1], marker="s", s=160, c="darkgreen", zorder=3, label="static 1")
    a0 = axR.scatter([], [], s=320, c="tab:blue", zorder=6, label="P0 (participant)")
    a1 = axR.scatter([], [], s=320, c="tab:red",  zorder=6, label="P1 (partner)")
    sh0 = axR.scatter([], [], s=110, c="tab:blue", alpha=0.3, zorder=4, label="shadow 0")
    sh1 = axR.scatter([], [], s=110, c="tab:red",  alpha=0.3, zorder=4, label="shadow 1")
    click_ring = axR.scatter([], [], s=1400, facecolors="none",
                             edgecolors="black", linewidths=3, zorder=7)
    title = axR.set_title("")
    axR.legend(loc="upper right", fontsize=7, framealpha=0.9)

    # ---- position-vs-time strip (whole trial, with a moving cursor) ----
    t = df["timestamp"].to_numpy()
    axS.plot(t, df["pos0"], color="tab:blue", lw=0.8, label="P0 pos")
    axS.plot(t, df["pos1"], color="tab:red",  lw=0.8, label="P1 pos")
    # mark clicks on the strip
    for i in onset0:
        axS.axvline(t[i], color="tab:blue", ls=":", alpha=0.6)
    for i in onset1:
        axS.axvline(t[i], color="tab:red", ls=":", alpha=0.6)
    axS.set_xlabel("time (s)"); axS.set_ylabel("position (0-600)")
    axS.set_title("positions over time (dotted = clicks)")
    axS.legend(loc="upper right", fontsize=7)
    cursor = axS.axvline(t[0], color="black", lw=1)

    def update(frame):
        i = min(frame*speed, n-1)
        row = df.iloc[i]
        a0.set_offsets([list(xy(row["pos0"]))])
        a1.set_offsets([list(xy(row["pos1"]))])
        sh0.set_offsets([list(xy((row["pos0"]+sd0) % RING))])
        sh1.set_offsets([list(xy((row["pos1"]+sd1) % RING))])
        a0.set_sizes([700 if row["motor_0_vibrate_software"] else 320])
        a1.set_sizes([700 if row["motor_1_vibrate_software"] else 320])

        # flash a black ring on a click (show for a short window after onset)
        recent_click = []
        if any(abs(i - c) < 25 for c in onset0):
            recent_click.append(list(xy(row["pos0"])))
        if any(abs(i - c) < 25 for c in onset1):
            recent_click.append(list(xy(row["pos1"])))
        click_ring.set_offsets(recent_click if recent_click else np.empty((0,2)))

        cursor.set_xdata([row["timestamp"], row["timestamp"]])
        title.set_text(f"t={row['timestamp']:.1f}s  "
                       f"motor0={int(row['motor_0_vibrate_software'])} "
                       f"motor1={int(row['motor_1_vibrate_software'])}")
        return a0, a1, sh0, sh1, click_ring, cursor, title

    frames = n // speed + 1
    anim = FuncAnimation(fig, update, frames=frames, interval=20, blit=False)
    plt.tight_layout()
    plt.show()
    return anim

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    speed = 4
    if "--speed" in sys.argv:
        speed = int(sys.argv[sys.argv.index("--speed")+1])
    if args:
        visualize(args[0], speed=speed)
    else:
        print("usage: python pce_viz2.py path/to/trial.csv [--speed N]")
