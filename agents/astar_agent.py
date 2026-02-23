import sys
import os
from env.pacman_gamestate import GameState, RIGHT, LEFT, UP, DOWN
from problems.pacman_problem import PacmanGridProblem

# Importa as direções e o motor do jogo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from search import astar_search
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