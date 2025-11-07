"""UI support module for ExpansionSim.
Contains HUD, GraphOverlay, Simulator class and global init_ui/draw functions.
The Simulator here is a lightweight runner; call init_ui(sim) after creating a Simulator
so HUD and GraphOverlay are initialized. draw(sim) is a global draw function called by
Simulator.run so overlays are kept outside the Simulator class logic.
"""
import os
import time
import json
from collections import deque

import pygame


class HUD:
    """Simple top-right HUD renderer for label/value pairs."""
    def __init__(self, font, width=800, padding=10, spacing=4, color=(255, 255, 255)):
        self.font = font
        self.width = width
        self.padding = padding
        self.spacing = spacing
        self.color = color

    def draw(self, surface, items):
        if not self.font:
            return
        y = self.padding
        for label, value in items:
            text = f"{label}: {value}"
            try:
                surf = self.font.render(str(text), True, self.color)
            except Exception:
                continue
            x = self.width - surf.get_width() - self.padding
            surface.blit(surf, (x, y))
            y += surf.get_height() + self.spacing


class GraphOverlay:
    """Top-left semi-transparent multi-series graph overlay with history."""
    def __init__(self, font, max_points=500, size=(260, 120), colors=None, padding=6):
        self.font = font
        self.max_points = max_points
        self.size = size
        self.padding = padding
        self.history = {}  # label -> deque
        self.colors = colors or [
            (255, 100, 100),
            (100, 255, 100),
            (100, 150, 255),
            (255, 200, 100),
            (200, 100, 255),
        ]

    def update(self, items):
        for label, value in items:
            if label not in self.history:
                self.history[label] = deque(maxlen=self.max_points)
            try:
                self.history[label].append(float(value))
            except Exception:
                self.history[label].append(0.0)

    def draw(self, surface, items=None, pos=(10, 10)):
        # if items provided, update history first
        if items:
            self.update(items)
        w, h = self.size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # semi-transparent background
        surf.fill((20, 20, 20, 160))
        # border
        pygame.draw.rect(surf, (255, 255, 255, 40), (0, 0, w, h), 1)

        # draw each series in the order of items if provided, else stable order
        labels = [lab for lab, _ in (items or [])]
        if not labels:
            labels = list(self.history.keys())

        for idx, label in enumerate(labels):
            dq = self.history.get(label)
            if not dq or len(dq) < 2:
                continue
            vals = list(dq)
            minv = min(vals)
            maxv = max(vals)
            if abs(maxv - minv) < 1e-6:
                minv -= 0.5
                maxv += 0.5
            left = self.padding
            right = w - self.padding
            top = self.padding
            bottom = h - 18
            vx = (right - left) / max(1, len(vals) - 1)
            scale_y = (bottom - top) / (maxv - minv)
            pts = []
            for i, v in enumerate(vals):
                x = int(left + i * vx)
                y = int(bottom - (v - minv) * scale_y)
                pts.append((x, y))
            color = self.colors[idx % len(self.colors)]
            color_a = (*color, 200)
            pygame.draw.lines(surf, color_a, False, pts, 2)
            # label text (latest value)
            if self.font:
                try:
                    text = f"{label}: {vals[-1]:.2f}"
                    txt_s = self.font.render(text, True, (*color, 220))
                    surf.blit(txt_s, (left, h - 16))
                except Exception:
                    pass

        surface.blit(surf, pos)


class Simulator:
    """Lightweight simulator/runner that holds state used by UI draw().
    Note: UI elements (hud, graph) are set by init_ui(sim) function so they are
    decoupled from the Simulator implementation.
    """
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
        # simulation time (seconds)
        self.sim_time = 0.0
        # overlay placeholders (initialized by init_ui)
        try:
            pygame.font.init()
            self.font = pygame.font.SysFont(None, 24)
        except Exception:
            self.font = None
        self.hud = None
        self.graph = None
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

    def save_snapshot(self):
        ts = time.time()
        fname = os.path.join(self.snapshots_dir, f"snapshot_{int(ts * 1000)}.json")
        data = {"time": ts, "objects": self.space.snapshot()}
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print("Saved snapshot:", fname)

    def run(self, target_fps=60, draw_function=None, periodic_functions=None):
        print("Controls: SPACE pause/resume, +/- adjust dot size, S save snapshot, ESC quit")
        while self.running:
            dt_ms = self.clock.tick(target_fps)
            dt = dt_ms / 1000.0
            self.handle_events()
            if not self.paused:
                # advance simulation
                self.space.step(dt, self.sim_time)
                # advance simulation time only while running
                self.sim_time += dt

            # use the global draw function defined below
            if draw_function:
                draw_function(self)

            if periodic_functions:
                # Run periodic functions at their specified rates
                for rate, func in periodic_functions:
                    if not hasattr(func, "_last_called"): func._last_called = 0
                    now = time.time()
                    if (now - func._last_called) >= (1.0 / rate):
                        func(self)
                        func._last_called = now

            now = time.time()
            if self.save_interval > 0 and (now - self._last_save) >= self.save_interval:
                self.save_snapshot()
                self._last_save = now

        pygame.quit()

