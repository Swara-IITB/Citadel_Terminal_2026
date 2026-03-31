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

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.suppress_warnings(True)
        self.starter_strategy(game_state)
        game_state.submit_turn()

    def starter_strategy(self, game_state):
        """ The Dynamic Engine: Adaptive Battery, Sieve Expansion, and Path-Scored Swarms """
        self.build_dynamic_battery(game_state)
        self.build_dynamic_sieve(game_state)
        self.dynamic_shielded_offense(game_state)

    def build_dynamic_battery(self, game_state):
        """
        Dynamically maintains a cluster of Supports in a designated 'safe zone'.
        It checks if they exist, and builds/upgrades them if SP allows.
        """
        
        battery_zone = [[7, 11], [6, 11], [7, 10]]
        
        for loc in battery_zone:
            
            unit = game_state.contains_stationary_unit(loc)
            if not unit:
                if game_state.get_resource(SP) >= 4:
                    game_state.attempt_spawn(SUPPORT, [loc])
            
            
            unit = game_state.contains_stationary_unit(loc)
            if unit and unit.unit_type == SUPPORT and not unit.upgraded:
                if game_state.get_resource(SP) >= 4:
                    game_state.attempt_upgrade([loc])

    def build_dynamic_sieve(self, game_state):
        """
        Generates the Turret arc mathematically. Starts from the center 
        and expands outward, skipping tiles to create a breathable sieve.
        """
        center_x = 13
        
        
        left_xs = list(range(center_x - 1, -1, -3))  
        right_xs = list(range(center_x + 2, 28, 3))  
        
        target_frontline_xs = []
        for l, r in zip(left_xs, right_xs):
            target_frontline_xs.extend([l, r])
            
        
        for x in target_frontline_xs:
            loc = [x, 13]
            if not game_state.contains_stationary_unit(loc) and game_state.get_resource(SP) >= 3:
                game_state.attempt_spawn(TURRET, [loc])

        
        left_xs_back = list(range(center_x - 2, -1, -3))
        right_xs_back = list(range(center_x + 3, 28, 3))
        
        target_backline_xs = []
        for l, r in zip(left_xs_back, right_xs_back):
            target_backline_xs.extend([l, r])

        for x in target_backline_xs:
            loc = [x, 12]
            
            if loc in [[7, 11], [6, 11], [7, 10], [6, 12], [7, 12]]: 
                continue
            if not game_state.contains_stationary_unit(loc) and game_state.get_resource(SP) >= 3:
                game_state.attempt_spawn(TURRET, [loc])

    def dynamic_shielded_offense(self, game_state):
        """
        The Path-Scoring Engine: Simulates every valid edge, finds the path 
        that intersects the highest number of friendly Support shields, and swarms it.
        """
        current_mp = game_state.get_resource(MP)
        
        
        if current_mp >= 8:
            
            my_supports = []
            for x in range(28):
                for y in range(14):
                    loc = [x, y]
                    unit = game_state.contains_stationary_unit(loc)
                    if unit and unit.unit_type == SUPPORT:
                        my_supports.append(unit)

            
            edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + \
                    game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
            valid_edges = self.filter_blocked_locations(edges, game_state)

            best_spawn_loc = None
            max_shield_score = -1

            
            if valid_edges:
                for edge in valid_edges:
                    path = game_state.find_path_to_edge(edge)
                    shield_score = 0
                    
                    if path:
                        for step in path:
                            
                            for support in my_supports:
                                
                                dist = math.sqrt((step[0] - support.x)**2 + (step[1] - support.y)**2)
                                
                                if dist <= 8: 
                                    shield_score += 1
                                    
                    
                    if shield_score > max_shield_score:
                        max_shield_score = shield_score
                        best_spawn_loc = edge

                
                if not best_spawn_loc:
                    best_spawn_loc = valid_edges[0]

                
                num_scouts = int(current_mp)
                if num_scouts > 0:
                    game_state.attempt_spawn(SCOUT, best_spawn_loc, num_scouts)

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()