import pygame
import pytest


@pytest.fixture
def pygame_surface():
    pygame.init()
    surface = pygame.display.set_mode((800, 480))
    yield surface
    pygame.quit()
