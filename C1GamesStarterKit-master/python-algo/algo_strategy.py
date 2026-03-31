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
        """ Read in config and perform any initial setup here """
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
        """ This function is called every turn with the game state wrapper """
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.suppress_warnings(True)

        self.starter_strategy(game_state)

        game_state.submit_turn()

    def starter_strategy(self, game_state):
        """ The Adaptive Engine: Sieve, Bridge, Backup, and Swarm """
        self.adaptive_bridge_and_swarm(game_state)
        self.build_reactive_defense(game_state)

    def adaptive_bridge_and_swarm(self, game_state):
        self.frontline_gaps = []
        
        
        
        for x in range(28):
            loc = [x, 13]
            unit = game_state.contains_stationary_unit(loc)
            if unit:
                
                threshold = 72 if unit.unit_type == WALL else 42
                if unit.health < threshold:
                    backup_loc = [x, 12]
                    
                    if not game_state.contains_stationary_unit(backup_loc) and x not in [13, 14]:
                        if game_state.get_resource(SP) >= 3:
                            game_state.attempt_spawn(WALL, [backup_loc])
                            game_state.attempt_upgrade([backup_loc])
            else:
                
                if x not in [13, 14]:
                    self.frontline_gaps.append(x)

        
        
        anchors = [0, 5, 10, 17, 22, 27]
        for x in anchors:
            loc = [x, 13]
            if not game_state.contains_stationary_unit(loc) and game_state.get_resource(SP) >= 3:
                game_state.attempt_spawn(TURRET, [loc])
                if x in self.frontline_gaps: self.frontline_gaps.remove(x)

        
        for x in range(28):
            if x in [13, 14] or x in anchors: continue
            loc = [x, 13]
            if not game_state.contains_stationary_unit(loc) and game_state.get_resource(SP) >= 3:
                game_state.attempt_spawn(WALL, [loc])
                game_state.attempt_upgrade([loc])
                if x in self.frontline_gaps: self.frontline_gaps.remove(x)

        
        current_mp = game_state.get_resource(MP)
        
        
        if len(self.frontline_gaps) > 0 and current_mp >= 3:
            avg_gap_x = sum(self.frontline_gaps) / len(self.frontline_gaps)
            edge_type = game_state.game_map.BOTTOM_LEFT if avg_gap_x < 14 else game_state.game_map.BOTTOM_RIGHT
            edges = game_state.game_map.get_edge_locations(edge_type)
            deploy_options = self.filter_blocked_locations(edges, game_state)
            
            if deploy_options:
                spawn_loc = deploy_options[len(deploy_options)//2]
                game_state.attempt_spawn(INTERCEPTOR, spawn_loc, 1)
                
                if game_state.get_resource(MP) > 0:
                    game_state.attempt_spawn(SCOUT, spawn_loc, game_state.get_resource(MP))

        
        elif len(self.frontline_gaps) == 0 and current_mp >= 6:
            all_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + \
                        game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
            deploy_options = self.filter_blocked_locations(all_edges, game_state)
            
            if deploy_options:
                best_loc = self.least_damage_spawn_location(game_state, deploy_options)
                
                game_state.attempt_spawn(DEMOLISHER, best_loc, 1)
                game_state.attempt_spawn(SCOUT, best_loc, 1000)

    def build_reactive_defense(self, game_state):
        for location in self.scored_on_locations:
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, build_location)

    def filter_blocked_locations(self, locations, game_state):
        return [loc for loc in locations if not game_state.contains_stationary_unit(loc)]

    def least_damage_spawn_location(self, game_state, location_options):
        damages = []
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            if path:
                for path_location in path:
                    
                    damage += len(game_state.get_attackers(path_location, 0)) * 6 
            damages.append(damage if path else float('inf'))
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