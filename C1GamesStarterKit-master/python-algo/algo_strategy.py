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
        
        
        self.loss_heatmap = {} 
        self.current_structures = {} 
        self.INTERCEPT_THRESHOLD = 3 

    def on_turn(self, turn_state):
        """ This function is called every turn with the game state wrapper """
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.suppress_warnings(True)
        self.starter_strategy(game_state)
        game_state.submit_turn()

    def starter_strategy(self, game_state):
        """ The Smart Aegis Strategy: Upgraded Sieve with Reactive Interceptor """
        self.build_upgraded_sieve(game_state)
        self.build_reactive_defense(game_state)
        self.heatmap_interceptor_defense(game_state)
        self.dynamic_shielded_offense(game_state)

    def build_upgraded_sieve(self, game_state):
        """
        Builds and updates a defensive sieve based on the annotated plan.
        Turn 1: Drops base setup with upgraded supports (38 SP total).
        Subsequent turns: Prioritizes wall upgrades, then adds turrets.
        """
        
        anchors = [1, 9, 18, 26]
        turrets_front = [3, 7, 11, 14, 16, 20, 24]
        supports = [[12, 12], [15, 12]]
        
        
        if game_state.turn_number == 0:
            
            game_state.attempt_spawn(SUPPORT, supports)
            
            game_state.attempt_upgrade(supports)
            
            turret_coords = [[x, 13] for x in anchors]
            game_state.attempt_spawn(TURRET, turret_coords)
            
            wall_coords = [[x, 13] for x in turrets_front]
            game_state.attempt_spawn(WALL, wall_coords)
        
        
        else:
            
            game_state.attempt_spawn(SUPPORT, supports)
            game_state.attempt_upgrade(supports)

            
            turret_coords = [[x, 13] for x in anchors]
            game_state.attempt_spawn(TURRET, turret_coords)
            
            
            wall_coords = [[x, 13] for x in turrets_front]
            game_state.attempt_spawn(WALL, wall_coords)

            
            
            
            for x in turrets_front:
                loc = [x, 13]
                unit = game_state.contains_stationary_unit(loc)
                if unit and unit.unit_type == WALL and not unit.upgraded:
                    if game_state.get_resource(SP) >= 1:
                        game_state.attempt_upgrade([loc])

            
            turrets_back = [[4, 12], [8, 12], [19, 12], [23, 12]]
            if game_state.get_resource(SP) >= 3:
                game_state.attempt_spawn(TURRET, turrets_back)

    def heatmap_interceptor_defense(self, game_state):
        """
        Tracks structure losses to build a heatmap and deploys an interceptor to the "hottest" nearby region.
        """
        
        new_structures = {}
        for x in range(28):
            for y in range(14):
                loc = [x, y]
                unit = game_state.contains_stationary_unit(loc)
                if unit:
                    new_structures[(x, y)] = unit

        
        for loc, unit in self.current_structures.items():
            if loc not in new_structures:
                x, y = loc
                
                
                for nearby_x in range(x - 2, x + 3):
                    if 0 <= nearby_x < 28:
                        self.loss_heatmap[nearby_x] = self.loss_heatmap.get(nearby_x, 0) + 1

        
        self.current_structures = new_structures
        for x in self.loss_heatmap:
            self.loss_heatmap[x] = max(0, self.loss_heatmap[x] - 0.25) 

        
        
        if game_state.get_resource(MP) >= 3:
            try:
                
                edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + \
                        game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
                deploy_options = self.filter_blocked_locations(edges, game_state)
                
                
                for edge in deploy_options:
                    x = edge[0]
                    nearby_loss_count = sum(self.loss_heatmap.get(nx, 0) for nx in range(x - 2, x + 3))
                    if nearby_loss_count >= self.INTERCEPT_THRESHOLD:
                        game_state.attempt_spawn(INTERCEPTOR, edge, 1)
                        
                        for nx in range(x - 2, x + 3):
                            self.loss_heatmap[nx] = 0
                        break 
            except Exception as e:
                gamelib.debug_write(f"Heatmap Interceptor error: {e}")

    def dynamic_shielded_offense(self, game_state):
        """
        Simulates all paths and sends a massive pulse through the one with the highest shield score.
        """
        current_mp = game_state.get_resource(MP)
        
        
        if current_mp >= 8:
            try:
                
                edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + \
                        game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
                valid_edges = self.filter_blocked_locations(edges, game_state)
                
                best_location = None
                max_shield_score = -1

                if valid_edges:
                    for location in valid_edges:
                        path = game_state.find_path_to_edge(location)
                        shield_score = 0
                        
                        if path:
                            for path_location in path:
                                
                                for support in [[12, 12], [15, 12]]:
                                    
                                    dist = math.sqrt((path_location[0] - support[0])**2 + (path_location[1] - support[1])**2)
                                    if dist <= 12: 
                                        shield_score += 1
                                        
                        
                        if shield_score > max_shield_score:
                            max_shield_score = shield_score
                            best_location = location
                
                
                if not best_location:
                    best_location = [13, 0] 

                
                game_state.attempt_spawn(SCOUT, best_location, 1000)
            except Exception as e:
                gamelib.debug_write(f"Dynamic offence simulation error: {e}")

    def build_reactive_defense(self, game_state):
        """ Build upgraded walls to plug holes if scored upon. """
        for location in self.scored_on_locations:
            build_location = [location[0], location[1]+1]
            if not game_state.contains_stationary_unit(build_location):
                if game_state.get_resource(SP) >= 3:
                    game_state.attempt_spawn(WALL, build_location)
                    game_state.attempt_upgrade(build_location)

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
        """ Action frame processor to track opponent breaches. """
        state = json.loads(turn_string)
        events = state.get("events", {})
        for breach in events.get("breach", []):
            if breach[4] != 1: 
                self.scored_on_locations.append(breach[0])

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()