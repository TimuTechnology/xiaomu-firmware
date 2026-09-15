import numpy as np
import time
import random

CHARACTER_E = 1
CHARACTER_I = 2
threadshold = [
#(id,saw_ges_inter_min_time,saw_per_inter_min_time, saw_his_per_inter_min_time, touch_inter_min_time, humid_inter_min_time, temp_inter_min_time, intent_match_min, inter_to_sleep_min_time, inter_follow_per_time)
(1, 10, 5, 5, 60, 60*60, 60*60, 0.86, 2*60, 3),
(2, 30, 60, 60, 5*60, 4*60*60, 4*60*60, 0.88, 2*60, 6)

]

def get_char_ts(character):
    for ts in threadshold:
        if ts[0] == character:
            return ts
    
class RobotCharacter:
    def __init__(self, logger, character):
        self.logger = logger
        self.character = character
        ts = get_char_ts(character)
        self.ges_inter_min = ts[1]
        self.per_inter_min = ts[2]
        self.his_per_inter_min = ts[3]
        self.touch_inter_min = ts[4]
        self.humid_inter_min = ts[5]
        self.temp_inter_min = ts[6]
        self.intent_match_min = ts[7]
        self.sleep_inter_min = ts[8]
        self.follow_per_min = ts[9]
    def get_character(self):
        return self.character
    def get_ges_inter_min(self):
        return self.ges_inter_min
    def get_per_inter_min(self):
        return self.per_inter_min
    def get_his_per_inter_min(self):
        return self.his_per_inter_min
    def get_touch_inter_min(self):
        return self.touch_inter_min
    def get_humid_inter_min(self):
        return self.humid_inter_min
    def get_temp_inter_min(self):
        return self.temp_inter_min
    def get_intent_match_min(self):
        return self.intent_match_min
    def get_sleep_inter_min(self):
        return self.sleep_inter_min
    def get_follow_per_min(self):
        return self.follow_per_min
    
    
        
    
    
        
    
        
        

