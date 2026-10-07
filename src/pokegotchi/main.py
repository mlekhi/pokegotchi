"""Run the touchscreen game."""

from pathlib import Path

import pygame

from .app import PokegotchiApp
from .save_store import save_game


def main() -> None:
    pygame.init()
    save_path = Path.home() / ".local/share/pokegotchi/save.json"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    surface = pygame.display.set_mode((800, 480), pygame.FULLSCREEN)
    app = PokegotchiApp(surface, save_path)
    clock = pygame.time.Clock()

    try:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                if event.type == pygame.MOUSEBUTTONUP:
                    app.handle_tap(event.pos)
                    if app.state is not None:
                        save_game(save_path, app.state)

            if running:
                app.draw()
                pygame.display.flip()
                clock.tick(30)
    finally:
        if app.state is not None:
            save_game(save_path, app.state)
        pygame.quit()


if __name__ == "__main__":
    main()
