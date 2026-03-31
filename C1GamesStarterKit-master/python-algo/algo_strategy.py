import gamelib
import random
import math
import warnings
from sys import maxsize
import json

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        
        self.scored_on_locations = []
        self.breached_lanes = []

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)

        self.my_strategy(game_state)
        game_state.submit_turn()

    def my_strategy(self, game_state):
        self.build_initial_defenses(game_state)
        self.build_reactive_defenses(game_state)
        self.build_greedy_turrets(game_state)
        self.send_scouts(game_state)

    def build_initial_defenses(self, game_state):
        
        if not hasattr(self, 'core_supports'):
            self.core_supports = [[13, 11], [14, 11], [13, 12], [14, 12]]
            self.upgraded_supports = [[13, 12], [14, 12]]
            self.core_turrets = [[12, 12], [13, 13], [14, 13], [15, 12]]

        game_state.attempt_spawn(SUPPORT, self.core_supports)
        game_state.attempt_upgrade(self.upgraded_supports)
        game_state.attempt_spawn(TURRET, self.core_turrets)

    def build_reactive_defenses(self, game_state):
        for loc in self.scored_on_locations:
            x_coord = loc[0]
            if x_coord not in self.breached_lanes:
                self.breached_lanes.append(x_coord)
        
        self.scored_on_locations = []

        middle_supports = [[13, 11], [14, 11]]
        game_state.attempt_upgrade(middle_supports)

        supports_fully_upgraded = True
        for loc in middle_supports:
            is_upgraded = False
            if game_state.contains_stationary_unit(loc):
                for unit in game_state.game_map[loc]:
                    if unit.unit_type == SUPPORT and unit.upgraded:
                        is_upgraded = True
            if not is_upgraded:
                supports_fully_upgraded = False

        for x in self.breached_lanes:
            front_turret_loc = [x, 13]
            game_state.attempt_spawn(TURRET, front_turret_loc)

        if supports_fully_upgraded:
            for x in self.breached_lanes:
                back_turret_loc = [x, 11] 
                game_state.attempt_spawn(TURRET, back_turret_loc)

    def build_greedy_turrets(self, game_state):
        
        if not hasattr(self, 'greedy_locations'):
            self.greedy_locations = []
            for x in range(0, 13, 3):  
                self.greedy_locations.append([x, 13])
            for x in range(27, 14, -3): 
                self.greedy_locations.append([x, 13])
            for x in range(1, 13, 3):
                self.greedy_locations.append([x, 11])
            for x in range(26, 14, -3):
                self.greedy_locations.append([x, 11])

        game_state.attempt_spawn(TURRET, self.greedy_locations)

    def send_scouts(self, game_state):
        if game_state.get_resource(MP) < 1:
            return

        
        if not hasattr(self, 'friendly_edges'):
            self.friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + \
                                  game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
            self.enemy_edges = game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT) + \
                               game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT)
            self.turret_damage = gamelib.GameUnit(TURRET, game_state.config).damage_i

        deploy_locations = self.filter_blocked_locations(self.friendly_edges, game_state)
        
        if not deploy_locations:
            return

        if game_state.turn_number <= 1:
            corner_options = [[0, 13], [1, 12], [2, 11], [27, 13], [26, 12], [25, 11]]
            valid_corners = [loc for loc in corner_options if loc in deploy_locations]
            
            if valid_corners:
                spawn_loc = random.choice(valid_corners)
                game_state.attempt_spawn(SCOUT, spawn_loc, 5)
                return

        num_samples = min(5, len(deploy_locations))
        random_options = random.sample(deploy_locations, num_samples)
        
        best_location, is_landlocked = self.least_damage_spawn_location(game_state, random_options)
        
        if best_location:
            if is_landlocked:
                game_state.attempt_spawn(DEMOLISHER, best_location, 1000)
            else:
                game_state.attempt_spawn(SCOUT, best_location, 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        valid_options = []
        valid_damages = []
        landlocked_options = []
        landlocked_damages = []
        
        
        
        tile_damage_cache = {}
        
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            
            for path_location in path:
                loc_tuple = (path_location[0], path_location[1])
                
                
                if loc_tuple not in tile_damage_cache:
                    tile_damage_cache[loc_tuple] = len(game_state.get_attackers(path_location, 0)) * self.turret_damage
                
                
                damage += tile_damage_cache[loc_tuple]
            
            if path[-1] in self.enemy_edges:
                if damage == 0:
                    return location, False
                    
                valid_options.append(location)
                valid_damages.append(damage)
            else:
                landlocked_options.append(location)
                landlocked_damages.append(damage)
        
        if valid_options:
            best_idx = valid_damages.index(min(valid_damages))
            return valid_options[best_idx], False
        elif landlocked_options:
            best_idx = landlocked_damages.index(min(landlocked_damages))
            return landlocked_options[best_idx], True
            
        return None, False

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        
        
        
        if '"breach": []' in turn_string or '"breach":[]' in turn_string:
            return
            
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            
            if not unit_owner_self:
                self.scored_on_locations.append(location)

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()