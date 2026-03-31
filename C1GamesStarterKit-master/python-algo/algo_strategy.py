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
        
        self.last_turn_structures = {}
        self.damage_heatmap = {}
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.suppress_warnings(True)
        self.starter_strategy(game_state)
        game_state.submit_turn()

    def starter_strategy(self, game_state):
        """ Final User Blueprint: 6 Turrets, Upgraded Supports, Heatmap Walls, Scout Pulse ONLY """
        self.update_heatmap(game_state)
        self.build_initial_setup(game_state)
        self.build_later_defenses(game_state)
        self.scout_pulse_offense(game_state)
        self.build_reactive_defense(game_state)

    def update_heatmap(self, game_state):
        """ Tracks structural losses to know where the enemy is attacking """
        current_structures = {}
        for x in range(28):
            for y in range(14):
                loc = [x, y]
                unit = game_state.contains_stationary_unit(loc)
                if unit:
                    current_structures[(x, y)] = unit.unit_type

        
        for loc, unit_type in self.last_turn_structures.items():
            if loc not in current_structures:
                x, y = loc
                self.damage_heatmap[x] = self.damage_heatmap.get(x, 0) + 10 

        for location in self.scored_on_locations:
            x = location[0]
            self.damage_heatmap[x] = self.damage_heatmap.get(x, 0) + 5

        self.last_turn_structures = current_structures
        
        
        for x in list(self.damage_heatmap.keys()):
            self.damage_heatmap[x] *= 0.7  

    def build_initial_setup(self, game_state):
        
        supports = [[12, 12], [15, 12]]
        for loc in supports:
            if not game_state.contains_stationary_unit(loc) and game_state.get_resource(SP) >= 4:
                game_state.attempt_spawn(SUPPORT, [loc])
        for loc in supports:
            unit = game_state.contains_stationary_unit(loc)
            if unit and unit.unit_type == SUPPORT and not unit.upgraded and game_state.get_resource(SP) >= 4:
                game_state.attempt_upgrade([loc])

        
        walls = [[11, 12], [11, 13], [13, 13], [14, 13], [16, 13], [16, 12]]
        for loc in walls:
            if not game_state.contains_stationary_unit(loc) and game_state.get_resource(SP) >= 2:
                game_state.attempt_spawn(WALL, [loc])

        
        turrets = [[0, 13], [5, 10], [9, 13], [18, 13], [22, 10], [27, 13]]
        for loc in turrets:
            if not game_state.contains_stationary_unit(loc) and game_state.get_resource(SP) >= 3:
                game_state.attempt_spawn(TURRET, [loc])

    def build_later_defenses(self, game_state):
        
        initial_walls = [[11, 12], [11, 13], [13, 13], [14, 13], [16, 13], [16, 12]]
        for loc in initial_walls:
            unit = game_state.contains_stationary_unit(loc)
            if unit and unit.unit_type == WALL and not unit.upgraded and game_state.get_resource(SP) >= 1:
                game_state.attempt_upgrade([loc])
                
        
        open_frontline_xs = []
        for x in range(1, 27):
            loc = [x, 13]
            if not game_state.contains_stationary_unit(loc):
                open_frontline_xs.append(x)
                
        
        open_frontline_xs.sort(key=lambda x: self.damage_heatmap.get(x, 0), reverse=True)
        
        for x in open_frontline_xs:
            loc = [x, 13]
            
            if self.damage_heatmap.get(x, 0) > 0 or game_state.get_resource(SP) > 15:
                if game_state.get_resource(SP) >= 3:
                    game_state.attempt_spawn(WALL, [loc])
                    game_state.attempt_upgrade([loc])

    def scout_pulse_offense(self, game_state):
        """ The Flank Pulse: Waits for 6 MP, then launches a massive Scout wave NO INTERCEPTORS """
        current_mp = game_state.get_resource(MP)
        
        
        if current_mp >= 6:
            flank_options = [[1, 12], [26, 12], [2, 11], [25, 11]]
            valid_flanks = self.filter_blocked_locations(flank_options, game_state)
            
            if valid_flanks:
                
                best_flank = self.least_damage_spawn_location(game_state, valid_flanks)
                num_scouts = int(current_mp)
                
                
                if num_scouts > 0:
                    game_state.attempt_spawn(SCOUT, best_flank, num_scouts)

    def build_reactive_defense(self, game_state):
        """ Plugs breaches with Upgraded Walls immediately """
        for location in self.scored_on_locations:
            build_location = [location[0], location[1]+1]
            if not game_state.contains_stationary_unit(build_location) and game_state.get_resource(SP) >= 3:
                game_state.attempt_spawn(WALL, build_location)
                game_state.attempt_upgrade([build_location])

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def least_damage_spawn_location(self, game_state, location_options):
        damages = []
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            if path:
                for path_location in path:
                    damage += len(game_state.get_attackers(path_location, 0)) * 6 
            damages.append(damage if path else float('inf'))
            
        if not damages:
            return location_options[0]
        return location_options[damages.index(min(damages))]

    def on_action_frame(self, turn_string):
        state = json.loads(turn_string)
        events = state.get("events", {})
        for breach in events.get("breach", []):
            if breach[4] != 1: 
                self.scored_on_locations.append(breach[0])

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()