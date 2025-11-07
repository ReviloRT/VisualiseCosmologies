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

# Class for storing, interpolating and integrating a single value over time
class TimeValue:
    def __init__(self, initial_value=0.0):
        self.initial_value = initial_value
        self.value = initial_value
        self.history = []

    # Get the current value
    def get(self):
        return self.value
    
    # Update the value and store
    def update(self, new_value, time):
        self.value = new_value
        self.history.append((time, self.value))
    
    # Integrate value from given time until now using trapezoidal rule
    def integrate(self, start_time):
        total = 0.0
        prev_time = self.history[-1][0] if self.history else start_time
        prev_value = self.get()
        for t, v in reversed(self.history):
            if t <= start_time:
                break
            dt = prev_time - t
            total += 0.5 * (prev_value + v) * dt
            prev_time = t
            prev_value = v
        # Use interpolated value at start_time for last part segment
        dt = prev_time - start_time
        total += 0.5 * (prev_value + self.get_at_time(start_time)) * dt
        return total

    # Interpolate value for a given time
    def get_at_time(self, query_time):
        if not self.history:
            return self.get()
        for i in range(len(self.history)-1, -1, -1):
            t, v = self.history[i]
            if t <= query_time:
                if i == len(self.history) - 1:
                    return v
                t_next, v_next = self.history[i+1]
                # Linear interpolation
                factor = (query_time - t) / (t_next - t)
                return v + factor * (v_next - v)
        return self.history[0][1]

    # override the math operators like * + - / **to act like a float when interacting with other numbers
    # This allows TimeValue to be used seamlessly in calculations
    def __mul__(self, other):
        if isinstance(other, TimeValue):
            return self.value * other.value
        return self.value * other
    
    def __rmul__(self, other):
        return self.__mul__(other) 
    
    def __add__(self, other):
        if isinstance(other, TimeValue):
            return self.value + other.value
        return self.value + other
    
    def __radd__(self, other):
        return self.__add__(other)  
    
    def __sub__(self, other):
        if isinstance(other, TimeValue):
            return self.value - other.value
        return self.value - other
    
    def __rsub__(self, other):
        if isinstance(other, TimeValue):
            return other.value - self.value
        return other - self.value
    
    def __truediv__(self, other):
        if isinstance(other, TimeValue):
            return self.value / other.value
        return self.value / other
    
    def __rtruediv__(self, other):
        if isinstance(other, TimeValue):
            return other.value / self.value
        return other / self.value
    
    def __pow__(self, power, modulo=None):
        return self.value ** power
    
    def __rpow__(self, other):
        return other ** self.value

    def __str__(self):
        return f"TimeValue({self.value})"
    
    def __repr__(self):
        return f"TimeValue({self.value})"


class SpaceTime:
    integrate_on_scale: bool = True
    scale_factor: TimeValue = TimeValue(1.0)
    light_speed: TimeValue = TimeValue(10.0)
    expansion_rate: float = 1
    omega_matter: float = 0.3
    omega_dark_energy: float = 0.7
    hubble_param: float = 0.1
    t_lambda: float = 0.0


    def __init__(self, objects=None):
        self.objects = objects or []

    def step(self, dt: float, time: float): 
        # Replace with different expansion models
        
        # self.lambda_cdm(dt, time)
        self.constant(dt, time)
        # self.update_light_speed(dt, time)


    def update_light_speed(self, dt: float, time: float):
        self.light_speed.update(self.light_speed.get() * 0.99, time)
        integrate_on_scale = False


    def static(self, dt: float, time: float):
        pass

    def constant(self, dt: float, time: float):
        self.scale_factor.update(self.scale_factor.get() + self.expansion_rate * dt, time)

    def lambda_cdm(self, dt: float, time: float):
        self.t_lambda = 2.0 / 3.0 / self.hubble_param / math.sqrt(self.omega_dark_energy)
        self.scale_factor.update((self.omega_matter / self.omega_dark_energy) ** (1/3) * math.sinh(time / self.t_lambda) ** (2/3), time)


    # For a given time and object, iterate a solution for the time taken for light to reach the observer at position zero.
    def get_observed_time_over_scale(self, obj, now, max_iterations=10, tolerance=0.01):
        distance = math.sqrt(obj.pos[0]**2 + obj.pos[1]**2)
        if distance < 1e-6:
            return now
        time_estimate = distance / self.light_speed
        for _ in range(max_iterations):
            a_avg = self.scale_factor.integrate(now - time_estimate) / time_estimate
            new_time_estimate = (a_avg) * distance / self.light_speed
            print(distance, time_estimate, new_time_estimate, a_avg)
            if abs(new_time_estimate - time_estimate) < tolerance:
                break
            time_estimate = 0.5 * (time_estimate + new_time_estimate)  # relax the update to help convergence
        return now - time_estimate



    def get_observed_time_over_time(self, obj, now, max_iterations=10, tolerance=0.01):
        distance = math.sqrt(obj.pos[0]**2 + obj.pos[1]**2)
        if distance < 1e-6:
            return now
        time_estimate = distance / self.light_speed
        for _ in range(max_iterations):
            c_avg = self.light_speed.integrate(now - time_estimate)/time_estimate
            new_time_estimate = distance / c_avg
            if abs(new_time_estimate - time_estimate) < tolerance:
                time_estimate = new_time_estimate
                break
            time_estimate = 0.5 * (time_estimate + new_time_estimate)  # relax the update to help convergence
        return now - time_estimate

    def snapshot(self):
        return [{"pos": [float(o.pos[0]), float(o.pos[1])]} for o in self.objects]

    def render_from_observer(self, time):
        for obj in self.objects:
            obj.pos = [obj.dim_pos[0] * self.scale_factor, obj.dim_pos[1] * self.scale_factor]
            yield obj.pos, (255, 0, 0)

            if self.integrate_on_scale: observed_time = self.get_observed_time_over_scale(obj, time)
            else: observed_time = self.get_observed_time_over_time(obj, time)
            scale_at_obs = self.scale_factor.get_at_time(observed_time)
            pos_at_obs = [obj.dim_pos[0] * scale_at_obs, obj.dim_pos[1] * scale_at_obs]
            yield pos_at_obs, (0, 255, 0)

            implied_distance = self.light_speed.initial_value * (time - observed_time)
            implied_pos = [obj.dim_pos[0] * (implied_distance / math.sqrt(obj.dim_pos[0]**2 + obj.dim_pos[1]**2)),
                           obj.dim_pos[1] * (implied_distance / math.sqrt(obj.dim_pos[0]**2 + obj.dim_pos[1]**2))]
            yield implied_pos, (0, 0, 255)

def random_space(num=100, spread=200.0):
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
    sim.hud.draw(screen, [
        ("t", f"{sim.sim_time:.2f}s"), 
        ("a", f"{sim.space.scale_factor.get():.2f}"), 
        ("t_Λ", f"{sim.space.t_lambda:.2f}s"),
        ("c", f"{sim.space.light_speed.get():.2f}"),
        ("Blue:", "Apparent Pos Now"),
        ("Green:", "Pos When Emitted"),
        ("Red:", "Pos Now"),
    ])

    pygame.display.flip()

def update_graph(sim):
    # Update the graph data
    sim.graph.update([("a", sim.space.scale_factor.get())])

def main():
    parser = argparse.ArgumentParser(description="2D SpaceTime renderer")
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--scale", type=float, default=1.0, help="pixels per world unit")
    parser.add_argument("--dot-size", type=float, default=3.0, help="base dot radius in pixels")
    parser.add_argument("--save-interval", type=float, default=1.0, help="seconds between automatic snapshots; 0 to disable")
    parser.add_argument("--num", type=int, default=100, help="number of random objects to create if no input provided")
    parser.add_argument("--spread", type=float, default=2000.0, help="spread of random objects")

    args = parser.parse_args()

    space = random_space(100, 200)
    sim = Simulator(space, width=args.width, height=args.height, scale=args.scale, dot_size=args.dot_size, save_interval=args.save_interval)
    init_ui(sim)
    sim.run(60, draw, [(20, update_graph)])


if __name__ == '__main__':
    main()
