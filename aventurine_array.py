#!/usr/bin/env python3
"""Aventurine Array — neon laser-mirror arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/AVENTURINE_ARRAY_ElbowOS.mp4")
TITLE, HANDLE = "AVENTURINE ARRAY", "x.com/ElbowOS"

INK = (6, 18, 12)
MOSS = (18, 48, 28)
MINT = (72, 255, 176)
GOLD = (255, 214, 72)
LEAF = (46, 196, 92)
TEAL = (48, 220, 210)
ROSE = (255, 92, 140)
AMBER = (255, 160, 48)
FOG = (160, 210, 180)
WHITE = (236, 255, 244)


class Game:
    def __init__(self, record=False):
        self.record = record
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY and not record else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            self.screen = pygame.Surface((W, H))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.SysFont("dejavusans", 54, bold=True)
        self.font_md = pygame.font.SysFont("dejavusans", 36, bold=True)
        self.font_sm = pygame.font.SysFont("dejavusans", 28)
        self.reset()

    def reset(self):
        self.score = 0
        self.combo = 0
        self.sel = 0
        self.t = 0.0
        self.sparks = []
        self.gems = []
        self.mirrors = [
            {"x": W // 2, "y": 520, "ang": 40},
            {"x": 300, "y": 780, "ang": 130},
            {"x": 780, "y": 1020, "ang": 50},
            {"x": 360, "y": 1280, "ang": 140},
            {"x": 720, "y": 1520, "ang": 40},
        ]
        self.emitter = (W // 2, 280)
        for _ in range(7):
            self._spawn_gem()
        self.beam = []

    def _spawn_gem(self):
        y = random.randint(460, 1700)
        x = random.randint(120, W - 120)
        vx = random.choice((-1, 1)) * random.uniform(70, 140)
        col = random.choice((GOLD, MINT, AMBER, ROSE, TEAL))
        self.gems.append({"x": float(x), "y": float(y), "vx": vx, "r": 24, "col": col, "hit": 0})

    def burst(self, x, y, col, n=16):
        for _ in range(n):
            a = random.uniform(0, 6.283)
            sp = random.uniform(80, 280)
            self.sparks.append({"x": x, "y": y, "vx": math.cos(a) * sp, "vy": math.sin(a) * sp,
                                "life": random.uniform(0.3, 0.8), "col": col})

    def _trace(self):
        x, y = float(self.emitter[0]), float(self.emitter[1])
        dx, dy = 0.0, 1.0
        pts = [(x, y)]
        hits = []
        used = set()
        for _ in range(18):
            hit_kind, hit_i, hx, hy, ndx, ndy, dist = None, -1, x, y, dx, dy, 2400
            for i, m in enumerate(self.mirrors):
                if i in used:
                    continue
                mx, my = m["x"], m["y"]
                wx, wy = mx - x, my - y
                proj = wx * dx + wy * dy
                if proj <= 8:
                    continue
                px, py = x + dx * proj, y + dy * proj
                if math.hypot(px - mx, py - my) < 46 and proj < dist:
                    dist = proj
                    hit_kind, hit_i, hx, hy = "m", i, px, py
                    rad = math.radians(m["ang"])
                    nx, ny = math.cos(rad), math.sin(rad)
                    dot = dx * nx + dy * ny
                    ndx, ndy = dx - 2 * dot * nx, dy - 2 * dot * ny
                    ln = math.hypot(ndx, ndy) or 1
                    ndx, ndy = ndx / ln, ndy / ln
            for i, g in enumerate(self.gems):
                if g["hit"]:
                    continue
                gx, gy = g["x"], g["y"]
                wx, wy = gx - x, gy - y
                proj = wx * dx + wy * dy
                if proj <= 4:
                    continue
                px, py = x + dx * proj, y + dy * proj
                if math.hypot(px - gx, py - gy) < g["r"] + 6 and proj < dist:
                    dist = proj
                    hit_kind, hit_i, hx, hy = "g", i, px, py
                    ndx, ndy = dx, dy
            ts = []
            if dx > 0.05:
                ts.append(((W - 40 - x) / dx, "w"))
            if dx < -0.05:
                ts.append(((40 - x) / dx, "w"))
            if dy > 0.05:
                ts.append(((H - 80 - y) / dy, "w"))
            if dy < -0.05:
                ts.append(((240 - y) / dy, "w"))
            for tw, _k in ts:
                if 12 < tw < dist:
                    dist = tw
                    hit_kind = "w"
                    hx, hy = x + dx * tw, y + dy * tw
            if hit_kind is None:
                pts.append((x + dx * 900, y + dy * 900))
                break
            pts.append((hx, hy))
            if hit_kind == "g":
                hits.append(hit_i)
                break
            if hit_kind == "w":
                break
            used.add(hit_i)
            x, y, dx, dy = hx + ndx * 8, hy + ndy * 8, ndx, ndy
            pts.append((x, y))
        self.beam = pts
        return hits

    def autoplay(self):
        if not self.gems:
            return
        m = self.mirrors[self.sel]
        g = min(self.gems, key=lambda z: abs(z["y"] - m["y"]) + 0.15 * abs(z["x"] - m["x"]))
        want = math.degrees(math.atan2(g["y"] - m["y"], g["x"] - m["x"]))
        target = (want + 90) % 360
        diff = (target - m["ang"] + 180) % 360 - 180
        if abs(diff) > 8:
            m["ang"] = (m["ang"] + max(-22, min(22, diff))) % 360
        if self.t * 2 % 1 < 0.08:
            self.sel = (self.sel + 1) % len(self.mirrors)

    def update(self, dt):
        self.t += dt
        if self.record:
            self.autoplay()
        for g in self.gems:
            g["x"] += g["vx"] * dt
            g["y"] += math.sin(self.t * 2.2 + g["y"] * 0.01) * 18 * dt
            if g["x"] < 70 or g["x"] > W - 70:
                g["vx"] *= -1
                g["x"] = max(70, min(W - 70, g["x"]))
        hits = self._trace()
        scored = False
        for i in hits:
            g = self.gems[i]
            g["hit"] = 1
            self.combo += 1
            self.score += 80 + 20 * self.combo
            self.burst(g["x"], g["y"], g["col"])
            scored = True
        if not scored:
            self.combo = max(0, self.combo - (1 if random.random() < 0.02 else 0))
        self.gems = [g for g in self.gems if not g["hit"]]
        while len(self.gems) < 6:
            self._spawn_gem()
        for s in self.sparks:
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            s["life"] -= dt
        self.sparks = [s for s in self.sparks if s["life"] > 0]

    def handle(self, ev):
        if ev.type != pygame.KEYDOWN:
            return
        if ev.key in (pygame.K_w, pygame.K_UP):
            self.sel = (self.sel - 1) % len(self.mirrors)
        elif ev.key in (pygame.K_s, pygame.K_DOWN):
            self.sel = (self.sel + 1) % len(self.mirrors)
        elif ev.key in (pygame.K_a, pygame.K_LEFT):
            self.mirrors[self.sel]["ang"] = (self.mirrors[self.sel]["ang"] - 15) % 360
        elif ev.key in (pygame.K_d, pygame.K_RIGHT):
            self.mirrors[self.sel]["ang"] = (self.mirrors[self.sel]["ang"] + 15) % 360
        elif ev.key == pygame.K_r:
            self.reset()

    def _diamond(self, s, x, y, ang, col, r=40, width=4):
        pts = []
        for k in range(4):
            a = math.radians(ang + 45 + k * 90)
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        pygame.draw.polygon(s, col, pts, width)
        nx, ny = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        pygame.draw.line(s, col, (x - nx * 18, y - ny * 18), (x + nx * 28, y + ny * 28), 3)

    def draw(self, s):
        s.fill(INK)
        for i in range(14):
            y = 240 + i * 120 + int(math.sin(self.t * 0.7 + i) * 6)
            pygame.draw.line(s, MOSS, (40, y), (W - 40, y), 1)
        pygame.draw.rect(s, LEAF, (28, 230, W - 56, H - 310), 3, border_radius=18)
        ex, ey = self.emitter
        pulse = 16 + int(6 * math.sin(self.t * 8))
        pygame.draw.circle(s, GOLD, (ex, ey), pulse)
        pygame.draw.circle(s, WHITE, (ex, ey), 8)
        pygame.draw.polygon(s, AMBER, [(ex - 28, ey - 8), (ex + 28, ey - 8), (ex, ey + 22)])
        if len(self.beam) >= 2:
            glow = [(int(p[0]), int(p[1])) for p in self.beam]
            pygame.draw.lines(s, (40, 90, 50), False, glow, 14)
            pygame.draw.lines(s, MINT, False, glow, 6)
            pygame.draw.lines(s, WHITE, False, glow, 2)
        for i, m in enumerate(self.mirrors):
            col = GOLD if i == self.sel else TEAL
            self._diamond(s, m["x"], m["y"], m["ang"], col, 44 if i == self.sel else 38,
                          6 if i == self.sel else 3)
        for g in self.gems:
            pygame.draw.circle(s, g["col"], (int(g["x"]), int(g["y"])), g["r"])
            pygame.draw.circle(s, WHITE, (int(g["x"] - 6), int(g["y"] - 6)), 5)
        for sp in self.sparks:
            pygame.draw.circle(s, sp["col"], (int(sp["x"]), int(sp["y"])), max(2, int(sp["life"] * 8)))
        title = self.font_lg.render(TITLE, True, MINT)
        s.blit(title, title.get_rect(center=(W // 2, 64)))
        handle = self.font_sm.render(HANDLE, True, GOLD)
        s.blit(handle, handle.get_rect(center=(W // 2, 118)))
        meta = self.font_md.render(f"SCORE  {self.score}    COMBO  {self.combo}", True, FOG)
        s.blit(meta, meta.get_rect(center=(W // 2, 176)))
        hint = self.font_sm.render("W/S select   A/D rotate   R reset", True, LEAF)
        s.blit(hint, hint.get_rect(center=(W // 2, H - 42)))

    def play(self):
        run = True
        while run:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    run = False
                self.handle(ev)
            self.update(dt)
            self.draw(self.screen)
            pygame.display.flip()
        pygame.quit()

    def record_mp4(self, path):
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        frames = SECS * FPS
        surf = self.screen
        for _ in range(frames):
            self.update(1.0 / FPS)
            self.draw(surf)
            proc.stdin.write(pygame.image.tostring(surf, "RGB"))
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "ignore")
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1200:]}")
        print("wrote", path)
        pygame.quit()


def main():
    g = Game(record=RECORD)
    if PLAY and not RECORD:
        g.play()
    else:
        g.record_mp4(OUT)


if __name__ == "__main__":
    main()
