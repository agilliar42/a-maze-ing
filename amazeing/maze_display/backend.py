from abc import ABC, abstractmethod


class PixelCoord:
    def __init__(self, x: int, y: int) -> None:
        self.x: int = x
        self.y: int = y


class Backend(ABC):
    """
    ABC for the maze display.
    defining how the maze should be drawn.
    (PixelCoord)
    """
    @abstractmethod
    def draw_pixel(self, pos: PixelCoord) -> None:
        pass
