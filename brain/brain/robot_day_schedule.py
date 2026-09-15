import calendar
import datetime
import json
import os
import random
import time
from datetime import timedelta

import brain.plat_api as api
import brain.robot_feedback_en
import brain.robot_feedback_zh_Hans
import holidays
import requests
from brain.plat_request import PlatRequests
from sympy import false, true

from robot_interfaces.msg import Sensor, Saw, Action, Emotion, Touch, Speak, Imu, Person, Listen, See, Servo, Led

'''
从平台拉取日程配置信息
'''
def init_time_conf_from_api(logger,data_path,token,check_wifi,host):
    logger.info("3、从平台拉取日程配置信息")
    try:
        if not token or not check_wifi:
            return None
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            "authorization": token
        }
        payload = {}
        response = requests.post(
            url     = api.robotGetTimeConf.replace("host-place-holder", host),
            headers = headers,
            json    = payload,
            timeout = 10       )
        response.raise_for_status()
        update_info = response.json()["data"]
        if update_info:
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(update_info, f, ensure_ascii=False, indent=2)  # indent使文件更易读
        return update_info
    except Exception as e:
        logger.error("拉取app的时间配置失败: %s" % e)
        return None

def local_load_user_id(logger,data_path):
    try:
        logger.info("1、local_load_user_id")
        with open(data_path, 'r', encoding='utf-8') as f:
            user_id = f.read().strip()
            logger.info("   user_id:%s" %  user_id)
            return user_id
    except FileNotFoundError:
        # 文件不存在，可以创建或进行其他处理
        with open(data_path, 'w', encoding='utf-8') as file:
            file.write("")  # 或者其他初始化操作
            return None
    except Exception as e:
        logger.error("获取本地user_id参数失败: %s" % e)
        return None
def local_load_token(logger,data_path):
    try:
        logger.info("2、local_load_token")
        with open(data_path, 'r', encoding='utf-8') as f:
            token = f.read().strip()
            logger.info("   token:%s" % token)
            return token
    except FileNotFoundError:
        # 文件不存在，可以创建或进行其他处理
        with open(data_path, 'w', encoding='utf-8') as file:
            file.write("")  # 或者其他初始化操作
            return None
    except Exception as e:
        logger.error("获取本地token参数失败: %s" % e)
        return None
def local_load_last_sick(logger,data_path):
    try:
        logger.info("7、local_load_last_sick")
        with open(data_path, 'r', encoding='utf-8') as f:
            last_sick = f.read().strip()
            logger.info("   last_sick:%s" % last_sick)
            if last_sick:
                return datetime.datetime.strptime(last_sick, '%Y-%m-%d')
        return None
    except FileNotFoundError:
        # 文件不存在，可以创建或进行其他处理
        with open(data_path, 'w', encoding='utf-8') as file:
            file.write("")  # 或者其他初始化操作
            return None
    except Exception as e:
        logger.error("获取本地本月生病日期 失败: %s" % e)
        return None
def local_load_last_day_off(logger,data_path):
    try:
        logger.info("8、local_load_last_day_off")
        with open(data_path, 'r', encoding='utf-8') as f:
            last_day_off = f.read().strip()
            logger.info("   last_day_off: %s" % last_day_off)
            if last_day_off:
                return datetime.datetime.strptime(last_day_off, '%Y-%m-%d')
        return None
    except FileNotFoundError:
        # 文件不存在，可以创建或进行其他处理
        with open(data_path, 'w', encoding='utf-8') as file:
            file.write("")  # 或者其他初始化操作
            return None
    except Exception as e:
        logger.error("获取本地本月请假日期 失败: %s" % e)
        return None
'''
加载用户的日程时间配置
'''
def local_load_time_conf(logger,data_path):
    try:
        logger.info("4、local_load_time_conf")
        with open(data_path, 'r', encoding='utf-8') as f:
            time_conf_str = f.read()
            loads = json.loads(time_conf_str)
            if not loads['getUp']:
                loads['getUp'] = "08:30:00"
            return loads
    except FileNotFoundError:
        # 文件不存在，可以创建或进行其他处理
        with open(data_path, 'w', encoding='utf-8') as file:
            init_data = {
                "getUp": "08:30:00",
                "physical": "09:00:00",
                "watering": "10:00:00",
                "noonEating": "11:00:00",
                "noontime": "12:00:00",
                "noonEnding": "14:00:00",
                "weeding": "15:00:00",
                "learning": "16:00:00",
                "playing": "17:00:00",
                "dinner": "18:00:00",
                "chatting": "19:00:00",
                "sleeping": "21:00:00",
                "weekendGetUp": "09:00:00",
                "weekendWatering": "10:00:00",
                "weekendFishBegin": "12:00:00",
                "weekendFishEnd": "14:00:00",
                "weekendWeeding": "15:00:00",
                "weekendSleeping": "22:30:00"    }
            json.dump(init_data, file, ensure_ascii=False, indent=2)  # 或者其他初始化操作
            return init_data
    except Exception as e:
        logger.error("获取时间配置失败: %s" % e)
        return None
def local_load_grow_tree_step(logger,data_path):
    try:
        logger.info("6、local_load_grow_tree_step")
        with open(data_path, 'r', encoding='utf-8') as f:
            grow_tree_step = f.read()
            return json.loads(grow_tree_step)
    except FileNotFoundError:
        # 文件不存在，可以创建或进行其他处理
        with open(data_path, 'w', encoding='utf-8') as file:
            init_data = [
                {"id": 1, "levelName": "种子", "energy": 0, "type": 1},
                {"id": 2, "levelName": "发芽", "energy": 10, "type": 1},
                {"id": 3, "levelName": "树苗", "energy": 25, "type": 1},
                {"id": 4, "levelName": "小树", "energy": 45, "type": 1},
                {"id": 5, "levelName": "大树", "energy": 75, "type": 1},
                {"id": 6, "levelName": "开花", "energy": 95, "type": 1},
                {"id": 7, "levelName": "结果", "energy": 125, "type": 1},
                {"id": 8, "levelName": "枯萎", "energy": 23, "type": 2}
            ]
            json.dump(init_data, file, ensure_ascii=False, indent=2)  # 或者其他初始化操作
            return init_data
    except Exception as e:
        logger.error("获取心灵之树配置失败: %s" % e)
        return None


def is_weekend(today):
    return today.weekday() >= 5

def is_holiday_myself(logger, today):
    holiday_list = ['2026-01-01', '2026-02-12', '2026-04-05']  # 自定义节假日列表
    return today in holiday_list

def is_holiday_api(logger, today):
    cn_holidays = holidays.China(years = today.year)
    if today in cn_holidays:
        logger.info("节假日的结果: %s " % cn_holidays[today])
        return cn_holidays[today]
    return None

def is_51holiday(logger, today):
    month = today.month
    day = today.day
    # 判断当前时间是否为hour:minute
    if month == 5 and day == 1:
        logger.info('当前时间是:五月一日,情感森林节假日')
        return True
    return false

STAT_DEFAULT = 0
STAT_GET_UP = 1
STAT_PHYSICAL = 2
STAT_WATERING = 3
STAT_NOON_EATING = 4
STAT_NOON = 5
STAT_WEEDING = 6
STAT_LEARNING = 7
STAT_PLAYING = 8
STAT_DINNER = 9
STAT_CHATTING = 10
STAT_SLEEPING = 11
STAT_WEEKEND_GETUP = 12
STAT_WEEKEND_WATERING = 13
STAT_WEEKEND_FISHING = 14
STAT_WEEKEND_WEEDING = 16
STAT_WEEKEND_SLEEPING = 17
STAT_ROLE_PLAY = 18
STAT_DAY_OFF = -1
STAT_DAY_OFF_ING = -11
STAT_SICK = -2
STAT_INTERUPT = -3
value_to_key = {"0":STAT_DEFAULT,"1":STAT_GET_UP,"2":STAT_PHYSICAL,"3":STAT_WATERING,"4":STAT_NOON_EATING,
                "5":STAT_NOON,"6":STAT_WEEDING,"7":STAT_LEARNING,"8":STAT_PLAYING,"9":STAT_DINNER,
                "10":STAT_CHATTING,"11":STAT_SLEEPING,"12":STAT_WEEKEND_GETUP,"13":STAT_WEEKEND_WATERING,
                "14":STAT_WEEKEND_FISHING,
                "16":STAT_WEEKEND_WEEDING,"17":STAT_WEEKEND_SLEEPING,"-1":STAT_DAY_OFF,"-2":STAT_SICK  }
# 离线数据上报相关
biz_type_energy = 'energy'
biz_type_reading = 'reading'
type_inc = 1
type_dec = 2
trans_type_water = 11
trans_type_water_comb = 12
trans_type_weed = 13
trans_type_weed_comb = 14
trans_type_weed_transfer = 15
trans_type_weed_drop = 16
trans_type_dialog = 17

upload_line_number = 100

long_no_water_2month = 60 * 24 * 60 * 60
long_no_water_month = 30 * 24 * 60 * 60
long_no_water_week = 7 * 24 * 60 * 60
class DaySchedule:
    def __init__(self, language,logger, root_dir,device_code,
                 speak_pub, emotion_pub, eye_pub,action_pub,
                 character,robotStatus,fb,time_split,
                 hand_action,grow_tree,
                 check_wifi, stat_to_speak_path, schedule_task_controller):
        self.speak_pub = speak_pub
        self.emotion_pub = emotion_pub
        self.eye_pub =  eye_pub
        self.action_pub = action_pub
        self.character =  character
        self.root_dir = root_dir
        self.logger = logger
        self.language = language
        self.robotStatus = robotStatus
        self.device_code = device_code
        #self.fb = brain.robot_feedback_zh if self.language == 'zh-Hans' else brain.robot_feedback_en
        self.fb = fb
        self.time_split = time_split
        self.hand_action = hand_action
        self.host = 'api.timuai.com'
        if self.language == 'zh-Hans':
            self.host = 'cnapi.timuai.com'

        self.user_id = local_load_user_id(self.logger ,self.root_dir + api.user_id_path)
        self.token = local_load_token(self.logger, self.root_dir + api.token_path)
        init_time_conf_from_api(self.logger, self.root_dir + api.time_conf_path, self.token, check_wifi,self.host)
        self.time_json = local_load_time_conf(self.logger, self.root_dir + api.time_conf_path)
        self.time_json = self.deal_time_json()
        self.grow_tree = grow_tree #self.local_load_grow_tree_info(self.root_dir + api.grow_tree_path)
        self.command_look_heat_tree_props([Emotion.EMOTION_EFFECTION_FRIEND_FLOWER, Emotion.EMOTION_EFFECTION_SPRITE_FLOWER
                                              , Emotion.EMOTION_EFFECTION_MAGIC_CLAY, Emotion.EMOTION_EFFECTION_SPRITE_DEW
                                              , Emotion.EMOTION_EFFECTION_HEART_WATER])
        self.grow_tree_step_conf =  local_load_grow_tree_step(self.logger, self.root_dir + api.grow_tree_step)

        self.sick_path = self.root_dir + api.last_sick
        self.day_off_path = self.root_dir + api.last_day_off
        self.sick_day = local_load_last_sick(self.logger, self.sick_path)
        self.day_off = local_load_last_day_off(self.logger, self.day_off_path)
        self.status_path = self.root_dir + api.robot_status
        self.work_mode = self.local_load_robot_status(self.status_path)
        self.logger.info("   self.work_mode: %s" % self.work_mode)
        self.logger.info("10、启动时检查一次token")
        self.one_day_refresh_token(check_wifi)
        self.person = None
        self.local_load_person_data(self.root_dir + api.person_data)
        self.nick = None
        self.logger.info("12、启动时获取昵称")
        self.do_nick_refresh(check_wifi)
        # 每日获取能量上限
        self.day_energy_limit = 1
        self.today_energy = 0
        # 从brain传入的看见人员情况
        self.saw_person_count = 0
        self.last_saw_per_time = 0
        # 看到人之后的邀请间隔
        self.invite_inner_min = 5 * 60
        # 运动参数
        self.last_invite_physical_time = 0
        self.cooper_physical_count = 0
        # 浇水参数
        self.today_has_water = True
        self.last_invite_water_time = 0
        self.cooper_water_count = 0
        # 除草参数
        self.today_has_weed = True
        self.last_invite_weed_time = 0
        self.cooper_weed_count = 0
        # 地图参数
        self.enter_status = 0
        self.last_enter_map_time = 0
        # 看书
        self.last_reading_time = 0
        # 钓鱼
        self.fish_num = 0
        # 生病&请假 生病和请假的时长
        self.sick_or_day_off = {'sick_flag': 0, 'sick_exp_time': 0, 'day_off_flag': 0,'day_off_exp_time': 0}
        self.sick_inner = 12 * 60 * 60
        self.chat_dia_turns = {}
        # 请假三次
        self.day_off_need_apply = 'no'
        self.day_off_apply_count = 0
        self.last_invite_day_off_time = 0
        self.check_sick_status_vari()
        self.check_day_off_status_vari()
        # 树
        self.tree_level_to_emotion = {"种子":Emotion.HEART_TREE_SEED,"发芽":Emotion.HEART_TREE_GERMINATION,
                                      "树苗":Emotion.HEART_TREE_SAPLING,"小树":Emotion.HEART_TREE_YOUNG_TREE,
                                      "大树":Emotion.HEART_TREE_BIG_TREE,"开花":Emotion.HEART_TREE_FLOWERING,
                                      "结果":Emotion.HEART_TREE_EFFECTION_FRUIT,"枯萎":Emotion.HEART_TREE_WITHER}
        #状态
        self.s_t_spk = {}
        self.load_stat_to_speak(stat_to_speak_path)
        self.stat_to_speak = {STAT_DEFAULT: [self.s_t_spk['default'],Emotion.EMOTION_USUAL], STAT_GET_UP: [self.s_t_spk['get_up'],Emotion.EMOTION_MORNING_WAKE_UP],
                                  STAT_PHYSICAL: [self.s_t_spk['physical'],Emotion.EMOTION_EXERCISING],STAT_WATERING: [self.s_t_spk['watering'],Emotion.EMOTION_WATERING],
                                  STAT_NOON_EATING: [self.s_t_spk['noon_eating'],Emotion.EMOTION_LUNCHING], STAT_NOON: [self.s_t_spk['noon'],Emotion.EMOTION_SHALLOW_SLEEP],
                                  STAT_WEEDING: [self.s_t_spk['weeding'],Emotion.EMOTION_WEED], STAT_LEARNING: [self.s_t_spk['learning'],Emotion.EMOTION_READ_BOOK],
                                  STAT_PLAYING: [self.s_t_spk['playing'],Emotion.EMOTION_PLAY_IN_FOREST],
                                  STAT_DINNER: [self.s_t_spk['dinner'],Emotion.EMOTION_DINNER], STAT_CHATTING: [self.s_t_spk['chatting'],Emotion.EMOTION_USUAL],
                                  STAT_SLEEPING: [self.s_t_spk['sleeping'],Emotion.EMOTION_NIGHT_SLEEPING],
                                  STAT_WEEKEND_GETUP: [self.s_t_spk['weekend_getup'],Emotion.EMOTION_MORNING_WAKE_UP],
                                  STAT_WEEKEND_WATERING: [self.s_t_spk['weekend_watering'],Emotion.EMOTION_WATERING],
                                  STAT_WEEKEND_FISHING: [self.s_t_spk['weekend_fishing'],Emotion.EMOTION_FISH],
                                  STAT_WEEKEND_WEEDING: [self.s_t_spk['weekend_weeding'],Emotion.EMOTION_WEED],
                                  STAT_WEEKEND_SLEEPING: [self.s_t_spk['weekend_sleeping'],Emotion.EMOTION_DEEP_SLEEP],
                                  STAT_DAY_OFF: [self.s_t_spk['day_off'],Emotion.EMOTION_LEAVE],
                                  STAT_SICK: [self.s_t_spk['sick'],Emotion.EMOTION_ILLNESS],
                                  STAT_DAY_OFF_ING:[self.s_t_spk['day_off_ing'],Emotion.EMOTION_LEAVE],
                                  STAT_ROLE_PLAY:[self.s_t_spk['role_play'],Emotion.EMOTION_USUAL] }
        #
        self.time_to_english = {1: "one", 2: "two", 3: "three", 4: "forth", 5: "five", 6: "six",
                                7: "seven", 8: "eight", 9: "nine", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
                                16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 21: "twenty-one", 22: "twenty-two",
                                23: "twenty-three", 10: "ten", 20: "twenty", 30: "thirty", 40: "forty", 50: "fifty"}
        #
        self.forest_result = {}
        self.mail_body =[]
        #
        self.last_no_token_dialog = 0
        #
        self.last_weed_act = 0
        self.last_water_act = 0
        self.last_physical_act = 0
        self.last_waterweed = 0

        self.requests = PlatRequests(self.user_id, self.token, self.device_code, self.language, self.logger)
        self.schedule_task_controller = schedule_task_controller
        self.schedule_task_controller.set_requests(self.requests)

    def do_day_schedule(self, cur, check_wifi):
        # 获取当前时间
        current_time = time.localtime()
        dt_dt = datetime.datetime
        today =  dt_dt.today()
        cur_time = dt_dt.strptime(dt_dt.now().strftime("%H:%M:%S"), "%H:%M:%S").time()
        #holiday = is_holiday_api(self.logger, today)
        #if holiday:
        #    self.logger.info("节假日： %s "% holiday)
        #is_51holiday(self.logger, today)

        if not self.time_json:
            return
        if not is_weekend(today):
            if self.sick_or_day_off['sick_flag'] == 1 and cur <= self.sick_or_day_off['sick_exp_time']:
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_illness[0][1], 36))
                return
            elif self.sick_or_day_off['day_off_flag'] == 1 and cur <= self.sick_or_day_off['day_off_exp_time']:
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_leave_default[0][1], 36))
                return
            elif self.is_time(cur_time,'begin','getUp'):
                if self.work_mode != STAT_SLEEPING:
                    self.logger.info("早上睡觉时间")
                    self.work_mode = STAT_SLEEPING
                self.emotion_pub.publish( self._emotion_without_effect(Emotion.EMOTION_NIGHT_SLEEPING, 36))
            elif self.is_time(cur_time,'getUp','physical'):
                if self.work_mode == STAT_GET_UP:
                    self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_get_up[0][1], 36))
                    if self.day_off_need_apply == 'yes' and cur - self.last_waterweed > 6 * 60:
                        # 开启
                        self.last_waterweed = cur
                        self.robotStatus.set_last_sleep3_time(cur + 30)
                        self.pub_see_command(See.COMMAND_START_SEE)
                    return
                self.logger.info("起床时间咯")
                self.work_mode = STAT_GET_UP
                self.local_persist_robot_status(self.work_mode)
                self.reset_day_param()
                self.robotStatus.set_last_busy_time(cur)

                if not self.sick_day or self.sick_day.month != current_time.tm_mon:
                    self.logger.info("sick_day:11111111111")
                    # 示例：获取当前月份的一个随机工作日
                    current_year = current_time.tm_year
                    current_month = current_time.tm_mon
                    current_mday = current_time.tm_mday
                    random_date_time = self.get_random_workday_of_month(current_year, current_month, current_mday)
                    self.local_persist_last_sick(self.sick_path,random_date_time)
                    if random_date_time.day == current_mday:
                        self.sick_or_day_off['sick_flag'] = 1
                        self.sick_or_day_off['sick_exp_time'] = cur + self.sick_inner
                        self.emotion_pub.publish(self._emotion_all(self.fb.feedback_day_illness[0][1], int(self.sick_or_day_off['sick_exp_time'])))
                        self.speak_pub.publish(self._speak_text(self.fb.feedback_day_illness[0][0]))
                    else:
                        self.speak_pub.publish(self._speak_text(self.fb.feedback_day_get_up[0][0]))
                        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_WAKE, 4))
                        time.sleep(1)
                        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_get_up[0][1], 36))

                        time.sleep(1)
                        self.act_action_with_hand_relative(0.5, 25, 0, 0, -40, 45)
                        time.sleep(1)
                        self.act_action_with_hand_relative(0.5, -25, 0, 0,40,-45)
                elif self.sick_day.day == current_time.tm_mday:
                    self.logger.info("sick_day:22222222")
                    self.sick_or_day_off['sick_flag'] = 1
                    self.sick_or_day_off['sick_exp_time'] = cur + self.sick_inner
                    self.emotion_pub.publish(self._emotion_all(self.fb.feedback_day_illness[0][1], int(self.sick_or_day_off['sick_exp_time'])))
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_illness[0][0]))
                elif not self.day_off or self.day_off.month != current_time.tm_mon:
                    self.logger.info("day_off:3333333")
                    # 示例：获取当前月份的一个随机工作日
                    current_year = current_time.tm_year
                    current_month = current_time.tm_mon
                    current_mday = current_time.tm_mday
                    random_date_time = self.get_random_workday_of_month(current_year, current_month, current_mday)
                    self.local_persist_last_day_off(self.day_off_path, random_date_time)
                    if random_date_time.day == current_mday:
                        self.day_off_need_apply = 'yes'
                        self.day_off_apply_count = 0
                        #开启
                        self.robotStatus.set_last_sleep3_time(time.time() + 30)
                        self.pub_see_command(See.COMMAND_START_SEE)
                        self.last_waterweed = cur
                    else:
                        self.speak_pub.publish(self._speak_text(self.fb.feedback_day_get_up[0][0]))
                        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_WAKE, 4))
                        time.sleep(1)
                        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_get_up[0][1], 36))

                        time.sleep(1)
                        self.act_action_with_hand_relative(0.5, 25, 0, 0, -40, 45)
                        time.sleep(1)
                        self.act_action_with_hand_relative(0.5, -25, 0, 0,40,-45)
                elif self.day_off.day == current_time.tm_mday:
                    self.logger.info("day_off:4444444")
                    self.day_off_need_apply = 'yes'
                    self.day_off_apply_count = 0
                    # 开启
                    self.robotStatus.set_last_sleep3_time(time.time() + 30 )
                    self.pub_see_command(See.COMMAND_START_SEE)
                    self.last_waterweed = cur
                else:
                    # 默认起床
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_get_up[0][0]))
                    self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_WAKE, 4))
                    time.sleep(1)
                    self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_get_up[0][1], 36))

                    # action
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, 25, 0, 0, -40, 45)
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, -25, 0, 0,40,-45)

            elif self.is_time(cur_time,'physical','watering'):
                if self.day_off_need_apply == 'yes':
                    self.default_day_off(cur)
                    return
                if self.work_mode != STAT_PHYSICAL:
                    self.work_mode = STAT_PHYSICAL
                    self.local_persist_robot_status(self.work_mode)
                    self.logger.info("运动时间")
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_physical[0][0]))
                    self.robotStatus.set_last_sleep3_time(cur + 30)
                    self.pub_see_command(See.COMMAND_START_SEE)
                    self.last_waterweed = cur
                    self.robotStatus.set_last_busy_time(cur)
                    #self.hand_action
                if cur - self.last_physical_act > 10 * 60:
                    self.last_physical_act = cur
                    self.act_action_reset()
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, 0, 0, 0, -40, -40)
                    # time.sleep(0.5)
                    self.act_action_with_hand_relative(0.5, 0, 0, 0, 80, 80)
                    # time.sleep(0.5)
                    self.act_action_with_hand_relative(0.5, 0, 0, 0, -80, -80)
                    # time.sleep(0.5)
                    self.act_action_with_hand_relative(0.5, 0, 0, 0, 80, 80)
                    # time.sleep(0.5)
                    self.act_action_with_hand_relative(0.5, 0, 0, 0, -80, -80)
                    # time.sleep(0.5)
                    self.act_action_with_hand_relative(0.5, 0, 0, 0, 40, 40)
                    time.sleep(1)
                    self.act_action_reset()
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_physical[0][1], 36))
                if self.cooper_physical_count == 0 and cur - self.last_waterweed > 6 * 60:
                    self.robotStatus.set_last_sleep3_time(cur + 30)
                    self.pub_see_command(See.COMMAND_START_SEE)
                    self.last_waterweed = cur

            elif self.is_time(cur_time,'watering','noonEating'):
                if self.work_mode != STAT_WATERING:
                    self.logger.info("浇水时间咯")
                    self.work_mode = STAT_WATERING
                    self.last_water_act = cur - 29 * 60
                    self.local_persist_robot_status(self.work_mode)
                    self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_watering[0][1], 10))
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_watering[0][0]))
                    self.robotStatus.set_last_sleep3_time(time.time() + 30 )
                    self.pub_see_command(See.COMMAND_START_SEE)
                    self.last_waterweed = cur
                    strftime = dt_dt.now().strftime("%Y-%m-%d %H:%M:%S")
                    payload = {"bizType": biz_type_energy,"type":type_inc,"trans_type":trans_type_water,"nums":0.05,"timeStr":strftime}
                    self.append_biz_data(payload)
                    self.robotStatus.set_last_busy_time(cur)
                if cur - self.last_water_act > 30 * 60:
                    self.last_water_act = cur
                    time.sleep(1)
                    self.act_action_reset()
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_watering_act[0][0]))
                    index = random.randint(0, 1)
                    if index == 0:
                        self.act_action_with_hand_relative(0.5,0,0,30,0,30)
                        time.sleep(1)
                        self.act_action_with_hand_relative(0.5,0,0,-30,0,-30)
                    else:
                        self.act_action_with_hand_relative(0.5,0,0,-30,0,30)
                        time.sleep(1)
                        self.act_action_with_hand_relative(0.5, 0, 0, 30, 0, -30)
                    time.sleep(1)
                    self.act_action_reset()
                self.emotion_pub.publish(self._emotion_expired(Emotion.EMOTION_EFFECTION_WATERING, int(cur + 56)))
                if self.cooper_water_count == 0 and cur - self.last_waterweed > 6 * 60:
                    self.robotStatus.set_last_sleep3_time(cur + 30)
                    self.pub_see_command(See.COMMAND_START_SEE)
                    self.last_waterweed = cur

            elif self.is_time(cur_time,'noonEating','noontime'):
                if self.work_mode != STAT_NOON_EATING:
                    self.logger.info("午饭时间咯")
                    self.work_mode = STAT_NOON_EATING
                    self.local_persist_robot_status(self.work_mode)
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_noonEating[0][0]))
                    self.robotStatus.set_last_busy_time(cur)
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_noonEating[0][1], 36))

            elif self.is_time(cur_time,'noontime','noonEnding'):
                if self.work_mode != STAT_NOON:
                    self.logger.info("午休时间咯")
                    self.work_mode = STAT_NOON
                    self.local_persist_robot_status(self.work_mode)
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_noontime[0][0]))
                    self.robotStatus.set_last_busy_time(cur)
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_noontime[0][1], 36))

            elif self.is_time(cur_time,'weeding','learning'):
                if self.work_mode != STAT_WEEDING:
                    self.logger.info("除草时间咯")
                    self.work_mode = STAT_WEEDING
                    self.last_weed_act = cur - 29 * 60
                    self.local_persist_robot_status(self.work_mode)
                    self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_weeding[0][1], 10))
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_weeding[0][0]))
                    self.robotStatus.set_last_sleep3_time(time.time() + 30  )
                    self.pub_see_command(See.COMMAND_START_SEE)
                    self.last_waterweed = cur
                    strftime = dt_dt.now().strftime("%Y-%m-%d %H:%M:%S")
                    payload = {"bizType": biz_type_energy,"type":type_inc, "trans_type": trans_type_weed, "nums": 0.05,"timeStr":strftime}
                    self.append_biz_data(payload)
                    self.robotStatus.set_last_busy_time(cur)
                    # action
                    self.act_action_reset()
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, 25, 0, 0, -30, 45)
                    time.sleep(1)
                    self.act_action_relative(0.5,0,12,0)
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, -25, 0, 0, 30, -45)
                    time.sleep(1)
                    self.act_action_relative(0.5, 0, -12, 0)
                    time.sleep(1)
                    self.act_action_reset()
                if cur - self.last_weed_act > 30 * 60:
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_weeding_act[0][0]))
                    time.sleep(1)
                    self.act_action_reset()
                    self.last_weed_act = cur
                    index = random.randint(0, 1)
                    if index == 0:
                        self.act_action_with_hand_relative(0.5,0,0,30,0,80)
                        time.sleep(1)
                        self.act_action_with_hand_relative(0.5,0,0,-30,0,-80)
                    else:
                        self.act_action_with_hand_relative(0.5,0,0,-30,0,80)
                        time.sleep(1)
                        self.act_action_with_hand_relative(0.5, 0, 0, 30, 0, -80)
                    time.sleep(1)
                    self.act_action_reset()
                self.emotion_pub.publish(self._emotion_expired(Emotion.EMOTION_EFFECTION_WEED, int(cur + 56) ))
                if self.cooper_weed_count == 0 and cur - self.last_waterweed > 6 * 60:
                    self.robotStatus.set_last_sleep3_time(cur + 30)
                    self.pub_see_command(See.COMMAND_START_SEE)
                    self.last_waterweed = cur

            elif self.is_time(cur_time,'learning','playing'):
                if self.work_mode != STAT_LEARNING:
                    self.logger.info("学习看书时间")
                    self.work_mode = STAT_LEARNING
                    self.local_persist_robot_status(self.work_mode)
                    self.last_reading_time = cur
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_learning[0][0]))
                    self.robotStatus.set_last_busy_time(cur)
                    # action
                    #self.act_xled_brightness(5,10)
                    self.act_action_with_hand_relative(0.5, 0, 12, 0, -45, 45)
                    time.sleep(1)
                    #self.act_xled_brightness(5, 0)
                    self.act_action_with_hand_relative(0.5, 0, -12, 0, 45, -45)
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_learning[0][1], 36))
                if 10 * 60 > cur - self.last_reading_time > 5 * 60:
                    self.last_reading_time = cur
                    strftime = dt_dt.now().strftime("%Y-%m-%d %H:%M:%S")
                    payload = {"bizType": biz_type_reading, "nums": 0.1, "timeStr": strftime}
                    self.append_biz_data(payload)

            elif self.is_time(cur_time,'playing','dinner'):
                """
                情感森林探索
                """
                if not self.token or not check_wifi:
                    if self.work_mode == STAT_LEARNING or self.work_mode == STAT_PLAYING:
                        self.work_mode = STAT_DEFAULT
                    return
                self.logger.info("情感森林玩耍时间 self.enter_status： %s "  % self.enter_status)
                if self.work_mode != STAT_PLAYING:
                    self.logger.info("情感森林玩耍时间")
                    self.work_mode = STAT_PLAYING
                    self.local_persist_robot_status(self.work_mode)
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_playing[0][0]))
                    #self.emotion_pub.publish(self._emotion_expired(self.fb.feedback_day_playing[0][1], int(cur + 60 * 60)))
                    self.robotStatus.set_last_busy_time(cur)
                self.emotion_pub.publish(self._emotion_expired(self.fb.feedback_day_playing[0][1], int(cur + 56)))
                if self.enter_status == 0:
                    payload = {"user_id": self.user_id, "deviceCode": self.device_code}
                    self.enter_emo_forest(payload, cur)
                    self.robotStatus.set_last_busy_time(cur)
                elif 2 >= self.enter_status >=1 and cur - self.last_enter_map_time >= 30 * 60 :
                    payload = {"user_id": self.user_id, "deviceCode": self.device_code}
                    self.get_emo_forest_status(payload)
                    self.robotStatus.set_last_busy_time(cur)

            elif self.is_time(cur_time,'dinner','chatting'):
                if self.work_mode != STAT_DINNER:
                    self.logger.info("晚饭时间")
                    self.work_mode = STAT_DINNER
                    self.local_persist_robot_status(self.work_mode)
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_dinner[0][0]))
                    self.robotStatus.set_last_busy_time(cur)
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_dinner[0][1], 36))

            elif self.is_time(cur_time,'chatting','sleeping'):
                if self.work_mode != STAT_CHATTING:
                    self.logger.info("聊天时间")
                    self.work_mode = STAT_CHATTING
                    self.local_persist_robot_status(self.work_mode)
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_chatting[0][0]))
                    self.robotStatus.set_last_busy_time(cur)
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_chatting[0][1], 36))
            elif self.is_time(cur_time,'sleeping','end'):
                if self.work_mode != STAT_SLEEPING:
                    self.logger.info("睡觉时间")
                    self.work_mode = STAT_SLEEPING
                    self.pub_see_command(See.COMMAND_STOP_SEE)
                    self.chat_dialog_add_energy()
                    self.local_persist_robot_status(self.work_mode)
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_go_sleeping[0][0]))
                    self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_go_sleeping[0][1], 10))
                    self.robotStatus.set_last_busy_time(cur)
                    time.sleep(20)
                self.emotion_pub.publish( self._emotion_without_effect(Emotion.EMOTION_NIGHT_SLEEPING, 36))
            else:
                self.work_mode = STAT_DEFAULT
        else:
            if self.is_time(cur_time,'begin','weekendGetUp'):
                if self.work_mode != STAT_WEEKEND_SLEEPING:
                    self.logger.info("周末早上睡觉时间")
                    self.work_mode = STAT_WEEKEND_SLEEPING
                self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_NIGHT_SLEEPING, 36))
            elif self.is_time(cur_time,'weekendGetUp','weekendWatering'):
                if self.work_mode != STAT_WEEKEND_GETUP:
                    self.logger.info("周末起床时间")
                    self.work_mode = STAT_WEEKEND_GETUP
                    self.local_persist_robot_status(self.work_mode)
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_get_up[0][0]))
                    self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_WAKE, 4))
                    self.reset_day_param()
                    self.robotStatus.set_last_busy_time(cur)

                    # action
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, 25, 0, 0, -45, 45)
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, -25, 0, 0,40,-45)
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_get_up[0][1],36) )

            elif self.is_time(cur_time,'weekendWatering','weekendFishBegin'):
                if self.work_mode != STAT_WEEKEND_WATERING:
                    self.logger.info("周末浇水时间")
                    self.work_mode = STAT_WEEKEND_WATERING
                    self.last_water_act = cur - 29 * 60
                    self.local_persist_robot_status(self.work_mode)
                    self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_watering[0][1],10))
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_watering[0][0]))
                    self.robotStatus.set_last_sleep3_time(cur + 30 )
                    self.last_waterweed = cur
                    self.pub_see_command(See.COMMAND_START_SEE)

                    strftime = dt_dt.now().strftime("%Y-%m-%d %H:%M:%S")
                    payload = {"bizType": biz_type_energy,"type":type_inc,"trans_type":trans_type_water,"nums":0.05,"timeStr":strftime}
                    self.append_biz_data(payload)
                    self.robotStatus.set_last_busy_time(cur)
                if cur - self.last_water_act > 30 * 60:
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_watering_act[0][0]))
                    self.act_action_reset()
                    time.sleep(1)
                    self.last_water_act = cur
                    index = random.randint(0, 1)
                    if index == 0:
                        self.act_action_with_hand_relative(0.5,0,0,30,0,30)
                        time.sleep(1)
                        self.act_action_with_hand_relative(0.5,0,0,-30,0,-30)
                    else:
                        self.act_action_with_hand_relative(0.5,0,0,-30,0,30)
                        time.sleep(1)
                        self.act_action_with_hand_relative(0.5,0,0,30,0,-30)
                    time.sleep(1)
                    self.act_action_reset()
                self.emotion_pub.publish(self._emotion_expired(Emotion.EMOTION_EFFECTION_WATERING, int(cur + 56)))
                if self.cooper_water_count == 0 and cur - self.last_waterweed > 6 * 60:
                    self.robotStatus.set_last_sleep3_time(cur + 30)
                    self.pub_see_command(See.COMMAND_START_SEE)
                    self.last_waterweed = cur

            elif self.is_time(cur_time,'weekendFishBegin','weekendFishEnd'):
                if self.work_mode != STAT_WEEKEND_FISHING:
                    self.logger.info("周末钓鱼时间")
                    self.work_mode = STAT_WEEKEND_FISHING
                    self.local_persist_robot_status(self.work_mode)
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_fishing[0][0]))
                    self.robotStatus.set_last_busy_time(cur)
                    # action
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, 45)
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, -45)
                    time.sleep(1)
                    self.act_action_reset()

                if self.fish_num == 0:
                    self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_fishing[0][1], 34))
                else:
                    self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_fished[0][1], 36))
                    return
                now = datetime.datetime.now()
                # 解析目标时间字符串
                target_hour, target_minute, target_second = map(int, self.time_json['weekendFishEnd'].split(':'))
                # 创建今天的目标时间
                target_time_today = datetime.datetime.combine(
                    now.date(),
                    datetime.time(target_hour, target_minute, target_second)
                )
                # 计算时间差（返回timedelta对象）
                time_diff = target_time_today - now
                if (0 < time_diff.total_seconds() < 3 * 60) and self.fish_num == 0:
                    x = random.randint(1, 100)
                    if x <= 30:
                        self.fish_num = 1
                        self.speak_pub.publish(self._speak_text(self.fb.feedback_day_fished[0][0]))
                        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_fished[0][1], 36))
                        self.robotStatus.set_last_busy_time(cur)
                    else:
                        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_NO_FISH, 36))
            elif self.is_time(cur_time,'weekendWeeding','dinner'):
                if self.work_mode != STAT_WEEKEND_WEEDING:
                    self.logger.info("周末除草时间")
                    self.work_mode = STAT_WEEKEND_WEEDING
                    self.last_weed_act = cur - 29 * 60
                    self.local_persist_robot_status(self.work_mode)
                    self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_weeding[0][1], 10))
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_weeding[0][0]))
                    self.robotStatus.set_last_sleep3_time(cur + 30 )
                    self.last_waterweed = cur
                    self.pub_see_command(See.COMMAND_START_SEE)

                    strftime = dt_dt.now().strftime("%Y-%m-%d %H:%M:%S")
                    payload = {"bizType": biz_type_energy,"type":type_inc,"trans_type": trans_type_weed, "nums": 0.05,"timeStr":strftime}
                    self.append_biz_data(payload)
                    self.robotStatus.set_last_busy_time(cur)
                    # action
                    self.act_action_reset()
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, 25, 0, 0, -30, 45)
                    time.sleep(1)
                    self.act_action_relative(0.5, 0, 12, 0)
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, -25, 0, 0, 30, -45)
                    time.sleep(1)
                    self.act_action_relative(0.5, 0, -12, 0)
                    time.sleep(1)
                    self.act_action_reset()

                if cur - self.last_weed_act > 30 * 60:
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_weeding_act[0][0]))
                    time.sleep(1)
                    self.act_action_reset()
                    self.last_weed_act = cur
                    index = random.randint(0, 1)
                    if index == 0:
                        self.act_action_with_hand_relative(0.5,0,0,30,0,80)
                        time.sleep(1)
                        self.act_action_with_hand_relative(0.5,0,0,-30,0,-80)
                    else:
                        self.act_action_with_hand_relative(0.5,0,0,-30,0,80)
                        time.sleep(1)
                        self.act_action_with_hand_relative(0.5,0,0,30,0,-80)
                    time.sleep(1)
                    self.act_action_reset()
                self.emotion_pub.publish(self._emotion_expired(Emotion.EMOTION_EFFECTION_WEED, int(cur + 56) ))
                if self.cooper_weed_count == 0 and cur - self.last_waterweed > 6 * 60:
                    self.robotStatus.set_last_sleep3_time(cur + 30)
                    self.pub_see_command(See.COMMAND_START_SEE)
                    self.last_waterweed = cur

            elif self.is_time(cur_time,'dinner','weekendSleeping'):
                if self.work_mode != STAT_DINNER:
                    self.logger.info("周末晚饭时间")
                    self.work_mode = STAT_DINNER
                    self.local_persist_robot_status(self.work_mode)
                    feedback = self.fb.feedback_day_dinner
                    if self.fish_num > 0:
                        feedback = self.fb.feedback_day_fished_dinner
                    self.speak_pub.publish(self._speak_text(feedback[0][0]))
                    self.robotStatus.set_last_busy_time(cur)
                feedback = self.fb.feedback_day_dinner
                if self.fish_num > 0:
                    feedback = self.fb.feedback_day_fished_dinner
                self.emotion_pub.publish(self._emotion_without_effect(feedback[0][1], 36))
            elif self.is_time(cur_time,'weekendSleeping','end'):
                if self.work_mode != STAT_WEEKEND_SLEEPING:
                    self.logger.info("周末睡觉时间")
                    self.work_mode = STAT_WEEKEND_SLEEPING
                    self.pub_see_command(See.COMMAND_STOP_SEE)
                    self.chat_dialog_add_energy()
                    self.local_persist_robot_status(self.work_mode)
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_go_sleeping[0][0]))
                    self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_go_sleeping[0][1], 10))
                    self.robotStatus.set_last_busy_time(cur)
                    time.sleep(20)
                self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_NIGHT_SLEEPING, 36))
            else:
                self.work_mode = STAT_DEFAULT

    def set_saw_person_info(self,person_c,cur):
        self.saw_person_count = person_c
        self.last_saw_per_time = cur

    def do_cooper_watering(self,cur):
        if ( (self.work_mode == STAT_WATERING or self.work_mode == STAT_WEEKEND_WATERING )
                and self.cooper_water_count == 0):
            datetime_datetime = datetime.datetime
            strftime = datetime_datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload = { "bizType": biz_type_energy,"type":type_inc,"trans_type": trans_type_water_comb, "nums": 0.05,"timeStr":strftime}
            self.append_biz_data(payload)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_day_cooper_watering[0][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_cooper_watering[0][1],20))
            self.cooper_water_count += 1
            self.robotStatus.set_last_busy_time(cur)
            #self.robotStatus.set_last_sleep3_time(cur)
            # action
            self.act_action_reset()
            time.sleep(1)
            self.act_action_with_hand_relative(0.5, 0, 12, 0, 0, 45)
            time.sleep(1)
            self.act_action_with_hand_relative(0.5, 0, -12, 0, 0, -45)

    def do_cooper_weeding(self,cur):
        if ( (self.work_mode == STAT_WEEDING  or self.work_mode == STAT_WEEKEND_WEEDING )
                and self.cooper_weed_count == 0):
            datetime_datetime = datetime.datetime
            strftime = datetime_datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload = {"bizType": biz_type_energy,"type":type_inc,"trans_type": trans_type_weed_comb, "nums": 0.05,"timeStr":strftime}
            self.append_biz_data(payload)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_day_cooper_weeding[0][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_cooper_weeding[0][1],20))
            self.cooper_weed_count += 1
            self.robotStatus.set_last_busy_time(cur)
            #self.robotStatus.set_last_sleep3_time(cur)

    def do_invite_when_saw_person(self,cur):
        if self.work_mode == STAT_GET_UP:
            if cur - self.last_invite_day_off_time < self.invite_inner_min:
                return None
            if self.day_off_need_apply == 'yes':
                self.last_invite_day_off_time = cur
                if self.day_off_apply_count < 3:
                    self.day_off_apply_count += 1
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_day_leave[0][0]))
                    self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_leave[0][1],20))
                    return "day_off"
                else:
                    self.default_day_off(cur)
        elif self.work_mode == STAT_PHYSICAL:
            """
            邀请人来一起运动
            """
            if self.cooper_physical_count == 0 and cur - self.last_invite_physical_time > self.invite_inner_min:
                self.last_invite_physical_time = cur
                self.cooper_physical_count +=1
                self.speak_pub.publish(self._speak_text(self.fb.feedback_day_invite_physical[0][0]))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_invite_physical[0][1], 20))
                self.robotStatus.set_last_busy_time(cur)
                #self.robotStatus.set_last_sleep3_time(cur)
        elif self.work_mode == STAT_WATERING:
            """
            邀请人来一起浇水
            """
            if self.cooper_water_count == 0 and cur - self.last_invite_water_time > self.invite_inner_min:
                self.last_invite_water_time = cur
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_invite_water[0][1], 20))
                self.speak_pub.publish(self._speak_text(self.fb.feedback_day_invite_water[0][0]))
                self.robotStatus.set_last_busy_time(cur)
                # action
                self.act_action_reset()
                time.sleep(1)
                self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, 45)
                time.sleep(1)
                self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, -45)
                time.sleep(1)
                self.act_action_reset()
                return "water"
        elif self.work_mode == STAT_WEEDING:
            """
            邀请人来一起除草
            """
            if  self.cooper_weed_count == 0 and cur - self.last_invite_weed_time > self.invite_inner_min:
                self.last_invite_weed_time = cur
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_invite_weed[0][1], 20))
                self.speak_pub.publish(self._speak_text(self.fb.feedback_day_invite_weed[0][0]))
                self.robotStatus.set_last_busy_time(cur)
                return "weed"
        elif self.work_mode == STAT_WEEKEND_WATERING:
            """
            邀请人来一起浇水
            """
            if  self.cooper_water_count == 0 and cur - self.last_invite_water_time >= self.invite_inner_min:
                self.last_invite_water_time = cur
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_invite_water[0][1], 20))
                self.speak_pub.publish(self._speak_text(self.fb.feedback_day_invite_water[0][0]))
                self.robotStatus.set_last_busy_time(cur)
                # action
                self.act_action_reset()
                time.sleep(1)
                self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, 45)
                time.sleep(1)
                self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, -45)
                time.sleep(1)
                self.act_action_reset()
                return "water"
        elif self.work_mode == STAT_WEEKEND_WEEDING:
            """
            邀请人来一起除草
            """
            if self.cooper_weed_count == 0  and cur - self.last_invite_weed_time >= self.invite_inner_min:
                self.last_invite_weed_time = cur
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_invite_weed[0][1], 20))
                self.speak_pub.publish(self._speak_text(self.fb.feedback_day_invite_weed[0][0]))
                self.robotStatus.set_last_busy_time(cur)
                return "weed"
        return None

    def _speak_text(self, text):
        speak = Speak()
        speak.audio_file = ""
        speak.text = text
        return speak
    def _emotion_without_effect(self, _type, display_count = 1):
        emotion = Emotion()
        emotion.emotion_type = _type
        emotion.emotion_display_count = display_count
        return emotion
    def _emotion_expired(self, _type, expired_time):
        emotion = Emotion()
        emotion.emotion_type = _type
        emotion.effection_expired_time = expired_time
        return emotion
    def _emotion_tree(self, _type,number, expired_time):
        emotion = Emotion()
        emotion.emotion_type = _type
        emotion.effection_expired_time = expired_time
        emotion.effection_number = number
        return emotion
    def _emotion_all(self, _type,expired_time, display_count = 1):
        emotion = Emotion()
        emotion.emotion_type = _type
        emotion.emotion_display_count = display_count
        emotion.effection_expired_time = expired_time
        return emotion
    def pub_see_command(self, command):
        see = See()
        see.command = command
        self.eye_pub.publish(see)

    def get_day_timestamp(self,datetime_datetime,time_str):
        today = datetime_datetime.now().date()
        full_datetime_str = f"{today} {time_str}"
        # 解析组合后的字符串为datetime对象
        dt = datetime_datetime.strptime(full_datetime_str, "%Y-%m-%d %H:%M:%S")
        # 获取时间戳
        return dt.timestamp()

    def is_sleep_time(self):
        dt_dt = datetime.datetime
        today = dt_dt.today()
        cur_time = dt_dt.strptime(dt_dt.now().strftime("%H:%M:%S"), "%H:%M:%S").time()
        if not is_weekend(today):
            if (self.time_json["begin" + "ts"] <= cur_time < self.time_json["getUp" + "ts"]
                or self.time_json["sleeping" + "ts"] <= cur_time < self.time_json["end" + "ts"]):
                return True
        else:
            if (self.time_json["begin" + "ts"] <= cur_time < self.time_json["weekendGetUp" + "ts"]
                or self.time_json["weekendSleeping" + "ts"] <= cur_time < self.time_json["end" + "ts"]):
                return True
        return False

    def is_time(self,cur_time,begin_str,end_str):
        if ( (begin_str + "ts") in self.time_json and self.time_json[begin_str + "ts"] and
              (end_str + "ts") in self.time_json  and self.time_json[end_str + "ts"]):
            # 判断当前时间是否为hour:minute
            if self.time_json[begin_str + "ts"] <= cur_time < self.time_json[end_str + "ts"]:
                self.logger.info('当前时间 是:%s - %s ，%s' % (self.time_json[begin_str + "ts"],self.time_json[end_str + "ts"],begin_str))
                return True
            else:
                #self.logger.info('当前时间不是:"%s" : "%s" ' % (self.time_json[begin_str + "ts"],self.time_json[end_str + "ts"]))
                return False
        else:
            return False

    def deal_time_json(self):
        self.time_json["begin" + "ts"] = datetime.datetime.strptime("00:00:00", "%H:%M:%S").time()
        self.time_json["end" + "ts"] = datetime.datetime.strptime("23:59:59", "%H:%M:%S").time()
        if self.time_json["getUp"]:
            self.time_json["getUp" + "ts"] = datetime.datetime.strptime(self.time_json["getUp"], "%H:%M:%S").time()
        if self.time_json["physical"]:
            self.time_json["physical" + "ts"] = datetime.datetime.strptime(self.time_json["physical"], "%H:%M:%S").time()
        if self.time_json["watering"]:
            self.time_json["watering" + "ts"] = datetime.datetime.strptime(self.time_json["watering"], "%H:%M:%S").time()
        if self.time_json["noonEating"]:
            self.time_json["noonEating" + "ts"] = datetime.datetime.strptime(self.time_json["noonEating"], "%H:%M:%S").time()
        if self.time_json["noontime"]:
            self.time_json["noontime" + "ts"] = datetime.datetime.strptime(self.time_json["noontime"], "%H:%M:%S").time()
        if self.time_json["noonEnding"]:
            self.time_json["noonEnding" + "ts"] = datetime.datetime.strptime(self.time_json["noonEnding"], "%H:%M:%S").time()
        if self.time_json["weeding"]:
            self.time_json["weeding" + "ts"] = datetime.datetime.strptime(self.time_json["weeding"], "%H:%M:%S").time()
        if self.time_json["learning"]:
            self.time_json["learning" + "ts"] = datetime.datetime.strptime(self.time_json["learning"], "%H:%M:%S").time()
        if self.time_json["playing"]:
            self.time_json["playing" + "ts"] = datetime.datetime.strptime(self.time_json["playing"], "%H:%M:%S").time()
        if self.time_json["dinner"]:
            self.time_json["dinner" + "ts"] = datetime.datetime.strptime(self.time_json["dinner"], "%H:%M:%S").time()
        if self.time_json["chatting"]:
            self.time_json["chatting" + "ts"] = datetime.datetime.strptime(self.time_json["chatting"], "%H:%M:%S").time()
        if self.time_json["sleeping"]:
            self.time_json["sleeping" + "ts"] = datetime.datetime.strptime(self.time_json["sleeping"], "%H:%M:%S").time()
        if self.time_json["weekendGetUp"]:
            self.time_json["weekendGetUp" + "ts"] = datetime.datetime.strptime(self.time_json["weekendGetUp"], "%H:%M:%S").time()
        if self.time_json["weekendWatering"]:
            self.time_json["weekendWatering" + "ts"] = datetime.datetime.strptime(self.time_json["weekendWatering"], "%H:%M:%S").time()
        if self.time_json["weekendFishBegin"]:
            self.time_json["weekendFishBegin" + "ts"] = datetime.datetime.strptime(self.time_json["weekendFishBegin"], "%H:%M:%S").time()
        if self.time_json["weekendFishEnd"]:
            self.time_json["weekendFishEnd" + "ts"] = datetime.datetime.strptime(self.time_json["weekendFishEnd"], "%H:%M:%S").time()
        if self.time_json["weekendWeeding"]:
            self.time_json["weekendWeeding" + "ts"] = datetime.datetime.strptime(self.time_json["weekendWeeding"], "%H:%M:%S").time()
        if self.time_json["weekendSleeping"]:
            self.time_json["weekendSleeping" + "ts"] = datetime.datetime.strptime(self.time_json["weekendSleeping"], "%H:%M:%S").time()
        return self.time_json

    def is_param_time(self,current_time,time_str):
        if time_str:
            conf_time = time_str.split(':')
            print("conf_time:", conf_time)
            # 提取当前的小时和分钟
            current_hour = current_time.tm_hour
            current_minute = current_time.tm_min
            # 判断当前时间是否为hour:minute
            if current_hour == int(conf_time[0]) and current_minute > int(conf_time[1]):
                self.logger.info('当前时间是:"%s" : "%s" ' % (conf_time[0],conf_time[1]))
                return True
            else:
                self.logger.info('当前时间不是:"%s" : "%s" ' % (conf_time[0],conf_time[1]))
                return False
        else:
            return False

    def is_param_time_range(self,current_time,time_str_begin,time_str_end):
        if time_str_begin and time_str_end:
            conf_time_begin = time_str_begin.split(':')
            conf_time_end = time_str_end.split(':')
            print("conf_time_begin:", conf_time_begin)
            print("conf_time_end:", conf_time_end)
            # 提取当前的小时和分钟
            current_hour = current_time.tm_hour
            current_minute = current_time.tm_min
            # 判断当前时间是否为hour:minute
            if (int(conf_time_begin[0]) <= int(current_hour) < int(conf_time_end[0])
                    and current_minute > int(conf_time_begin[1])):
                self.logger.info('当前时间是:"%s":"%s" ' % (conf_time_begin[0],conf_time_begin[1]))
                return True
            else:
                self.logger.info('当前时间不是:"%s":"%s" ' % (conf_time_begin[0],conf_time_begin[1]))
                return False
        else:
            return False

    def get_robot_work_mode(self,brain_w_mode):
        if brain_w_mode == 7:
            return STAT_ROLE_PLAY
        cur = time.time()
        if self.sick_or_day_off['sick_flag'] == 1 and cur <= self.sick_or_day_off['sick_exp_time']:
            return STAT_SICK
        elif self.sick_or_day_off['day_off_flag'] == 1 and cur <= self.sick_or_day_off['day_off_exp_time']:
            return STAT_DAY_OFF
        elif self.work_mode == STAT_GET_UP and self.day_off_need_apply =='yes' and self.day_off_apply_count <=3:
            return STAT_DAY_OFF_ING
        return self.work_mode

    def check_is_busy(self):
        if (self.work_mode == STAT_PLAYING and self.enter_status <= 2) or self.work_mode == STAT_WEEKEND_FISHING:
            return true
        return false

    def get_grow_tree_status(self):
        self.sync_grow_tree_from_plat()
        return self.grow_tree

    def show_grow_tree(self):
        self.sync_grow_tree_from_plat()
        level_ = self.grow_tree['currLevel']

    def reset_day_param(self):
        # 每日能量
        self.day_energy = 0
        # 浇水参数
        self.cooper_water_count = 0
        # 除草参数
        self.cooper_weed_count = 0
        # 地图
        self.enter_status = 0
        # 看书
        self.last_reading_time = 0
        # 钓鱼
        self.fish_num = 0
        # 病假
        self.sick_or_day_off['sick_flag'] = 0
        # 请假
        self.sick_or_day_off['day_off_flag'] = 0
        self.day_off_need_apply = 'no'
        self.day_off_apply_count = 0
        #
        self.cooper_physical_count = 0

    def day_off_yes_or_no_callback(self,cur,yes_or_no):
        self.day_off_need_apply = 'no'
        self.day_off_apply_count = 0
        if yes_or_no == 'yes':
            self.sick_or_day_off['day_off_flag'] = 1
            self.sick_or_day_off['day_off_exp_time'] = cur + self.sick_inner
            self.speak_pub.publish(self._speak_text(self.fb.feedback_day_leave_yes[0][0]))
            self.emotion_pub.publish(self._emotion_all(self.fb.feedback_day_leave_yes[0][1],int(self.sick_or_day_off['day_off_exp_time'])))
        else:
            self.sick_or_day_off['day_off_flag'] = 0
            self.speak_pub.publish(self._speak_text(self.fb.feedback_day_leave_no[0][0]))
    def default_day_off(self,cur):
        self.day_off_need_apply = 'no'
        self.day_off_apply_count = 0
        self.sick_or_day_off['day_off_flag'] = 1
        self.sick_or_day_off['day_off_exp_time'] = cur + self.sick_inner
        self.speak_pub.publish(self._speak_text(self.fb.feedback_day_leave_default[0][0]))
        self.emotion_pub.publish(self._emotion_all(self.fb.feedback_day_leave_default[0][1],int(self.sick_or_day_off['day_off_exp_time'])))

    def chat_dialog_turns(self):
        current_time = time.localtime()  # 获取本地时间
        day = current_time.tm_mday
        if day in self.chat_dia_turns:
            self.chat_dia_turns[day] =  self.chat_dia_turns[day] + 1
        else:
            self.chat_dia_turns = {day: 1}
        self.logger.info("chat_dialog_turns: %s " % self.chat_dia_turns[day])
        return day

    def chat_dialog_add_energy(self):
        nums = 0
        current_time = time.localtime()  # 获取本地时间
        day = current_time.tm_mday
        if day in self.chat_dia_turns:
            if self.chat_dia_turns[day] >= 100:
                nums = 0.4
            elif self.chat_dia_turns[day] >= 50:
                nums = 0.2
            elif self.chat_dia_turns[day] >= 10:
                nums = 0.1
        else:
            return
        if nums ==  0:
            return
        self.chat_dia_turns[day] = {}
        dt_dt = datetime.datetime
        strftime = dt_dt.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {"bizType": biz_type_energy, "type": type_inc, "trans_type": trans_type_dialog, "nums": nums,
                   "timeStr": strftime}
        self.append_biz_data(payload)

    def chat_dialog_sub_sick(self,day):
        if self.sick_or_day_off['sick_flag'] == 0:
            return
        if day in self.chat_dia_turns:
            cur = time.time()
            if self.chat_dia_turns[day] == 10:
                self.sub_sick_expired_time(cur, 1 * 60 * 60)
            elif self.chat_dia_turns[day] == 20:
                self.sub_sick_expired_time(cur, 2 * 60 * 60)
            elif self.chat_dia_turns[day] == 50:
                self.sub_sick_expired_time(cur, 4 * 60 * 60)

    # 生病时间缩短
    def sub_sick_expired_time(self,cur,sub_time):
        self.sick_or_day_off['sick_exp_time'] = self.sick_or_day_off['sick_exp_time']  - sub_time
        self.logger.info("self.sick_or_day_off['sick_exp_time']: %s " % self.sick_or_day_off['sick_exp_time'])
        if cur > self.sick_or_day_off['sick_exp_time']:
            self.sick_or_day_off['sick_flag'] = 0

    def get_random_workday_of_month(self, year, month,day):
        # 获取当月第一天
        # first_day_of_month = datetime.datetime(year, month, day)
        # 获取当月最后一天
        today = datetime.datetime.today()
        _, last_day_of_month = calendar.monthrange(year, month)
        last_day_of_month = today.replace(day=last_day_of_month)

        # 生成这个月份的所有日期
        #all_days = [first_day_of_month + datetime.timedelta(days=x) for x in
        #            range((last_day_of_month - first_day_of_month).days + 1)]

        # 过滤出工作日的日期（周一至周五）
        # workdays = [day for day in all_days if day.weekday() < 5]  # weekday() 返回0（周一）到6（周日）
        # 计算当月的工作日列表
        workdays = [day for day in range(1, last_day_of_month.day + 1) if
                    calendar.day_name[datetime.datetime(year, month, day).weekday()] not in ['Saturday', 'Sunday']]
        # 随机选择一个工作日
        if workdays:
            random_date_time = datetime.datetime(year, month, random.choice(workdays))
            self.logger.info("随机选择一个工作日: %s " % random_date_time)
            return random_date_time
        else:
            return None  # 如果没有工作日（理论上不太可能），返回None

    def do_bind_app(self,user_id):
        try:
            payload = {"userId": user_id, "deviceCode":self.device_code }
            response = requests.post(
                url  = api.bindApp.replace("host-place-holder", self.host),
                json = payload,
                timeout=10)
            response.raise_for_status()
            json = response.json()
            self.logger.info("绑定结果：%s " % json)
            status_ = json["status"]
            if status_ == 0:
                bind_result = json["data"]
                if bind_result:
                    self.user_id = bind_result["id"]
                    self.local_persist_user_id(self.user_id)
                    self.token = bind_result["token"]
                    self.local_persist_token(self.token)
                    self.requests.set_token(self.token)
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app_success[0][0]))
                    self.do_nick_refresh(True)
                    return True
                else:
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app_fail[0][0]))
            elif status_ == 101:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app_fail1[0][0]))
            elif status_ == 102:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app_fail2[0][0]))
            elif status_ == 103:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app_fail3[0][0]))
            elif status_ == 104:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app_fail4[0][0]))
            self.pub_see_command(See.COMMAND_USUAL)
            self.pub_see_command(See.COMMAND_STOP_SEE)
            return False
        except Exception as e:
            self.logger.error("绑定app失败: %s" % e)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app_fail[0][0]))
            self.pub_see_command(See.COMMAND_USUAL)
            self.pub_see_command(See.COMMAND_STOP_SEE)
            return False

    def append_biz_data(self, data, persistence_grow_tree=True):
        if data['bizType'] == biz_type_energy:
            if self.today_energy >= self.day_energy_limit:
                return
            self.today_energy = self.today_energy + data['nums']
            this_energy = data['nums']
            if self.today_energy >= self.day_energy_limit:
                this_energy = self.day_energy_limit - self.today_energy
            # 计算
            if data["trans_type"] in [trans_type_water,trans_type_water_comb,trans_type_weed,trans_type_weed_comb]:
                self.grow_tree['lastWater'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.grow_tree['currEnergy'] = self.grow_tree['currEnergy'] + this_energy
            self.set_curr_level(self.grow_tree['currLevel'],self.grow_tree['currEnergy'])
            if persistence_grow_tree:
                # 持久化树的状态
                self.persistence_grow_tree(self.grow_tree, self.root_dir + api.grow_tree_path)
        self.append_droop_data(data)
    def append_droop_data(self, data):
        month = data['timeStr'][0:7].replace("-", "")
        with open(self.root_dir + api.biz_data + month, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data) + "\n")
        with open(self.root_dir + api.biz_data_total + month, 'a', encoding='utf-8') as bdt:
            bdt.write(json.dumps(data) + "\n")

    def set_curr_level(self,currLevel,currEnergy):
        if '结果' == currLevel:
            get_level = self.get_level(currLevel)
            if not get_level:
                return
            mod = (currEnergy - get_level['energy']) // 5
            self.grow_tree['fruit'] = int(mod) + 1
            return
        shot_step = self.grow_tree_step_conf[0]
        for item in self.grow_tree_step_conf:
            if item['type'] != 1:
                continue
            if currEnergy >= item['energy']:
                shot_step = item
        if '枯萎' == currLevel or shot_step['id'] > self.grow_tree['id']:
            if '结果' == shot_step['levelName']:
                self.grow_tree['fruit'] = 1
            self.grow_tree['id'] = shot_step['id']
            self.grow_tree['currLevel'] = shot_step['levelName']

    def greater_than_level(self, level_name):
        for item in self.grow_tree_step_conf:
            if item['type'] != 1:
                continue
            if item['levelName'] == level_name and self.grow_tree['id'] > item['id']:
                return true
        return false

    def get_level(self, level_name):
        for item in self.grow_tree_step_conf:
            if item['levelName'] == level_name:
                return item
        return None

    def enter_emo_forest(self,payload,cur):
        try:
            if not self.token:
                return None
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                "authorization": self.token
            }
            response = requests.post(
                url     =  api.enterEmoForest.replace("host-place-holder", self.host),
                headers =  headers,
                json    =  payload,
                timeout=10)
            if response.status_code == 403:
                logger.info("enter_emo_forest，接口403 Forbidden Error，调用一次权限接口")
                self.one_day_refresh_token(True)
                return None
            else:
                response.raise_for_status()
                result = response.json()["data"]
                self.logger.info("进入情感森林 成功: %s" % result)
                if result and "mapName" in result:
                    self.enter_status = result['status']
                    #dt = datetime.datetime.strptime(result['enterTime'], "%Y-%m-%d %H:%M:%S")
                    #self.last_enter_map_time = dt.timestamp()
                    self.last_enter_map_time = cur
                    self.logger.info("进入情感森林 self.last_enter_map_time: %s" % self.last_enter_map_time)
                    current_time = time.localtime()  # 获取本地时间
                    day = current_time.tm_mday
                    a = {'mapName': result['mapName']}
                    self.forest_result[day] = a
        except Exception as e:
            self.logger.error("进入情感森林 失败: %s"  % e)

    def get_emo_forest_status(self,payload):
        try:
            if not self.token:
                return
            headers = {
                'Accept':       'application/json',
                'Content-Type': 'application/json',
                "authorization": self.token
            }
            response = requests.post(
                url     =  api.getEmoForestStatus.replace("host-place-holder", self.host),
                headers =  headers,
                json    =  payload,
                timeout=10)
            if response.status_code == 403:
                logger.info("get_emo_forest_status，接口403 Forbidden Error，调用一次权限接口")
                self.one_day_refresh_token(True)
            else:
                response.raise_for_status()
                result = response.json()["data"]
                self.logger.error("获取结果 成功: %s" % result)
                if result and result['status']:
                    self.enter_status = result['status']
                    if result['props']:
                        with open(self.root_dir + api.props_data, 'a', encoding='utf-8') as f:
                            for item in result['props']:
                                f.write(json.dumps(item) + "\n")
                        current_time = time.localtime()  # 获取本地时间
                        day = current_time.tm_mday
                        a = self.forest_result[day]
                        pros_str = []
                        act_result = None
                        datetime_datetime = datetime.datetime
                        for item in result['props']:
                            if item['propsName'] == '友谊之花':
                                self.grow_tree['friendship_time'] = item['expiredTime']
                                pros_str.append('友谊之花')
                                dt = datetime_datetime.strptime(self.grow_tree['friendship_time'], "%Y-%m-%d %H:%M:%S")
                                expired_timestamp = time.mktime(dt.timetuple())
                                self.emotion_pub.publish(self._emotion_expired(Emotion.EMOTION_EFFECTION_FRIEND_FLOWER,
                                                                               int(expired_timestamp)))
                            elif item['propsName'] == '精灵之花':
                                self.grow_tree['sprit_time'] = item['expiredTime']
                                pros_str.append('精灵之花')
                                dt = datetime_datetime.strptime(self.grow_tree['sprit_time'], "%Y-%m-%d %H:%M:%S")
                                expired_timestamp = time.mktime(dt.timetuple())
                                self.emotion_pub.publish(self._emotion_expired(Emotion.EMOTION_EFFECTION_SPRITE_FLOWER,
                                                                               int(expired_timestamp)))
                            elif item['propsName'] == '魔力黏土':
                                self.grow_tree['soil_time'] = item['expiredTime']
                                pros_str.append('魔力黏土')
                                act_result = '魔力黏土'
                                dt = datetime_datetime.strptime(self.grow_tree['soil_time'], "%Y-%m-%d %H:%M:%S")
                                expired_timestamp = time.mktime(dt.timetuple())
                                self.emotion_pub.publish(self._emotion_expired(Emotion.EMOTION_EFFECTION_MAGIC_CLAY,
                                                                               int(expired_timestamp)))
                            elif item['propsName'] == '精灵花露':
                                self.grow_tree['lotus_time'] = item['expiredTime']
                                pros_str.append('精灵花露')
                                act_result = '精灵花露'
                                dt = datetime_datetime.strptime(self.grow_tree['lotus_time'], "%Y-%m-%d %H:%M:%S")
                                expired_timestamp = time.mktime(dt.timetuple())
                                self.emotion_pub.publish(self._emotion_expired(Emotion.EMOTION_EFFECTION_SPRITE_DEW,
                                                                               int(expired_timestamp)))
                            elif item['propsName'] == '心灵之水':
                                self.grow_tree['soulwater_time'] = item['expiredTime']
                                pros_str.append('心灵之水')
                                act_result = '心灵之水'
                                dt = datetime_datetime.strptime(self.grow_tree['soulwater_time'], "%Y-%m-%d %H:%M:%S")
                                expired_timestamp = time.mktime(dt.timetuple())
                                self.emotion_pub.publish(self._emotion_expired(Emotion.EMOTION_EFFECTION_HEART_WATER,
                                                                               int(expired_timestamp)))
                        if pros_str:
                            a['props'] = '，'.join(str(i) for i in pros_str)
                            self.logger.info("获取情感森林状态 self.forest_result[day]: %s" % self.forest_result[day])
                            self.persistence_grow_tree(self.grow_tree, self.root_dir + api.grow_tree_path)
                            if act_result:
                                index = random.randint(0, len(self.fb.feedback_command_forest_2) - 1)
                                feedback__format = self.fb.feedback_command_forest_2[index][0]
                                if '%s' in feedback__format:
                                    feedback__format = feedback__format % act_result
                                self.speak_pub.publish(self._speak_text(feedback__format))
                            else:
                                self.speak_pub.publish(self._speak_text(self.fb.feedback_command_forest_1[0][0]))
        except Exception as e:
            self.logger.error("获取情感森林状态 失败: %s" % e)
    def props_expired_transfer_schedule(self):
        props_data_expired = []
        props_data_no_expire = []
        time_time = time.time()
        datetime_datetime = datetime.datetime
        strftime = datetime_datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        props_data_path = self.root_dir + api.props_data
        self.logger.info("检查道具过期-----------")
        if not os.path.exists(props_data_path):
            return
        lines_count = 0
        with open(props_data_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()  # 读取行
            lines_count = len(lines)
            for item in lines:
                if item.strip() == '':
                    continue
                data = json.loads(item)
                if 'expiredTime_timestamp' in data:
                    expired_timestamp = data['expiredTime_timestamp']
                else:
                    dt = datetime_datetime.strptime(data['expiredTime'], "%Y-%m-%d %H:%M:%S")
                    # 转换为time.time()
                    expired_timestamp = time.mktime(dt.timetuple())
                    data['expiredTime_timestamp'] = expired_timestamp
                if expired_timestamp > time_time:
                    props_data_no_expire.append(data)
                else:
                    props_data_expired.append(data)
        if not props_data_expired:
            return
        content = ''
        with open(props_data_path, 'r', encoding='utf-8') as file:
            lasted_lines = file.readlines()  # 读取
            if len(lasted_lines) > lines_count:
                content = lasted_lines[lines_count:]
        if content:
            for line in content:
                line_json = json.loads(line)
                props_data_no_expire.append(line_json)
        with open(props_data_path, 'w', encoding='utf-8') as file:
            if props_data_no_expire:
                for item in props_data_no_expire:
                    file.write(json.dumps(item) + "\n")
            else:
                file.write('')
        for item in props_data_expired:
            payload = {"bizType": biz_type_energy, "type": type_inc,
                       "trans_type": trans_type_weed_transfer, "nums": item['totalNum'],
                       "timeStr": strftime  }
            self.append_biz_data(payload,False)
        self.persistence_grow_tree(self.grow_tree, self.root_dir + api.grow_tree_path)

    def long_no_water_schedule(self):
        self.logger.info("每日检查长期不浇水")
        if not self.grow_tree['lastWater']:
            return
        try:
            dt_dt = datetime.datetime
            dt = dt_dt.strptime(self.grow_tree['lastWater'], "%Y-%m-%d %H:%M:%S")
            # 转换为time.time()
            lastWater_timestamp = time.mktime(dt.timetuple())
            time_time = time.time()
            if time_time - lastWater_timestamp < long_no_water_week:
                return
            if time_time - lastWater_timestamp >= long_no_water_2month  :
                if self.grow_tree['currLevel'] !='种子' :
                    utctime = dt_dt.now().strftime("%Y-%m-%d %H:%M:%S")
                    payload = {"bizType": biz_type_energy, "type": type_dec, "trans_type": trans_type_weed_drop,
                               "nums": - self.grow_tree['currEnergy'],
                               "timeStr": utctime}
                    self.grow_tree['id'] = 1
                    self.grow_tree['currLevel'] = '种子'
                    self.grow_tree['currEnergy'] = 0
                    self.grow_tree['fruit'] = 0
                    self.persistence_grow_tree(self.grow_tree, self.root_dir + api.grow_tree_path)
                    self.append_droop_data(payload)
            elif time_time - lastWater_timestamp >= long_no_water_month:
                if self.grow_tree['currEnergy'] > 23 and self.grow_tree['currLevel'] !='枯萎'  :
                    utctime = dt_dt.now().strftime("%Y-%m-%d %H:%M:%S")
                    payload = {"bizType": biz_type_energy, "type": type_dec, "trans_type": trans_type_weed_drop,
                                   "nums": 23 - self.grow_tree['currEnergy'],
                               "timeStr": utctime}
                    self.grow_tree['id'] = 8
                    self.grow_tree['currLevel'] = '枯萎'
                    self.grow_tree['currEnergy'] = 23
                    self.grow_tree['fruit'] = 0
                    self.persistence_grow_tree(self.grow_tree, self.root_dir + api.grow_tree_path)
                    self.append_droop_data(payload)
            elif time_time - lastWater_timestamp >= long_no_water_week :
                if self.grow_tree['currEnergy'] > 75:
                    utctime = dt_dt.now().strftime("%Y-%m-%d %H:%M:%S")
                    payload = {"bizType": biz_type_energy, "type": type_dec, "trans_type": trans_type_weed_drop,
                               "nums": 75 - self.grow_tree['currEnergy'],
                               "timeStr": utctime}
                    self.grow_tree['currLevel'] = '大树'
                    get_level = self.get_level('大树')
                    self.grow_tree['currEnergy'] = 75 if get_level else get_level['energy']
                    self.grow_tree['id'] = 5 if get_level else get_level['id']
                    self.grow_tree['fruit'] = 0
                    self.persistence_grow_tree(self.grow_tree, self.root_dir + api.grow_tree_path)
                    self.append_droop_data(payload)
        except Exception as e:
            self.logger.error("每日检查长期不浇水 失败: %s" % e)

    def query_tree_status(self):
        feedback = self.fb.feedback_command_query_tree
        feedback__format = feedback[0][0] % self.grow_tree['currLevel']
        fruit = self.grow_tree['fruit']
        if fruit > 0:
            feedback = self.fb.feedback_command_query_tree_fruits
            feedback__format = feedback[0][0] % fruit
        self.speak_pub.publish(self._speak_text(feedback__format))
        self.emotion_pub.publish(self._emotion_without_effect(feedback[0][1], 3))

    def help_water(self,cur):
        if self.work_mode == STAT_WATERING or self.work_mode == STAT_WEEKEND_WATERING:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_answer_help_water[0][0]))
            self.last_invite_water_time = cur
            self.robotStatus.set_last_sleep3_time(cur + 30)
            self.pub_see_command(See.COMMAND_START_SEE)
        else:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_answer_help_water_no[0][0]))
    def help_weed(self):
        if self.work_mode == STAT_WEEDING or self.work_mode == STAT_WEEKEND_WEEDING:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_answer_help_weed[0][0]))
            self.last_invite_water_time = cur
            self.robotStatus.set_last_sleep3_time(cur + 30)
            self.pub_see_command(See.COMMAND_START_SEE)
        else:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_answer_help_weed_no[0][0]))

    def command_query_happen_forest(self, feedback):
        #   玩的非常开心。今天我在%s还捡到%s带回来了。
        current_time = time.localtime()  # 获取本地时间
        day = current_time.tm_mday
        if day in self.forest_result:
            result_1 = self.forest_result[day]
            if 'props' in result_1 and 'mapName' in result_1:
                feedback__format = feedback[0][0] % (result_1['mapName'],result_1['props'])
                self.speak_pub.publish(self._speak_text(feedback__format))
                self.emotion_pub.publish(self._emotion_without_effect(feedback[0][1], 10))
            elif 'mapName' in result_1:
                    feedback =  self.fb.feedback_command_result_in_forest_map_ing
                    feedback__format = feedback[0][0] % result_1['mapName']
                    self.speak_pub.publish(self._speak_text(feedback__format))
                    self.emotion_pub.publish(self._emotion_without_effect(feedback[0][1], 10))
            else:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_command_result_in_forest_ing[0][0]))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_command_result_in_forest_ing[0][1], 10))
        else:
            self.forest_result = {}
            self.speak_pub.publish(self._speak_text(self.fb.feedback_command_result_in_forest_ing[0][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_command_result_in_forest_ing[0][1], 10))

    def get_speak_txt(self,time_str):
        split = time_str.split(":")
        hour = int(split[0])
        minute = split[1]
        speak_txt = str(hour) + self.time_split
        if minute != 0:
            speak_txt = speak_txt + str(minute)
        return speak_txt

    def command_query_wake_time(self, feedback):
        dt_dt = datetime.datetime
        today = dt_dt.today()
        if not is_weekend(today):
            speak_txt = self.get_speak_txt(self.time_json["getUp"])
            feedback__format = feedback[0][0] % speak_txt
            self.speak_pub.publish(self._speak_text(feedback__format))
        else:
            speak_txt = self.get_speak_txt(self.time_json["weekendGetUp"])
            feedback__format = feedback[0][0] % speak_txt
            self.speak_pub.publish(self._speak_text(feedback__format))
        self.emotion_pub.publish(self._emotion_without_effect(feedback[0][1], 5))

    def command_query_sleep_time(self, feedback):
        dt_dt = datetime.datetime
        today = dt_dt.today()
        if not is_weekend(today):
            speak_txt = self.get_speak_txt(self.time_json["sleeping"])
            feedback__format = feedback[0][0] % speak_txt
            self.speak_pub.publish(self._speak_text(feedback__format))
        else:
            speak_txt = self.get_speak_txt(self.time_json["weekendSleeping"])
            feedback__format = feedback[0][0] % speak_txt
            self.speak_pub.publish(self._speak_text(feedback__format))
        self.emotion_pub.publish(self._emotion_without_effect(feedback[0][1], 5))

    def command_query_lunch_time(self, feedback):
        eat_time = self.time_json['noontime']
        split = eat_time.split(":")
        hour = int(split[0])
        minute = split[1]
        speak_txt = str(hour) + self.time_split
        if minute != 0:
            speak_txt = speak_txt + str(minute)
        feedback__format = feedback[0][0] % speak_txt
        self.speak_pub.publish(self._speak_text(feedback__format))
        self.emotion_pub.publish(self._emotion_without_effect(feedback[0][1],5))
    def command_query_dinner_time(self, feedback):
        eat_time = self.time_json['dinner']
        split = eat_time.split(":")
        hour = int(split[0])
        minute = split[1]
        speak_txt = str(hour) + self.time_split
        if minute != 0:
            speak_txt = speak_txt + str(minute)
        feedback__format = feedback[0][0] % speak_txt
        self.speak_pub.publish(self._speak_text(feedback__format))
        #self.emotion_pub.publish(self._emotion_without_effect(feedback[0][1]))

    def command_query_time_to_forest(self, feedback):
        speak_txt = self.get_speak_txt(self.time_json["playing"])
        feedback__format = feedback[0][0] % speak_txt
        self.speak_pub.publish(self._speak_text(feedback__format))
        self.emotion_pub.publish(self._emotion_without_effect(feedback[0][1],5))

    def command_look_heat_tree(self, feedback,cur):
        level_ = self.grow_tree['currLevel']
        if level_ == '结果':
            self.emotion_pub.publish(self._emotion_tree(Emotion.HEART_TREE_EFFECTION_FRUIT,self.grow_tree['fruit'],int(cur+30) ))
        else:
            self.emotion_pub.publish(self._emotion_without_effect(self.tree_level_to_emotion[level_],20))
        #self.speak_pub.publish(self._speak_text(feedback[0][0]))
        self.command_look_heat_tree_props([Emotion.HEART_EFFECTION_FRIEND_FLOWER,Emotion.HEART_EFFECTION_SPRITE_FLOWER
                                           ,Emotion.HEART_EFFECTION_MAGIC_CLAY,Emotion.HEART_EFFECTION_SPRITE_DEW
                                           ,Emotion.HEART_EFFECTION_HEART_WATER])

    def command_look_heat_tree_props(self,emotions):
        time_time = time.time()
        datetime_datetime = datetime.datetime
        if self.grow_tree['friendship_time']:
            dt = datetime_datetime.strptime(self.grow_tree['friendship_time'], "%Y-%m-%d %H:%M:%S")
            # 转换为time.time()
            expired_timestamp = time.mktime(dt.timetuple())
            if expired_timestamp > time_time:
                self.emotion_pub.publish(self._emotion_expired(emotions[0], int(expired_timestamp)))
        if self.grow_tree['sprit_time']:
            dt = datetime_datetime.strptime(self.grow_tree['sprit_time'], "%Y-%m-%d %H:%M:%S")
            # 转换为time.time()
            expired_timestamp = time.mktime(dt.timetuple())
            if expired_timestamp > time_time:
                self.emotion_pub.publish(self._emotion_expired(emotions[1], int(expired_timestamp)))
        if self.grow_tree['soil_time']:
            dt = datetime_datetime.strptime(self.grow_tree['soil_time'], "%Y-%m-%d %H:%M:%S")
            # 转换为time.time()
            expired_timestamp = time.mktime(dt.timetuple())
            if expired_timestamp > time_time:
                self.emotion_pub.publish(self._emotion_expired(emotions[2], int(expired_timestamp)))
        if self.grow_tree['lotus_time']:
            dt = datetime_datetime.strptime(self.grow_tree['lotus_time'], "%Y-%m-%d %H:%M:%S")
            # 转换为time.time()
            expired_timestamp = time.mktime(dt.timetuple())
            if expired_timestamp > time_time:
                self.emotion_pub.publish(self._emotion_expired(emotions[3], int(expired_timestamp)))
        if self.grow_tree['soulwater_time']:
            dt = datetime_datetime.strptime(self.grow_tree['soulwater_time'], "%Y-%m-%d %H:%M:%S")
            # 转换为time.time()
            expired_timestamp = time.mktime(dt.timetuple())
            if expired_timestamp > time_time:
                self.emotion_pub.publish(self._emotion_expired(emotions[4], int(expired_timestamp)))

    def command_query_robot_status(self,brain_w_mode, feedback):
        #   我正在%s
        mode = self.get_robot_work_mode(brain_w_mode)
        self.logger.info("mode: %s" % mode)
        self.logger.info("self.stat_to_speak[mode]: %s" % self.stat_to_speak[mode])
        feedback__format = feedback[0][0] % self.stat_to_speak[mode][0]
        self.speak_pub.publish(self._speak_text(feedback__format))
        self.emotion_pub.publish(self._emotion_without_effect(self.stat_to_speak[mode][1],10))
    def get_robot_work_mode_trans(self,mode):
        return self.stat_to_speak[mode][0]

    def do_dialog(self,msg,cur,dialog_times):
        if self.fb.schedule_task_indicator in msg.lower():
            msg = self.fb.schedule_task_msg_template % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), msg)
            self.logger.info("当前是提醒")
        self.logger.info("自由对话:%s" % msg)

        try:
            if not self.token:
                if len(msg) > 5:
                    index = random.randint(0, len(self.fb.feedback_no_need_bind_dialog) - 1)
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_no_need_bind_dialog[index][0]))
                elif cur - self.last_no_token_dialog >= 2 * 60:
                    self.last_no_token_dialog = cur
                    index = random.randint(0, len(self.fb.feedback_no_need_bind_dialog) - 1)
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_no_need_bind_dialog[index][0]))
                return None
            headers = {
                'Accept'        : 'application/json',
                'Content-Type'  : 'application/json',
                "authorization" : self.token
            }
            backend = ""
            if len(self.mail_body)>0:
                backend = backend + "总共"+str(len(self.mail_body))+"封邮件，"
                i = 1
                for from_addr, subject, body,date in self.mail_body:
                    backend = backend + "邮件" + str(i) + ":" + from_addr + "发的；"
                    i = i+1
            payload = {"userId":self.user_id,"deviceCode":self.device_code,"msg":msg,"lan":self.language,"backend":backend}
            response = requests.post(
                url=    api.say.replace("host-place-holder", self.host),
                headers=headers,
                json=   payload,
                timeout=15)
            if response.status_code == 403:
                self.logger.info("对话say接口403 Forbidden Error，调用一次权限接口")
                self.one_day_refresh_token(True)
                self.speak_pub.publish(self._speak_text(self.fb.feedback_no_need_bind[0][0]))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_no_need_bind[0][1]))
            else:
                response.raise_for_status()
                resp = response.json()["data"]
                if resp:
                    dialog_times.append(cur)
                    if len(dialog_times) > 3:
                        dialog_times.pop(0)
                    if resp["skill"] =='chat':
                        self.speak_pub.publish(self._speak_text(resp["title"]))
                        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_LAUGH,5))
                        self.chat_dialog_sub_sick(self.chat_dialog_turns())
                    elif resp["skill"] =='reminder':
                        self.schedule_task_controller.create_task(resp["cycle_value"], resp["cycle_time"], resp["title"], resp["cycle_type"], resp["label"])
                    elif resp["skill"] =='expl':
                        num = resp["label"]
                        if num:
                            self.logger.info("self.mail_body:%s" % self.mail_body)
                            mail_ = self.mail_body[int(num) - 1]
                            self.speak_pub.publish(self._speak_text(self.fb.feedback_email_speaker[0][0] % (mail_[3],mail_[0],mail_[1],mail_[2])))
                        else:
                            self.speak_pub.publish(self._speak_text(self.fb.feedback_email_no_query[0][0]))
        except Exception as e:
            self.logger.error("聊天 失败: %s" % e)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_no4[0][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_no4[0][1]))

    def get_currentRole(self):
        self.logger.info("获取角色扮演当前角色")
        try:
            if not self.token:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_no_need_bind[0][0]))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_no_need_bind[0][1]))
                return None
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                "authorization": self.token
            }
            payload = {"userId": self.user_id, "deviceCode": self.device_code}
            response = requests.post(
                url=api.currentRole.replace("host-place-holder", self.host),
                headers=headers,
                json=payload,
                timeout=10)
            response.raise_for_status()
            resp = response.json()["data"]
            if resp:
                return resp['roleName']
        except Exception as e:
            self.logger.error("获取角色扮演当前角色 失败: %s" % e)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_no[0][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_no[0][1]))
        #return "小木"
        return None

    def do_roleSay(self, msg):
        self.logger.info("角色扮演:%s" % msg)
        try:
            if not self.token:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_no_need_bind[0][0]))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_no_need_bind[0][1]))
                return None
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                "authorization": self.token
            }
            payload = {"userId": self.user_id, "deviceCode": self.device_code, "msg": msg ,"lan":self.language }
            response = requests.post(
                url=api.roleSay.replace("host-place-holder", self.host),
                headers=headers,
                json=payload,
                timeout=10)
            response.raise_for_status()
            resp = response.json()["data"]
            if resp:
                self.speak_pub.publish(self._speak_text(resp))
                self.chat_dialog_sub_sick(self.chat_dialog_turns())
        except Exception as e:
            self.logger.error("角色扮演 失败: %s" % e)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_no[0][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_no[0][1]))

    def get_call_me_nick(self):
        #if self.nick:
        #    feedback__format = self.fb.feedback_nick[0][0] % self.nick
        feedback__format = self.fb.feedback_nick[0][0]
        self.speak_pub.publish(self._speak_text(feedback__format))
        #else:
        #    self.speak_pub.publish(self._speak_text(self.fb.feedback_no_nick[0][0]))

    def do_nick_refresh(self,check_wifi):
        self.logger.info("刷新昵称")
        if not self.user_id or not check_wifi:
            return None
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                "authorization": self.token
            }
            payload = {"deviceCode": self.device_code}
            response = requests.post(
                url=        api.refreshNick.replace("host-place-holder", self.host),
                headers =   headers,
                json=       payload,
                timeout=    10)
            response.raise_for_status()
            r_json = response.json()
            self.logger.info("每日检查昵称，r_json：%s" % r_json)
            self.nick = r_json["data"]
        except Exception as e:
            self.logger.error("检查昵称失败: %s" % e)
            return None

    def who_are_you(self):
        self.speak_pub.publish(self._speak_text(self.fb.feedback_who_am_i[0][0]))

    def local_persist_last_sick(self, data_path, date):
        try:
            with open(data_path, 'w', encoding='utf-8') as file:
                file.write(date.strftime("%Y-%m-%d"))  # 或者其他初始化操作
            self.sick_day = date
        except Exception as e:
            self.logger.error("保存生病日 失败: %s" % e)

    def local_persist_last_day_off(self, data_path, date):
        try:
            with open(data_path, 'w', encoding='utf-8') as file:
                file.write(date.strftime("%Y-%m-%d"))  # 或者其他初始化操作
            self.day_off = date
        except Exception as e:
            self.logger.error("保存请假日 失败: %s" % e)

    def local_persist_user_id(self, user_id):
        try:
            with open(self.root_dir + api.user_id_path, 'w', encoding='utf-8') as file:
                file.write(str(user_id))  # 或者其他初始化操作
        except Exception as e:
            self.logger.error("保存user_id 失败: %s" % e)

    def local_persist_token(self, token):
        try:
            with open(self.root_dir + api.token_path, 'w', encoding='utf-8') as file:
                file.write(token)  # 或者其他初始化操作
        except Exception as e:
            self.logger.error("保存token 失败: %s" % e)

    '''
    持久化成长之树最新状态
    '''
    def persistence_grow_tree(self, data, data_path):
        try:
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)  # indent使文件更易读
        except Exception as e:
            self.logger.error("持久化心灵之树当前状态失败: %s" % e)

    '''
    加载成长之树最新状态
    '''
    def local_load_grow_tree_info(self, data_path):
        try:
            self.logger.info("5、local_load_grow_tree_info")
            with open(data_path, 'r', encoding='utf-8') as f:
                grow_tree_str = f.read()
                return json.loads(grow_tree_str)
        except FileNotFoundError:
            # 文件不存在，可以创建或进行其他处理
            with open(data_path, 'w', encoding='utf-8') as file:
                init_data = {"id": 1, "currLevel": "种子", "currEnergy": 0,"fruit": 0,
                             "friendship": 0, "friendship_time": "",
                             "sprit": 0, "sprit_time": "",
                             "soil": 0, "soil_time": "",
                             "lotus": 0, "lotus_time": "",
                             "soulwater": 0,"soulwater_time": "",
                             "lastWater": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                json.dump(init_data, file, ensure_ascii=False, indent=2)  # 或者其他初始化操作
                self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_CONNECTION_FOUND, 3))
                return init_data
        except Exception as e:
            self.logger.error("获取心灵之树当前状态失败: %s" % e)
            return None

    def sync_grow_tree_from_plat(self):
        try:
            if not self.token:
                return
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                "authorization": self.token
            }
            payload = {"user_id": self.user_id, "deviceCode": self.device_code}
            response = requests.post(
                url     =  api.getGrowTreeStatus.replace("host-place-holder", self.host),
                headers =  headers,
                json    =  payload,
                timeout=10)
            response.raise_for_status()
            result = response.json()["data"]
            if result:
                # 刷新树的缓存
                if result['friendship']:
                    self.grow_tree['friendship'] = result['friendship']
                    self.grow_tree['friendship_time'] = result['friendshipTime']
                if result['sprit']:
                    self.grow_tree['sprit'] = result['sprit']
                    self.grow_tree['sprit_time'] = result['spritTime']
                if result['soil']:
                    self.grow_tree['soil'] = result['soil']
                    self.grow_tree['soil_time'] = result['soilTime']
                if result['lotus']:
                    self.grow_tree['lotus'] = result['lotus']
                    self.grow_tree['lotus_time'] = result['lotusTime']
                if result['soulwater']:
                    self.grow_tree['soulwater'] = result['soulwater']
                    self.grow_tree['soulwater_time'] = result['soulwaterTime']
                # 持久化树的状态
                self.persistence_grow_tree(self.grow_tree, self.root_dir + api.grow_tree_path)
        except Exception as e:
            self.logger.error("获取心灵之树的状态 失败: %s" % e)

    def one_hour_task(self,check_wifi):
        self.props_expired_transfer_schedule()
        time.sleep(1)
        self.read_lines_then_remove(check_wifi)

    def read_lines_then_remove(self,check_wifi):
        self.logger.info("每小时上报-----------")
        if not self.token or not check_wifi:
            return
        today = datetime.datetime.now()
        # 初始化一个空列表来存储最近12个月的月份
        months = []
        # 计算当前月和前12个月，注意月份是从0开始计数的（0代表1月，11代表12月）
        for i in range(13):
            month = today - timedelta(days=30 * i)  # 假设每个月有30天，这实际上是不精确的，但对于大多数目的足够了。
            month = month.replace(day= 1)  # 确保是每个月的第一天，这样更容易处理月份的开始。
            months.append(month.strftime('%Y%m'))  # 格式化为YYYYMM格式
        months.reverse()
        for index in range(len(months)):
            if not self.token:
                return
            try:
                business_data = []
                i_month = months[index]
                file_path = self.root_dir + api.biz_data + i_month
                if not os.path.exists(file_path):
                    continue
                with open(file_path, 'r', encoding='utf-8') as file:
                    lines = file.readlines()  # 读取
                    for line in lines:
                        data = json.loads(line[line.find("{"):])
                        business_data.append(data)
                if not business_data:
                    if index != len(months) - 1:
                        os.unlink(file_path)
                    continue
                payload = {"mac": "MAC", "user_id": self.user_id, "deviceCode": self.device_code,
                           "lastWater": self.grow_tree['lastWater'],
                           "currLevel": self.grow_tree['currLevel'], "currEnergy": self.grow_tree['currEnergy'],
                           "list": business_data}
                result = self.async_upload_data(payload,self.token)
                if "success" == result:
                    # 重置本地流水文件
                    if index == len(months)-1:
                        content =''
                        with open(file_path, 'r', encoding='utf-8') as file:
                            lasted_lines = file.readlines()  # 读取
                            if len(lasted_lines) > len(business_data):
                                content = lasted_lines[len(business_data):]
                        with open(file_path, 'w', encoding='utf-8') as file:
                            file.writelines(content)
                    else:
                        os.unlink(file_path)
                time.sleep(0.2)
            except Exception as e:
                self.logger.error("每小时上报 失败: '%s' '%s'" % (months[index] ,e))

    def read_lines_then_remove_bak(self):
        if not self.token:
            return
        business_data = []
        with open(self.root_dir + api.biz_data, 'r', encoding='utf-8') as file:
            lines = file.readlines()[:upload_line_number]  # 读取前upload_line_number行
            for line in lines:
                data = json.loads(line)
                business_data.append(data)
        payload = {"mac": "MAC", "user_id": self.user_id, "deviceCode": self.device_code,
                   "currLevel": self.grow_tree['currLevel'], "currEnergy": self.grow_tree['currEnergy'],
                   "list": business_data}
        result = self.async_upload_data( payload,self.token)
        if result:
            # 刷新树的缓存
            self.grow_tree['currLevel'] = result['currLevel']
            self.grow_tree['currEnergy'] = result['currEnergy']
            if result['friendship']:
                self.grow_tree['friendship'] = result['friendship']
                self.grow_tree['friendship_time'] = result['friendshipTime']
            if result['sprit']:
                self.grow_tree['sprit'] = result['sprit']
                self.grow_tree['sprit_time'] = result['spritTime']
            if result['soil']:
                self.grow_tree['soil'] = result['soil']
                self.grow_tree['soil_time'] = result['soilTime']
            if result['lotus']:
                self.grow_tree['lotus'] = result['lotus']
                self.grow_tree['lotus_time'] = result['lotusTime']
            if result['soulwater']:
                self.grow_tree['soulwater'] = result['soulwater']
                self.grow_tree['soulwater_time'] = result['soulwaterTime']
            # 持久化树的状态
            self.persistence_grow_tree(self.grow_tree, self.root_dir + api.grow_tree_path)

            # 重置本地流水文件
            content = lines[upload_line_number:]
            with open(self.root_dir + api.biz_data, 'w', encoding='utf-8') as file:
                file.writelines(content)

    def one_day_task(self,check_wifi):
        self.logger.info("每日任务")
        # 1、检查token
        self.one_day_refresh_token(check_wifi)
        # 2、时间配置
        conf_f = init_time_conf_from_api(self.logger, self.root_dir + api.time_conf_path,self.token,check_wifi,self.host)
        if conf_f:
            self.time_json = local_load_time_conf(self.logger, self.root_dir + api.time_conf_path)
            self.time_json = self.deal_time_json()
        # 3、情感森林 长期不浇水或者除草
        self.long_no_water_schedule()
        # 4、获取最新昵称
        self.do_nick_refresh(check_wifi)


    def one_day_refresh_token(self,check_wifi):
        self.logger.info("每日检查token")
        if not self.user_id or not check_wifi:
            return None
        try:
            payload = {"userId": self.user_id, "deviceCode": self.device_code,"token":self.token}
            response = requests.post(
                url     =   api.refreshToken.replace("host-place-holder", self.host),
                json    =   payload,
                timeout =   10)
            response.raise_for_status()
            r_json = response.json()
            self.logger.info("每日检查token，r_json：%s" % r_json)
            status_ = r_json["status"]
            token_result = r_json["data"]
            if status_ == '101':
                self.user_id = ""
                self.local_persist_user_id(self.user_id)
                self.token = ""
                self.local_persist_token(self.token)
                self.requests.set_token(self.token)
                # 面容信息
                self.person = None
                self.persistence_person_none()
                # 昵称
                self.nick = None
            elif token_result:
                self.user_id = token_result["id"]
                self.local_persist_user_id(self.user_id)
                self.token = token_result["token"]
                self.local_persist_token(self.token)
        except Exception as e:
            self.logger.error("检查token失败: %s" % e)
            return None

    def check_today_water_weed(self):
        today = datetime.datetime.now().strftime('%Y%m')
        file_path = self.root_dir + api.biz_data + today
        if not os.path.exists(file_path):
            return
        lines = []
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()  # 读取
        if not lines:
            return
        # 获取最后两个记录
        if len(lines)>  4:
            lines =lines[-4:]

    def local_load_robot_status(self, data_path):
        try:
            self.logger.info("9、local_load_robot_status")
            with open(data_path, 'r', encoding='utf-8') as f:
                status = f.read().strip()
                self.logger.info("   robot_status: %s" % status)
                if str(status) in value_to_key:
                    return value_to_key[str(status)]
                return STAT_DEFAULT
        except FileNotFoundError:
            # 文件不存在，可以创建或进行其他处理
            with open(data_path, 'w', encoding='utf-8') as file:
                file.write(str(STAT_DEFAULT))
                return STAT_DEFAULT
        except Exception as e:
            self.logger.error("获取日程当前状态失败: %s" % e)
            return STAT_DEFAULT

    def local_persist_robot_status(self,  value):
        try:
            with open(self.status_path, 'w', encoding='utf-8') as file:
                file.write(str(value))  # 或者其他初始化操作
        except Exception as e:
            self.logger.error("保存日程当前状态失败: %s" % e)

    def check_sick_status_vari(self):
        current_time = time.localtime()
        # 示例：获取当前月份的一个随机工作日
        current_mday = current_time.tm_mday
        if not self.sick_day:
            return
        if self.sick_day.month == current_time.tm_mon and self.sick_day.day == current_mday:
            self.logger.info("启动检测-生病中")
            self.sick_or_day_off['sick_flag'] = 1
            self.sick_or_day_off['sick_exp_time'] = int(time.time() + self.sick_inner)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_day_illness[0][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_day_illness[0][1], 20))
            self.logger.info("self.sick_or_day_off['sick_exp_time']：%s" %  self.sick_or_day_off['sick_exp_time'])

    def check_day_off_status_vari(self):
        current_time = time.localtime()
        # 示例：获取当前月份的一个随机工作日
        current_mday = current_time.tm_mday
        if not self.day_off:
            return
        if self.sick_day.month == current_time.tm_mon and self.day_off.day == current_mday:
            self.logger.info("启动检测-请假申请中")
            self.day_off_need_apply = 'yes'

    def now_time(self,feedback):
        current_time = datetime.datetime.now().strftime("%H:%M")
        split = current_time.split(":")
        hour = int(split[0])
        minute = split[1]
        speak_txt = str(hour) + self.time_split
        if minute != 0:
            speak_txt = speak_txt + str(minute)
        feedback__format = feedback[0][0] % speak_txt
        self.speak_pub.publish(self._speak_text(feedback__format))

    def check_bind(self):
        try:
            if not self.user_id:
                return 0
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            payload = {"user_id": self.user_id, "deviceCode": self.device_code}
            response = requests.post(
                url     =  api.checkBind.replace("host-place-holder", self.host),
                headers =  headers,
                json    =  payload,
                timeout=10)
            response.raise_for_status()
            return response.json()["status"]
        except Exception as e:
            self.logger.error("查询设备绑定情况 失败: %s" % e)

    '''
    上传日程数据，并返回平台处理结果
    '''
    def async_upload_data(self, payload, token):
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                "authorization": token
            }
            response = requests.post(
                url=api.uploadDataOnline.replace("host-place-holder", self.host),
                headers=headers,
                json=payload,
                timeout=10)
            if response.status_code == 403:
                self.logger.info("上传日程数据，接口403 Forbidden Error，调用一次权限接口")
                self.one_day_refresh_token(True)
                return None
            else:
                response.raise_for_status()
                return "success"
        except Exception as e:
            self.logger.error("上传日程数据 失败: %s" % e)
            return None

    def local_load_person_data(self,path):
        try:
            self.logger.info("11、local_load_person_data")
            with open(path, 'r', encoding='utf-8') as f:
                person = f.read().strip()
                if person:
                    self.logger.info("   person:%s" % person)
                    self.person = json.loads(person)
        except FileNotFoundError:
            # 文件不存在，可以创建或进行其他处理
            with open(path, 'w', encoding='utf-8') as file:
                file.write("")
        except Exception as e:
            self.logger.error("加載主人信息 失败: %s" % e)

    def persistence_person_data(self, person):
        try:
            self.person = self.person_to_dict(person)
            with open(self.root_dir + api.person_data, 'w', encoding='utf-8') as f:
                json.dump(self.person, f, ensure_ascii = False, indent=2)  # indent使文件更易读
        except Exception as e:
            self.logger.error("保存主人信息 失败: %s" % e)
    def persistence_person_none(self):
        try:
            with open(self.root_dir + api.person_data, 'w', encoding='utf-8') as f:
                file.write("")
        except Exception as e:
            self.logger.error("清空主人信息 失败: %s" % e)

    def person_to_dict(self,person):
        """将Person消息转换为字典"""
        return {
            'emotion': person.emotion,
            'emotion_point': person.emotion_point,
            'sex': person.sex,
            'distance': person.distance,
            'head_direction': person.head_direction,
            'position': person.position,
            # 'bound': person.bound,
            'check_frontal': person.check_frontal,
            'face_height': person.face_height,
            'face_width': person.face_width,
            'ratio_face_wid_hei': person.ratio_face_wid_hei,
            'ratio_nose_face_wid': person.ratio_nose_face_wid,
            'ratio_mouth_wid': person.ratio_mouth_wid,
            'ratio_lefteye_wid': person.ratio_lefteye_wid,
            'ratio_lefteye_hei': person.ratio_lefteye_hei,
            'ratio_righteye_wid': person.ratio_righteye_wid,
            'ratio_righteye_hei': person.ratio_righteye_hei,
            'ratio_lefteyebrow_wid': person.ratio_lefteyebrow_wid,
            'ratio_lefteyebrow_hei': person.ratio_lefteyebrow_hei,
            'ratio_righteyebrow_wid': person.ratio_righteyebrow_wid,
            'ratio_righteyebrow_hei': person.ratio_righteyebrow_hei,
            'ratio_chin_wid': person.ratio_chin_wid,
            'ratio_forehead_wid': person.ratio_forehead_wid
        }

    def act_action_reset(self, dur_time=1):
        action = Action()
        action.time = float(dur_time)
        action.type = Action.TYPE_RESET
        self.action_pub.publish(action)

    def act_xled_brightness(self, time, brightness):
        self.logger.info("act_xled_brightness: %s %s" % (time, brightness))
        action = Action()
        action.time = float(time)
        action.type = Action.TYPE_RELATIVE_MOVE
        action.leds = []
        x = Led()
        x.index = Action.INDEX_X_LED
        x.bright = brightness
        action.leds.append(x)
        self.action_pub.publish(action)

    def act_action_relative(self, dur_time, head_yaw_angle, head_pitch_angle, body_yaw_angle):
        action = Action()
        action.time = float(dur_time)
        action.type = Action.TYPE_RELATIVE_MOVE
        action.servos = []

        if head_yaw_angle != 0:
            servo = Servo()
            servo.index = Action.INDEX_HEAD_YAW
            servo.angle = head_yaw_angle
            action.servos.append(servo)
        if head_pitch_angle != 0:
            servo = Servo()
            servo.index = Action.INDEX_HEAD_PITCH
            servo.angle = head_pitch_angle
            action.servos.append(servo)
        if body_yaw_angle != 0:
            servo = Servo()
            servo.index = Action.INDEX_BODY_YAW
            servo.angle = body_yaw_angle
            action.servos.append(servo)
        self.action_pub.publish(action)

    def act_action_with_hand_relative(self, dur_time, head_yaw_angle, head_pitch_angle, body_yaw_angle, left_hand_angle, right_hand_angle):
        action = Action()
        action.time = float(dur_time)
        action.type = Action.TYPE_RELATIVE_MOVE
        action.servos = []

        if head_yaw_angle != 0:
            servo = Servo()
            servo.index = Action.INDEX_HEAD_YAW
            servo.angle = head_yaw_angle
            action.servos.append(servo)
        if head_pitch_angle != 0:
            servo = Servo()
            servo.index = Action.INDEX_HEAD_PITCH
            servo.angle = head_pitch_angle
            action.servos.append(servo)
        if body_yaw_angle != 0:
            servo = Servo()
            servo.index = Action.INDEX_BODY_YAW
            servo.angle = body_yaw_angle
            action.servos.append(servo)
        if left_hand_angle != 0:
            servo = Servo()
            servo.index = Action.INDEX_LEFT_HAND_YAW
            servo.angle = left_hand_angle
            action.servos.append(servo)
        if right_hand_angle != 0:
            servo = Servo()
            servo.index = Action.INDEX_RIGHT_HAND_YAW
            servo.angle = right_hand_angle
            action.servos.append(servo)
        self.action_pub.publish(action)

    def load_stat_to_speak(self, path):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    json_str = f.read()
                self.s_t_spk = json.loads(json_str)
                self.logger.info('load_stat_to_speak: %s' % self.s_t_spk)
            except Exception as e:
                self.logger.info('load_stat_to_speak: exception %s' % e)
        else:
            self.logger.info('load_stat_to_speak: path not exist')

