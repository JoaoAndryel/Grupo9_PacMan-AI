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
from env.pacman_gamestate import GameState, RIGHT, LEFT, UP, DOWN
from agents.astar_agent import GridAStarAgent

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
            game.timer.tick(60)
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

            if game.moving and not game.game_over and not game.game_won:
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