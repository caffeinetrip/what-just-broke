import pygame
from scripts.tilemap import AnimBlock

class PhysicsEntity():
    def __init__(self, game, e_type, pos, size):
        self.game = game
        self.type = e_type
        self.pos = list(pos)
        self.size = size
        self.velocity = [0, 0]
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}
        self.action = ''
        self.anim_offset = (-3, -3)
        self.flip = False
        self.set_action('idle')
        self.buffs = {}
        self.last_movement = [0, 0]
        self.death = False
        
        self.end_death = False

    def rect(self):
        return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])
    
    def set_action(self, action):
        if action != self.action:
            self.action = action
            self.animation = self.game.animations[self.type + '/' + self.action].copy()
            
    def update(self, tilemap, movement=(0, 0)):
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}
        frame_movement = (movement[0] + self.velocity[0], movement[1] + self.velocity[1])
        
        self.pos[0] += frame_movement[0]
        entity_rect = self.rect()
        for rect in tilemap.physics_rects_around(self.pos):
            if entity_rect.colliderect(rect):
                if frame_movement[0] > 0:
                    entity_rect.right = rect.left
                    self.collisions['right'] = True
                if frame_movement[0] < 0:
                    entity_rect.left = rect.right
                    self.collisions['left'] = True
                self.pos[0] = entity_rect.x
        
        self.pos[1] += frame_movement[1]
        entity_rect = self.rect()
        for rect in tilemap.physics_rects_around(self.pos):
            if entity_rect.colliderect(rect):
                if frame_movement[1] > 0:
                    entity_rect.bottom = rect.top
                    self.collisions['down'] = True
                if frame_movement[1] < 0:
                    entity_rect.top = rect.bottom
                    self.collisions['up'] = True
                self.pos[1] = entity_rect.y
                
        if movement[0] > 0:
            self.flip = False
        if movement[0] < 0:
            self.flip = True
            
        self.last_movement = movement

        self.velocity[1] = min(5, self.velocity[1] + 0.1)
        
        if self.collisions['down'] or self.collisions['up']:
            self.velocity[1] = 0
        
        self.animation.update()
    
    def render(self, surf, offset=(0, 0)):
        surf.blit(pygame.transform.flip(self.animation.img(), self.flip, False), 
                  (self.pos[0] - offset[0] + self.anim_offset[0], self.pos[1] - offset[1] + self.anim_offset[1] + 2))
class Player(PhysicsEntity):
    def __init__(self, game, pos, size):
        super().__init__(game, 'player', pos, size)
        self.air_time = 0
        self.jumps = 1
        self.wall_slide = False
        self.was_falling = False
        self.move_speed = 0.1
        self.on_edge = False
        self.land_timer = 0
        self.dash_duration = 20
        self.dash_speed = 3.0
        self.dashing = False
        self.death_animation_played = False
        self.last_tile = None
        self.tile = None
        self.anim_blocks = []
        self.angle = 0
        
        # SOunds
        self.sounds = {
            'jump': pygame.mixer.Sound('data/sounds/jump.mp3'),
            'death': pygame.mixer.Sound('data/sounds/death.mp3'),
            'land': pygame.mixer.Sound('data/sounds/land.mp3' ),
            'dash': pygame.mixer.Sound('data/sounds/dash.mp3'),
            'anomaly_0': pygame.mixer.Sound('data/sounds/anomaly_0.mp3'),
            'anomaly_1': pygame.mixer.Sound('data/sounds/anomaly_1.mp3'),
            'checkpoint': pygame.mixer.Sound('data/sounds/checkpoint.mp3'),
            'run': pygame.mixer.Sound('data/sounds/run.mp3')
        }
        
        self.sounds['run'].set_volume(0.15) 
        self.run_sound_duration = 0.3
        self.last_run_sound_time = 0
        
        self.sounds['anomaly_0'].set_volume(0.3)
        self.sounds['anomaly_1'].set_volume(0.3)
        
        self.sounds['land'].set_volume(0.3)
        self.sounds['dash'].set_volume(0.25)
        self.sounds['death'].set_volume(0.45)
        self.sounds['jump'].set_volume(0.1)
        self.sounds['checkpoint'].set_volume(0.005)
        
        self.left_channel_bust = pygame.mixer.Channel(1)
        self.left_channel_bust.set_volume(2.075, 2.0)

    def update(self, tilemap, movement=(0, 0)):
        if self.death:
            if not self.death_animation_played:
                self.set_action('death')
                self.death_animation_played = True
                self.left_channel_bust.play(self.sounds['death'])

            self.animation.update()
            super().update(tilemap)
            return
        
        for tile in tilemap.tiles_around(self.pos, '|'):
            if tile['tile_id'] == '139':
                self.velocity[1] = -2
                self.velocity[0] = 0
                movement = [False,False]
                self.set_action('fall')
                
            if tile['tile_id'] == '140':
                self.death = True
                self.game.transition_vfx['value'] = 39
                self.game.death_vfx_timer = 0 
                self.game.scenes['sub_scene'] = 'ending'
                
        super().update(tilemap, movement=movement)

        self.air_time += 1
        last_direction = None 

        if not hasattr(self, 'last_collision_direction'):
            self.last_collision_direction = None
            
        #print(self.pos)
            
        for tile in tilemap.tiles_around(self.pos, ':'):
            if tile['tile_id'] == '110':
                self.game.checkpoint = [tile['pos'][0] * tilemap.tile_size, tile['pos'][1] * tilemap.tile_size]
                
                tilemap.tilemap[str(tile['pos'][0]) + ':' + str(tile['pos'][1])]['tile_id'] = '111'
                self.sounds['checkpoint'].play()
                
                for key, tile_ in tilemap.tilemap.items():
                    if tile != tile_ and tile_['tile_id'] == '111':
                        tile_['tile_id'] = '110'


        for direction in ['down', 'up', 'left', 'right']:
            if self.collisions[direction]:
                check_pos = [self.pos[:], self.pos[:]]

                if direction == 'down':
                    check_pos[0][1] += self.size[1]
                    check_pos[1][1] += self.size[1]
                    check_pos[1][0] += self.size[0]
                    
                elif direction == 'up':
                    check_pos[0][1] -= 1
                    check_pos[1][1] -= 1
                    check_pos[1][0] += self.size[0]
                    
                elif direction == 'left':
                    check_pos[0][0] -= 1
                    check_pos[1][0] -= 1
                    check_pos[1][1] += self.size[1]
                    
                elif direction == 'right':
                    check_pos[0][0] += self.size[0] + 1
                    check_pos[1][0] += self.size[0] + 1
                    check_pos[1][1] += self.size[1]

                self.tile = [tilemap.solid_check(check_pos[0]), tilemap.solid_check(check_pos[1])]
                self.last_collision_direction = direction
                
                #print(tilemap.solid_check(check_pos[0]))

                if self.tile[0] and self.tile[1]:
                    if self.tile[0]['tile_id'] in ['10', '22', '77', '78'] or self.tile[1]['tile_id'] in ['10', '22', '77', '78']:
                        self.death = True
                        self.game.transition_vfx['value'] = 39
                        self.game.death_vfx_timer = 0 
                        return

        for direction in ['down', 'up', 'left', 'right']:
            if self.collisions[direction]:
                if last_direction is None:
                    last_direction = direction

        if self.last_tile and self.last_tile[0]:
           
            if (self.last_tile[0]['tile_id'] == '44' and self.last_tile[0] != self.tile[0]) or (self.last_tile[0]['tile_id'] == '44' and self.velocity[1] <= -2.5):
                original_pos = self.last_tile[0]['pos'].copy()
                tile_loc = f"{original_pos[0]};{original_pos[1]}"
                if tile_loc in tilemap.tilemap:
                    tilemap.tilemap[tile_loc]['tile_id'] = '22'

                directions = [(0, -1, 0), (0, 1, 180), (1, 0, 270), (-1, 0, 90)]
                for dx, dy, dir_angle in directions:
                    check_pos = (original_pos[0] + dx, original_pos[1] + dy)
                    check_loc = f"{check_pos[0]}|{check_pos[1]}"
                    if not tilemap.tile_exists(check_pos[0], check_pos[1]):
                        tilemap.tilemap[check_loc] = {'tile_id': '17', 'pos': list(check_pos)}
                        self.game.map['rotatesset'][check_loc] = dir_angle
                        self.anim_blocks.append(AnimBlock(self.game, check_pos, dir_angle, self.game.animations['danger_block/create'].copy()))

        self.last_tile = self.tile

        for anim in self.anim_blocks:
            anim.update()
        self.anim_blocks = [anim for anim in self.anim_blocks if anim.timer < anim.duration]

        if self.dashing:
            self.dash_timer -= 1
            self.velocity[1] = 0.321321
            if self.dash_timer <= 0:
                self.dashing = False
                self.velocity[0] = 0 
            
            if self.action != 'land':
                self.set_action('fall')

                
        else:
            if self.action == 'land':
                self.land_timer -= 1
                if self.land_timer <= 0:
                    self.land_timer = 0

            if self.collisions['down']:
                if self.was_falling:
                    self.set_action('land')
                    self.sounds['land'].set_volume((self.air_time/100)*0.4)
                    self.left_channel_bust.play(self.sounds['land'])
                    self.was_falling = False
                    self.land_timer = 10
                self.air_time = 0
                self.jumps = 1
            else:
                if self.velocity[1] > 0.5:
                    self.was_falling = True
                    self.set_action('fall')

            self.wall_slide = False
            if (self.collisions['right'] or self.collisions['left']) and self.air_time > 4 and self.velocity[0]:
                self.wall_slide = True
                self.velocity[1] = min(self.velocity[1]*0.95, 0.5)
                self.flip = self.collisions['left']
                self.set_action('wall_slide')

            if self.collisions['down'] and movement[0] == 0:
                left_point = (self.pos[0], self.pos[1] + self.size[1] + 1)
                right_point = (self.pos[0] + self.size[0], self.pos[1] + self.size[1] + 1)
                left_has_tile = any(rect.collidepoint(left_point) for rect in tilemap.physics_rects_around(self.pos))
                right_has_tile = any(rect.collidepoint(right_point) for rect in tilemap.physics_rects_around(self.pos))
                self.on_edge = not (left_has_tile and right_has_tile)

        if not self.wall_slide and self.land_timer == 0:
            if self.air_time > 4:
                if self.was_falling:
                    self.set_action('fall')
                else:
                    self.set_action('jump')
            elif movement[0] != 0:
                self.set_action('run')
                self.on_edge = False

                current_time = pygame.time.get_ticks() / 1000  
                if current_time - self.last_run_sound_time >= self.run_sound_duration:
                    self.left_channel_bust.play(self.sounds['run'])
                    self.last_run_sound_time = current_time 
            else:
                self.set_action('edge_idle' if self.on_edge else 'idle')

        if movement[0] > 0 and not self.dashing:
            self.velocity[0] = min(self.velocity[0] + self.move_speed, self.move_speed)
        elif movement[0] < 0 and not self.dashing:
            self.velocity[0] = max(self.velocity[0] - self.move_speed, -self.move_speed)
        else:
            if self.velocity[0] > 0:
                self.velocity[0] = max(self.velocity[0] - 0.1, 0)
            else:
                self.velocity[0] = min(self.velocity[0] + 0.1, 0)
                
        for anim in self.anim_blocks:
            anim.render(self.game.displays['main'], offset=self.game.render_scroll)
            
    def jump(self, jump_power=0):
        if self.wall_slide:
            if self.flip and self.last_movement[0] < 0 or not self.flip and self.last_movement[0] > 0:
                self.velocity[0] = 3.5 * (1 if self.flip else -1)
                self.velocity[1] = -2.5 + jump_power
                self.air_time = 5
                self.jumps = max(0, self.jumps - 1)
                self.sounds['land'].set_volume(0.2)
                self.left_channel_bust.play(self.sounds['land'])
                if 'x2jump' in self.buffs:
                    self.buffs['x2jump'].ui.clear_buff()

                return True    
            
        elif self.jumps and self.action in ['edge_idle', 'idle', 'run', 'land']:
            self.velocity[1] = -3.0 + jump_power
            self.jumps -= 1
            self.air_time = 5
            self.left_channel_bust.play(self.sounds['jump'])
            if 'x2jump' in self.buffs:
                self.buffs['x2jump'].ui.clear_buff()
                
            return True
    
    def dash(self):
        self.dashing = True
        self.dash_timer = self.dash_duration
        self.velocity[0] = self.dash_speed * (-1 if self.flip else 1) 
        self.left_channel_bust.play(self.sounds['dash'])
        return True
    
    def render(self, surf, offset=(0, 0)):
        if self.death and self.animation.done:
            return 
        
        def process_sprite(color_map):
            sprite = self.animation.img()
            sprite_copy = sprite.copy()
            width, height = sprite_copy.get_size()
            for x in range(width):
                for y in range(height):
                    r, g, b, a = sprite_copy.get_at((x, y))
                    if (r, g, b) in color_map:
                        sprite_copy.set_at((x, y), (*color_map[(r, g, b)], a))
            return sprite_copy

        color_maps = {'x2jump': {(255, 0, 0): (152, 1, 1)}}

        for buff, color_map in color_maps.items():
            if buff in self.buffs:
                processed_sprite = process_sprite(color_map)
                surf.blit(pygame.transform.flip(processed_sprite, self.flip, False),
                          (self.pos[0] - offset[0] + self.anim_offset[0],
                           self.pos[1] - offset[1] + self.anim_offset[1] + 2))
                return

        super().render(surf, offset=offset)