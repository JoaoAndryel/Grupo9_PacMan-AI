"""
A* Pac-Man Agent
================
Uses the GameState / StateSnapshot interface from pacman_gamestate.py to plan
Pac-Man's moves with A* search and a Manhattan-distance heuristic.

How it works
------------
- The **search space** is the directed graph of StateSnapshots built by
  GameState.get_successors().
- The **cost** g(n) counts the number of moves taken so far (each edge = 1).
- The **heuristic** h(n) estimates remaining work as the sum of Manhattan
  distances from Pac-Man's current grid cell to every remaining food dot,
  weighted and adjusted for ghost proximity (see ManhattanHeuristic below).
- A* expands the node with the lowest f(n) = g(n) + h(n) first.
- After finding the optimal first action, the agent executes it, then
  **re-plans from the resulting state** (receding-horizon / online A*).
  This keeps individual searches fast and naturally adapts to ghosts moving.

Run this file directly to watch A* play:
    python astar_pacman.py
"""

import sys
import os
import pygame

# Importa as direções e o motor do jogo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pacman_gamestate import GameState, RIGHT, LEFT, UP, DOWN

# Importa as classes OBRIGATÓRIAS do aima-python
try:
    from search import Problem, astar_search
except ImportError:
    print("Erro: O repositório aima-python (search.py) não foi encontrado.")
    sys.exit(1)

WIDTH, HEIGHT = 900, 950
NUM1 = (HEIGHT - 50) // 32   # Altura da célula na tela
NUM2 = WIDTH // 30           # Largura da célula na tela

def pixel_to_grid(px: float, py: float):
    """Converte a posição física (pixels) para (Linha, Coluna) na matriz."""
    return int((py + 24) // NUM1), int((px + 23) // NUM2)

# ======================================================================
#  ESPECIFICAÇÃO FORMAL DO PROBLEMA (Mapeamento em Grid)
# ======================================================================
class PacmanGridProblem(Problem):
    """
    Subclasse de Problem do AIMA. 
    Aqui o A* enxerga o mapa como uma matriz 33x30, ignorando os pixels.
    """
    def __init__(self, initial, goal, board, ghosts):
        super().__init__(initial, goal)
        self.board = board
        self.ghosts = ghosts # Lista de posições (linha, coluna) dos fantasmas
        
    def actions(self, state):
        r, c = state
        possible = []
        
        # Função auxiliar para checar se a próxima célula é andável e segura
        def is_safe_and_walkable(nr, nc):
            if nr < 0 or nr >= 33 or nc < 0 or nc >= 30: 
                return False
            # Verifica se é parede (valores >= 3 no board são paredes)
            if self.board[nr][nc] >= 3 and self.board[nr][nc] != 9:
                return False
            # Verifica se tem fantasma muito perto daquela célula
            for gr, gc in self.ghosts:
                if abs(nr - gr) + abs(nc - gc) <= 2: # Raio de perigo
                    return False
            return True

        # Testa as 4 direções (Cima, Baixo, Esquerda, Direita)
        if is_safe_and_walkable(r-1, c): possible.append(UP)
        if is_safe_and_walkable(r+1, c): possible.append(DOWN)
        if is_safe_and_walkable(r, c-1): possible.append(LEFT)
        if is_safe_and_walkable(r, c+1): possible.append(RIGHT)
        
        # Regra do Túnel nas bordas do mapa
        if c == 0 and is_safe_and_walkable(r, 29): possible.append(LEFT)
        if c == 29 and is_safe_and_walkable(r, 0): possible.append(RIGHT)
        
        return possible

    def result(self, state, action):
        r, c = state
        if action == UP: return (r-1, c)
        if action == DOWN: return (r+1, c)
        if action == LEFT: return (r, 29) if c == 0 else (r, c-1)
        if action == RIGHT: return (r, 0) if c == 29 else (r, c+1)
        return state

    def path_cost(self, c, state1, action, state2):
        return c + 1
        
    def h(self, node):
        # Heurística: Distância de Manhattan no Grid
        r1, c1 = node.state
        r2, c2 = self.goal
        # Lida com a distância através do túnel
        dc = min(abs(c1 - c2), 30 - abs(c1 - c2))
        return abs(r1 - r2) + dc

# ======================================================================
#  AGENTE A* ONLINE
# ======================================================================
class GridAStarAgent:
    def __init__(self, game: GameState):
        self.game = game

    def get_action(self):
        # 1. Percebe sua própria posição no grid
        p_row, p_col = pixel_to_grid(self.game.player_x, self.game.player_y)
        
        # 2. Percebe todas as comidas restantes no grid
        foods = []
        for i in range(33):
            for j in range(30):
                if self.game.level[i][j] in (1, 2):
                    foods.append((i, j))
                    
        if not foods: 
            return None # Venceu
        
        # 3. Percebe os fantasmas ativos para desviar
        ghosts = []
        if not self.game.powerup:
            for gx, gy, dead in [
                (self.game.blinky_x, self.game.blinky_y, self.game.blinky_dead),
                (self.game.inky_x, self.game.inky_y, self.game.inky_dead),
                (self.game.pinky_x, self.game.pinky_y, self.game.pinky_dead),
                (self.game.clyde_x, self.game.clyde_y, self.game.clyde_dead)
            ]:
                if not dead:
                    ghosts.append(pixel_to_grid(gx, gy))
                
        # 4. Define o objetivo: A comida mais próxima
        target = min(foods, key=lambda f: abs(p_row - f[0]) + abs(p_col - f[1]))
        
        # 5. Formula o problema para as classes do AIMA
        problem = PacmanGridProblem((p_row, p_col), target, self.game.level, ghosts)
        
        # 6. Executa a Busca A*
        node = astar_search(problem, problem.h)
        
        # 7. Retorna a ação
        if node and len(node.solution()) > 0:
            return node.solution()[0]
        else:
            # Failsafe: Se estiver encurralado pelos fantasmas, pega a primeira saída válida do motor
            for d in [RIGHT, LEFT, UP, DOWN]:
                if self.game.turns_allowed[d]:
                    return d
            return self.game.direction

# ======================================================================
#  LOOP DO JOGO
# ======================================================================
class AStarGameLoop:
    def __init__(self):
        self.game  = GameState()
        self.agent = GridAStarAgent(self.game)

    def run(self):
        game = self.game
        game._reset()
        running = True
        
        while running:
            game.timer.tick(60) # Roda super fluido agora a 60 FPS
            game._update_counters()
            game.screen.fill("black")
            game._draw_board()

            cx = game.player_x + 23
            cy = game.player_y + 24
            game._update_ghost_speeds()
            game._check_win_condition()

            player_circle = pygame.draw.circle(game.screen, "black", (cx, cy), 20, 2)
            game._draw_player()

            blinky, inky, pinky, clyde = game._make_ghost(0), game._make_ghost(1), game._make_ghost(2), game._make_ghost(3)
            ghosts = [blinky, inky, pinky, clyde]

            game._draw_misc()
            game.targets = game._get_targets(blinky, inky, pinky, clyde)
            game.turns_allowed = game._check_position(cx, cy)

            # --- A INTELIGÊNCIA ARTIFICIAL ENTRA AQUI ---
            if game.moving and not game.game_over and not game.game_won:
                # O agente pensa a cada frame de forma ultra-rápida!
                action = self.agent.get_action()
                if action is not None: 
                    game.direction_cmd = action

            # Aplica o comando de direção se a parede permitir
            for d in [RIGHT, LEFT, UP, DOWN]:
                if game.direction_cmd == d and game.turns_allowed[d]: 
                    game.direction = d

            # Move os personagens
            if game.moving:
                game._move_player()
                game._move_ghosts(blinky, inky, pinky, clyde)

            # Checa colisões
            game.score, game.powerup, game.power_counter, game.eaten_ghost = game._check_food_collisions(cx, cy)
            game._handle_ghost_collisions(player_circle, ghosts)

            # Túnel
            if game.player_x > 900: game.player_x = -47
            elif game.player_x < -50: game.player_x = 897

            for ghost, attr in [(blinky, "blinky_dead"), (inky, "inky_dead"), (pinky, "pinky_dead"), (clyde, "clyde_dead")]:
                if ghost.in_box and getattr(game, attr): setattr(game, attr, False)

            # Eventos de Fechar e Reiniciar
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and (game.game_over or game.game_won):
                        game._reset()
            
            
            # Encolhe a imagem do labirinto e joga na sua janela real
            tela_redimensionada = pygame.transform.smoothscale(game.screen, (game.tela_w, game.tela_h))
            game.real_screen.blit(tela_redimensionada, (0, 0))
            
            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    print("=" * 50)
    print(" Agente A* Pac-Man (Modo Grid AIMA)")
    print("=" * 50)
    loop = AStarGameLoop()
    loop.run()