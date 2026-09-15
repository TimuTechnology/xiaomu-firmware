import time

class RobotStatus:
    def __init__(self):
        # 闲下来动作 1是5分钟 2是15分钟 3是30分钟
        self.enjoy_type = 0
        self.last_busy_time = time.time()
        #
        self.last_enjoy_time_5 = 0
        self.last_enjoy_time_15 = 0
        self.last_enjoy_time_30 = 0
        #
        self.last_emotion_to_intents = 0
        self.last_happy_emotion_time = 0
        self.happy_count = 0
        self.last_sad_emotion_time = 0
        self.sad_count = 0
        # 注视 频次
        self.frontal = {}
        self.last_frontal_time = 0
        self.last_frontal_act_time = 0
        #
        self.last_sleep3_time = 0

    def set_last_busy_time(self,cur):
        self.last_busy_time = cur
        self.last_enjoy_time_30 = 0
        self.last_enjoy_time_5 = 0
        self.last_enjoy_time_15 = 0

    def get_last_busy_time(self):
        return self.last_busy_time

    def set_last_enjoy_time_30(self,cur):
        self.last_enjoy_time_30 = cur

    def get_last_enjoy_time_30(self):
        return self.last_enjoy_time_30

    def set_last_enjoy_time_5(self,cur):
        self.last_enjoy_time_5 = cur
    def get_last_enjoy_time_5(self):
        return self.last_enjoy_time_5

    def set_last_enjoy_time_15(self,cur):
        self.last_enjoy_time_15 = cur
    def get_last_enjoy_time_15(self):
        return self.last_enjoy_time_15

    def set_last_emotion_to_intents_time(self, cur):
        self.last_emotion_to_intents = cur

    def get_last_emotion_to_intents_time(self):
        return self.last_emotion_to_intents

    def set_frontal(self, frontal):
        self.frontal = frontal
    def set_frontal_value(self, key,value):
        self.frontal[key] = value

    def get_enjoy_type(self):
        return self.enjoy_type
    def set_enjoy_type(self,_type):
        self.enjoy_type =   _type

    def set_last_sleep3_time(self, cur):
        self.last_sleep3_time = cur
