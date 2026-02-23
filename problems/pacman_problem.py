import sys
from env.pacman_gamestate import RIGHT, LEFT, UP, DOWN

try:
    from search import Problem
except ImportError:
    print("Erro: O repositório aima-python (search.py) não foi encontrado.")
    sys.exit(1)

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
