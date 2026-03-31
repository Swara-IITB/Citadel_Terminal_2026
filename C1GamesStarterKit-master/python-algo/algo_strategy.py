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
        """ 
        Read in config and perform any initial setup here 
        """
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
        
        core_supports = [[13, 9], [14, 9], [13, 10], [14, 10]]
        upgraded_supports = [[13, 10], [14, 10]]
        
        game_state.attempt_spawn(SUPPORT, core_supports)
        game_state.attempt_upgrade(upgraded_supports)

        
        core_turrets = [[12, 10], [13, 11], [14, 11], [15, 10]]
        game_state.attempt_spawn(TURRET, core_turrets)

    def build_reactive_defenses(self, game_state):
        for loc in self.scored_on_locations:
            x_coord = loc[0]
            if x_coord not in self.breached_lanes:
                self.breached_lanes.append(x_coord)
        
        self.scored_on_locations = []

        
        middle_supports = [[13, 9], [14, 9]]
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
            wall_loc = [x, 13]
            game_state.attempt_spawn(WALL, wall_loc)

        
        if supports_fully_upgraded:
            for x in self.breached_lanes:
                wall_loc = [x, 13]
                turret_loc = [x, 12] 
                
                game_state.attempt_spawn(TURRET, turret_loc)
                game_state.attempt_upgrade(wall_loc)

    def build_greedy_turrets(self, game_state):
        greedy_locations = []
        
        for x in range(0, 13, 2):  
            greedy_locations.append([x, 13])
        for x in range(27, 14, -2): 
            greedy_locations.append([x, 13])
            
        for x in range(1, 13, 2):
            greedy_locations.append([x, 12])
        for x in range(26, 14, -2):
            greedy_locations.append([x, 12])

        game_state.attempt_spawn(TURRET, greedy_locations)

    def send_scouts(self, game_state):
        """
        Always send scouts every turn, but avoid landlocked paths.
        If all paths are blocked, send Demolishers to break the walls.
        """
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + \
                         game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        if deploy_locations:
            
            num_samples = min(5, len(deploy_locations))
            random_options = random.sample(deploy_locations, num_samples)
            
            
            best_location, is_landlocked = self.least_damage_spawn_location(game_state, random_options)
            
            if best_location:
                if is_landlocked:
                    
                    game_state.attempt_spawn(DEMOLISHER, best_location, 1000)
                else:
                    
                    game_state.attempt_spawn(SCOUT, best_location, 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        Evaluates paths. Separates valid paths (reach the enemy edge) from 
        landlocked paths (end early at a wall). Returns the best location and 
        a boolean indicating if it is forced to use a landlocked path.
        """
        enemy_edges = game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT) + \
                      game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT)
                      
        valid_options = []
        valid_damages = []
        
        landlocked_options = []
        landlocked_damages = []
        
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            
            
            if path[-1] in enemy_edges:
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
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()