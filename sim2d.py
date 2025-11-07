"""sim2d.py

Real-time 2D renderer for SpaceObjects in SpaceTime using pygame.
- White dots represent objects (configurable size).
- Real-time update loop (pausable).
- Saves state snapshots (JSON) at regular intervals into ./snapshots.
- Keyboard controls: +/- to change dot size, SPACE to pause, S to save snapshot now, ESC or window close to quit.

Usage: python sim2d.py [--dot-size 3.0] [--scale 1.0] [--save-interval 1.0]

Install dependency: pip install -r requirements.txt

"""
import os
import json
import time
import math
import argparse
import random
from dataclasses import dataclass, asdict

try:
    import pygame
except Exception as e:
    raise SystemExit("pygame is required. Install with: pip install pygame")

# -------------------- Model --------------------

@dataclass
class SpaceObject:
    pos: list  # [x, y]

class SpaceTime:
    def __init__(self, objects=None):
        self.objects = objects or []

    def step(self, dt: float):
        pass

    def snapshot(self):
        return [
            {"pos": [float(o.pos[0]), float(o.pos[1])]}
            for o in self.objects
        ]
    
    def render_from_observer(self):
        for obj in self.objects:
            yield obj.pos

# -------------------- Renderer / Controller --------------------

class Simulator:
    def __init__(self, space, width=800, height=600, scale=1.0, dot_size=3.0, save_interval=1.0):
        self.space = space
        self.width = width
        self.height = height
        self.scale = float(scale)
        self.dot_size = float(dot_size)
        self.save_interval = float(save_interval)

        pygame.init()
        pygame.display.set_caption("SpaceTime 2D")
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = False
        self._last_save = time.time()
        # simulation time (seconds) - advances only when not paused
        self.sim_time = 0.0
        # initialize font for HUD (time counter)
        try:
            # pygame.font is initialized as part of pygame.init(), but ensure font module is ready
            pygame.font.init()
            self.font = pygame.font.SysFont(None, 24)
        except Exception:
            self.font = None
        self.snapshots_dir = os.path.join(os.path.dirname(__file__), "snapshots")
        os.makedirs(self.snapshots_dir, exist_ok=True)

    def world_to_screen(self, x, y):
        sx = self.width / 2 + x * self.scale
        sy = self.height / 2 - y * self.scale
        return int(sx), int(sy)

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.running = False
                elif ev.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif ev.key == pygame.K_s:
                    self.save_snapshot()
                elif ev.key == pygame.K_PLUS or ev.key == pygame.K_EQUALS:
                    self.dot_size *= 1.2
                elif ev.key == pygame.K_MINUS or ev.key == pygame.K_UNDERSCORE:
                    self.dot_size /= 1.2

    def draw(self):
        # black background, white dots
        self.screen.fill((0, 0, 0))
        for pos in self.space.render_from_observer():
            sx, sy = self.world_to_screen(pos[0], pos[1])
            r = int(self.dot_size)
            pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy), r)

        # draw simulation time in top-right corner
        if self.font is not None:
            try:
                time_text = f"t = {self.sim_time:.2f}s"
                text_surf = self.font.render(time_text, True, (255, 255, 255))
                tx = self.width - text_surf.get_width() - 10
                ty = 10
                self.screen.blit(text_surf, (tx, ty))
            except Exception:
                pass
        pygame.display.flip()

    def save_snapshot(self):
        ts = time.time()
        fname = os.path.join(self.snapshots_dir, f"snapshot_{int(ts * 1000)}.json")
        data = {"time": ts, "objects": self.space.snapshot()}
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print("Saved snapshot:", fname)

    def run(self, target_fps=60):
        print("Controls: SPACE pause/resume, +/- adjust dot size, S save snapshot, ESC quit")
        while self.running:
            dt_ms = self.clock.tick(target_fps)
            dt = dt_ms / 1000.0
            self.handle_events()
            if not self.paused:
                self.space.step(dt)
                # advance simulation time only while running
                self.sim_time += dt

            self.draw()

            now = time.time()
            if self.save_interval > 0 and (now - self._last_save) >= self.save_interval:
                self.save_snapshot()
                self._last_save = now

        pygame.quit()

# -------------------- Utilities / Example setup --------------------

def random_space(num=100, spread=200.0, speed=20.0):
    objs = []
    for _ in range(num):
        x = random.uniform(-spread, spread)
        y = random.uniform(-spread, spread)
        objs.append(SpaceObject([x, y]))
    return SpaceTime(objs)


def main():
    parser = argparse.ArgumentParser(description="2D SpaceTime renderer")
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--scale", type=float, default=1.0, help="pixels per world unit")
    parser.add_argument("--dot-size", type=float, default=3.0, help="base dot radius in pixels")
    parser.add_argument("--save-interval", type=float, default=1.0, help="seconds between automatic snapshots; 0 to disable")
    parser.add_argument("--num", type=int, default=200, help="number of random objects to create if no input provided")

    args = parser.parse_args()

    space = random_space(num=args.num)
    sim = Simulator(space, width=args.width, height=args.height, scale=args.scale, dot_size=args.dot_size, save_interval=args.save_interval)
    sim.run()


if __name__ == '__main__':
    main()
