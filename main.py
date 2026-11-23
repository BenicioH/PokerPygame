"""Ponto de entrada do jogo. Execute com: python main.py"""

from poker.app import App
from poker.scenes.menu import MenuScene


def main():
    """Cria a janela e abre o menu principal."""
    app = App()
    app.run(MenuScene(app))


if __name__ == "__main__":
    main()
