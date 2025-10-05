import os
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import main


def stop_later(delay: float = 1.0) -> None:
    time.sleep(delay)
    pygame.event.post(pygame.event.Event(pygame.QUIT))


def run_smoke(delay: float = 1.0) -> None:
    thread = threading.Thread(target=stop_later, args=(delay,), daemon=True)
    thread.start()
    main.main()


if __name__ == "__main__":
    run_smoke()
