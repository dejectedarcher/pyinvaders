import pygame
import gameobjects
from pygame.locals import (
    QUIT,
    MOUSEBUTTONDOWN,
    MOUSEBUTTONUP,
    KEYDOWN,
    KEYUP
)
import datetime
import random
import Randomizer
from levels import Waves


class Input():
    def __init__(self):
        self._events = {}
        self._events_pressed = {}

    def register(self, key_code, command):
        '''Called when key changes state'''
        self._events[key_code] = command

    def register_pressed(self, key_code, command):
        '''Called when key is pressed only'''
        self._events_pressed[key_code] = command

    def on_key(self, key_code, down=True):
        if key_code in self._events:
            self._events[key_code](down)
        elif key_code in self._events_pressed and down:
            self._events_pressed[key_code]()


class World():
    def __init__(self):
        # Key: Object type string
        # Value: Object
        self._objects = {}

        # Contains all objects
        self._all_objects = []

        gameobjects.WorldHelper.append = self.append
        gameobjects.WorldHelper.remove = self.remove

    def append(self, object):
        type_name = object.OBJECT_TYPE
        self._append_dic(type_name, object, self._objects)
        self._append_list(object, self._all_objects)

    def _append_dic(self, key, value, dic):
        if key in dic:
            self._append_list(value, dic[key])
        else:
            dic[key] = []
            self._append_list(value, dic[key])

    def _append_list(self, value, list):
        if value not in list:
            list.append(value)

    def get_all_objects(self):
        return self._all_objects

    def remove(self, object):
        object.on_world_remove()
        g = self._objects[object.OBJECT_TYPE]
        g.remove(object)
        self._all_objects.remove(object)

    def get_by_type(self, type):
        type_name = type.OBJECT_TYPE
        if type_name not in self._objects:
            # Create the requested type_name and
            # return it as an empty array
            self._objects[type_name] = []
            return self._objects[type_name]
        return self._objects[type_name]

    def get_main_dic(self):
        return self._objects

    def clear(self):
        # if 2 objects are referencing each other
        # they will never be removed
        # we gotta check that one by one
        for obj in self._all_objects:
            obj.on_removed_event.clear()

        self._objects.clear()
        self._all_objects.clear()


class Controller:
    DEBUG1 = 'a'
    DEBUG2 = 'z'
    DEBUG3 = 'k'
    DEBUG4 = ']'
    DEBUG5 = '['
    DEBUG6 = 'm'
    PAUSE = 'p'
    RESET = 'r'
    LOSE = 'l'

    def __init__(self, game, updater):
        self._game = game
        self._player = game.world.get_by_type(gameobjects.Player)[0]
        self._updater = updater

        self.keyboard = Input()
        self.register_key(self.DEBUG1, self._player.upgrade_shoot)
        self.register_key(self.DEBUG2, self._player.downgrade_shoot)
        self.register_key(self.PAUSE, game.game_state.on_pause)
        self.register_key(self.RESET, game.game_state.on_reset)
        self.register_key(self.LOSE, game.game_state.on_lost)
        self.register_key(self.DEBUG3, game.spawner.kill_wave)
        self.register_key(self.DEBUG4, self.inc_sim_speed)
        self.register_key(self.DEBUG5, self.dec_sim_speed)        
        self.register_key(self.DEBUG6, self.test)
        self.mouse = Input()
        self.mouse.register_pressed(1, self._player.shoot)

        self.key_press_events = []

        self._game_state = game.game_state

    def register_key(self, char, event):
        self.keyboard.register_pressed(ord(char), event)

    def update_player_pos(self):
        mouse_pos = pygame.mouse.get_pos()
        self._player.set_pos(mouse_pos)

    def inc_sim_speed(self):
        self._updater.time_scale *= 2

    def dec_sim_speed(self):
        self._updater.time_scale /= 2

    def test(self):
        mg = gameobjects.MeteorGenerator(10)
        mg.interval = 0.5
        mg.life_time = 20
        self._game.world.append(mg)


def create_explosion(world, pos):
    exp = gameobjects.Explosion()
    world.append(exp)
    exp.set_pos(pos)


def drop_powerup(world, pos):
    if Randomizer.Bool(0.07):
        rand_type = random.randint(0, 2)
        type = [gameobjects.PowerupHealth,
                gameobjects.PowerupWeapon,
                gameobjects.PowerupShield][rand_type]
        pu = type()
        world.append(pu)
        pu.set_pos(pos)


class Collisions:
    '''
    Handles events of main gameobjects collisions
    '''
    def __init__(self, world, game_state):
        self._world = world
        self._player = world.get_by_type(gameobjects.Player)[0]
        self._bullets = world.get_by_type(gameobjects.Bullet)
        self._enemies = world.get_by_type(gameobjects.Enemy)
        self._e_bullets = world.get_by_type(gameobjects.EBullet)
        self._powerups = world.get_by_type(gameobjects.DropItem)
        self._meteors = world.get_by_type(gameobjects.Meteor)
        self._game_state = game_state

    def check_list(self, obj, list, callback, only_one=True):
        for offender in list:
            if obj.collides(offender):
                callback(obj, offender)
                if only_one:
                    break

    def on_enemy_bullet(self, bullet, enemy):
        self._world.remove(bullet)
        if enemy.take_damage(bullet.DAMAGE):
            self._world.remove(enemy)
            self._player.score += enemy.SCORE

            create_explosion(self._world, enemy.get_pos())
            drop_powerup(self._world, enemy.get_pos())

    def on_player_bullet(self, player, bullet):
        self._world.remove(bullet)
        if player.take_damage(bullet.DAMAGE):
            self._game_state.on_lost()

    def on_powerup(self, player, p):
        self._player.on_powerup(p)
        self._world.remove(p)

    def on_player_enemy(self, player, enemy):
        self._game_state.on_lost()

    def on_player_meteor(self, player, meteor):
        self._game_state.on_lost()

    def update(self):
        # Check if enemy is hit
        for bullet in self._bullets:
            self.check_list(bullet, self._enemies, self.on_enemy_bullet)

        # Check if player is hit
        self.check_list(self._player, self._e_bullets,
                        self.on_player_bullet, False)

        # Check if powerup hits player
        self.check_list(self._player, self._powerups, self.on_powerup)

        # Check player hitting enemy
        self.check_list(self._player, self._enemies, self.on_player_enemy)

        # Check player hitting meteor
        self.check_list(self._player, self._meteors, self.on_player_meteor)


class EnemySpwaner:
    LOWER_LIMIT = 720

    def __init__(self, world, game_state):
        self._world = world
        self._player = self._world.get_by_type(gameobjects.Player)[0]
        self._game_state = game_state

        self.enemies = []
        self.next_wave_index = 1
        self.spawn_wave()

    def spawn_wave(self):
        enemies = Waves.create_wave(self.next_wave_index, self._player)

        if len(enemies) > 0:
            for etemp in enemies:
                self._add_enemy_temp(etemp)

        self.next_wave_index += 1

    def on_child_removed(self, child):
        self.enemies.remove(child)
        if len(self.enemies) == 0:
            self.spawn_wave()

    def reset(self):
        self.next_wave_index = 1
            # I don't want world to notify me
        for enemy in self.enemies:
            enemy.on_removed_event.clear()

    def kill_wave(self):
        # We don't want to spawn enemies while removing them
        # Also not removing them from the list while iterating on them
        # Remove on_child_event from them first!
        for enemy in self.enemies:
            enemy.on_removed_event.remove(self.on_child_removed)
            self._world.remove(enemy)
        self.enemies.clear()
        self.spawn_wave()

    def _add_enemy_temp(self, etemp):
        self._world.append(etemp.enemy)
        if etemp.mover is not None:
            self._world.append(etemp.mover)
        if etemp.shooter is not None:
            self._world.append(etemp.shooter)
        self.enemies.append(etemp.enemy)
        etemp.enemy.on_removed_event.append(self.on_child_removed)


class Animator():
    def __init__(self):
        self._objects_loop = []  # Keep animating
        self._objects_onetime = {}  # {object, callback}

    def update(self, delta_time):
        for obj in self._objects_loop:
            self._update_obj(obj, delta_time)

        to_remove = []
        for obj, callback in self._objects_onetime.items():
            if self._update_obj(obj, delta_time):
                to_remove.append(obj)
                callback()

        for r in to_remove:
            del self._objects_onetime[r]

    def _update_obj(self, obj, delta_time):
        '''
        Returns True when replaying.
        '''
        asprite = obj.sprite
        fps = asprite.fps
        obj.internal_frame += delta_time * fps
        if obj.internal_frame >= 1:
            delta_frames = int(obj.internal_frame)
            obj.internal_frame -= delta_frames
            obj.frame += delta_frames
            if obj.frame >= asprite.frames_count:
                obj.frame %= asprite.frames_count
                return True
        return False

    def add_object_loop(self, object):
        if object not in self._objects_loop:
            object.internal_frame = 0
            self._objects_loop.append(object)

    def remove_object(self, object):
        if object in self._objects_loop:
            self._objects_loop.remove(object)

    def add_object_onetime(self, object, callback):
        if object not in self._objects_onetime:
            object.internal_frame = 0
            self._objects_onetime[object] = callback

    def clear(self):
        self._objects_loop.clear()
        self._objects_onetime.clear()


class Updater:
    FPS_LIMIT = 60

    def __init__(self, game):
        self.game = game
        self._lastdt = datetime.datetime.now()
        self.clock = pygame.time.Clock()
        self.time_scale = 1

    def pygame_events(self, controller):
        for event in pygame.event.get():
            if event.type == QUIT:
                return False
            elif event.type == MOUSEBUTTONDOWN:
                controller.mouse.on_key(event.button, True)
            elif event.type == MOUSEBUTTONUP:
                controller.mouse.on_key(event.button, False)
            elif event.type == KEYUP or event.type == KEYDOWN:
                controller.keyboard.on_key(
                    event.key, event.type == KEYDOWN)

        return True

    def update_world(self, delta_time):
        for gobj in self.game.world.get_all_objects():
            gobj.update(delta_time)

        self.game.collisions.update()

    def update_all(self, paused):
        tnow = datetime.datetime.now()
        dt = (tnow - self._lastdt).total_seconds()
        self._lastdt = tnow

        if not paused:
            self.update_world(dt * self.time_scale)

        self.game.gui.update()
        pygame.display.update()

        self.clock.tick(Updater.FPS_LIMIT)
        return dt


class Render:
    def __init__(self, game, display):
        self.bg = gameobjects.ResourcesLoader.sprites['background']
        self.game = game
        self.display = display

    def draw(self, deltatime):
        self.game.animator.update(deltatime)
        self.bg.draw(self.display, deltatime)

        for obj in self.game.world.get_all_objects():
            obj.draw(self.display)

        self.game.gui.draw(self.display)


class GUI:
    def __init__(self, player):
        self._health = gameobjects.ProgressBar()
        self._shield = gameobjects.ProgressBar((0, 0, 255), (0, 0, 0))
        self._score = gameobjects.TextUI('0', (255, 0, 0), 32)
        self._big_message = gameobjects.TextUI('Loser', size=100)
        self._lost = False
        self._player = player

    def draw(self, surface):
        self._health.draw(surface, (20, 20))
        self._shield.draw(surface, (20, 60))
        self._score.draw(surface, (20, 100))

        rect = surface.get_rect()
        screen_center = (rect.width/2, rect.height/2)
        screen_center = self._big_message.top_left_to_center(screen_center)
        if self._lost:
            self._big_message.draw(surface, screen_center)

    def update(self):
        self._health.set_value(self._player.health /
                               self._player.HEALTH)
        self._shield.set_value(self._player.get_shield_health() /
                               gameobjects.shield_1.HEALTH)
        self._score.set_test('Score: {}'.format(self._player.score))

    def loser(self, lost=True):
        self._lost = lost


class Components():
    def __init__(self, game_state):
        self.animator = Animator()
        gameobjects.WorldHelper.animator = self.animator

        self.world = World()
        self.player = gameobjects.Player()
        self.world.append(self.player)

        self.gui = GUI(self.player)

        self.spawner = EnemySpwaner(self.world, game_state)

        self.collisions = Collisions(self.world, game_state)

        self.game_state = game_state

    def reset(self):
        self.spawner.reset()
        # YOu can't clear world first
        # this will trigger a loop of clear/respawn

        self.world.clear()
        self.animator.clear()
        self.player.__init__()
        self.world.append(self.player)
        self.collisions.__init__(self.world, self.game_state)
        self.gui.loser(False)
        self.spawner.__init__(self.world, self.game_state)
