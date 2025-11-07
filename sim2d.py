"""sim2d.py - simulation-specific code only. UI and runner live in ui.py"""
import argparse
import random
import math
import os
import sys
import pygame
from dataclasses import dataclass

from ui import Simulator, HUD, GraphOverlay


@dataclass
class SpaceObject:
    dim_pos: list
    pos: list = None


class SpaceTime:
    scale_factor: float = 1.0
    expansion_rate: float = 1.0
    omega_matter: float = 0.3
    omega_dark_energy: float = 0.7
    hubble_param: float = 1.0

    def __init__(self, objects=None):
        self.objects = objects or []

    def step(self, dt: float, time: float):
        self.lambda_cdm(dt, time)

    def static(self, dt: float, time: float):
        pass

    def constant(self, dt: float, time: float):
        self.scale_factor += self.expansion_rate * dt

    def lambda_cdm(self, dt: float, time: float):
        self.t_lambda = 2.0 / 3.0 / self.hubble_param / math.sqrt(self.omega_dark_energy)
        self.scale_factor = (self.omega_matter / self.omega_dark_energy) ** (1/3) * math.sinh(time / self.t_lambda) ** (2/3)

    def snapshot(self):
        return [{"pos": [float(o.pos[0]), float(o.pos[1])]} for o in self.objects]

    def render_from_observer(self, time):
        for obj in self.objects:
            obj.pos = [obj.dim_pos[0] * self.scale_factor, obj.dim_pos[1] * self.scale_factor]
            colour = (255, 255, 255)
            yield obj.pos, colour


def random_space(num=100, spread=20.0):
    objs = []
    for _ in range(num):
        theta = random.uniform(0, 2 * math.pi)
        r = spread * math.sqrt(random.random())
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        objs.append(SpaceObject([x, y]))
    return SpaceTime(objs)

    
# UI helper functions
def init_ui(simulator):
    """Initialize HUD and GraphOverlay on an existing Simulator instance."""
    simulator.hud = HUD(simulator.font, width=simulator.width)
    simulator.graph = GraphOverlay(simulator.font, max_points=1000, size=(260, 120))


def draw(sim):
    """Global draw function that renders the simulation and overlays for the given Simulator instance."""
    # clear
    screen = sim.screen
    screen.fill((0, 0, 0))

    # draw space objects
    for pos, colour in sim.space.render_from_observer(sim.sim_time):
        sx, sy = sim.world_to_screen(pos[0], pos[1])
        r = int(sim.dot_size)
        pygame.draw.circle(screen, colour, (sx, sy), r)

    # draw graph (top-left)
    sim.graph.draw(screen, None, pos=(10, 10))

    # draw HUD (top-right)
    sim.hud.draw(screen, [("t", f"{sim.sim_time:.2f}s"), ("a", f"{sim.space.scale_factor:.2f}"), ("t_Λ", f"{sim.space.t_lambda:.2f}s")])

    pygame.display.flip()

def update_graph(sim):
    # Update the graph data
    sim.graph.update([("a", sim.space.scale_factor)])

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
    init_ui(sim)
    sim.run(60, draw, [(20, update_graph)])


if __name__ == '__main__':
    main()
