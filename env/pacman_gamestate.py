"""
Pac-Man refactored into a GameState class with a directed graph
representing game states and their transitions.

Key additions over the original:
  - GameState.get_start_state()  → returns the initial state snapshot
  - GameState.is_goal_state()    → True when all food/capsules are gone (win)
  - GameState.get_successors()   → list of (action, next_state) pairs reachable
                                   from the current state (directed graph edges)
  - GameState.run()              → executes the pygame game loop
"""

import os, sys, copy, math
import pygame
from pathlib import Path

# Carregamento robusto e dinâmico do board sem forçar caminhos específicos
try:
    from env.board import boards
    BOARDS = boards
except ImportError:
    print("Erro: O arquivo board.py não foi encontrado na mesma pasta.")
    sys.exit(1)

# Assume que a pasta 'assets' está no mesmo diretório que este script
ASSETS = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets"))

WIDTH, HEIGHT = 900, 950
FPS = 60
PI = math.pi
RIGHT, LEFT, UP, DOWN = 0, 1, 2, 3

# ══════════════════════════════════════════════════════════════════════════════
#  StateSnapshot OTIMIZADO - Super Rápido para o A*
# ══════════════════════════════════════════════════════════════════════════════
class StateSnapshot:
    __slots__ = (
        "player_pos", "player_dir",
        "ghost_positions", "ghost_directions", "ghost_dead", "ghost_in_box",
        "active_food", "active_capsules",  # OTIMIZAÇÃO: Usa frozenset em vez da matriz inteira
        "score", "powerup", "power_counter",
        "eaten_ghost", "lives", "game_over", "game_won",
    )

    def __init__(self, **kw):
        for k, v in kw.items():
            object.__setattr__(self, k, v)

    def __setattr__(self, *_):
        raise AttributeError("StateSnapshot is immutable")

    def __hash__(self):
        return hash((
            self.player_pos, self.player_dir,
            tuple(self.ghost_positions),
            tuple(self.ghost_directions),
            tuple(self.ghost_dead),
            self.active_food,
            self.active_capsules,
            self.score,
            self.powerup,
            self.lives,
        ))

    def __eq__(self, other):
        return (
            isinstance(other, StateSnapshot)
            and self.player_pos    == other.player_pos
            and self.player_dir    == other.player_dir
            and self.ghost_positions == other.ghost_positions
            and self.active_food   == other.active_food
            and self.active_capsules == other.active_capsules
            and self.score         == other.score
            and self.powerup       == other.powerup
            and self.lives         == other.lives
        )

# ══════════════════════════════════════════════════════════════════════════════
#  Ghost 
# ══════════════════════════════════════════════════════════════════════════════
class Ghost:
    def __init__(self, x, y, target, speed, img, direction, dead, in_box, gid,
                 level, powerup, eaten_ghost, spooked_img, dead_img, screen):
        self.x_pos     = x
        self.y_pos     = y
        self.center_x  = x + 22
        self.center_y  = y + 22
        self.target    = target
        self.speed     = speed
        self.img       = img
        self.direction = direction
        self.dead      = dead
        self.in_box    = in_box
        self.id        = gid
        self._level       = level
        self._powerup     = powerup
        self._eaten_ghost = eaten_ghost
        self._spooked     = spooked_img
        self._dead_img    = dead_img
        self._screen      = screen
        self.turns, self.in_box = self._check_collisions()
        self.rect = self._draw()

    def _draw(self):
        pg = self._powerup
        eg = self._eaten_ghost
        if (not pg and not self.dead) or (eg[self.id] and pg and not self.dead):
            self._screen.blit(self.img, (self.x_pos, self.y_pos))
        elif pg and not self.dead and not eg[self.id]:
            self._screen.blit(self._spooked, (self.x_pos, self.y_pos))
        else:
            self._screen.blit(self._dead_img, (self.x_pos, self.y_pos))
        return pygame.rect.Rect((self.center_x - 18, self.center_y - 18), (36, 36))

    def _check_collisions(self):
        level = self._level
        num1  = (HEIGHT - 50) // 32
        num2  = WIDTH // 30
        num3  = 15
        self.turns = [False, False, False, False]
        if 0 < self.center_x // 30 < 29:
            if level[(self.center_y - num3) // num1][self.center_x // num2] == 9:
                self.turns[UP] = True
            for (turn_idx, cx, cy) in [
                (LEFT,  self.center_x - num3, self.center_y),
                (RIGHT, self.center_x + num3, self.center_y),
                (DOWN,  self.center_x,        self.center_y + num3),
                (UP,    self.center_x,        self.center_y - num3),
            ]:
                cell = level[cy // num1][cx // num2]
                if cell < 3 or (cell == 9 and (self.in_box or self.dead)):
                    self.turns[turn_idx] = True

            for moving_axis in ([UP, DOWN], [LEFT, RIGHT]):
                if self.direction in moving_axis:
                    if 12 <= self.center_x % num2 <= 18:
                        for cy, t in [(self.center_y + num3, DOWN), (self.center_y - num3, UP)]:
                            c = level[cy // num1][self.center_x // num2]
                            if c < 3 or (c == 9 and (self.in_box or self.dead)):
                                self.turns[t] = True
                    if 12 <= self.center_y % num1 <= 18:
                        for cx, t in [(self.center_x - num2, LEFT), (self.center_x + num2, RIGHT)]:
                            c = level[self.center_y // num1][cx // num2]
                            if c < 3 or (c == 9 and (self.in_box or self.dead)):
                                self.turns[t] = True
        else:
            self.turns[RIGHT] = self.turns[LEFT] = True

        self.in_box = 350 < self.x_pos < 550 and 370 < self.y_pos < 480
        return self.turns, self.in_box

    def _greedy_move(self, prefer_vertical: bool, prefer_horizontal: bool):
        tx, ty = self.target
        d      = self.direction
        t      = self.turns
        sp     = self.speed

        def try_turn_vertical():
            if ty > self.y_pos and t[DOWN]:
                self.direction = DOWN;  self.y_pos += sp;  return True
            if ty < self.y_pos and t[UP]:
                self.direction = UP;    self.y_pos -= sp;  return True
            return False

        def try_turn_horizontal():
            if tx > self.x_pos and t[RIGHT]:
                self.direction = RIGHT; self.x_pos += sp;  return True
            if tx < self.x_pos and t[LEFT]:
                self.direction = LEFT;  self.x_pos -= sp;  return True
            return False

        def fallback():
            for td, dx, dy in [(DOWN,0,sp),(UP,0,-sp),(LEFT,-sp,0),(RIGHT,sp,0)]:
                if t[td]:
                    self.direction = td
                    self.x_pos   += dx
                    self.y_pos   += dy
                    return

        if d == RIGHT:
            if tx > self.x_pos and t[RIGHT]:
                if prefer_vertical and try_turn_vertical(): pass
                else: self.x_pos += sp
            elif not t[RIGHT]:
                if not try_turn_vertical() and not try_turn_horizontal():
                    fallback()
            else:
                if prefer_vertical and try_turn_vertical(): pass
                else: self.x_pos += sp
        elif d == LEFT:
            if tx < self.x_pos and t[LEFT]:
                if prefer_vertical and try_turn_vertical(): pass
                else: self.x_pos -= sp
            elif not t[LEFT]:
                if not try_turn_vertical() and not try_turn_horizontal():
                    fallback()
            else:
                if prefer_vertical and try_turn_vertical(): pass
                else: self.x_pos -= sp
        elif d == UP:
            if ty < self.y_pos and t[UP]:
                if prefer_horizontal and try_turn_horizontal(): pass
                else: self.y_pos -= sp
            elif not t[UP]:
                if not try_turn_horizontal() and not try_turn_vertical():
                    fallback()
            else:
                if prefer_horizontal and try_turn_horizontal(): pass
                else: self.y_pos -= sp
        elif d == DOWN:
            if ty > self.y_pos and t[DOWN]:
                if prefer_horizontal and try_turn_horizontal(): pass
                else: self.y_pos += sp
            elif not t[DOWN]:
                if not try_turn_horizontal() and not try_turn_vertical():
                    fallback()
            else:
                if prefer_horizontal and try_turn_horizontal(): pass
                else: self.y_pos += sp

        if self.x_pos < -30:  self.x_pos = 900
        elif self.x_pos > 900: self.x_pos -= 30
        return self.x_pos, self.y_pos, self.direction

    def move_blinky(self): return self._greedy_move(prefer_vertical=False, prefer_horizontal=False)
    def move_inky(self):   return self._greedy_move(prefer_vertical=True, prefer_horizontal=False)
    def move_pinky(self):  return self._greedy_move(prefer_vertical=False, prefer_horizontal=True)
    def move_clyde(self):  return self._greedy_move(prefer_vertical=True, prefer_horizontal=True)


# ══════════════════════════════════════════════════════════════════════════════
#  GameState 
# ══════════════════════════════════════════════════════════════════════════════
class GameState:
    def __init__(self):
        pygame.init()
        
        # 1. Descobre o tamanho do seu monitor (tira 80px da barra de tarefas)
        info = pygame.display.Info()
        tela_maxima_y = info.current_h - 80 
        
        # 2. Define o fator de encolhimento automático
        fator = min(1.0, tela_maxima_y / HEIGHT)
        self.tela_w = int(WIDTH * fator)
        self.tela_h = int(HEIGHT * fator)
        
        # 3. Cria a janela real encolhida e a tela virtual
        self.real_screen = pygame.display.set_mode([self.tela_w, self.tela_h])
        self.screen = pygame.Surface([WIDTH, HEIGHT]) # O jogo é desenhado aqui
        pygame.display.set_caption("Pac-Man A*")
        
        self.timer  = pygame.time.Clock()
        
        self.font   = pygame.font.Font("freesansbold.ttf", 20)

        self.player_images = [
            pygame.transform.scale(
                pygame.image.load(ASSETS / f"player_images/{i}.png"), (45, 45)
            ) for i in range(1, 5)
        ]
        def _ghost_img(name):
            return pygame.transform.scale(
                pygame.image.load(ASSETS / f"ghost_images/{name}.png"), (45, 45)
            )
        self.blinky_img  = _ghost_img("red")
        self.pinky_img   = _ghost_img("pink")
        self.inky_img    = _ghost_img("blue")
        self.clyde_img   = _ghost_img("orange")
        self.spooked_img = _ghost_img("powerup")
        self.dead_img    = _ghost_img("dead")

        self._graph: dict = {}
        self._reset()

    def _reset(self):
        self.level           = [list(row) for row in BOARDS]
        # OTIMIZAÇÃO: Cache das comidas para não varrer a matriz inteira
        self.active_food     = set((i, j) for i, row in enumerate(self.level) for j, v in enumerate(row) if v == 1)
        self.active_capsules = set((i, j) for i, row in enumerate(self.level) for j, v in enumerate(row) if v == 2)
        
        self.player_x        = 450
        self.player_y        = 663
        self.direction       = RIGHT
        self.direction_cmd   = RIGHT
        self.turns_allowed   = [False, False, False, False]
        self.player_speed    = 2
        self.score           = 0
        self.lives           = 3
        self.powerup         = False
        self.power_counter   = 0
        self.eaten_ghost     = [False, False, False, False]
        self.blinky_x, self.blinky_y, self.blinky_dir = 56,  58,  RIGHT
        self.inky_x,   self.inky_y,   self.inky_dir   = 440, 388, UP
        self.pinky_x,  self.pinky_y,  self.pinky_dir  = 440, 438, UP
        self.clyde_x,  self.clyde_y,  self.clyde_dir  = 440, 438, UP
        self.blinky_dead = self.inky_dead = self.pinky_dead = self.clyde_dead = False
        self.blinky_box  = self.inky_box  = self.pinky_box  = self.clyde_box  = False
        self.targets      = [(self.player_x, self.player_y)] * 4
        self.ghost_speeds  = [2, 2, 2, 2]
        self.counter       = 0
        self.flicker       = False
        self.moving        = False
        self.startup_counter = 0
        self.game_over     = False
        self.game_won      = False

    def get_start_state(self) -> StateSnapshot:
        self._reset()
        snap = self._snapshot()
        self._graph.setdefault(snap, [])
        return snap

    @staticmethod
    def is_goal_state(state: StateSnapshot) -> bool:
        return len(state.active_food) == 0 and len(state.active_capsules) == 0

    def get_successors(self, state: StateSnapshot) -> list:
        if state.game_over or state.game_won:
            return []

        self._load_snapshot(state)
        successors = []
        cx = self.player_x + 23
        cy = self.player_y + 24
        allowed = self._check_position(cx, cy)

        action_names = {RIGHT: "RIGHT", LEFT: "LEFT", UP: "UP", DOWN: "DOWN"}

        for action in [RIGHT, LEFT, UP, DOWN]:
            if not allowed[action]:
                continue
            saved = self._mutable_vars()
            self.direction     = action
            self.turns_allowed = allowed
            self._advance_frame()
            next_snap = self._snapshot()
            self._graph.setdefault(state,     [])
            self._graph.setdefault(next_snap, [])
            edge = (action_names[action], next_snap)
            if edge not in self._graph[state]:
                self._graph[state].append(edge)
            successors.append(edge)
            self._restore_vars(saved)

        return successors

    def run(self):
        self._reset()
        running = True
        while running:
            self.timer.tick(FPS)
            self._update_counters()
            self.screen.fill("black")
            self._draw_board()

            cx = self.player_x + 23
            cy = self.player_y + 24
            self._update_ghost_speeds()
            self._check_win_condition()

            player_circle = pygame.draw.circle(self.screen, "black", (cx, cy), 20, 2)
            self._draw_player()

            blinky = self._make_ghost(0)
            inky   = self._make_ghost(1)
            pinky  = self._make_ghost(2)
            clyde  = self._make_ghost(3)
            ghosts = [blinky, inky, pinky, clyde]

            self._draw_misc()
            self.targets = self._get_targets(blinky, inky, pinky, clyde)
            self.turns_allowed = self._check_position(cx, cy)

            if self.moving:
                self._move_player()
                self._move_ghosts(blinky, inky, pinky, clyde)

            self.score, self.powerup, self.power_counter, self.eaten_ghost = \
                self._check_food_collisions(cx, cy)

            self._handle_ghost_collisions(player_circle, ghosts)
            snap = self._snapshot()
            self.get_successors(snap)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    self._handle_keydown(event.key)
                if event.type == pygame.KEYUP:
                    self._handle_keyup(event.key)

            for d in [RIGHT, LEFT, UP, DOWN]:
                if self.direction_cmd == d and self.turns_allowed[d]:
                    self.direction = d

            if   self.player_x > 900: self.player_x = -47
            elif self.player_x < -50: self.player_x = 897

            for ghost, attr in [(blinky, "blinky_dead"), (inky, "inky_dead"),
                                 (pinky,  "pinky_dead"),  (clyde, "clyde_dead")]:
                if ghost.in_box and getattr(self, attr):
                    setattr(self, attr, False)

            pygame.display.flip()
        pygame.quit()

    # ── Snapshot Otimizado ───────────────────────────────────────────────────
    def _snapshot(self) -> StateSnapshot:
        return StateSnapshot(
            player_pos        = (self.player_x, self.player_y),
            player_dir        = self.direction,
            ghost_positions   = (
                (self.blinky_x, self.blinky_y),
                (self.inky_x,   self.inky_y),
                (self.pinky_x,  self.pinky_y),
                (self.clyde_x,  self.clyde_y),
            ),
            ghost_directions  = (self.blinky_dir, self.inky_dir, self.pinky_dir,  self.clyde_dir),
            ghost_dead        = (self.blinky_dead, self.inky_dead, self.pinky_dead,  self.clyde_dead),
            ghost_in_box      = (self.blinky_box, self.inky_box, self.pinky_box,  self.clyde_box),
            active_food       = frozenset(self.active_food),     # Instantâneo
            active_capsules   = frozenset(self.active_capsules), # Instantâneo
            score             = self.score,
            powerup           = self.powerup,
            power_counter     = self.power_counter,
            eaten_ghost       = tuple(self.eaten_ghost),
            lives             = self.lives,
            game_over         = self.game_over,
            game_won          = self.game_won,
        )

    def _load_snapshot(self, s: StateSnapshot):
        self.level = [list(row) for row in BOARDS]
        for i in range(len(self.level)):
            for j in range(len(self.level[i])):
                if BOARDS[i][j] in (1, 2):
                    if (i, j) not in s.active_food and (i, j) not in s.active_capsules:
                        self.level[i][j] = 0

        self.active_food = set(s.active_food)
        self.active_capsules = set(s.active_capsules)
        
        self.player_x, self.player_y = s.player_pos
        self.direction     = s.player_dir
        (self.blinky_x, self.blinky_y), (self.inky_x,   self.inky_y), (self.pinky_x,  self.pinky_y), (self.clyde_x,  self.clyde_y) = s.ghost_positions
        self.blinky_dir, self.inky_dir, self.pinky_dir,  self.clyde_dir = s.ghost_directions
        self.blinky_dead, self.inky_dead, self.pinky_dead,  self.clyde_dead = s.ghost_dead
        self.blinky_box, self.inky_box, self.pinky_box,  self.clyde_box  = s.ghost_in_box
        self.score         = s.score
        self.powerup       = s.powerup
        self.power_counter = s.power_counter
        self.eaten_ghost   = list(s.eaten_ghost)
        self.lives         = s.lives
        self.game_over     = s.game_over
        self.game_won      = s.game_won
        self.targets       = [s.player_pos] * 4
        self.ghost_speeds  = [2, 2, 2, 2]
        self.moving        = True
        self.startup_counter = 180

    def _mutable_vars(self) -> dict:
        keys = [
            "level", "active_food", "active_capsules", "player_x", "player_y", "direction", "score",
            "lives", "powerup", "power_counter", "eaten_ghost",
            "blinky_x", "blinky_y", "blinky_dir", "blinky_dead", "blinky_box",
            "inky_x",   "inky_y",   "inky_dir",   "inky_dead",   "inky_box",
            "pinky_x",  "pinky_y",  "pinky_dir",  "pinky_dead",  "pinky_box",
            "clyde_x",  "clyde_y",  "clyde_dir",  "clyde_dead",  "clyde_box",
            "targets", "ghost_speeds", "game_over", "game_won",
        ]
        saved = {}
        for k in keys:
            v = getattr(self, k)
            if k == "level":
                saved[k] = [list(row) for row in v] # MUITO mais rápido que deepcopy
            elif k in ("active_food", "active_capsules"):
                saved[k] = set(v)
            elif isinstance(v, list):
                saved[k] = list(v) # Cópia rasa
            else:
                saved[k] = v
        return saved

    def _restore_vars(self, saved: dict):
        for k, v in saved.items():
            setattr(self, k, v)

    def _advance_frame(self):
        cx = self.player_x + 23
        cy = self.player_y + 24
        self.turns_allowed = self._check_position(cx, cy)
        self._move_player()
        cx = self.player_x + 23
        cy = self.player_y + 24
        self.score, self.powerup, self.power_counter, self.eaten_ghost = self._check_food_collisions(cx, cy)

    def _make_ghost(self, gid: int) -> Ghost:
        xs    = [self.blinky_x, self.inky_x,   self.pinky_x,  self.clyde_x]
        ys    = [self.blinky_y, self.inky_y,    self.pinky_y,  self.clyde_y]
        dirs  = [self.blinky_dir, self.inky_dir, self.pinky_dir, self.clyde_dir]
        deads = [self.blinky_dead, self.inky_dead, self.pinky_dead, self.clyde_dead]
        boxes = [self.blinky_box,  self.inky_box,  self.pinky_box,  self.clyde_box]
        imgs  = [self.blinky_img, self.inky_img, self.pinky_img, self.clyde_img]
        return Ghost(
            xs[gid], ys[gid], self.targets[gid], self.ghost_speeds[gid],
            imgs[gid], dirs[gid], deads[gid], boxes[gid], gid,
            self.level, self.powerup, self.eaten_ghost,
            self.spooked_img, self.dead_img, self.screen,
        )

    def _move_ghosts(self, blinky, inky, pinky, clyde):
        def _apply(ghost, name, x_attr, y_attr, d_attr, dead_attr):
            if not getattr(self, dead_attr) and not ghost.in_box:
                nx, ny, nd = getattr(ghost, f"move_{name}")()
            else:
                nx, ny, nd = ghost.move_clyde()
            setattr(self, x_attr, nx)
            setattr(self, y_attr, ny)
            setattr(self, d_attr, nd)

        _apply(blinky, "blinky", "blinky_x", "blinky_y", "blinky_dir", "blinky_dead")
        _apply(pinky,  "pinky",  "pinky_x",  "pinky_y",  "pinky_dir",  "pinky_dead")
        _apply(inky,   "inky",   "inky_x",   "inky_y",   "inky_dir",   "inky_dead")
        cx, cy, cd = clyde.move_clyde()
        self.clyde_x, self.clyde_y, self.clyde_dir = cx, cy, cd

    def _handle_ghost_collisions(self, player_circle, ghosts):
        blinky, inky, pinky, clyde = ghosts
        ghost_list = [(blinky, "blinky_dead", 0), (inky, "inky_dead", 1), (pinky, "pinky_dead", 2), (clyde, "clyde_dead", 3)]

        if not self.powerup:
            if any(player_circle.colliderect(g.rect) and not g.dead for g, _, _ in ghost_list):
                self._lose_life()
            return

        for ghost, dead_attr, gid in ghost_list:
            if not player_circle.colliderect(ghost.rect) or ghost.dead:
                continue
            if self.eaten_ghost[gid]:
                self._lose_life()
            else:
                setattr(self, dead_attr, True)
                self.eaten_ghost[gid] = True
                self.score += (2 ** self.eaten_ghost.count(True)) * 100

    def _lose_life(self):
        if self.lives > 0:
            self.lives -= 1
            self._reset_positions()
        else:
            self.game_over = True
            self.moving    = False

    def _reset_positions(self):
        self.powerup = False;  self.power_counter = 0
        self.startup_counter = 0
        self.player_x, self.player_y = 450, 663
        self.direction = self.direction_cmd = RIGHT
        self.blinky_x, self.blinky_y, self.blinky_dir = 56,  58,  RIGHT
        self.inky_x,   self.inky_y,   self.inky_dir   = 440, 388, UP
        self.pinky_x,  self.pinky_y,  self.pinky_dir  = 440, 438, UP
        self.clyde_x,  self.clyde_y,  self.clyde_dir  = 440, 438, UP
        self.eaten_ghost = [False, False, False, False]
        self.blinky_dead = self.inky_dead = self.pinky_dead = self.clyde_dead = False

    def _check_food_collisions(self, cx, cy):
        num1 = (HEIGHT - 50) // 32
        num2 = WIDTH // 30
        scor, power, pcnt, eaten = self.score, self.powerup, self.power_counter, self.eaten_ghost
        if 0 < self.player_x < 870:
            row, col = cy // num1, cx // num2
            cell = self.level[row][col]
            if cell == 1:
                self.level[row][col] = 0
                self.active_food.discard((row, col)) # Remove do cache em O(1)
                scor += 10
            elif cell == 2:
                self.level[row][col] = 0
                self.active_capsules.discard((row, col)) # Remove do cache
                scor += 50
                power = True
                pcnt  = 0
                eaten = [False, False, False, False]
        return scor, power, pcnt, eaten

    def _move_player(self):
        d, t, sp = self.direction, self.turns_allowed, self.player_speed
        if   d == RIGHT and t[RIGHT]: self.player_x += sp
        elif d == LEFT  and t[LEFT]:  self.player_x -= sp
        elif d == UP    and t[UP]:    self.player_y -= sp
        elif d == DOWN  and t[DOWN]:  self.player_y += sp

    def _check_position(self, cx, cy) -> list:
        turns = [False, False, False, False]
        num1  = (HEIGHT - 50) // 32
        num2  = WIDTH // 30
        num3  = 15
        if cx // 30 < 29:
            d = self.direction
            checks = {
                RIGHT: (cy // num1, (cx + num3) // num2),
                LEFT:  (cy // num1, (cx - num3) // num2),
                UP:    ((cy - num3) // num1, cx // num2),
                DOWN:  ((cy + num3) // num1, cx // num2),
            }
            if d in (UP, DOWN):
                for row, col, t in [((cy + num3) // num1, cx // num2, DOWN), ((cy - num3) // num1, cx // num2, UP)]:
                    if 12 <= cx % num2 <= 18 and self.level[row][col] < 3: turns[t] = True
                for row, col, t in [(cy // num1, (cx - num2) // num2, LEFT), (cy // num1, (cx + num2) // num2, RIGHT)]:
                    if 12 <= cy % num1 <= 18 and self.level[row][col] < 3: turns[t] = True
            if d in (RIGHT, LEFT):
                for row, col, t in [((cy + num1) // num1, cx // num2, DOWN), ((cy - num1) // num1, cx // num2, UP)]:
                    if 12 <= cx % num2 <= 18 and self.level[row][col] < 3: turns[t] = True
                for row, col, t in [(cy // num1, (cx - num3) // num2, LEFT), (cy // num1, (cx + num3) // num2, RIGHT)]:
                    if 12 <= cy % num1 <= 18 and self.level[row][col] < 3: turns[t] = True
            for t, (r, c) in checks.items():
                if self.level[r][c] < 3: turns[t] = True
        else:
            turns[RIGHT] = turns[LEFT] = True
        return turns

    def _get_targets(self, blinky, inky, pinky, clyde) -> list:
        px, py = self.player_x, self.player_y
        run_x  = 900 if px < 450 else 0
        run_y  = 900 if py < 450 else 0
        home   = (380, 400)

        def target_for(ghost, gid, chase_target):
            if ghost.dead: return home
            if self.powerup and not self.eaten_ghost[gid]: return (run_x, run_y)
            if self.powerup and self.eaten_ghost[gid]:
                if 340 < ghost.x_pos < 560 and 340 < ghost.y_pos < 500: return (400, 100)
                return (px, py)
            if 340 < ghost.x_pos < 560 and 340 < ghost.y_pos < 500: return (400, 100)
            return chase_target

        return [target_for(blinky, 0, (px, py)), target_for(inky, 1, (px, py)), target_for(pinky, 2, (px, py)), target_for(clyde, 3, (px + 50, py))]

    def _update_counters(self):
        if self.counter < 19:
            self.counter += 1
            if self.counter > 3: self.flicker = False
        else:
            self.counter = 0;  self.flicker = True

        if self.powerup and self.power_counter < 600: self.power_counter += 1
        elif self.powerup and self.power_counter >= 600:
            self.power_counter = 0;  self.powerup = False
            self.eaten_ghost = [False, False, False, False]

        if self.startup_counter < 180 and not self.game_over and not self.game_won:
            self.moving = False;  self.startup_counter += 1
        else:
            self.moving = True

    def _update_ghost_speeds(self):
        self.ghost_speeds = [1 if self.powerup else 2] * 4
        for i, eaten in enumerate(self.eaten_ghost):
            if eaten: self.ghost_speeds[i] = 2
        for i, attr in enumerate(["blinky_dead","inky_dead","pinky_dead","clyde_dead"]):
            if getattr(self, attr): self.ghost_speeds[i] = 4

    def _check_win_condition(self):
        self.game_won = all(1 not in row and 2 not in row for row in self.level)

    def _draw_board(self):
        num1 = (HEIGHT - 50) // 32
        num2 = WIDTH // 30
        for i, row in enumerate(self.level):
            for j, cell in enumerate(row):
                cx = j * num2 + 0.5 * num2
                cy = i * num1 + 0.5 * num1
                if cell == 1: pygame.draw.circle(self.screen, "white", (cx, cy), 4)
                if cell == 2 and not self.flicker: pygame.draw.circle(self.screen, "white", (cx, cy), 10)
                if cell == 3: pygame.draw.line(self.screen, "blue", (cx, i*num1), (cx, i*num1+num1), 3)
                if cell == 4: pygame.draw.line(self.screen, "blue", (j*num2, cy), (j*num2+num2, cy), 3)
                arcs = {
                    5: ([(j*num2-(num2*0.4))-2, i*num1+(0.5*num1), num2, num1], 0,       PI/2),
                    6: ([(j*num2+(num2*0.5)),    i*num1+(0.5*num1), num2, num1], PI/2,    PI),
                    7: ([(j*num2+(num2*0.5)),    i*num1-(0.4*num1), num2, num1], PI,      3*PI/2),
                    8: ([(j*num2-(num2*0.4))-2,  i*num1-(0.4*num1), num2, num1], 3*PI/2, 2*PI),
                }
                if cell in arcs:
                    rect, start, stop = arcs[cell]
                    pygame.draw.arc(self.screen, "blue", rect, start, stop, 3)
                if cell == 9: pygame.draw.line(self.screen, "white", (j*num2, cy), (j*num2+num2, cy), 3)

    def _draw_player(self):
        img = self.player_images[self.counter // 5]
        if   self.direction == RIGHT: self.screen.blit(img, (self.player_x, self.player_y))
        elif self.direction == LEFT:  self.screen.blit(pygame.transform.flip(img,True,False), (self.player_x, self.player_y))
        elif self.direction == UP:    self.screen.blit(pygame.transform.rotate(img, 90),  (self.player_x, self.player_y))
        elif self.direction == DOWN:  self.screen.blit(pygame.transform.rotate(img, 270), (self.player_x, self.player_y))

    def _draw_misc(self):
        self.screen.blit(self.font.render(f"Score: {self.score}", True, "white"), (10, 920))
        if self.powerup: pygame.draw.circle(self.screen, "blue", (140, 930), 15)
        for i in range(self.lives):
            self.screen.blit(pygame.transform.scale(self.player_images[0], (30, 30)), (650 + i * 40, 915))
        for condition, color, text in [(self.game_over, "red", "Game over! Space bar to restart!"), (self.game_won,  "green", "Victory! Space bar to restart!")]:
            if condition:
                pygame.draw.rect(self.screen, "white",    [50, 200, 800, 300], 0, 10)
                pygame.draw.rect(self.screen, "dark gray",[70, 220, 760, 260], 0, 10)
                self.screen.blit(self.font.render(text, True, color), (100, 300))

    def _handle_keydown(self, key):
        mapping = {pygame.K_RIGHT: RIGHT, pygame.K_LEFT: LEFT, pygame.K_UP: UP, pygame.K_DOWN: DOWN}
        if key in mapping: self.direction_cmd = mapping[key]
        if key == pygame.K_SPACE and (self.game_over or self.game_won):
            self._reset()
            self._graph.clear()

    def _handle_keyup(self, key):
        mapping = {pygame.K_RIGHT: RIGHT, pygame.K_LEFT: LEFT, pygame.K_UP: UP, pygame.K_DOWN: DOWN}
        if key in mapping and self.direction_cmd == mapping[key]:
            self.direction_cmd = self.direction
