import numpy as np
import pygame
import sys
import time

class shoot():
    def __init__(self, number_ships = 3, nbr_good = 1, fixed_good_ship = False, fixed_missile_speed = True,
                 ships_lifes = 3, max_steps = 500):
        np.random.seed(100)
        self.number_ships = number_ships
        self.first_render = True
        self.nbr_good_ref = nbr_good
        self.nbr_bad_ref = number_ships-nbr_good
        self.fixed_good_ship = fixed_good_ship
        self.fixed_missile_speed = fixed_missile_speed
        self.ships_lifes = ships_lifes
        self.act_dim = 1


        self.nofb_obs_dim = self.number_ships * 2 + 1 # pos_x, pos_y, timestep
        self.obs_dim = self.nofb_obs_dim + self.act_dim + 1 # actions and reward
        self.max_size = 1
        self.resolution = 640
        self.zone_size = 0.4
        self.default_speed = self.max_size/10.0
        self.max_steps = max_steps
        self.stop_duration = 10
        self.default_order = [i for i in range(number_ships)]
        self.pixel_coord_ratio = 640 / (4*self.max_size)
        self.create_references()

    def random_range(self, range_max):
        return (np.random.rand()-0.5) * 2 * range_max

    def create_references(self):
        self.refs = []
        for r in range(self.number_ships):
            created = False
            while not created:
                random_pos = [self.random_range(self.max_size), 1, r<self.nbr_good_ref]
                distances = []
                for existing_ref in self.refs:
                    distances.append(self.euc_dist(random_pos, existing_ref))
                if True or distances == [] or np.min(distances) > 1*self.zone_size:
                    created = True
                    self.refs.append(random_pos)

    def create_pos(self):
        created = False
        while not created:
            pot_pos = [self.random_range(1.5 * self.max_size), self.random_range(1.5 * self.max_size)]
            distances = []
            for existing_ref in self.refs:
                distances.append(self.euc_dist(pot_pos, existing_ref))
            if np.min(distances) > 1.5*self.zone_size:
                created = True
        return pot_pos

    def euc_dist(self, ref1, ref2):
        return np.sqrt(np.square(ref1[0]-ref2[0]) + np.square(ref1[1]-ref2[1]))

    def test_show(self):
        self.reset()
        done = False
        while not done:
            _,_, done,_ = self.take_step([0.0, 0.0])
            self.render()

    def take_step(self, actions):
        pos, timestep, prev_action, prev_reward = self.state
        self.dt = 0.1
        self.episode_step += 1
        if self.episode_step in self.switches:
            # self.order = np.flip(self.order, 0)
            for r in self.refs:
                r[-1] = not r[-1]
        direction = actions[0]
        direction *= np.pi
        direction = self.angle_normalize(direction)
        if self.control_speed:
            move = actions[1]
            move = np.clip(move, 0.0, 5.0)
        else:
            move = 2.5
            # move = 12.5

        distances_to_references = []
        for r in self.refs:
            distances_to_references.append(self.euc_dist(pos, r))
        self.distances_to_references = distances_to_references
        minimum_distance = np.min(distances_to_references)
        reward = 0.0
        if minimum_distance <= self.zone_size:
            touched_ref = np.argmin(distances_to_references)
            isgood = self.refs[touched_ref][-1]
            if isgood:
                reward = 100.0
                # TODO : ADDED FOR TEST
                if np.random.rand() < self.intra_var_percentage:
                    self.order = np.random.choice(self.number_dots, self.number_dots, False)
                    self.create_references()
            else:
                reward = -100.0
            if not self.fixed_position:
                new_pos = self.create_pos()
            else:
                new_pos = self.default_pos
            if not self.fixed_references:
                self.create_references()
            self.change += 1
        else:
            new_pos = [pos[0] + np.cos(direction) * move * self.default_speed,
                       pos[1] + np.sin(direction) * move * self.default_speed]
        new_posx = new_pos[0]
        new_posy = new_pos[1]
        if new_posx > self.max_size * 2:
            new_posx -= 4 * self.max_size
        elif new_posx < -2 * self.max_size:
            new_posx += 4 * self.max_size
        if new_posy > self.max_size * 2:
            new_posy -= 4 * self.max_size
        elif new_posy < -2 * self.max_size:
            new_posy += 4 * self.max_size

        # new_posx = np.clip(new_posx, -self.max_size*2, self.max_size*2)
        # new_posy = np.clip(new_posy, -self.max_size*2, self.max_size*2)

        done = False
        if self.episode_step >= self.max_steps:
            done = True
        if not self.control_speed:
            self.state = [[new_posx, new_posy], self.episode_step, [direction], reward]
        else:
            self.state = [[new_posx, new_posy], self.episode_step, [direction, move], reward]
        return self._get_obs(), reward, done, self.change

    def angle_normalize(self, x):
        if x > 0:
            return x % (2*np.pi)
        else:
            return 2*np.pi - (np.abs(x) % (2 * np.pi))

    def _get_obs(self):
        pos, timestep, prev_action, prev_reward = self.state
        refs = np.array(self.refs)
        self.references_dif = np.concatenate([[el[0]-pos[0],el[1]-pos[1]] for el in refs[self.order]])
        self.to_show_ref_dif = refs
        to_concat_obs = self.references_dif
        if self.stop_input:
            to_concat_obs = np.concatenate([to_concat_obs, [self.stopped]])
        return np.concatenate([to_concat_obs, [timestep*1e-3], prev_action, [prev_reward]])

    def reset(self, params = None):
        self.switches = params
        if params == None:
            self.switches = []
        self.stop_counter = 0
        self.change = 0
        self.episode_step = 0
        self.create_references()
        self.stopped = -1
        position = self.create_pos()
        if self.control_speed:
            self.state = [position, 0, [0.0, 0.0], 0.0]
        else:
            self.state = [position, 0, [0.0], 0.0]
        if self.fixed_good_refs:
            self.order = self.default_order
        else:
            self.order = np.random.choice(self.number_dots, self.number_dots, False)
        self.next_order = self.order
        if not params == None:
            pass
        return self._get_obs()

    def map_to_screen(self, x, y):
        point = (int((x+2*self.max_size) * self.resolution/(4*self.max_size)),
                 self.resolution - int((y+2*self.max_size) * self.resolution/(4*self.max_size)))
        return point

    def render(self):
        pos, timestep, prev_action, prev_reward = self.state
        resolution = (self.resolution, self.resolution)
        if self.first_render:
            self.first_render = False
            pygame.init()
            pygame.font.init()
            self.screen = pygame.display.set_mode(resolution)
            self.previous_time = time.time()
        self.screen.fill((255,255,255))
        myfont = pygame.font.SysFont('Comic Sans MS', 30)
        textsurface = myfont.render(str(prev_action), False, (0, 0, 0))
        self.screen.blit(textsurface, (int(resolution[0] / 2), 0))
        textsurface2 = myfont.render(str(self.references_dif), False, (0, 0, 0))
        self.screen.blit(textsurface2, (int(resolution[0] / 2) - 200, 40))
        textsurface3 = myfont.render(str(self.order), False, (0, 0, 0))
        self.screen.blit(textsurface3, (int(resolution[0] / 2) - 200, 80))
        textsurface3 = myfont.render(str(self.change), False, (0, 0, 0))
        self.screen.blit(textsurface3, (int(resolution[0] / 2) - 100, 120))

        for r in self.refs:
            if r[-1]:
                color = (0,255,0)
            else:
                color = (255,0,0)
            points = self.map_to_screen(r[0],r[1])
            pygame.draw.circle(self.screen, color, points, 3, 3)
            pygame.draw.circle(self.screen, color, points, int(self.zone_size*self.pixel_coord_ratio), 3)
        points = self.map_to_screen(pos[0],pos[1])
        pygame.draw.circle(self.screen, (0,0,255), points, 3, 3)

        action_points = [self.map_to_screen(pos[0], pos[1]),
                         self.map_to_screen(pos[0] + np.cos(prev_action[0]) * 0.4,
                                            pos[1] + np.sin(prev_action[0]) * 0.4)]
        pygame.draw.lines(self.screen, (0,0,0), False, action_points, 2)

        cur_time = time.time()
        pygame.display.update()
        for event in pygame.event.get():
            pass
        while not (cur_time - self.previous_time >= 1.*self.dt):
            cur_time = time.time()
        self.previous_time = cur_time