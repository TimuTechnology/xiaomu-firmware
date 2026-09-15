from brain.tm_brain_model import TmBrainModel
import numpy as np
import time
import json

from robot_interfaces.msg import Emotion
import brain.robot_sequence as sq 

COMMAND_DO_HIS = 'do_his'
COMMAND_CANCEL_HIS = 'cancel_his'
COMMAND_DO_GAME = 'do_game'
COMMAND_CANCEL_GAME = 'cancel_game'
COMMAND_ENTER_HEART = 'do_heart'
COMMAND_CONNECT_WIFI = 'do_wifi'
COMMAND_DIS_CONNECT_WIFI = 'do_dis_wifi'
COMMAND_DO_DANCE = 'do_dance'
COMMAND_CANCEL_DANCE = 'cancel_dance'
COMMAND_LOOK_LEFT = 'look_left'
COMMAND_LOOK_RIGHT = 'look_right'
COMMAND_TURN_LEFT = 'turn_left'
COMMAND_TURN_RIGHT = 'turn_right'
COMMAND_LOOK_UP = 'look_up'
COMMAND_LOOK_DOWN = 'look_down'
COMMAND_RAISE_RHAND = 'raise_hand'
COMMAND_INCREASE_VOLUME = 'increase_volume'
COMMAND_DECREASE_VOLUME = 'decrease_volume'
COMMAND_BIND_APP = 'bind_app'

COMMAND_DAY_OFF = 'day_off'
COMMAND_HELP_WATER = 'help_water'
COMMAND_HELP_WEED = 'help_weed'
COMMAND_QUERY_HAPPEN_FOREST = 'query_happen_forest'
COMMAND_QUERY_TEMP = 'query_temp'
COMMAND_QUERY_HUMID = 'query_humid'
COMMAND_QUERY_WAKE_TIME = 'query_wake_time'
COMMAND_QUERY_SLEEP_TIME = 'query_sleep_time'
COMMAND_QUERY_EAT_TIME = 'query_eat_time'
COMMAND_QUERY_LUNCH_TIME = 'query_lunch_time'
COMMAND_QUERY_DINNER_TIME = 'query_dinner_time'
COMMAND_QUERY_TIME_TO_FOREST = 'query_play_forest_time'
COMMAND_LOOK_HEAT_TREE = 'look_tree'
COMMAND_QUERY_TREE_STATUS = 'query_tree_status'
COMMAND_QUERY_ROBOT_STATUS = 'query_robot_status'
COMMAND_WHAT_IS_THIS = 'what_is_this'
COMMAND_DOZE_OFF = 'command_doze_off'
COMMAND_DOZE_ON = 'command_doze_on'
COMMAND_ROLEPLAY_IN = 'command_roleplay_in'
COMMAND_ROLEPLAY_OUT = 'command_roleplay_out'
COMMAND_CALIBRATION ='calibration'
COMMAND_UPGRADE ='upgrade'
COMMAND_NOW_TIME = 'command_now_time'
COMMAND_GATHER = 'command_gather'
COMMAND_GATHER_REMEMBER_ME ='command_gather_remember_me'
COMMAND_AM_I = 'command_am_i'
COMMAND_ARE_YOU = 'command_are_you'
COMMAND_TURN_ON ='command_turn_on'
COMMAND_TURN_OFF ='command_turn_off'
COMMAND_TO_CHINESE='command_to_chinese'
COMMAND_TO_ENGLISH='command_to_english'
COMMAND_TO_GERMAN='command_to_german'

COMMAND_WATCH_TV = 'watch_tv'
COMMAND_STOP_WATCH_TV = 'stop_watch_tv'
COMMAND_LISTEN_MUSIC = 'listen_music'
COMMAND_STOP_LISTEN_MUSIC = 'stop_listen_music'
COMMAND_WATCH_TV_SAY = 'watch_tv_say'
COMMAND_MUSIC_SAY = 'music_say'
COMMAND_EMAIL_BEGIN = 'email_begin'
COMMAND_SHUTDOWN = 'shutdown'
COMMAND_ACTION_RESET = 'action_reset'
COMMAND_BATTERY_STATUS = 'battery_status'

COMMAND_QUERY_TODAY_SCHEDULE = 'query_today_schedule'
COMMAND_QUERY_TOMORROW_SCHEDULE = 'query_tomorrow_schedule'

COMMAND_NOWIFI_STORY = 'nowifi_story'
COMMAND_NOWIFI_POETRY = 'nowifi_poetry'
COMMAND_NOWIFI_JOKE = 'nowifi_joke'

class RobotIntent:
    def __init__(self, msgs, embeddings, feedback, command):
        self.msgs = msgs
        self.embeddings = embeddings
        self.feedback = feedback
        self.command = command
        
class RobotIntents:
    def __init__(self, lan, logging, fb, locale, data_path):
        self.lan = lan
        self.logger = logging
        self.embedding_model = TmBrainModel(lan, logging)
        
        with open(data_path, 'r', encoding='utf-8') as f:
            json_str = f.read()
        store_en = json.loads(json_str)
        self.pre_intents  = [
            self._create_intent(store_en, locale.intent_connect_wifi, None, COMMAND_CONNECT_WIFI),
            self._create_intent(store_en, locale.intent_disconnect_wifi, None, COMMAND_DIS_CONNECT_WIFI),
            self._create_intent(store_en, locale.intent_how_bind_device, fb.feedback_answer_bind_app, None),
            self._create_intent(store_en, locale.intent_bind_device, None, COMMAND_BIND_APP),
            self._create_intent(store_en, locale.intent_ok, None, COMMAND_DO_HIS),
            self._create_intent(store_en, locale.intent_no, None, COMMAND_CANCEL_HIS),
            self._create_intent(store_en, locale.intent_play_game, fb.feedback_command_game, COMMAND_DO_GAME),
            #self._create_intent(store_en, locale.intent_have_dance, fb.feedback_command_dance, COMMAND_DO_DANCE),
            self._create_intent(store_en, locale.intent_turn_left, fb.feedback_command_turn_left, COMMAND_TURN_LEFT),
            self._create_intent(store_en, locale.intent_turn_right, fb.feedback_command_turn_right, COMMAND_TURN_RIGHT),
            self._create_intent(store_en, locale.intent_look_left, fb.feedback_command_look_left, COMMAND_LOOK_LEFT),
            self._create_intent(store_en, locale.intent_look_right, fb.feedback_command_look_right, COMMAND_LOOK_RIGHT),
            self._create_intent(store_en, locale.intent_look_up, fb.feedback_command_look_up, COMMAND_LOOK_UP),
            self._create_intent(store_en, locale.intent_look_down, fb.feedback_command_look_down, COMMAND_LOOK_DOWN),
            self._create_intent(store_en, locale.intent_raise_rhand, fb.feedback_command_raise_rhand, COMMAND_RAISE_RHAND),
            self._create_intent(store_en, locale.intent_stop_game, fb.feedback_command_game_stop, COMMAND_CANCEL_GAME),
            self._create_intent(store_en, locale.intent_stop_dance, fb.feedback_command_dance_stop, COMMAND_CANCEL_DANCE),
            self._create_intent(store_en, locale.intent_up_volume, None , COMMAND_INCREASE_VOLUME),
            self._create_intent(store_en, locale.intent_down_volume, None, COMMAND_DECREASE_VOLUME),
            self._create_intent(store_en, locale.intent_heart_forest, fb.feedback_answer_heartwood_forest, None),
            self._create_intent(store_en, locale.intent_sprite_flower, fb.feedback_answer_sprite_flower, None),
            self._create_intent(store_en, locale.intent_friend_flower, fb.feedback_answer_friendship_flower, None),
            self._create_intent(store_en, locale.intent_magic_clay, fb.feedback_answer_magic_clay, None),
            self._create_intent(store_en, locale.intent_sprite_dew, fb.feedback_answer_sprite_dew, None),
            self._create_intent(store_en, locale.intent_heart_water, fb.feedback_answer_heart_water, None),
            self._create_intent(store_en, locale.intent_purpose_water, fb.feedback_answer_watering, None),
            self._create_intent(store_en, locale.intent_purpose_weeding, fb.feedback_answer_weeding, None),
            self._create_intent(store_en, locale.intent_catch_fish, fb.feedback_answer_catch_fish, None),
            self._create_intent(store_en, locale.intent_exercise_tired, fb.feedback_answer_exercise_tiring, None),
            self._create_intent(store_en, locale.intent_what_lunch, fb.feedback_answer_lunch, None),
            self._create_intent(store_en, locale.intent_what_dinner, fb.feedback_answer_dinner, None),
            self._create_intent(store_en, locale.intent_go_foreset, fb.feedback_answer_why_to_forest, None),
            self._create_intent(store_en, locale.intent_why_books, fb.feedback_answer_why_read_book, None),
            self._create_intent(store_en, locale.intent_what_books, fb.feedback_answer_read_what_book, None),
            self._create_intent(store_en, locale.intent_can_fish, fb.feedback_answer_eat_fish, None),
            self._create_intent(store_en, locale.intent_what_language, fb.feedback_answer_languages, None),
            self._create_intent(store_en, locale.intent_how_network, fb.feedback_answer_connect_wifi, None),
            self._create_intent(store_en, locale.intent_has_fish, fb.feedback_answer_dinner_fish, None),
            self._create_intent(store_en, locale.intent_how_sick, fb.feedback_answer_why_sick, None),
            self._create_intent(store_en, locale.intent_how_2forest, fb.feedback_answer_how_to_forest, None),
            self._create_intent(store_en, locale.intent_forest_back, fb.feedback_answer_return_anytime, None),
            self._create_intent(store_en, locale.intent_flower_from, fb.feedback_answer_flower_from, None),
            self._create_intent(store_en, locale.intent_soil_from, fb.feedback_answer_soil_from, None),
            self._create_intent(store_en, locale.intent_water_from , fb.feedback_answer_drop_from, None),
            self._create_intent(store_en, locale.intent_name, fb.feedback_answer_name, None),
            self._create_intent(store_en, locale.intent_where_from, fb.feedback_answer_from_where, None),
            self._create_intent(store_en, locale.intent_can_do, fb.feedback_answer_what_can_do, None),
            self._create_intent(store_en, locale.intent_what_tree, fb.feedback_answer_heart_tree, None),
            self._create_intent(store_en, locale.intent_why_nurture, fb.feedback_answer_why_tree, None),
            self._create_intent(store_en, locale.intent_help_tree, fb.feedback_answer_user_help_tree, None),
            self._create_intent(store_en, locale.intent_how_recover, fb.feedback_answer_help_recover, None),
            self._create_intent(store_en, locale.intent_help_water, None, COMMAND_HELP_WATER),
            self._create_intent(store_en, locale.intent_help_weed, None, COMMAND_HELP_WEED),
            self._create_intent(store_en, locale.intent_care_me, fb.feedback_answer_care_user, None),
            self._create_intent(store_en, locale.intent_work_finish, fb.feedback_work_finish, None),
            self._create_intent(store_en, locale.intent_how_in_forest, None, COMMAND_QUERY_HAPPEN_FOREST),
            self._create_intent(store_en, locale.intent_what_temp, None, COMMAND_QUERY_TEMP),
            self._create_intent(store_en, locale.intent_what_humid, None, COMMAND_QUERY_HUMID),
            self._create_intent(store_en, locale.intent_when_wake, None, COMMAND_QUERY_WAKE_TIME),
            self._create_intent(store_en, locale.intent_when_sleep, None, COMMAND_QUERY_SLEEP_TIME),
            self._create_intent(store_en, locale.intent_when_lunch, None, COMMAND_QUERY_LUNCH_TIME),
            self._create_intent(store_en, locale.intent_when_dinner, None, COMMAND_QUERY_DINNER_TIME),
            self._create_intent(store_en, locale.intent_when_2forest, None, COMMAND_QUERY_TIME_TO_FOREST),
            self._create_intent(store_en, locale.intent_see_tree, None, COMMAND_LOOK_HEAT_TREE),
            self._create_intent(store_en, locale.intent_tree_status, None, COMMAND_QUERY_TREE_STATUS),
            self._create_intent(store_en, locale.intent_do_what, None, COMMAND_QUERY_ROBOT_STATUS),
            self._create_intent(store_en, locale.intent_what_is, fb.feedback_command_what_this, COMMAND_WHAT_IS_THIS),
            self._create_intent(store_en, locale.intent_what_time, None, COMMAND_NOW_TIME),
            self._create_intent(store_en, locale.intent_who_I, None, COMMAND_AM_I),
            self._create_intent(store_en, locale.intent_who_you, None, COMMAND_ARE_YOU),
            self._create_intent(store_en, locale.intent_hello, fb.feedback_answer_hello, None),
            self._create_intent(store_en, locale.intent_hello_moning, fb.feedback_answer_hello_moning, None),
            self._create_intent(store_en, locale.intent_hello_noon, fb.feedback_answer_hello_noon, None),
            self._create_intent(store_en, locale.intent_hello_night, fb.feedback_answer_hello_night, None),
            self._create_intent(store_en, locale.intent_hello_goodnight, fb.feedback_answer_hello_goodnight, None),
            self._create_intent(store_en, locale.intent_hello_byb, fb.feedback_answer_hello_byb, None),
            self._create_intent(store_en, locale.intent_hello_chat, fb.feedback_answer_hello_chat, None),
            self._create_intent(store_en, locale.intent_hello_whether, fb.feedback_answer_hello_whether, None),
            self._create_intent(store_en, locale.intent_comp_whiney, fb.feedback_answer_comp_whiney, None),
            self._create_intent(store_en, locale.intent_comp_lonely, fb.feedback_answer_comp_lonely, None),
            self._create_intent(store_en, locale.intent_comp_press, fb.feedback_answer_comp_press, None),
            self._create_intent(store_en, locale.intent_comp_ring, fb.feedback_answer_comp_ring, None),
            self._create_intent(store_en, locale.intent_comp_confidence, fb.feedback_answer_comp_confidence, None),
            self._create_intent(store_en, locale.intent_comp_tired, fb.feedback_answer_comp_tired, None),
            self._create_intent(store_en, locale.intent_comp_giveup, fb.feedback_answer_comp_giveup, None),
            self._create_intent(store_en, locale.intent_comp_think, fb.feedback_answer_comp_think, None),
            self._create_intent(store_en, locale.intent_comp_conflict, fb.feedback_answer_comp_conflict, None),
            self._create_intent(store_en, locale.intent_old_music, fb.feedback_answer_old_music, None),
            self._create_intent(store_en, locale.intent_old_boring, fb.feedback_answer_old_boring, None),
            self._create_intent(store_en, locale.intent_old_sick, fb.feedback_answer_old_sick, None),
            self._create_intent(store_en, locale.intent_child_homework, fb.feedback_answer_child_homework, None),
            self._create_intent(store_en, locale.intent_child_bully, fb.feedback_answer_child_bully, None),
            self._create_intent(store_en, locale.intent_oper_volum, fb.feedback_answer_oper_volum, None),
            self._create_intent(store_en, locale.intent_oper_lang, fb.feedback_answer_oper_lang, None),
            self._create_intent(store_en, locale.intent_oper_light, fb.feedback_answer_oper_light, None),
            self._create_intent(store_en, locale.intent_oper_lock, fb.feedback_answer_oper_lock, None),
            self._create_intent(store_en, locale.intent_oper_charge, fb.feedback_answer_oper_charge, None),
            self._create_intent(store_en, locale.intent_q_happy, fb.feedback_answer_q_happy, None),
            self._create_intent(store_en, locale.intent_q_can, fb.feedback_answer_q_can, None),
            self._create_intent(store_en, locale.intent_q_like, fb.feedback_answer_q_like, None),
            self._create_intent(store_en, locale.intent_q_eat, fb.feedback_answer_q_eat, None),
            self._create_intent(store_en, locale.intent_life_earlybed, fb.feedback_answer_life_earlybed, None),
            self._create_intent(store_en, locale.intent_life_sleepless, fb.feedback_answer_life_sleepless, None),
            self._create_intent(store_en, locale.intent_life_eat, fb.feedback_answer_life_eat, None),
            self._create_intent(store_en, locale.intent_life_sitlong, fb.feedback_answer_life_sitlong, None),

            self._create_intent(store_en, locale.intent_listen_sleep, fb.feedback_answer_touch, None),
            self._create_intent(store_en, locale.intent_why_dead, fb.feedback_answer_pet, None),
            self._create_intent(store_en, locale.intent_can_pets, fb.feedback_answer_know_pet, None),
            self._create_intent(store_en, locale.intent_how_emotion, fb.feedback_answer_know_emotion, None),
            self._create_intent(store_en, locale.intent_will_smater, fb.feedback_answer_clever, None),
            self._create_intent(store_en, locale.intent_can_run, fb.feedback_answer_run, None),
            self._create_intent(store_en, locale.intent_exercise_everyday, fb.feedback_answer_sport, None),
            self._create_intent(store_en, locale.intent_can_dialects, fb.feedback_answer_language, None),
            self._create_intent(store_en, locale.intent_like_book, fb.feedback_answer_read, None),
            self._create_intent(store_en, locale.intent_like_which_book, fb.feedback_answer_book, None),
            self._create_intent(store_en, locale.intent_why_earth, fb.feedback_answer_come_earth, None),

            self._create_intent(store_en, locale.intent_keep_quiet, None, COMMAND_DOZE_OFF),
            self._create_intent(store_en, locale.intent_wake_up, None, COMMAND_DOZE_ON),
            self._create_intent(store_en, locale.intent_calibrate_motor, None, COMMAND_CALIBRATION),
            self._create_intent(store_en, locale.intent_upgrade_system, None, COMMAND_UPGRADE),
            self._create_intent(store_en, locale.intent_remmber_me, None, COMMAND_GATHER_REMEMBER_ME),
            self._create_intent(store_en, locale.intent_turn_on_light, None, COMMAND_TURN_ON),
            self._create_intent(store_en, locale.intent_turn_off_light, None, COMMAND_TURN_OFF),
            self._create_intent(store_en, locale.intent_switch_2_chinese , None, COMMAND_TO_CHINESE),
            self._create_intent(store_en, locale.intent_switch_2_english, None, COMMAND_TO_ENGLISH),
            self._create_intent(store_en, locale.intent_switch_2_de, None, COMMAND_TO_GERMAN),

            self._create_intent(store_en, locale.intent_role_play, None, COMMAND_ROLEPLAY_IN),
            self._create_intent(store_en, locale.intent_stop_role, None, COMMAND_ROLEPLAY_OUT),

            self._create_intent(store_en, locale.intent_watch_tv, None, COMMAND_WATCH_TV),
            self._create_intent(store_en, locale.intent_stop_tv, None, COMMAND_STOP_WATCH_TV),
            self._create_intent(store_en, locale.intent_listen_music, None, COMMAND_LISTEN_MUSIC),
            self._create_intent(store_en, locale.intent_stop_music, None, COMMAND_STOP_LISTEN_MUSIC),
            self._create_intent(store_en, locale.intent_query_schedule_today, None, COMMAND_QUERY_TODAY_SCHEDULE),
            self._create_intent(store_en, locale.intent_query_schedule_tomorrow, None, COMMAND_QUERY_TOMORROW_SCHEDULE),

            self._create_intent(store_en, locale.intent_i_happy, None, sq.HappySequence(store_en, locale, fb)),
            self._create_intent(store_en, locale.intent_i_sad, None, sq.SadSequence(store_en, locale, fb)),
            self._create_intent(store_en, locale.intent_email, None, COMMAND_EMAIL_BEGIN),
            self._create_intent(store_en, locale.intent_shutdown, None, COMMAND_SHUTDOWN),
            self._create_intent(store_en, locale.intent_action_reset, None, COMMAND_ACTION_RESET),
            self._create_intent(store_en, locale.intent_battery_status, None, COMMAND_BATTERY_STATUS),
        ]

        self.no_wifi_intents = [
            self._create_intent(store_en, locale.intent_nowifi_story, fb.feedback_answer_nowifi_story_pre, COMMAND_NOWIFI_STORY),
            self._create_intent(store_en, locale.intent_nowifi_poetry, fb.feedback_answer_nowifi_poetry_pre, COMMAND_NOWIFI_POETRY),
            self._create_intent(store_en, locale.intent_nowifi_nowifi, fb.feedback_answer_nowifi_nowifi, None),
            self._create_intent(store_en, locale.intent_nowifi_noanswer, fb.feedback_answer_nowifi_noanswer, None),
            self._create_intent(store_en, locale.intent_nowifi_joke, fb.feedback_answer_nowifi_joke_pre, COMMAND_NOWIFI_JOKE),
        ]
    
    def _create_intent(self, store_en, msgs, feedback, command):
        embeddings = []
        
        for item in msgs:
            embeddings.append(store_en[item])
        
        return RobotIntent(msgs, embeddings, feedback, command)
    
        
    def _is_match(self, intent, another_embedding):
        most = -1
        
        for emb in intent.embeddings:
            cos = round(self.embedding_model.cosine_similarity(emb, another_embedding), 2)
            #self.logger.info('cal cos:"%s"' % cos)
            if cos > 0.8 and cos > most:
                most = cos
        if most > 0:
            return most
    
    def embedding_another(self, text):
        return self.embedding_model.embedding(text)
    
    def get_most_intent(self, another_emb):
        cap = 0
        most_intent = None
        start = time.time()
        for intent in self.pre_intents:
            re= self._is_match(intent, another_emb)
            if not re:
                continue
            if re > cap:
                most_intent = intent
                cap = re
        if most_intent:
            self.logger.info('matched intent: %s' % most_intent.msgs[0])
        return most_intent

    def get_most_nowifi_intent(self, another_emb):
        cap = 0
        most_intent = None
        start = time.time()
        for intent in self.no_wifi_intents:
            re= self._is_match(intent, another_emb)
            if not re:
                continue
            if re > cap:
                most_intent = intent
                cap = re
        if most_intent:
            self.logger.info('matched nowifi intent: %s' % most_intent.msgs[0])
        return most_intent
    
    def release(self):
        self.embedding_model.release()

    def get_intent(self, msgs):
        a_intent = None
        for intent in self.pre_intents:
            if intent.msgs[0] == msgs:
                return intent
        return a_intent

    def create_day_off_int(self):
        return RobotIntent(None, None, None, COMMAND_DAY_OFF)

    def create_gather(self):
        return RobotIntent(None, None, None, COMMAND_GATHER)

    def create_watch_tv_say(self):
        return RobotIntent(None, None, None, COMMAND_WATCH_TV_SAY)

    def create_music_say(self):
        return RobotIntent(None, None, None, COMMAND_MUSIC_SAY)

    def create_disconnect_wifi(self):
        return RobotIntent(None, None, None, COMMAND_DIS_CONNECT_WIFI)

    def create_upgrade(self):
        return RobotIntent(None, None, None, COMMAND_UPGRADE)

    def create_shutdown(self):
        return RobotIntent(None, None, None, COMMAND_SHUTDOWN)
