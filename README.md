# Poker Power-Up

Texas Hold'em No-Limit para computador, feito em Python 3 com PyGame, com um
toque a mais: **power-ups** sorteados numa roleta a cada 3 mãos.

## Membros do grupo

- Benício Huck (BenicioH)
- Pedro Henerique Pesce (Pedro5902)
- Heitor Visoso (Heitogv)

## Vídeo de apresentação

https://www.youtube.com/watch?v=FOlTEvk2nuA

## Como rodar o jogo

Precisa de Python 3.9 ou mais novo.

```bash
# 1. (opcional) criar um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. instalar as dependências
pip install -r requirements.txt

# 3. rodar
python main.py
```

A dependência é o **pygame-ce**, a versão mantida pela comunidade do PyGame. Ela usa
o mesmo `import pygame` e já tem instalador para o Python 3.14 (o `pygame` original
ainda não tem). Em Python 3.13 ou anterior, `pip install pygame` também funciona.
Não instale os dois ao mesmo tempo.

O arquivo a ser executado é o **`main.py`**. O progresso (saldo, nome, power-ups
guardados) fica em `data/save.json`.

### Pelo VS Code

1. Abra a pasta do projeto (**Arquivo > Abrir Pasta...**) e instale a extensão **Python**
   quando o VS Code sugerir.
2. Aperte **Ctrl+Shift+P** (no Mac, **Cmd+Shift+P**), procure **Python: Create Environment**,
   escolha **Venv** e marque o `requirements.txt`. O VS Code cria o `.venv` e instala o
   pygame-ce sozinho.
3. Na aba **Executar e Depurar** (ou **F5**), escolha **Jogar Poker Power-Up**. A opção
   **Rodar os testes** roda os testes automáticos.

## Descrição

O jogador começa com 2.000 fichas de saldo e escolhe, no lobby, uma de três salas:

| Sala          | Blinds | Buy-in do cash | Buy-in do torneio |
|---------------|--------|----------------|-------------------|
| Low Stakes    | 1/2    | 40 a 200       | 50                |
| Medium Stakes | 5/10   | 200 a 1.000    | 250               |
| High Stakes   | 25/50  | 1.000 a 5.000  | 1.000             |

Em cada sala há mesas com bots **Fácil**, **Médio** e **Difícil**, em dois modos:

- **Cash Game**: você leva fichas do saldo para a mesa e sai quando quiser. Bots que
  quebram são trocados por bots novos. Se você quebrar, pode recomprar.
- **Torneio (Sit & Go)**: 6 jogadores com 1.500 fichas, os blinds sobem a cada 8 mãos e
  quem perde tudo é eliminado. 1º lugar leva 65% do prêmio e 2º lugar 35%.

### Power-ups

A cada 3 mãos jogadas abre a **roleta de power-ups**. Cada power-up tem uma
fatia proporcional à sua raridade. Antes de girar, o jogador pode **pagar fichas da
mesa para tirar power-ups da roleta**, aumentando a chance dos que sobraram. O preço
cresce com a chance do power-up: `(5 + 0,6 × chance em %) big blinds`, ou seja, uns 21 BB
para tirar um comum e 6 BB para tirar o lendário. Cada remoção deixa as próximas 50% mais caras. Cada power-up é usado uma única vez e vale
para a mão em que foi usado. Dá para guardar até 4.

| Power-up        | Raridade (chance) | Efeito |
|-----------------|-------------------|--------|
| Trevo da Sorte  | Comum (27%)       | +20% de sorte: cada carta da mesa tem 20% de chance de ser escolhida como a melhor entre 4 para você |
| Próxima Carta   | Comum (27%)       | Mostra a próxima carta da mesa (não funciona no river) |
| Troca           | Incomum (14%)     | Troca uma das suas cartas por outra do baralho (até o turn) |
| Raio-X de Outs  | Incomum (14%)     | Lista as cartas que melhoram a sua mão e a chance de vir uma delas |
| Leitura         | Raro (7%)         | Revela uma carta de um adversário escolhido |
| Escudo          | Raro (7%)         | Se perder no showdown, recebe de volta metade do que apostou |
| Oráculo         | Lendário (3%)     | Mostra a sua chance real de ganhar e a de cada adversário, sem mostrar as cartas deles |

### Mini games e modalidades

A cada **2 mãos** todos os jogadores da mesa disputam um **mini game**. Os três se
revezam:

| Mini game | Como jogar | Quem vence |
|-----------|------------|------------|
| Escalada  | Apertar ESPAÇO o mais rápido possível; cada toque sobe um andar do prédio | Quem chega primeiro ao topo (60 andares) |
| Corrida   | Alternar as setas ESQUERDA e DIREITA; seta para CIMA pula as 3 barreiras (bater deixa tonto por 1 s) | Quem cruza a chegada primeiro |
| Quiz      | 3 perguntas de conhecimentos gerais, 10 s cada, respostas com 1-4 ou clique | Mais pontos: acerto = 100 + até 100 pela rapidez |

Quem vence **escolhe a modalidade** das mãos seguintes (até o próximo mini game):

| Modalidade    | Cartas | Regra |
|---------------|--------|-------|
| Texas Hold'em | 2      | Melhor mão com quaisquer 5 das 7 cartas |
| Omaha 4/5/6   | 4/5/6  | A mão usa **exatamente 2** cartas suas + **3** da mesa |
| Pineapple     | 3      | Depois das apostas do pré-flop, cada um descarta 1 carta; o resto é Hold'em |

Os bots também disputam: o desempenho deles (velocidade, erros nas barreiras, acertos no
quiz) é sorteado conforme a dificuldade. Um bot que vence escolhe uma modalidade ao acaso.

### Telas

Menu inicial, Como jogar (6 páginas), Configurações (nome, música, efeitos, apagar
progresso), Lobby (salas, cash e torneios), Mesa, Roleta, Pausa e
Resultado (lucro, mãos jogadas, maior pote, colocação no torneio).

### Controles

| Tecla             | Ação |
|-------------------|------|
| F                 | Desistir |
| C                 | Passar / pagar |
| R                 | Apostar / aumentar o valor escolhido |
| Setas / rodinha   | Mudar o valor da aposta |
| 1 a 4             | Usar o power-up daquele espaço |
| Espaço            | Próxima mão |
| Esc               | Pausa (ou cancela a escolha de alvo de um power-up) |
| F11               | Tela cheia |
| Espaço            | Escalada: subir um andar |
| Setas             | Corrida: esquerda/direita alternadas correm, cima pula |
| 1 a 4 / clique    | Quiz: responder |
| Clique na carta   | Pineapple: descartar |

## Estrutura do código

```
main.py                 ponto de entrada
poker/
  app.py                janela, laço principal e pilha de cenas
  config.py             tamanho da tela, cores e caminhos
  storage.py            jogo salvo (data/save.json)
  engine/               regras do jogo, sem nenhuma dependência de pygame
    cards.py            Card e Deck (com "espiar" e "travar" a próxima carta)
    evaluator.py        avaliação da melhor mão de 5 a 7 cartas
    equity.py           chances de vitória (exata ou Monte Carlo) e outs
    player.py           estado de um jogador
    hand.py             uma mão: blinds, apostas, potes laterais e showdown
    bots.py             estratégias Fácil, Médio e Difícil
    powerups.py         os 7 power-ups e a roleta
    variants.py         modalidades: Hold'em, Omaha 4/5/6 e Pineapple
    minigames.py        regras dos mini games (escalada, corrida, quiz) e as perguntas
    session.py          cash game e torneio (várias mãos seguidas)
  ui/                   desenho e som
    draw.py             textos, painéis, cartas e fichas desenhados com formas
    widgets.py          botão, controle deslizante, campo de texto, avisos
    effects.py          voos de cartas/fichas, textos flutuantes, confete
    table_view.py       desenho da mesa e animação dos eventos da mão
    sound.py            efeitos e música gerados por síntese
  scenes/               telas
    base.py             Scene, Modal, ConfirmDialog e o fundo animado
    menu.py, lobby.py, table.py, roulette.py, pause.py,
    results.py, tutorial.py, settings.py
    minigame.py         tela dos mini games e da escolha da modalidade
tests/test_engine.py    testes das regras (python -m unittest discover tests)
tests/test_variety.py   testes das modalidades e dos mini games
tools/autoplay.py       roda o jogo sem janela, joga sozinho e salva capturas em shots/
```

### Como as partes conversam

1. A **`Hand`** (`engine/hand.py`) é uma máquina de estados: `start()` posta os blinds e
   distribui as cartas, `act(tipo, valor)` aplica a decisão de quem está na vez e
   `advance()` abre a próxima carta quando a rodada de apostas acaba. Cada chamada
   devolve uma lista de **eventos** (`blind`, `deal`, `action`, `board`, `win`...).
2. A **`TableView`** (`ui/table_view.py`) recebe esses eventos numa fila e anima um por
   um (cartas voando, fichas indo para o pote). Enquanto ela está ocupada, ninguém age.
3. A **`TableScene`** (`scenes/table.py`) decide quem joga: quando é a vez de um bot,
   chama `bot.decide()`; quando é a vez do jogador, mostra os botões.
4. A **`Session`** (`engine/session.py`) liga uma mão na outra: move o botão do dealer,
   sobe os blinds do torneio, repõe bots no cash e conta as mãos até a roleta.

### Decisões importantes

- **Avaliador de mãos**: conta valores e naipes das 7 cartas de uma vez, em vez de testar
  as 21 combinações de 5 cartas. Devolve uma tupla comparável `(categoria, desempates...)`.
- **Potes laterais**: cada nível de all-in de quem ainda está na mão fecha um pote; só
  pode ganhar um pote quem colocou fichas até aquele nível (`Hand.build_pots`).
- **Bots**: estimam a chance de vitória contra mãos aleatórias (Monte Carlo) e comparam
  com as pot odds. A dificuldade muda a precisão, o ruído, a agressividade, os blefes e
  o quanto o bot "respeita" apostas grandes e com que frequência paga apostas pequenas sem
  odds. Os parâmetros foram ajustados em simulações de bots novos contra os antigos na
  mesma mesa (3 contra 3, milhares de mãos).
- **Próxima Carta + Trevo da Sorte**: a carta espiada fica travada no baralho, então a
  sorte nunca troca uma carta que o jogador já viu.
- **Sons**: todos gerados por código (`ui/sound.py`), sem arquivos de áudio de terceiros.

## Testes

```bash
python -m unittest discover tests     # 30 testes: regras, modalidades e mini games
python tools/autoplay.py 12           # joga 12 mãos de cash e um torneio inteiro sem janela
```

## Rascunhos e organização do grupo

(Coloquem aqui fotos dos rascunhos de tela, a divisão de tarefas e as decisões tomadas
nas reuniões.)

## Créditos

- Biblioteca [pygame-ce](https://pyga.me/).
- Nenhum trecho de código foi copiado de terceiros. Cartas, fichas e naipes são
  desenhados com formas do pygame e os sons são sintetizados pelo próprio jogo.
- Uso de IA: Assistencia de plataformas de IA como Claude sendo direcionada pelos autores do grupo.
