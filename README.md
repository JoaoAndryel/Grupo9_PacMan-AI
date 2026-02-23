# 🕹️ Pac-Man Inteligente (Busca A*)

Este projeto implementa um agente autônomo para o jogo Pac-Man, utilizando o algoritmo de Busca **A*** (A-Star). A modelagem segue rigorosamente a arquitetura do livro *Inteligência Artificial: Uma Abordagem Moderna (AIMA)*, separando o ambiente, o problema matemático e o agente tomador de decisão.

---

## 📁 Estrutura de Arquivos do Projeto

O repositório contém os seguintes arquivos na pasta principal:

```text
/Grupo9_PacMan-AI
│
├── astar_pacman.py       # Loop principal do jogo que integra a IA (Agente) e o Ambiente
├── pacman_gamestate.py   # Lógica do motor gráfico, renderização e física (Pygame)
├── board.py              # Matriz (grid 33x30) do mapa do labirinto
├── search.py             # Algoritmos de busca base do repositório oficial AIMA (A*, etc.)
├── utils.py              # Utilitários auxiliares obrigatórios para o funcionamento do AIMA
├── test.py               # Suíte de testes automatizados (Pytest) para validação da modelagem
└── /assets/              # Pasta contendo as imagens e sprites do jogo
````
---

## ⚙️ Instalação e Execução

**Pré-requisitos:** Python 3.10+ e Git.

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/JoaoAndryel/Grupo9_PacMan-AI.git
  ```bash 
   cd Grupo9_PacMan-AI
  ````

2. **Instale as dependências:**

  ```bash
pip install pygame pytest
````
3. **Inicie a simulação:**

  ```bash
python main.py
(O agente jogará sozinho. Pressione ESPAÇO em caso de Game Over para reiniciar).
````

4. **Rode os Testes Automatizados:**

  ```Bash
pytest tests/test.py -v
````
---

## 📐 Especificação Formal do Problema

A tradução do ambiente gráfico para a matemática do algoritmo () foi feita na classe `PacmanGridProblem`:

* **Representação dos Estados:** Coordenadas discretas `(linha, coluna)` em uma matriz 33x30.
* **Estado Inicial:** A coordenada exata do Pac-Man no instante da decisão.
* **Conjunto de Ações (`actions`):** `UP`, `DOWN`, `LEFT`, `RIGHT`. Ações são invalidadas caso o destino seja uma parede ou esteja em um raio de 2 blocos de um fantasma.
* **Modelo de Transição (`result`):** Alteração da coordenada baseada na ação escolhida (incluindo a regra de teletransporte nos túneis laterais).
* **Teste de Objetivo (`goal_test`):** O alvo dinâmico é alcançar a coordenada da pastilha de comida mais próxima.
* **Custo de Caminho (`path_cost`):** Uniforme. Cada passo no grid custa 1 ponto.

---

