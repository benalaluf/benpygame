import math
from math import copysign

import pygame
from pygame._sprite import collide_rect
from pygame.constants import *
from pygame.math import Vector2
from pygame.event import Event

import level
import player
from singleton import Singleton
from sprite import Sprite
from level import Level
import settings as config

# Return the sign of a number: getsign(-5)-> -1
getsign = lambda x: copysign(1, x)


class Player(Sprite, Singleton):
    def __init__(self, *args):
        Sprite.__init__(self, *args)
        self.__startrect = self.rect.copy()
        self.__maxvelocity = Vector2(config.PLAYER_MAX_SPEED, 100)
        self.__startspeed = 1.5

        self._velocity = Vector2()
        self._input = 0
        self._jumpforce = config.PLAYER_JUMPFORCE
        self._bonus_jumpforce = config.PLAYER_SPRING_JUMPFORCE

        self.gravity = config.GRAVITY
        self.accel = .5
        self.deccel = .6
        self.dead = False

        self.lastkeypressed = ['d']

        self.bullets = []
        self.__to_remove = []

    def _fix_velocity(self) -> None:
        self._velocity.y = min(self._velocity.y, self.__maxvelocity.y)
        self._velocity.y = round(max(self._velocity.y, -self.__maxvelocity.y), 2)
        self._velocity.x = min(self._velocity.x, self.__maxvelocity.x)
        self._velocity.x = round(max(self._velocity.x, -self.__maxvelocity.x), 2)

    def reset(self) -> None:
        self._velocity = Vector2()
        self.rect = self.__startrect.copy()
        self.camera_rect = self.__startrect.copy()
        self.dead = False

    def handle_event(self, event: Event) -> None:
        # Check if start moving
        if event.type == KEYDOWN:
            # Moves player only on x-axis (left/right)
            if event.key == K_LEFT or event.key == K_a:
                self._velocity.x = -self.__startspeed
                self._input = -1
                self.set_image(config.PLAYER_IMAGE_LEFT)
                self.lastkeypressed.append('a')

            elif event.key == K_RIGHT or event.key == K_d:
                self._velocity.x = self.__startspeed
                self._input = 1
                self.set_image(config.PLAYER_IMAGE_RIGHT)
                self.lastkeypressed.append('d')

            elif event.key == K_UP or event.key == K_w:
                self.set_image(config.PLAYER_IMAGE_SHOOT)
                self.lastkeypressed.append('w')
                b = Player.Bullet(self.rect.centerx - 10, self.rect.y, config.BULLET_SIZE[0], config.BULLET_SIZE[1],
                                  config.BULLET_IMAGE, config.BULLET_SPEED, self.rect.centerx, self.rect.centery - 1000)
                self.bullets.append(b)



        # Check if stop moving
        elif event.type == KEYUP:
            if (event.key == K_LEFT or event.key == K_a and self._input == -1) or (
                    event.key == K_RIGHT or event.key == K_d and self._input == 1):
                self._input = 0
            if self.lastkeypressed[len(self.lastkeypressed) - 1] == 'w':
                self.lastkeypressed.pop()
                if self.lastkeypressed[len(self.lastkeypressed) - 1] == 'd':
                    self.set_image(config.PLAYER_IMAGE_RIGHT)
                elif self.lastkeypressed[len(self.lastkeypressed) - 1] == 'a':
                    self.set_image(config.PLAYER_IMAGE_LEFT)

        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = pygame.mouse.get_pos()
            # print(x,y)
            print(self.rect.x, self.rect.y)
            self.bullets.append(
             Player.Bullet(self.rect.centerx, self.rect.y, config.BULLET_SIZE[0], config.BULLET_SIZE[1],
                              config.BULLET_IMAGE, config.BULLET_SPEED, x, y)
            )

    def jump(self, force: float = None) -> None:
        if not force: force = self._jumpforce
        self._velocity.y = -force

    def onCollide(self, obj: Sprite) -> None:
        self.rect.bottom = obj.rect.top
        self.jump()

    def onCollideNoJump(self, obj: Sprite) -> None:
        self.rect.bottom = obj.rect.top

    def collisions(self) -> None:
        lvl = Level.instance
        if not lvl: return
        for platform in lvl.platforms:
            # check falling and colliding <=> isGrounded ?
            if self._velocity.y > .5:
                # check collisions with platform's spring bonus
                if platform.bonus and collide_rect(self, platform.bonus):
                    platform.bonus.onCollide()
                    self.onCollide(platform.bonus)
                    self.jump(platform.bonus.force)

                # check collisions with platform
                if collide_rect(self, platform):
                    if platform.breakable:
                        pass
                    else:
                        self.onCollide(platform)
                    platform.onCollide()

    def update(self) -> None:
        if self.camera_rect.y > config.YWIN * 2:
            self.dead = True
            return
        self._velocity.y += self.gravity
        if self._input:  # accelerate
            self._velocity.x += self._input * self.accel
        elif self._velocity.x:  # deccelerate
            self._velocity.x -= getsign(self._velocity.x) * self.deccel
            self._velocity.x = round(self._velocity.x)
        self._fix_velocity()

        self.rect.x = (self.rect.x + self._velocity.x) % (config.XWIN - self.rect.width)
        self.rect.y += self._velocity.y

        for bullet in self.__to_remove:
            if bullet in self.bullets:
                self.bullets.remove(bullet)
        self.__to_remove = []

        for b in self.bullets:
            b.move()

        self.collisions()

    def remove_bullet(self, blt) -> bool:
        """ Removes a platform safely.
        :param plt Platform: the platform to remove
        :return bool: returns true if platoform successfully removed
        """
        if blt in self.bullets:
            self.__to_remove.append(blt)
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        for bullet in self.bullets:
            bullet.draw(surface)

    class Bullet(Sprite):
        def __init__(self, x, y, width, height, image, speed, targetx, targety):
            super().__init__(x, y, width, height, image)
            angle = math.atan2(targety - y, targetx - x)  # get angle to target in radians
            # print('Angle in degrees:', int(angle * 180 / math.pi))
            self.speed = speed
            self.dx = math.cos(angle) * speed
            self.dy = math.sin(angle) * speed
            self.x = x
            self.y = y
            self.player = Player.instance

        def move(self):
            # self.x and self.y are floats (decimals) so I get more accuracy
            # if I change self.x and y and then convert to an integer for
            # the rectangle.
            self.x = self.x + self.dx
            self.y = self.y + self.dy
            self.rect.x = self.x
            self.rect.y = self.y

        # Override
        def draw(self, surface: pygame.Surface) -> None:
            super().draw(surface)
            if self.camera_rect.y + self.rect.height > config.YWIN:
                self.player.remove_bullet(self)

        def update(self, dx, dy):
            self.dx = dx
            self.dy = dy
