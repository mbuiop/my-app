#!/usr/bin/env python3
"""
🚀 Galactic Cinematic Game - بازی کهکشانی سینمایی
نسخه قابل نصب با GitHub Actions
"""

import pygame
import sys
import os
import math
import random
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

class CinematicGraphics:
    def __init__(self, width=1200, height=800):
        self.WIDTH = width
        self.HEIGHT = height
        
    def setup_opengl(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (self.WIDTH / self.HEIGHT), 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        
    def create_starfield(self, count=2000):
        stars = []
        for _ in range(count):
            stars.append({
                'position': [random.uniform(-50, 50), random.uniform(-50, 50), random.uniform(-50, 50)],
                'size': random.uniform(0.005, 0.03),
                'brightness': random.uniform(0.5, 1.0),
                'color': random.choice([(1.0, 1.0, 1.0), (1.0, 0.9, 0.9), (0.9, 0.9, 1.0)])
            })
        return stars
    
    def draw_star(self, star):
        glPushMatrix()
        glTranslatef(*star['position'])
        glDisable(GL_LIGHTING)
        glColor3f(*star['color'])
        glPointSize(star['size'] * 800)
        glBegin(GL_POINTS)
        glVertex3f(0, 0, 0)
        glEnd()
        glEnable(GL_LIGHTING)
        glPopMatrix()

class Spaceship:
    def __init__(self):
        self.position = [0, 0, 0]
        self.rotation = [0, 0, 0]
        self.speed = 0.1
        
    def update(self, keys):
        if keys[pygame.K_LEFT]: self.rotation[1] -= 2
        if keys[pygame.K_RIGHT]: self.rotation[1] += 2
        if keys[pygame.K_UP]: self.rotation[0] -= 2
        if keys[pygame.K_DOWN]: self.rotation[0] += 2
        
        if keys[pygame.K_w]: self.position[2] -= self.speed
        if keys[pygame.K_s]: self.position[2] += self.speed
        if keys[pygame.K_a]: self.position[0] -= self.speed
        if keys[pygame.K_d]: self.position[0] += self.speed
        if keys[pygame.K_r]: self.position[1] += self.speed
        if keys[pygame.K_f]: self.position[1] -= self.speed

class GalacticGame:
    def __init__(self):
        self.width, self.height = 1200, 800
        self.setup_pygame()
        self.graphics = CinematicGraphics(self.width, self.height)
        self.graphics.setup_opengl()
        self.spaceship = Spaceship()
        self.stars = self.graphics.create_starfield(1500)
        self.running = True
        
    def setup_pygame(self):
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.OPENGL | pygame.DOUBLEBUF)
        pygame.display.set_caption("🚀 Galactic Cinematic Game - Installable Version")
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.running = False
                
    def render(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(0, 0, -10, 0, 0, 0, 0, 1, 0)
        
        for star in self.stars:
            self.graphics.draw_star(star)
            
        glPushMatrix()
        glTranslatef(*self.spaceship.position)
        glRotatef(self.spaceship.rotation[0], 1, 0, 0)
        glRotatef(self.spaceship.rotation[1], 0, 1, 0)
        
        glColor3f(0.2, 0.4, 0.8)
        glutSolidCone(0.5, 1.5, 16, 8)
        glPopMatrix()
        
        pygame.display.flip()
        
    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            self.handle_events()
            keys = pygame.key.get_pressed()
            self.spaceship.update(keys)
            self.render()
            clock.tick(60)
        pygame.quit()

def main():
    try:
        print("🚀 Starting Galactic Cinematic Game...")
        game = GalacticGame()
        game.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Press Enter to exit...")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
