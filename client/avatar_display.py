# avatar_display.py

import pygame
import time
import queue
from PIL import Image, ImageSequence
from pygame import transform
from logger_config import get_logger

logger = get_logger(__name__)

class AssistantAvatarPygame:
    def __init__(self, static_img_path, gif_path, scale=1.0):
        pygame.init()
        self.scale = scale
        self.static_img = pygame.image.load(static_img_path)
        self.screen = pygame.display.set_mode(self._scaled_size(self.static_img))
        if (self.scale != 1.0):
            # กำหนดขนาดใหม่ (เช่น ลดขนาด 50%)
            original_size = self.static_img.get_size()
            scale_factor = 0.5  # หรือ 1.5, 2.0 แล้วแต่ต้องการ

            new_size = (int(original_size[0] * scale_factor), int(original_size[1] * scale_factor))

            # ปรับขนาด
            self.static_img = pygame.transform.smoothscale(self.static_img, new_size)

        
        pygame.display.set_caption("PingPing Avatar")

        self.gif_frames = self._load_gif_frames(gif_path)
        self.gif_index = 0
        self.running = True
        self.is_animating = False
        self.command_queue = queue.Queue()

    def _scaled_size(self, surface):
        if self.scale == 1.0:
            return surface.get_size()
        return (int(surface.get_width() * self.scale), int(surface.get_height() * self.scale))

    def _load_gif_frames(self, gif_path):
        gif = Image.open(gif_path)
        frames = []
        for frame in ImageSequence.Iterator(gif):
            surface = pygame.image.fromstring(frame.convert("RGB").tobytes(), frame.size, "RGB")
            surface = transform.scale(surface, self._scaled_size(surface)) if self.scale != 1.0 else surface
            frames.append(surface)
        return frames

    def run(self):
        clock = pygame.time.Clock()
        self._display_static()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            while not self.command_queue.empty():
                cmd = self.command_queue.get()
                if cmd == "animate":
                    self.is_animating = True
                elif cmd == "static":
                    self.is_animating = False
                    self._display_static()

            if self.is_animating:
                self._display_gif_frame()
            else:
                time.sleep(0.05)
            clock.tick(4)

        pygame.quit()

    def _display_static(self):
        self.screen.blit(self.static_img, (0, 0))
        pygame.display.flip()

    def _display_gif_frame(self):
        frame = self.gif_frames[self.gif_index]
        self.screen.blit(frame, (0, 0))
        pygame.display.flip()
        self.gif_index = (self.gif_index + 1) % len(self.gif_frames)

    def start_animation(self):
        self.command_queue.put("animate")

    def stop_animation(self):
        self.command_queue.put("static")
        