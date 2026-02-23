import pytest
from search import Node  # Classe oficial do AIMA
from astar_pacman import PacmanGridProblem
from pacman_gamestate import UP, DOWN, LEFT, RIGHT

# ======================================================================
# FIXTURES (Ambiente Simulado para os Testes)
# ======================================================================

@pytest.fixture
def mini_board():
    """
    Cria um labirinto 5x5 simplificado em formato de grid.
    0 = Caminho livre
    3 = Parede
    """
    return [
        [3, 3, 3, 3, 3],
        [3, 0, 0, 0, 3],
        [3, 0, 3, 0, 3],
        [3, 0, 0, 0, 3],
        [3, 3, 3, 3, 3]
    ]

@pytest.fixture
def problema_base(mini_board):
    """
    Instancia o problema formal do AIMA com estado inicial em (1,1)
    e objetivo em (3,3), sem nenhum fantasma no mapa.
    """
    return PacmanGridProblem(initial=(1, 1), goal=(3, 3), board=mini_board, ghosts=[])

# ======================================================================
# CASOS DE TESTE OBRIGATÓRIOS (Para apresentação)
# ======================================================================

def test_acoes_respeitam_paredes(problema_base):
    """
    Testa a função actions(s).
    Estando em (1,1), o Pac-Man está cercado por paredes em CIMA (0,1) e ESQUERDA (1,0).
    Ele só deve poder ir para DIREITA (1,2) e BAIXO (2,1).
    """
    acoes_possiveis = problema_base.actions((1, 1))
    
    assert RIGHT in acoes_possiveis
    assert DOWN in acoes_possiveis
    assert UP not in acoes_possiveis    # É parede (3)
    assert LEFT not in acoes_possiveis  # É parede (3)

def test_modelo_de_transicao(problema_base):
    """
    Testa a função result(s, a).
    Verifica se aplicar a ação DIREITA na coordenada (1,1)
    resulta corretamente na coordenada (1,2).
    """
    novo_estado = problema_base.result((1, 1), RIGHT)
    assert novo_estado == (1, 2)

    novo_estado_baixo = problema_base.result((1, 1), DOWN)
    assert novo_estado_baixo == (2, 1)

def test_heuristica_manhattan(problema_base):
    """
    Testa a função h(n).
    A distância de Manhattan (linha reta sem diagonais) entre
    a largada (1,1) e a chegada (3,3) deve ser exatamente 4 passos.
    (|1 - 3| + |1 - 3| = 2 + 2 = 4)
    """
    no_inicial = Node(state=(1, 1))
    valor_heuristica = problema_base.h(no_inicial)
    
    assert valor_heuristica == 4

def test_fuga_de_fantasmas(mini_board):
    """
    Testa a lógica de is_safe_and_walkable().
    Se houver um fantasma na casa (1,3), o caminho para a DIREITA 
    a partir de (1,1) deve ser bloqueado (considerado inseguro).
    """
    posicao_fantasma = (1, 3)
    problema_perigoso = PacmanGridProblem(
        initial=(1, 1), goal=(3, 3), board=mini_board, ghosts=[posicao_fantasma]
    )
    
    acoes_seguras = problema_perigoso.actions((1, 1))
    
    # O A* deve proibir a ida para a direita para não morrer
    assert RIGHT not in acoes_seguras 
    assert DOWN in acoes_seguras  # O caminho para baixo continua seguro