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

    def on_turn(self, turn_state):
        try:
            game_state = gamelib.GameState(self.config, turn_state)
            gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
            game_state.suppress_warnings(True)

            self.starter_strategy(game_state)
            game_state.submit_turn()
        except Exception as e:
            gamelib.debug_write('CRITICAL ERROR in on_turn: {}'.format(e))

    def starter_strategy(self, game_state):
        self.maintain_and_build_defenses(game_state)
        self.build_reactive_defense(game_state)
        self.dynamic_offense(game_state)

    def maintain_and_build_defenses(self, game_state):
        self.frontline_gaps = []
        
        
        
        anchors = [0, 27, 4, 23, 8, 19, 12, 15]
        
        fillers = [2, 25, 6, 21, 10, 17]
        
        remaining = [i for i in range(28) if i not in anchors + fillers + [13, 14]]
        
        
        build_order = anchors + fillers + remaining
        
        for x in build_order:
            
            dist_from_edge = x if x < 14 else 27 - x
            target_y = 13 if dist_from_edge % 2 == 0 else 12
            loc = [x, target_y]
            
            if game_state.contains_stationary_unit(loc):
                units = game_state.game_map[tuple(loc)]
                if units and units[0].health < 30:
                    
                    if game_state.get_resource(SP) >= 3:
                        game_state.attempt_spawn(TURRET, [[x, 11]])
            else:
                if game_state.get_resource(SP) >= 3:
                    game_state.attempt_spawn(TURRET, [loc])
                else:
                    
                    
                    if x in anchors:
                        self.frontline_gaps.append(x)

        
        if game_state.get_resource(SP) >= 4:
            game_state.attempt_spawn(SUPPORT, [[13, 11], [14, 11]])

    def dynamic_offense(self, game_state):
        current_mp = game_state.get_resource(MP)
        
        
        if len(self.frontline_gaps) > 2 and current_mp >= 1:
            edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + \
                    game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
            deploy_options = self.filter_blocked_locations(edges, game_state)
            if deploy_options:
                game_state.attempt_spawn(INTERCEPTOR, deploy_options[0], 1)
                game_state.attempt_spawn(SCOUT, deploy_options[0], 1000)
                    
        
        elif current_mp >= 6:
            all_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + \
                        game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
            
            deploy_options = self.filter_blocked_locations(all_edges, game_state)
            if deploy_options:
                best_loc = self.least_damage_spawn_location(game_state, deploy_options)
                
                game_state.attempt_spawn(SCOUT, best_loc, 1000)

    def build_reactive_defense(self, game_state):
        for location in self.scored_on_locations:
            if game_state.get_resource(SP) >= 3:
                build_location = [location[0], 11]
                if game_state.game_map.in_arena_bounds(build_location):
                    game_state.attempt_spawn(TURRET, build_location)

    def filter_blocked_locations(self, locations, game_state):
        return [loc for loc in locations if not game_state.contains_stationary_unit(loc)]

    def least_damage_spawn_location(self, game_state, location_options):
        damages = []
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            if not path:
                damages.append(9999)
                continue
            damage = 0
            for path_location in path:
                
                damage += len(game_state.get_attackers(path_location, 0))
            damages.append(damage)
        
        if not damages: return location_options[0]
        return location_options[damages.index(min(damages))]

    def on_action_frame(self, turn_string):
        try:
            state = json.loads(turn_string)
            events = state.get("events", {})
            breaches = events.get("breach", [])
            for breach in breaches:
                if breach[4] == 2:
                    self.scored_on_locations.append(breach[0])
        except:
            pass

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()