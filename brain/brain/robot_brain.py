import email
import imaplib
import importlib
import json
import os
import random
import re
import subprocess
import threading
import time
import uuid
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime

import brain.plat_api as api
import brain.robot_sequence as sq
import rclpy
import requests
from brain.auto_time_syncer import AutoTimeSyncer
from brain.dance_jazz import DanceJazz
from brain.game_321 import Game321
from brain.robot_character import RobotCharacter, CHARACTER_E, CHARACTER_I
from brain.robot_collision import CollisionDetector, FallDetection, HandstandDetector, ShakeDetector
from brain.robot_day_schedule import DaySchedule
from brain.robot_intents import *
from brain.robot_ota import RobotOta
from brain.robot_status import RobotStatus
from brain.schedule_task import ScheduleTaskController
from pywifi import *
from rclpy.node import Node

from robot_interfaces.msg import Sensor, Saw, Action, Emotion, Touch, Speak, Imu, Servo, Person, Listen, See, Led, Rifd, \
    CommandRes, ListenCommand, KeepQuiet, Ota, BatteryStatus, \
    Status
from robot_interfaces.srv import ServoState

#MAC = uuid.UUID(int=uuid.getnode()).hex[-12:]
#SERVER_HOST = 'https://api.timuai.com'
#TALK_HEART_URL = SERVER_HOST + '/user/web/grow-script-text/talk'

#in cm
FAR_DISTANCE = 500
MAX_REMEMBER_PERSON = 100

WORK_MODE_COMMON = 0
WORK_MODE_GAME = 1
WORK_MODE_HEART = 2
WORK_MODE_SLEEP = 3
WORK_MODE_WIFI = 4
WORK_MODE_DANCE = 5
WORK_MODE_BIND = 6
WORK_MODE_ROLE_PLAY = 7
WORK_MODE_GATHER = 8
WORK_MODE_TV_PRE = 9
WORK_MODE_TV = 10
WORK_MODE_MUSIC_PRE = 11
WORK_MODE_MUSIC = 12

COSPLAY_ROLE_MOGU = 'mogu'
COSPLAY_ROLE_WIZARD = 'wizard'
COSPLAY_ROLE_NORMAL = 'normal'

INVITE_DAY_OFF 	= 'day_off'
INVITE_PHYSICAL = 'physical'
INVITE_WATER 	= 'water'
INVITE_WEED 	= 'weed'

class RobotBrain(Node):
    def __init__(self):
        super().__init__('robot_brain')
        self.declare_parameter("root_dir", '/root')
        self.declare_parameter("language", 'zh-Hans')
        self.declare_parameter("character", CHARACTER_E)
        self.root_dir = self.get_parameter("root_dir").get_parameter_value().string_value
        self.language = self.get_parameter("language").get_parameter_value().string_value
        self.get_lang()
        self.host = 'api.timuai.com'
        if self.language == 'zh-Hans':
            self.host = 'cnapi.timuai.com'

        self.device_code  = load_device(self.root_dir + '/asset/data/system')

        self.sensor = self.create_subscription(Sensor, 'sensor', self.sensor_callback,10)
        self.sensor  # prevent unused variable warning
        self.touch = self.create_subscription(Touch, 'touch', self.touch_callback,10)
        self.touch  # prevent unused variable warning
        self.touch = self.create_subscription(Imu, 'imu', self.imu_callback,10)
        self.touch  # prevent unused variable warning
        self.eye = self.create_subscription(Saw, 'saw', self.saw_callback,10)
        self.eye  # prevent unused variable warning
        self.ear = self.create_subscription(Listen, 'listen', self.listen_callback,10)
        self.ear# prevent unused variable warning
        self.rifd = self.create_subscription(Rifd, 'rifd', self.rifd_callback,10)
        self.rifd# prevent unused variable warning
        self.command_res = self.create_subscription(CommandRes, 'brain/command_res', self.command_res_callback,10)
        self.command_res# prevent unused variable warning
        self.battery = self.create_subscription(BatteryStatus, 'battery', self.battery_callback,10)

        self.fb = importlib.import_module(f'brain.robot_feedback_{self.language.replace("-", "_")}')
        self.locale = importlib.import_module(f'brain.locale_{self.language.replace("-", "_")}')
        data_path = self.root_dir + f'/asset/data/embedding_{self.language}.json'
        things_trans_path = self.root_dir + f'/asset/data/things_trans_{self.language}.json'
        stat_to_speak_path = self.root_dir + f'/asset/data/stat_to_speak_{self.language}.json'
        self.repl_punctuation = self.locale.repl_punctuation
        self.repl_no_master = self.locale.repl_no_master
        self.time_split = self.locale.time_split

        logger = self.get_logger()
        self.load_things_trans(things_trans_path)
        self.character = RobotCharacter(logger, self.get_parameter("character").get_parameter_value().integer_value)
        self.robot_intents = RobotIntents(self.language, logger, self.fb, self.locale, data_path)
        self.work_mode = WORK_MODE_COMMON
        self.history_intent=None
        self.history_intent_time = 0

        self.speak_pub = self.create_publisher(Speak, 'speak', 10)
        self.speaker_sub= self.create_subscription(
            Status,
            'speaker/status',
            self.speak_status_callback,
            10)
        self.action_pub = self.create_publisher(Action, 'action', 10)
        self.listen_pub = self.create_publisher(ListenCommand, 'listener/command', 10)
        self.quiet_pub = self.create_publisher(KeepQuiet,'listener/quiet',10)
        self.dance_thread = None
        self.dance_jazz = None

        self.emotion_pub = self.create_publisher(Emotion, 'emote', 10)
        self.eye_pub = self.create_publisher(See, 'eye', 10)
        self.ota_pub = self.create_publisher(Ota, 'ota', 10)

        self.robotStatus = RobotStatus()

        self.start_wifi_connect_time = 0
        # 碰撞检测
        self.collision = CollisionDetector()
        self.last_collision_notify_time = 0
        # 倒地
        self.fall = FallDetection()
        self.last_fall_time = 0
        self.last_continus_fall_count = 0
        self.last_fall_notify_time = 0
        # 悬挂倒立
        self.handstand = HandstandDetector()
        self.last_handstand_time  = 0
        self.last_continus_handstand_count = 0
        self.last_handstand_notify_time = 0
        # 摇晃
        self.shake = ShakeDetector()
        self.last_shake = 0
        self.last_shake_notify_time = 0
        #
        self.last_touch_once_emotion = 0
        self.last_touch_belly_once_emotion = 0

        self.humid_notified_time = 0
        self.temp_notified_time = 0

        self.last_accel_x = 0
        self.last_accel_y = 0
        self.last_accel_z = 0
        self.last_gyro_x = 0
        self.last_gyro_y = 0
        self.last_gyro_z = 0
        self.move_time = 0
        self.rotate_time = 0
        self.last_yaohuang_time = 0

        self.last_person_distance = FAR_DISTANCE
        self.person_count = 0
        self.last_walk_closer_time = 0
        self.last_saw_ges_time = time.time()
        self.last_saw_per_time = time.time()
        self.last_follow_per = 0

        self.last_rec_person_time = 0
        self.history_person = []
        self.talk_heart_user = None

        self.lasted_things = []
        self.last_saw_things_time = 0

        self.game_321 = Game321(self.get_logger())
        self.game_thread = None

        self.cosplay_role = COSPLAY_ROLE_NORMAL
        self.last_rifd_time = 0
        self.get_logger().info('language:"%s"' % self.language)

        # 意图反馈变量
        self.temperature = None
        self.humidity = None
        # 用户询物时间
        self.last_what_this_time = 0

        # 最后一次执行任务

        # 情感关怀
        self.late_night_care_his = {}
        # 百变模式
        self.last_rp_chat_time = 0
        #
        self.listener_mode = ListenCommand.MODE_QUICK

        #
        self.inited = False
        self.grow_tree = {}
        self.grow_tree_path=self.root_dir + '/asset/data/grow_tree.json'
        self.welcome_strategy(self.grow_tree_path)
        #
        self.gather_count = 0
        #
        self.last_person = None
        self.master_person_time = time.time()
        self.master_person_notify_time = 0
        #
        self.greeting_time = 0
        self.greeting_someone_time = 0
        self.greeting_stranger_time = 0
        self.frontal_master_time = 0
        self.frontal_stranger_time = 0
        #
        self.tv_try_count = 0
        self.tv_last_try_time = 0
        self.tv_msgs = []
        self.tv_last_emotion_time = 0
        self.tv_last_no_wifi_emotion_time = 0
        self.tv_last_msg_time = 0
        self.music_try_count = 0
        self.music_last_try_time = 0
        self.music_last_msg_time = 0
        self.music_last_emotion_time = 0
        self.tv_count = 0

        self.is_wifi_conneting = False
        wifi = self.check_wifi()
        self.time_store_path = self.root_dir + '/asset/data/sys_time.json'
        self.get_logger().info('----wifi:"%s"' % wifi)
        
        self.time_syncer = AutoTimeSyncer(self.get_logger())
        
        if wifi:
            self.time_syncer.sync()
            save_sys_time(self.time_store_path)
        else:
            load_sys_time(self.time_store_path)
        self.schedule_task_controller = ScheduleTaskController(self.fb, self.root_dir, logger, self.speak_pub, self.emotion_pub, self.action_pub, self.robot_intents.embedding_model)
        self.daySchedule = DaySchedule(self.language, logger, self.root_dir, self.device_code,
                                       speak_pub=self.speak_pub,
                                       emotion_pub=self.emotion_pub,
                                       eye_pub=self.eye_pub,
                                       action_pub=self.action_pub,
                                       character=self.character,
                                       robotStatus=self.robotStatus,
                                       fb=self.fb,
                                       time_split = self.time_split,
                                       hand_action = self.act_random_hand_action,
                                       grow_tree = self.grow_tree,
                                       check_wifi=wifi,
                                       stat_to_speak_path=stat_to_speak_path,
                                       schedule_task_controller= self.schedule_task_controller)

        self.thinker = self.create_timer(60, self.thinker_callback)
        self.one_hour = self.create_timer(60 * 60, self.upload_callback)
        self.one_day = self.create_timer(24 * 60 * 60, self.one_day_task_callback)
        #
        self.time_9 =   datetime.strptime("09:00:00", "%H:%M:%S").time()
        self.time_15 =  datetime.strptime("20:00:00", "%H:%M:%S").time()
        #
        self.mail_count = 0
        #
        self.lang_comand_trans = {COMMAND_TO_CHINESE: 'zh-Hans', COMMAND_TO_ENGLISH: 'en',COMMAND_TO_GERMAN: 'de' }
        try:
            self.schedule_task_controller.remove_history_task()
        except Exception as e:
            self.get_logger().info('remove_history_task exception:%s' % e)
        self.last_warn_time = datetime.now()
        self.sit_long_count = 0
        self.watch_long_count = 0
        self.health_warn_count = 0
        self.be_quiet = False
        self.last_see_sit_long_time = 0
        #
        self.last_rfid_notify_time = 0
        #
        self.bat_status = None
        self.bat_empty_warn_time = 0
        #
        self.last_no_wifi_dialog = 0
        #1
        self.last_callme_act_time = 0
        self.last_callme_act_flag = 0
        self.last_listen_callback_time = 0
        #2
        self.last_saw_person_act = 0
        #3
        self.last_guess_act_time = 0
        #7
        self.dialog_open_see_time = 0
        self.dialog_times = []

    def speak_status_callback(self, status):
        self.get_logger().info('speaker status:"%s"' % status)
        
        if self.work_mode == WORK_MODE_GAME or self.work_mode == WORK_MODE_DANCE:
            self.get_logger().info('speaker status: cur mode is not common')
            return
        
        if status.status == Status.END_SPEAK:
            emote = Emotion.EMOTION_USUAL
        else:
            emote = Emotion.EMOTION_THINKING
        self.emotion_pub.publish(self._emotion_without_effect(emote, 30))

    def load_things_trans(self, path):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    json_str = f.read()
                self.things_trans = json.loads(json_str)
                self.get_logger().info('load_things_trans: %s' % self.things_trans)
            except Exception as e:
                self.get_logger().info('load_things_trans: exception %s' % e)
        else:
            self.get_logger().info('load_things_trans: path not exist %s' % path)
            

    def print_thread_id(self):
        thread_id = threading.current_thread().ident
        self.get_logger().info("当前线程ID：'%s'" % thread_id)
    def find_person_in_history(self, person):
        index = 0
        for p, last_time, userId in self.history_person:
            ratio = self.find_person(person,p)

            if ratio > 0.8:
                return p, last_time, userId, index
            index += 1
        return (None, 0, None, None)
    def find_person(self,person,p):
        same_count = 0
        if abs(p.face_height - person.face_height) < 0.1:
            same_count += 1
        if abs(p.face_width - person.face_width) < 0.1:
            same_count += 1
        if abs(p.ratio_face_wid_hei - person.ratio_face_wid_hei) < 0.1:
            same_count += 1
        if abs(p.ratio_nose_face_wid - person.ratio_nose_face_wid) < 0.1:
            same_count += 1
        if abs(p.ratio_mouth_wid - person.ratio_mouth_wid) < 0.1:
            same_count += 1
        if abs(p.ratio_lefteye_wid - person.ratio_lefteye_wid) < 0.1:
            same_count += 1
        if abs(p.ratio_lefteye_hei - person.ratio_lefteye_hei) < 0.1:
            same_count += 1
        if abs(p.ratio_righteye_wid - person.ratio_righteye_wid) < 0.1:
            same_count += 1
        if abs(p.ratio_righteye_hei - person.ratio_righteye_hei) < 0.1:
            same_count += 1
        if abs(p.ratio_lefteyebrow_wid - person.ratio_lefteyebrow_wid) < 0.1:
            same_count += 1
        if abs(p.ratio_lefteyebrow_hei - person.ratio_lefteyebrow_hei) < 0.1:
            same_count += 1
        if abs(p.ratio_righteyebrow_wid - person.ratio_righteyebrow_wid) < 0.1:
            same_count += 1
        if abs(p.ratio_righteyebrow_hei - person.ratio_righteyebrow_hei) < 0.1:
            same_count += 1
        if abs(p.ratio_chin_wid - person.ratio_chin_wid) < 0.1:
            same_count += 1
        if abs(p.ratio_forehead_wid - person.ratio_forehead_wid) < 0.1:
            same_count += 1
        ratio = same_count * 1.0 / Person.SPEC_NUM
        self.get_logger().info('find_person_in_history :"%s"' % ratio)
        return ratio

    def do_dance(self):
        self.get_logger().info('in dance thread action service')
        self.dance_jazz = DanceJazz(self.get_logger(), self.act_action_with_hand_relative, self.act_led_brightness)
        self.dance_jazz.start_dance()
        self.act_action_reset()
        self.work_mode = WORK_MODE_COMMON

    def command_res_callback(self, res):
        self.get_logger().info('command_res_callback: %s' % res)
        if res.flag != CommandRes.FLAG_SPEAK:
            return
        if res.type == CommandRes.VOLUME:
            if res.status == CommandRes.STATUS_OK:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_volume_suc[0][0] % res.attr1))
            elif res.status == CommandRes.STATUS_ERROR:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_volume_fail))
        elif res.type == CommandRes.CALIB:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_calib[0][0]))
    
    def battery_callback(self, bat_status):
        self.get_logger().info('battery_callback: %s' % bat_status)
        self.bat_status =  bat_status.status
        cur = time.time()
        if cur - self.bat_empty_warn_time > 60*60 and self.bat_status == BatteryStatus.STATUS_ALMOST_EMPTY:
            self.bat_empty_warn_time = cur
            self.speak_pub.publish(self._speak_text(self.fb.feedback_bat_empty_warn[0][0]))
    def command_battery_status(self):
        if not self.bat_status:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_no[0][0]))
            return
        text = ''
        if self.bat_status == BatteryStatus.STATUS_CHARGING:
            text = self.fb.feedback_chargeing[0][0]
        elif self.bat_status == BatteryStatus.STATUS_FULL:
            text = self.fb.feedback_full[0][0]
        else:
            text = self.fb.feedback_baterry[0][0]
        self.speak_pub.publish(self._speak_text(text))

    def rifd_callback(self, rifd):
        if len(rifd.rifd_uid) > 0:
            self.get_logger().info('rifd_callback: %s' % rifd)
        time_time = time.time()
        if time_time - self.last_rfid_notify_time < 40:
            self.last_rfid_notify_time =  time_time
            return
        self.last_rfid_notify_time = time_time
        #TODO:check rifd is our
        #TODO:use rifd type
        if rifd.rifd_uid in ['77006C06','CE814FEF','3E404EEF']:
            #self.act_cosplay_mogu()
            self.last_rifd_time = time_time
        elif rifd.rifd_uid in ['BEE549EF','8ED94FEF']:
            #self.act_cosplay_wizard()
            self.last_rifd_time = time_time
        self.rfid_type(rifd.rifd_uid)
        #self.rfid_type_save(rifd.rifd_uid,1)

    def act_cosplay_mogu(self):
        if self.cosplay_role == COSPLAY_ROLE_MOGU:
            return
        self.get_logger().info('act_cosplay_mogu')
        self.cosplay_role = COSPLAY_ROLE_MOGU
        #self.speak_pub.publish(self._speak_asset(f'touShi_moGu2{self.res_suffix}.wav'))
        self.emotion_pub.publish(self._emotion_without_effect(
            Emotion.EMOTION_EFFECT_MOGU))

    def act_cosplay_wizard(self):
        if self.cosplay_role == COSPLAY_ROLE_WIZARD:
            return
        self.get_logger().info('act_cosplay_wizard')
        self.cosplay_role = COSPLAY_ROLE_WIZARD
        #self.speak_pub.publish(self._speak_asset(f'touShi_huaDuoMao{self.res_suffix}.wav'))
        #self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_TSUNDERE))

    def act_cosplay_normal(self):
        if self.cosplay_role == COSPLAY_ROLE_NORMAL:
            return
        self.get_logger().info('act_cosplay_normal')
        self.cosplay_role = COSPLAY_ROLE_NORMAL

    def touch_callback(self, touch_data):
        if self.work_mode == WORK_MODE_DANCE:
            return
        #单次轻拍头 抚摸头 多次拍头(master) 摸肚子(master)
        if self.check_touch_head(touch_data):
            return
        if self.check_touch_belly(touch_data):
            return
    def sensor_callback(self, sensor_data):
        if self.work_mode == WORK_MODE_DANCE:
            return
        #self.get_logger().info('receive sense data: ')
        self.check_temperature(sensor_data)
        self.check_humidity(sensor_data)

    def imu_callback(self, imu_data):
        if self.work_mode == WORK_MODE_DANCE or self.inited == False:
            return
        #self.check_imu(imu_data)
        self.check_collision_act(imu_data)

    def check_imu(self, sensor_data):
        #init data
        #self.get_logger().info('imu data: "%.2f" "%.2f" "%.2f"' % (sensor_data.accel_x, sensor_data.accel_y, sensor_data.accel_z))
        #self.get_logger().info('imu data: "%.2f" "%.2f" "%.2f"' % (sensor_data.gyro_x, sensor_data.gyro_y, sensor_data.gyro_z))

        if abs(self.last_accel_x - sensor_data.accel_x) > 2 or abs(self.last_accel_y - sensor_data.accel_y) > 2 or abs(self.last_accel_z - sensor_data.accel_z) > 2:
            self.move_time += 1
        if abs(self.last_gyro_x - sensor_data.gyro_x) > 2 or abs(self.last_gyro_y - sensor_data.gyro_y) > 2 or abs(self.last_gyro_z - sensor_data.gyro_z) > 2:
            self.rotate_time += 1
        if self.move_time > 2 or self.rotate_time > 2:
            self.move_time = 0
            self.rotate_time = 0
            self.get_logger().info('robot is moving or rotating')
            # self.copy_imu_2_last(sensor_data)
            self.act_yaohuang()
            return True
        self.copy_imu_2_last(sensor_data)
        return False
    def copy_imu_2_last(self, sensor_data):
        self.last_accel_x = sensor_data.accel_x
        self.last_accel_y = sensor_data.accel_y
        self.last_accel_z = sensor_data.accel_z
        self.last_gyro_x = sensor_data.gyro_x
        self.last_gyro_y = sensor_data.gyro_y
        self.last_gyro_z = sensor_data.gyro_z

    def check_humidity(self, sensor_data):
        self.humidity = sensor_data.humidity
        if sensor_data.humidity <31:
            self.get_logger().info('too dry')
            self.act_dry()
            return True
        elif sensor_data.humidity > 70:
            self.get_logger().info('too humid')
            self.act_humid()
            return True
        return False

    def check_temperature(self, sensor_data):
        self.temperature = sensor_data.temperature
        if sensor_data.temperature > 32:
            #self.get_logger().info('too hot')
            self.act_hot()
            return True
        elif sensor_data.temperature < -10:
            #self.get_logger().info('too cold')
            self.act_cold()
            return True
        return False

    def check_touch_belly(self, sensor_data):
        if sensor_data.belly_touch_state == 0:
            return
        
        if self.is_sleep_time():
            self.get_logger().info('should tell user to sleep')
            self.act_touch_belly_night()
        else:
            funcs = [self.act_touch_belly_long, self.act_touch_belly_once, self.act_touch_belly_triple]
            index = random.randint(0, len(funcs) - 1)
            funcs[index]()
        
    def is_sleep_time(self):
        #return time.localtime().tm_hour > 22
        mode = self.daySchedule.get_robot_work_mode(self.work_mode)
        return  mode == 11 or mode == 17

    def check_touch_head(self, sensor_data):
        if sensor_data.head_touch_state == 0:
            return
        
        if self.is_sleep_time():
            self.get_logger().info('should tell user to sleep')
            self.act_touch_head_night()
        else:
            funcs = [self.act_touch_head_long, self.act_touch_head_once, self.act_touch_head_triple, self.act_touch_head_slow]
            index = random.randint(0, len(funcs) - 1)
            funcs[index]()
            
        return False

    def connect_wifi(self, ssid, password):
        try:
            
            # 0. 先清理可能存在的同名旧连接配置
            subprocess.run(['nmcli', 'connection', 'delete', ssid], 
                       check=False, stderr=subprocess.DEVNULL)
            time.sleep(0.5)

            # 1. 创建连接配置，明确绑定到 wlan0
            add_cmd = [
                'nmcli', 'connection', 'add',
                'type', 'wifi',
                'ifname', 'wlan0',           # 强制使用 wlan0
                'con-name', ssid,            # 连接名称
                'ssid', ssid,                # WiFi 名称
                'wifi-sec.key-mgmt', 'wpa-psk',
                'wifi-sec.psk', password
            ]
            result_add = subprocess.run(add_cmd, capture_output=True, text=True)
        
            if result_add.returncode != 0:
                self.get_logger().info(f"❌ 创建连接配置失败: {result_add.stderr}")
                self.speak_pub.publish(self._speak_text(self.fb.feedback_connect_wifi_failed[0][0]))
                
                self.is_wifi_conneting = False
                return False

            # 2. 激活连接
            result_up = subprocess.run(
                ['nmcli', 'connection', 'up', ssid],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if result_up.returncode == 0:
                self.get_logger().info(f"✅ 成功连接到 {ssid}")
                self.act_wifi_connected()
                return True
            else:
                # 连接失败，清理掉刚创建的连接配置
                subprocess.run(['nmcli', 'connection', 'delete', ssid], 
                           check=False, stderr=subprocess.DEVNULL)
                self.get_logger().info(f"❌ 连接失败: {result_up.stderr}")
                self.speak_pub.publish(self._speak_text(self.fb.feedback_connect_wifi_failed[0][0]))
                
                self.is_wifi_conneting = False
                return False
        

        except subprocess.TimeoutExpired:
            # 超时时清理连接配置
            subprocess.run(['nmcli', 'connection', 'delete', ssid], 
                       check=False, stderr=subprocess.DEVNULL)
            self.get_logger().info("⏰ 连接超时，请检查网络或密码")
            self.act_wifi_connect_timeout()
            return False
        except Exception as e:
            self.get_logger().info(f"⚠️ 执行出错: {e}")
            self.speak_pub.publish(self._speak_text(self.fb.feedback_connect_wifi_failed[0][0]))
            self.is_wifi_conneting = False
            return False
        

    def act_disconnect_wifi_pre(self,cur):
        self.speak_pub.publish(self._speak_text(self.fb.feedback_wifi_disconnected_confirm[0][0]))
        self.history_intent_time = cur
        self.history_intent = self.robot_intents.create_disconnect_wifi()
    
    def act_disconnect_wifi_do(self):
        try:
            # 获取所有 WiFi 连接的名称（包括非活动的）
            result = subprocess.run(
                ['nmcli', '-g', 'NAME', 'connection', 'show'],
                capture_output=True, text=True
            )
        
            deleted = 0
            for conn_name in result.stdout.strip().splitlines():
                if not conn_name:
                    continue
                self.get_logger().info(f"🔌 正在删除连接中: {conn_name}")
                # 直接删除每个连接
                del_result = subprocess.run(
                    ['nmcli', 'connection', 'delete', conn_name],
                    capture_output=True
                )
                if del_result.returncode == 0:
                    deleted += 1
                    self.get_logger().info(f"🔌 已删除连接: {conn_name}")
        
            self.get_logger().info(f"✅ 已删除 {deleted} 个 WiFi 连接")
        
        except Exception as e:
            self.get_logger().info(f"⚠️ 断开 WiFi 时出错: {e}")
    
        self.speak_pub.publish(self._speak_text(self.fb.feedback_wifi_disconnected[0][0]))
    
    def act_disconnect_wifi_cancel(self):
        self.speak_pub.publish(self._speak_text(self.fb.feedback_cancel[0][0]))
        if self.history_intent and self.history_intent.command == COMMAND_DIS_CONNECT_WIFI:
            self.history_intent = None
    def act_command_cancel_auto(self,cur):
        if not self.history_intent:
            return
        if self.history_intent.command == COMMAND_DIS_CONNECT_WIFI and cur - self.history_intent_time > 30:
            self.get_logger().info('断开网络指令已自动取消')
            self.history_intent = None
        elif self.history_intent.command == COMMAND_UPGRADE and cur - self.history_intent_time > 30:
            self.get_logger().info('升级指令已自动取消')
            self.history_intent = None
        elif self.history_intent.command == COMMAND_SHUTDOWN and cur - self.history_intent_time > 30:
            self.get_logger().info('关机指令已自动取消')
            self.history_intent = None

    def act_upgrade_pre(self,cur):
        self.speak_pub.publish(self._speak_text(self.fb.feedback_upgrade_confirm[0][0]))
        self.history_intent_time = cur
        self.history_intent = self.robot_intents.create_upgrade()
    def act_upgrade_do(self):
        ota_data = Ota()
        self.ota_pub.publish(ota_data)
    def act_upgrade_cancel(self):
        self.speak_pub.publish(self._speak_text(self.fb.feedback_cancel[0][0]))
        if self.history_intent and self.history_intent.command == COMMAND_UPGRADE:
            self.history_intent = None

    def act_shutdown_pre(self,cur):
        self.speak_pub.publish(self._speak_text(self.fb.feedback_shutdown_confirm[0][0]))
        self.history_intent_time = cur
        self.history_intent = self.robot_intents.create_shutdown()
    def act_shutdown_do(self):
        os.system("exit")
    def act_shutdown_cancel(self):
        self.speak_pub.publish(self._speak_text(self.fb.feedback_cancel[0][0]))
        if self.history_intent and self.history_intent.command == COMMAND_SHUTDOWN:
            self.history_intent = None

    def check_wifi(self):
        wifi = PyWiFi()
        for ifaces in wifi.interfaces():
            self.get_logger().info('check wifi status: "%s"' % ifaces.status())
            self.get_logger().info('check wifi interface: "%s"' % ifaces.name())
            if ifaces.status() == const.IFACE_CONNECTED:
                return True
        return False

    def saw_callback(self, saw_data):
        self.get_logger().info('I saw: %s, 打盹状态：%s ' % (saw_data,self.robotStatus.get_enjoy_type() ))
        if saw_data.scrap_file:
            self.upload_scrap(saw_data,saw_data.scrap_file)
        #if self.robotStatus.get_enjoy_type() >= 3:
        #    return
        self.print_thread_id()
        what_is_this_flag = None
        cur1 = time.time()
        self.get_logger().info('time.time() - self.last_what_this_time: "%s"' % (cur1 - self.last_what_this_time) )
        things = saw_data.things
        if len(things) > 0 and cur1 - self.last_what_this_time <= 2 * 60:
            what_is_this_flag = 1
            self.last_what_this_time = 0
        saw_person_count = len(saw_data.persons)
        if self.work_mode == WORK_MODE_WIFI:
            self.get_logger().info('cur is wifi connect mode')
            if self.is_wifi_conneting:
                self.get_logger().info('wifi is connecting')
                return
            if what_is_this_flag:
                index = random.randint(0, len(self.fb.feedback_no2) - 1)
                self.speak_pub.publish(self._speak_text(self.fb.feedback_no2[index][0]))
            wifi_info = saw_data.wifi_info
            if len(wifi_info) > 0:
                self.speak_pub.publish(self._speak_asset("smok.wav"))
                try:
                    info = wifi_info.split('|')
                    ssid = info[0]
                    password = info[1]
                    self.get_logger().info('wifi info: "%s" "%s"' % (ssid, password))
                    self.is_wifi_conneting = True
                    self.connect_wifi(ssid, password)
                except Exception as e:
                    self.get_logger().error("连接网络失败: %s" % e)
            return
        elif self.work_mode == WORK_MODE_GAME:
            self.get_logger().info('cur is in game mode')
            if what_is_this_flag:
                index = random.randint(0, len(self.fb.feedback_no2) - 1)
                self.speak_pub.publish(self._speak_text(self.fb.feedback_no2[index][0]))
            if saw_person_count == 0:
                return
            person = saw_data.persons[0]
            if self.game_321.verify_command(person.head_direction):
                self.get_logger().info('epoch win')
            return
        elif self.work_mode == WORK_MODE_DANCE:
            self.get_logger().info('cur is in dance mode')
            if what_is_this_flag:
                index = random.randint(0, len(self.fb.feedback_no2) - 1)
                self.speak_pub.publish(self._speak_text(self.fb.feedback_no2[index][0]))
            return
        elif self.work_mode == WORK_MODE_BIND:
            self.get_logger().info('cur is bind app mode')
            user_id = saw_data.wifi_info
            if what_is_this_flag:
                index = random.randint(0, len(self.fb.feedback_no2) - 1)
                self.speak_pub.publish(self._speak_text(self.fb.feedback_no2[index][0]))
            if len(user_id) > 0:
                self.get_logger().info('bind qr info: "%s" ' % user_id)
                self.speak_pub.publish(self._speak_asset("smok.wav"))
                bind_res = self.daySchedule.do_bind_app(user_id)
                self.work_mode = WORK_MODE_COMMON
                self.pub_see_command(See.COMMAND_USUAL)
                self.pub_see_command(See.COMMAND_STOP_SEE)
                if not self.daySchedule.person:
                    self.gather_intro(bind_res,cur1)
            return
        elif self.work_mode == WORK_MODE_GATHER:
            if saw_person_count == 0:
                if self.gather_count==0:
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_gather_fail1[0][0]))
                elif self.gather_count==1:
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_gather_fail2[0][0]))
                elif self.gather_count == 2:
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_gather_fail3[0][0]))
                    self.work_mode = WORK_MODE_COMMON
                self.gather_count += 1
            else:
                self.daySchedule.persistence_person_data(saw_data.persons[0])
                self.speak_pub.publish(self._speak_text(self.fb.feedback_gather_success[0][0]))
                self.work_mode = WORK_MODE_COMMON
                self.master_person_time = cur1
            return
        elif self.work_mode == WORK_MODE_TV_PRE:
            self.watch_pre_to_tv(saw_data.things,cur1)
            return
        elif self.work_mode == WORK_MODE_TV:
            #if not self.check_wifi():
            self.watch_tv_no_wifi(saw_data,cur1)
            return
        self.act_exit_sleep()
        cur = time.time()
        self.get_logger().info('what_is_this_flag: "%s" ' % what_is_this_flag)
        if what_is_this_flag:
            self.act_what_is_this(saw_data)
        if saw_person_count == 1 and (cur - self.last_follow_per) > self.character.get_follow_per_min(): #3s
            self.last_follow_per = cur
            #self.act_action_fllow_person(saw_data.persons[0].position)
            # 邀请
            his_flag = None
            #if self.daySchedule.person and self.know_person_sim(saw_data.persons[0], self.daySchedule.person) > 0.6:
            his_flag = self.daySchedule.do_invite_when_saw_person(cur)
            self.get_logger().info('self.daySchedule.person：%s ,invite_flag: "%s" ' % (self.daySchedule.person,his_flag))
            self.deal_his_flag(cur,his_flag)
            # 表情转意图
            if not his_flag and self.work_mode != WORK_MODE_HEART and self.work_mode != WORK_MODE_ROLE_PLAY:
                self.emotion_to_intents(cur,saw_data.persons[0].emotion)
            elif cur - self.last_saw_person_act > 10 * 60:
                self.last_saw_person_act = cur
                self.act_action_reset()
                time.sleep(0.5)
                self.act_action_with_hand_relative(0.5,0,0,0,0,80)
                time.sleep(0.5)
                self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, -30)
                time.sleep(0.5)
                self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, 30)
                time.sleep(0.5)
                self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, -80)
                time.sleep(0.5)
                self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, 80)
                time.sleep(0.5)
                self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, -30)
                time.sleep(0.5)
                self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, 30)
                time.sleep(0.5)
                self.act_action_with_hand_relative(0.5, 0, 0, 0, 0, -80)
        if cur - self.last_saw_ges_time > self.character.get_ges_inter_min():
            if saw_data.gesture == Saw.GESTURE_LOVE:
                self.act_gesture_love()
                self.last_saw_ges_time = cur
            elif saw_data.gesture == Saw.GESTURE_POP:
                self.act_gesture_pop()
                self.last_saw_ges_time = cur
            elif saw_data.gesture == Saw.GESTURE_WATER:
                self.act_gesture_watering(cur)
                self.last_saw_ges_time = cur
            elif saw_data.gesture == Saw.GESTURE_WEED:
                self.act_gesture_weeding(cur)
                self.last_saw_ges_time = cur
        #
        self.do_see_dog_things_act(cur,things)
        self.do_care(saw_data)
        if cur - self.last_saw_per_time > self.character.get_per_inter_min(): #10s
            if saw_person_count > 1:
                self.get_logger().info('I saw many person')
                self.last_saw_per_time = cur
                self.last_person = self.daySchedule.person_to_dict(saw_data.persons[0])
                #self.act_saw_multi_person()
            elif saw_person_count == 0:
                self.person_count = 0
                self.last_person_distance = FAR_DISTANCE
            else:
                self.last_saw_per_time = cur
                person = saw_data.persons[0]
                self.last_person = self.daySchedule.person_to_dict(person)
                # 认识人&正面对视
                cur_time = datetime.strptime(datetime.now().strftime("%H:%M:%S"), "%H:%M:%S").time()
                if cur_time < self.time_9 or cur_time > self.time_15:
                    return
                # greeting 0:未识别  1是master 2是熟人 3是陌生人
                self.interaction_with_person(self.person_identity(person,cur),person, cur)
                #self.know_person(saw_data.persons[0], cur)
                # 正面的
                #self.check_frontal_act(is_master,saw_data.persons[0])


    def listen_callback(self, listen_data):
        text = listen_data.data
        cur = time.time()
        self.get_logger().info('I hear: %s,self.work_mode:%s' % (listen_data,self.work_mode))
        self.robotStatus.set_last_busy_time(cur)
        self.last_listen_callback_time = cur
        if listen_data.type == Listen.SETUP:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_setup[0][0]))
            return
        if self.work_mode == WORK_MODE_MUSIC_PRE and listen_data.type == Listen.MUSIC_UP:
            self.pre_to_music(True,cur)
        if self.work_mode == WORK_MODE_MUSIC and listen_data.type == Listen.MUSIC_UP:
            self.music_emotion(cur)
            return
        if listen_data.type == Listen.WAKE_UP:
            self.get_logger().info('i hear call me, stop everything')
            if self.work_mode == WORK_MODE_GAME:
                self.act_stop_game()
            if self.work_mode == WORK_MODE_HEART:
                self.act_stop_heart()
            #if self.work_mode == WORK_MODE_WIFI:
                #self.act_wifi_connect_tim eout()
            if self.work_mode == WORK_MODE_DANCE:
                self.act_stop_dance()
            if self.work_mode == WORK_MODE_TV:
                self.tv_last_msg_time = cur
                self.speak_pub.publish(self._speak_asset("en.wav"))
                self.history_intent = self.robot_intents.create_watch_tv_say()
                return
            if self.work_mode == WORK_MODE_MUSIC:
                self.music_last_msg_time = cur
                self.speak_pub.publish(self._speak_asset("en.wav"))
                self.history_intent = self.robot_intents.create_music_say()
                return
            else:
                self.act_call_me(cur)
                return

        if listen_data.type == Listen.LISTEN_TEXT and cur - self.dialog_open_see_time > 30 * 60:
            self.get_logger().info('self.dialog_times: %s' % self.dialog_times )
            if len(self.dialog_times) >= 3 and cur - self.dialog_times[0] <= 5 * 60:
                self.dialog_open_see_time = cur
                self.robotStatus.set_last_sleep3_time(time.time())
                self.pub_see_command(See.COMMAND_START_SEE)

        text_emb = self.robot_intents.embedding_another(text)

        most_intent = self.robot_intents.get_most_intent(text_emb)

        if not most_intent:
            self.get_logger().info('not matched any intent	, 	self.work_mode: %s' % self.work_mode )
            if len(text) <= 1:
                return
            if self.work_mode == WORK_MODE_HEART:
                self.get_logger().info('we are talking heart: text: %s' % text)
                self.act_talk_heart(text_emb)
            elif self.work_mode == WORK_MODE_ROLE_PLAY:
                self.robotStatus.set_last_sleep3_time(cur + 60)
                self.daySchedule.do_roleSay(text)
            elif self.work_mode == WORK_MODE_TV:
                if len(text) <= 2:
                    return
                self.tv_last_msg_time = cur
                self.get_logger().info('not most_intent self.history_intent %s' % self.history_intent)
                if self.history_intent and COMMAND_WATCH_TV_SAY == self.history_intent.command:
                    if self.check_wifi():
                        self.watch_tv_say(text)
                    self.history_intent = None
                else:
                    self.watch_tv_emotion(text,cur)
                    self.watch_tv_save_msgs(text, cur)
            elif self.work_mode == WORK_MODE_MUSIC:
                if len(text) <= 2:
                    return
                self.music_last_msg_time = cur
                self.get_logger().info('not most_intent self.history_intent %s' % self.history_intent)
                if self.history_intent and COMMAND_MUSIC_SAY == self.history_intent.command:
                    if self.check_wifi():
                        self.music_say(text)
                    self.history_intent = None
            else:
                if len(text) <= 1:
                    return
                #elif 3 < len(text) <= 4:
                #    self.act_feedback_common(self.fb.feedback_no3)
                elif not self.check_wifi():
                    self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_THINKING, 30))
                    nowifi_intent = self.robot_intents.get_most_nowifi_intent(text_emb)
                    if nowifi_intent:
                        if nowifi_intent.feedback:
                            self.act_intent_feedback(nowifi_intent.feedback)
                            time.sleep(1)
                        if nowifi_intent.command:
                            nowifi_command = nowifi_intent.command
                            if COMMAND_NOWIFI_STORY == nowifi_command:
                                self.get_logger().info('no wifi story')
                                index = random.randint(0, len(self.fb.feedback_answer_nowifi_story) - 1)
                                feedback_ = self.fb.feedback_answer_nowifi_story[index][0]
                                self.speak_pub.publish(self._speak_text(feedback_))
                            elif COMMAND_NOWIFI_POETRY == nowifi_command:
                                self.get_logger().info('no wifi poetey')
                                index = random.randint(0, len(self.fb.feedback_answer_nowifi_poetry) - 1)
                                feedback_ = self.fb.feedback_answer_nowifi_poetry[index][0]
                                self.speak_pub.publish(self._speak_text(feedback_))
                            elif COMMAND_NOWIFI_JOKE == nowifi_command:
                                self.get_logger().info('no wifi joke')
                                index = random.randint(0, len(self.fb.feedback_answer_nowifi_joke) - 1)
                                feedback_ = self.fb.feedback_answer_nowifi_joke[index][0]
                                self.speak_pub.publish(self._speak_text(feedback_))
                    elif listen_data.type == Listen.LISTEN_TEXT and cur - self.last_no_wifi_dialog >= 2 * 60:
                        self.last_no_wifi_dialog = cur
                        index = random.randint(0, len(self.fb.feedback_no_need_wifi_dialog) - 1)
                        self.speak_pub.publish(self._speak_text(self.fb.feedback_no_need_wifi_dialog[index][0]))
                elif listen_data.type != Listen.GUESS_TEXT:
                    # self.speak_pub.publish(self._speak_text(self.fb.feedback_no5[0][0]))
                    self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_THINKING, 30))
                    self.daySchedule.do_dialog(text,cur,self.dialog_times)
            return

        if listen_data.type == Listen.GUESS_TEXT and cur - self.last_guess_act_time > 10 * 60:
            self.act_action_reset()
            time.sleep(0.5)
            self.last_guess_act_time = cur
            index = random.randint(0, 1)
            if index == 0:
                self.act_action_relative(0.5, 30, 0, 0)
                time.sleep(0.5)
                self.act_action_relative(0.5, -30, 0, 0)
            else:
                self.act_action_relative(0.5, -30, 0, 0)
                time.sleep(0.5)
                self.act_action_relative(0.5, 30, 0, 0)

        if most_intent.feedback:
            self.act_intent_feedback(most_intent.feedback)
            time.sleep(1)
        if most_intent.command:
            command = most_intent.command
            if self.work_mode == WORK_MODE_TV:
                self.tv_last_msg_time = cur
                if COMMAND_STOP_WATCH_TV == command:
                    self.get_logger().info('most_intent stop watch tv')
                    self.stop_watch_tv(self.fb.feedback_stop_tv)
                else:
                    self.get_logger().info('most_intent self.history_intent %s' % self.history_intent)
                    if self.history_intent and COMMAND_WATCH_TV_SAY == self.history_intent.command:
                        if self.check_wifi():
                            self.watch_tv_say(text)
                        self.history_intent = None
                    else:
                        self.watch_tv_emotion(text,cur)
                        self.watch_tv_save_msgs(text, cur)
                return
            elif self.work_mode == WORK_MODE_MUSIC:
                self.music_last_msg_time = cur
                if COMMAND_STOP_LISTEN_MUSIC == command:
                    self.get_logger().info('most_intent stop watch music')
                    self.stop_music(self.fb.feedback_stop_music)
                else:
                    self.get_logger().info('most_intent self.history_intent %s' % self.history_intent)
                    if self.history_intent and COMMAND_MUSIC_SAY == self.history_intent.command:
                        if self.check_wifi():
                            self.music_say(text)
                        self.history_intent = None
                return

            if isinstance(command, sq.RobotSequences):
                self.get_logger().info('matched sequence')
                self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_THINKING, 30))
                self.talk_seq = command
                self.talk_seq.start(text_emb)
                self.act_talk_heart(text_emb)

                self.listen_pub.publish(self._listenCommand(ListenCommand.MODE_EXACT))
                self.listener_mode = ListenCommand.MODE_EXACT
                self.get_logger().info('isinstance self.work_mode: %s' % self.work_mode)
                return

            if COMMAND_DO_HIS == command:
                self.get_logger().info('self.history_intent %s' % self.history_intent)
                if self.history_intent:
                    if self.history_intent.feedback:
                        self.act_intent_feedback(self.history_intent.feedback)
                    his_c = self.history_intent.command
                    self.history_intent = None
                    if len(his_c) > 0:
                        self.get_logger().info('cur - self.history_intent_time %s' % (cur - self.history_intent_time) )
                        if COMMAND_DO_GAME == his_c:
                            self.get_logger().info('enter game because his intent')
                            self.act_game()
                        elif COMMAND_ENTER_HEART == his_c:
                            self.get_logger().info('enter heart because his intent')
                            self.act_talk_heart()
                            return
                        elif COMMAND_CONNECT_WIFI == his_c:
                            self.get_logger().info('enter wifi because his intent')
                            self.act_connect_wifi()
                            return
                        elif COMMAND_DO_DANCE == his_c:
                            self.get_logger().info('enter dance because his intent')
                            self.act_dance()
                            return
                        elif COMMAND_DAY_OFF == his_c and cur - self.history_intent_time <= 50:
                            self.get_logger().info('enter day_off_ because his intent')
                            self.daySchedule.day_off_yes_or_no_callback(cur,'yes')
                            return
                        elif COMMAND_GATHER == his_c and cur - self.history_intent_time <= 120:
                            self.get_logger().info('enter command_gather')
                            self.last_saw_per_time = cur
                            self.gather_agree()
                            return
                        elif COMMAND_DIS_CONNECT_WIFI == his_c:
                            self.get_logger().info('disconnect wifi')
                            self.act_disconnect_wifi_do()
                            return
                        elif COMMAND_UPGRADE == his_c:
                            self.get_logger().info('upgrade')
                            self.act_upgrade_do()
                            return
                        elif COMMAND_SHUTDOWN == his_c:
                            self.get_logger().info('shutdown')
                            self.act_shutdown_do()
                            return
                else:
                    self.get_logger().info('nothin todo because no his intent')
            elif COMMAND_CANCEL_HIS == command:
                if self.history_intent:
                    his_c = self.history_intent.command
                    self.history_intent = None
                    self.get_logger().info('cur - self.history_intent_time %s' % (cur - self.history_intent_time))
                    if len(his_c) > 0:
                        if COMMAND_DAY_OFF == his_c and cur - self.history_intent_time <= 50:
                            self.daySchedule.day_off_yes_or_no_callback(cur,'no')
                        elif COMMAND_GATHER == his_c and cur - self.history_intent_time <= 100:
                            self.gather_refuse()
                        elif COMMAND_DIS_CONNECT_WIFI == his_c:
                            self.get_logger().info('cancel disconnect wifi')
                            self.act_disconnect_wifi_cancel()
                        elif COMMAND_UPGRADE == his_c:
                            self.get_logger().info('cancel upgrade')
                            self.act_upgrade_cancel()
                        elif COMMAND_SHUTDOWN == his_c:
                            self.get_logger().info('cancel shutdown')
                            self.act_shutdown_cancel()
                            return
                self.get_logger().info('user canceled his intent')
            elif COMMAND_DO_GAME == command:
                self.get_logger().info('user enter game')
                self.act_game()
            elif COMMAND_CANCEL_GAME == command:
                if self.work_mode == WORK_MODE_GAME:
                    self.get_logger().info('user stop game')
                    self.act_stop_game()
                if self.work_mode == WORK_MODE_HEART:
                    self.get_logger().info('user stop heart')
                    self.act_stop_heart()
            elif COMMAND_ENTER_HEART == command:
                self.get_logger().info('user enter talk heart')
                self.act_talk_heart()
                return
            elif COMMAND_CONNECT_WIFI == command:
                self.get_logger().info('user enter connetct wifi')
                self.act_connect_wifi()
                return
            elif COMMAND_DIS_CONNECT_WIFI == command:
                self.get_logger().info('user disconnetct wifi')
                self.act_disconnect_wifi_pre(cur)
                return
            elif COMMAND_DO_DANCE == command:
                self.get_logger().info('user enter dance')
                self.act_dance()
                return
            elif COMMAND_CANCEL_DANCE == command:
                self.get_logger().info('user exit dance')
                self.act_stop_dance()
                return
            elif COMMAND_LOOK_LEFT == command:
                self.get_logger().info('user look left')
                self.act_look_leftright('left')
            elif COMMAND_LOOK_RIGHT == command:
                self.get_logger().info('user look right')
                self.act_look_leftright('right')
            elif COMMAND_TURN_LEFT == command:
                self.get_logger().info('user turn left')
                self.act_turn_leftright('left')
            elif COMMAND_TURN_RIGHT == command:
                self.get_logger().info('user turn right')
                self.act_turn_leftright('right')
            elif COMMAND_LOOK_UP == command:
                self.get_logger().info('user look up')
                self.act_head_updown('up',dur_time = 1)
            elif COMMAND_LOOK_DOWN == command:
                self.get_logger().info('user look down')
                self.act_head_updown('down',dur_time = 1)
            elif COMMAND_RAISE_RHAND == command:
                self.get_logger().info('user raise hand')
                self.act_righthand_updown('up',dur_time = 1)
            elif COMMAND_INCREASE_VOLUME == command:
                self.get_logger().info('user increase volume')
                self.act_increase_volume()
            elif COMMAND_DECREASE_VOLUME == command:
                self.get_logger().info('user decrease volume')
                self.act_decrease_volume()
            elif COMMAND_BIND_APP == command:
                self.get_logger().info('bind device')
                self.act_bind_app()
            elif COMMAND_HELP_WATER == command:
                self.get_logger().info('help_water')
                self.daySchedule.help_water(cur)
            elif COMMAND_HELP_WEED == command:
                self.get_logger().info('help_weed')
                self.daySchedule.help_weed(cur)
            elif COMMAND_QUERY_TREE_STATUS == command:
                self.get_logger().info('query_tree_status')
                self.daySchedule.query_tree_status()
            elif COMMAND_QUERY_HAPPEN_FOREST == command:
                self.get_logger().info('user query what happened in forest')
                self.daySchedule.command_query_happen_forest(self.fb.feedback_command_result_in_forest)
            elif COMMAND_QUERY_TEMP == command:
                self.get_logger().info('user query temprature')
                self.command_query_temp(self.fb.feedback_command_query_temp)
            elif COMMAND_QUERY_HUMID == command:
                self.get_logger().info('user query humidity')
                self.command_query_humid(self.fb.feedback_command_query_humid)
            elif COMMAND_QUERY_WAKE_TIME == command:
                self.get_logger().info('user query wake time')
                self.daySchedule.command_query_wake_time(self.fb.feedback_command_query_wake_time)
            elif COMMAND_QUERY_SLEEP_TIME == command:
                self.get_logger().info('user query sleep time')
                self.daySchedule.command_query_sleep_time(self.fb.feedback_command_query_sleep_time)
            elif COMMAND_QUERY_LUNCH_TIME == command:
                self.get_logger().info('user query lunch time')
                self.daySchedule.command_query_lunch_time(self.fb.feedback_command_query_lunch_time)
            elif COMMAND_QUERY_DINNER_TIME == command:
                self.get_logger().info('user query dinner time')
                self.daySchedule.command_query_dinner_time(self.fb.feedback_command_query_dinner_time)
            elif COMMAND_QUERY_TIME_TO_FOREST == command:
                self.get_logger().info('user query time to forest')
                self.daySchedule.command_query_time_to_forest(self.fb.feedback_command_query_time_forest)
            elif COMMAND_LOOK_HEAT_TREE == command:
                self.get_logger().info('user want to look tree')
                self.daySchedule.command_look_heat_tree(self.fb.feedback_command_look_heart_tree,cur)
            elif COMMAND_QUERY_ROBOT_STATUS == command:
                self.get_logger().info('user want to check robot status')
                self.daySchedule.command_query_robot_status(self.work_mode,self.fb.feedback_command_query_status)
            elif COMMAND_WHAT_IS_THIS == command:
                self.get_logger().info('what is this')
                self.act_stop_and_start_see()
            elif COMMAND_DOZE_OFF == command:
                self.get_logger().info('Keep quiet')
                self.command_enjoy_oneself_30(cur)
                self.be_quiet = True
                self.quiet_pub.publish(self._quiet(KeepQuiet.QUIET_FLAG))
            elif COMMAND_DOZE_ON == command:
                self.get_logger().info('wake up')
                self.command_enjoy_oneself_30_wakeup()
            elif COMMAND_ROLEPLAY_IN == command:
                self.get_logger().info('roleplay in')
                if not self.check_wifi():
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_no_need_wifi[0][0]))
                elif not self.daySchedule.token:
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_no_need_bind[0][0]))
                else:
                    #self.robotStatus.set_last_sleep3_time(cur + 1.5 * 60)
                    self.act_roleplay_in(cur)
            elif COMMAND_ROLEPLAY_OUT == command:
                self.get_logger().info('roleplay out')
                self.act_roleplay_out()
            elif COMMAND_CALIBRATION == command:
                self.get_logger().info('calibration')
                self.act_action_calibration(Action.TYPE_CALIBRATION)
            elif COMMAND_UPGRADE == command:
                self.get_logger().info('upgrade')
                self.act_upgrade_pre(cur)
            elif COMMAND_NOW_TIME == command:
                self.get_logger().info('now_time')
                self.daySchedule.now_time(self.fb.feedback_command_now_time)
            elif COMMAND_GATHER_REMEMBER_ME == command:
                self.get_logger().info('remember_me')
                self.gather_remember_me(cur)
            elif COMMAND_AM_I == command:
                self.get_logger().info('who am i')
                self.daySchedule.get_call_me_nick()
            elif COMMAND_ARE_YOU == command:
                self.get_logger().info('who are you')
                self.daySchedule.who_are_you()
            elif COMMAND_TURN_ON == command:
                self.get_logger().info('turn on the light')
                self.act_xled_brightness(4,50)
                self.speak_pub.publish(self._speak_text(self.fb.feedback_open_light[0][0]))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_open_light[0][1],5))
            elif COMMAND_TURN_OFF == command:
                self.get_logger().info('turn off the light')
                self.act_xled_brightness(4, 0)
                self.speak_pub.publish(self._speak_text(self.fb.feedback_close_light[0][0]))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_close_light[0][1],5))
            elif COMMAND_WATCH_TV == command:
                self.get_logger().info('watch tv')
                self.watch_tv_pre(cur)
            elif COMMAND_STOP_WATCH_TV == command:
                self.get_logger().info('stop watch tv')
                self.stop_watch_tv(self.fb.feedback_stop_tv)
            elif COMMAND_LISTEN_MUSIC == command:
                self.get_logger().info('listen music')
                self.music_pre(cur)
            elif COMMAND_STOP_LISTEN_MUSIC == command:
                self.get_logger().info('stop listen music')
                self.stop_music(self.fb.feedback_stop_music)
            elif command in self.lang_comand_trans:
                self.get_logger().info('change to lang')
                self.change_to_lang(self.lang_comand_trans[command])
            elif COMMAND_QUERY_TODAY_SCHEDULE == command:
                self.get_logger().info('query today schedule')
                try:
                    self.schedule_task_controller.tell_today_tasks()
                except Exception as e:
                    self.get_logger().info('query today schedule exception: %s' % e)
            elif COMMAND_QUERY_TOMORROW_SCHEDULE == command:
                self.get_logger().info('query tomorrow schedule')
                try:
                    self.schedule_task_controller.tell_tomorrow_tasks()
                except Exception as e:
                    self.get_logger().info('query tomorrow schedule exception: %s' % e)
            elif COMMAND_EMAIL_BEGIN == command:
                self.get_logger().info('query email')
                self.read_mail()
            elif COMMAND_SHUTDOWN == command:
                self.get_logger().info(' shutdown')
                self.act_shutdown_pre(cur)
            elif COMMAND_ACTION_RESET == command:
                self.get_logger().info(' action_reset')
                self.command_action_reset()
            elif COMMAND_BATTERY_STATUS == command:
                self.get_logger().info(' battery_status')
                self.command_battery_status()

        self.get_logger().info('nothing to do')

    def act_increase_volume(self):
        self.speak_pub.publish(self._speak_increase_volume())

    def act_decrease_volume(self):
        self.speak_pub.publish(self._speak_decrease_volume())

    def act_call_me(self,cur):
        self.get_logger().info('act call me')
        self.work_mode = WORK_MODE_COMMON

        self.speak_pub.publish(self._speak_asset("en.wav"))
        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_USUAL))
        #if self.listener_mode == ListenCommand.MODE_EXACT:
        #    self.listener_mode = ListenCommand.MODE_QUICK
        #    self.listen_pub.publish(self._listenCommand(ListenCommand.MODE_QUICK))
        self.robotStatus.set_enjoy_type(0)
        if cur - self.last_callme_act_time > 10 * 60 :
            self.act_action_relative(0.5,0,-25,0)
            self.last_callme_act_time = cur
            self.last_callme_act_flag = 1
        #self.robotStatus.set_last_sleep3_time(cur)
        #self.pub_see_command(See.COMMAND_USUAL)
        #self.pub_see_command(See.COMMAND_START_SEE)

    def act_dance(self):
        self.get_logger().info('act dance')
        if self.work_mode == WORK_MODE_DANCE:
            self.get_logger().info('already in dance mode')
            return
        self.act_exit_sleep()
        self.work_mode = WORK_MODE_DANCE
        self.speak_pub.publish(self._speak_dance("dance_jazz.wav"))
        self.act_action_reset()
        time.sleep(6)
        self.dance_thread = threading.Thread(target=self.do_dance, name="action-thread")
        self.dance_thread.start()

    def act_stop_dance(self):
        if self.dance_jazz:
            self.dance_jazz.stop_dance()

    def act_game(self):
        self.get_logger().info('act game')
        if self.work_mode == WORK_MODE_GAME:
            self.get_logger().info('already in game mode')
            return
        self.work_mode = WORK_MODE_GAME
        self.robotStatus.set_last_busy_time(time.time())
        self.speak_pub.publish(self._speak_game_bg_audio("game_321_background.wav"))
        self.emotion_pub.publish(self._emotion_without_effect(
            Emotion.EMOTION_GAME_321_ENTER))
        self.robotStatus.set_last_sleep3_time(time.time())
        self.pub_see_command(See.COMMAND_ENTER_GAME)
        self.game_thread = threading.Thread(target=self.do_game, name="game-thread")
        self.game_thread.start()

    def do_game(self):
        self.get_logger().info('do game now')
        self.print_thread_id()
        self.game_321.reset_game()
        self.robotStatus.set_last_busy_time(time.time())
        time.sleep(5)
        while self.work_mode == WORK_MODE_GAME and not self.game_321.is_game_finish():
            self.act_game_321_epoch()
            time.sleep(self.game_321.get_res_time())
            self.get_logger().info('do_game: "%s"' % self.game_321.is_command_verified())
            if self.game_321.is_command_verified() == False:
                self.act_game_321_epoch_lose()
                time.sleep(1)
            else:
                self.act_game_321_epoch_win()
                time.sleep(1)
        if self.game_321.is_game_finish():
            if self.game_321.is_winner():
                self.get_logger().info('user is winner final')
                self.act_game_321_win()
            else:
                self.get_logger().info('user is loser final')
                self.act_game_321_lose()
            time.sleep(1)
        self.act_stop_game()
        return

    def act_game_321_epoch(self):
        res = self.game_321.gen_next_command()
        if res is None:
            self.get_logger().info('game already finished')
            return
        epoch, game_command = res
        self.get_logger().info('get game command: "%s" "%s"' % (epoch, game_command))
        self.emotion_pub.publish(self._emotion_without_effect(
            game_command[3], 10))

    def act_game_321_epoch_win(self):
        self.get_logger().info('act user epoch win')
        self.speak_pub.publish(self._speak_asset("game_321_epoch_success.wav"))
        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_GAME_321_EPOCH_WIN, 10))
    def act_game_321_epoch_lose(self):
        self.get_logger().info('act user epoch lose')
        self.speak_pub.publish(self._speak_asset("game_321_epoch_fail.wav"))
        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_GAME_321_EPOCH_FAIL, 10))

    def act_game_321_win(self):
        self.get_logger().info('act user game win')
        self.speak_pub.publish(self._speak_asset("game_321_sucess.wav"))
        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_GAME_321_WIN, 10))

    def act_game_321_lose(self):
        self.get_logger().info('act user game lose')
        self.speak_pub.publish(self._speak_asset("game_321_fail.wav"))
        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_GAME_321_FAIL, 10))

    def act_stop_game(self):
        self.get_logger().info('stop game')
        self.work_mode = WORK_MODE_COMMON
        self.pub_see_command(See.COMMAND_EXIT_GAME)
        self.speak_pub.publish(self._speak_exit_game("game_321_background.wav"))
        self.emotion_pub.publish(self._emotion_without_effect(
            Emotion.EMOTION_USUAL))

    def act_talk_heart(self, emb=''):
        self.get_logger().info('act talk heart:')
        self.work_mode = WORK_MODE_HEART

        cur_seq = self.talk_seq.step()
        is_said = False
        while cur_seq and cur_seq.is_execution():
            self.act_feedback_common(cur_seq.feedback)
            cur_seq = self.talk_seq.step()
            is_said = True
        if is_said and cur_seq and not cur_seq.is_execution():
            self.talk_seq.back()
            return

        res = cur_seq.get_user_response(emb)
        self.act_feedback_common(res)
        if self.talk_seq.is_finish():
            self.work_mode = WORK_MODE_COMMON
            self.get_logger().info('act talk heart: seq is finished, change work mode to common')
            self.listen_pub.publish(self._listenCommand(ListenCommand.MODE_QUICK))

    def act_feedback_common(self, feedback, count=10):
        index = random.randint(0, len(feedback)-1)
        self.speak_pub.publish(self._speak_text(feedback[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(feedback[index][1],count))

    def act_stop_heart(self):
        self.get_logger().info('stop talk heart')
        self.work_mode = WORK_MODE_COMMON

    def _speak_asset(self, file_name):
        speak = Speak()
        speak.audio_file = file_name
        speak.text = ""
        speak.mode = 0
        return speak
    def _speak_dance(self, file_name):
        speak = Speak()
        speak.audio_file = file_name
        speak.text = ""
        speak.mode = Speak.ENTER_DANCE_MODE
        return speak
    def _speak_exit_dance(self, file_name):
        speak = Speak()
        speak.audio_file = file_name
        speak.text = ""
        speak.mode = Speak.EXIT_DANCE_MODE
        return speak
    def _speak_game_bg_audio(self, file_name):
        speak = Speak()
        speak.audio_file = file_name
        speak.text = ""
        speak.mode = Speak.ENTER_GAME_MODE
        return speak
    def _speak_exit_game(self, file_name):
        speak = Speak()
        speak.audio_file = ""
        speak.text = ""
        speak.mode = Speak.EXIT_GAME_MODE
        return speak
    def _speak_text(self, text):
        speak = Speak()
        speak.audio_file = ""
        speak.text = text
        return speak
    def _speak_increase_volume(self):
        speak = Speak()
        speak.mode = Speak.ADD_VOLUME
        return speak
    def _speak_decrease_volume(self):
        speak = Speak()
        speak.mode = Speak.SUB_VOLUME
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
    def _listenCommand(self, _type):
        listenCommand = ListenCommand()
        listenCommand.listen_mode = _type
        return listenCommand
    def _quiet(self, _type):
        q = KeepQuiet()
        q.is_quiet = _type
        return q

    def act_yaohuang(self):
        if self.work_mode == WORK_MODE_DANCE:
            return
        self.act_exit_sleep(True)
        cur = time.time()
        if cur - self.last_yaohuang_time < self.character.get_touch_inter_min():
            self.get_logger().info('already show yaohuang effect in 5s')
            return
        index = random.randint(0, len(self.fb.feedback_yaohuang)-1)
        self.get_logger().info('index: "%s"' % index)
        if cur - self.last_yaohuang_time < 15 * 60:
            self.get_logger().info('dont speak in 10min')
            self.speak_pub.publish(self._speak_text(self.fb.feedback_yaohuang[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_yaohuang[index][1]))
        #self.action_pub.pub()
        self.last_yaohuang_time = cur

    def act_cold(self):
        cur = time.time()
        if cur - self.temp_notified_time < self.character.get_temp_inter_min():
            return
        self.temp_notified_time = cur
        index = random.randint(0, len(self.fb.feedback_cold)-1)
        self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_cold[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_cold[index][1],10))
        #self.action_pub.pub()
    def act_hot(self):
        cur = time.time()
        if cur - self.temp_notified_time < self.character.get_temp_inter_min():
            return
        self.temp_notified_time = cur
        index = random.randint(0, len(self.fb.feedback_hot)-1)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_hot[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_hot[index][1],10))
        #self.action_pub.pub()
    def act_humid(self):
        cur = time.time()
        if cur - self.humid_notified_time < self.character.get_humid_inter_min():
            return False
        self.humid_notified_time = cur
        index = random.randint(0, len(self.fb.feedback_humid)-1)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_humid[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_humid[index][1],10))
        #self.action_pub.pub()
    def act_dry(self):
        cur = time.time()
        if cur - self.humid_notified_time < self.character.get_humid_inter_min():
            return False
        self.humid_notified_time = cur
        index = random.randint(0, len(self.fb.feedback_dry)-1)
        self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_dry[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_dry[index][1],10))
        #self.action_pub.pub()
    def act_touch_head_long(self):
        self.act_exit_sleep(True)
        cur = time.time()
        if cur - self.last_touch_once_emotion < self.character.get_touch_inter_min():
            return
        self.last_touch_once_emotion = cur
        mode = self.daySchedule.get_robot_work_mode(self.work_mode)
        if mode == 0:
            self.get_logger().info('陪伴模式')
            index = random.randint(0, len(self.fb.feedback_touch_head_long) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_head_long[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_long[index][1]))
        elif mode == 11 or mode == 17:
            self.get_logger().info('睡眠状态')
            index = random.randint(0, len(self.fb.feedback_touch_head_stroke_sleep_mode) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_head_stroke_sleep_mode[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_stroke_sleep_mode[index][1]))
        elif mode == 8:
            self.get_logger().info('情感森林')
            index = random.randint(0, len(self.fb.feedback_touch_head_stroke_forest_mode) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_head_stroke_forest_mode[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_stroke_forest_mode[index][1]))
        else:
            self.get_logger().info('日常行程')
            index = random.randint(0, len(self.fb.feedback_touch_head_stroke_usual_mode) - 1)
            feedback__format = self.fb.feedback_touch_head_stroke_usual_mode[index][0]
            if '%s' in feedback__format:
                feedback__format = feedback__format % self.daySchedule.get_robot_work_mode_trans(mode)
            self.speak_pub.publish(self._speak_text(feedback__format))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_stroke_usual_mode[index][1]))
    def act_touch_head_once(self):
        self.act_exit_sleep(True)
        cur = time.time()
        if cur - self.last_touch_once_emotion < self.character.get_touch_inter_min():
            self.get_logger().info("act_touch_head_once: low vs touch_inter_once %s" % self.character.get_touch_inter_min())
            return
        self.last_touch_once_emotion = cur
        mode = self.daySchedule.get_robot_work_mode(self.work_mode)
        if mode == 0:
            self.get_logger().info('陪伴模式')
            index = random.randint(0, len(self.fb.feedback_touch_head_once) - 1)
            # self.get_logger().info('index: "%s"' % index)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_head_once[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_once[index][1]))
            self.act_head_updown('up')
        elif mode == 11 or mode == 17:
            self.get_logger().info('睡眠状态')
            index = random.randint(0, len(self.fb.feedback_touch_head_once_sleep_mode) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_head_once_sleep_mode[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_once_sleep_mode[index][1]))
            self.act_head_updown('up')
            #self.act_xled_brightness(5,30)
        elif mode == 8:
            self.get_logger().info('情感森林')
            index = random.randint(0, len(self.fb.feedback_touch_head_once_forest_mode) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_head_once_forest_mode[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_once_forest_mode[index][1]))
            self.act_head_updown('up')
        else:
            self.get_logger().info('日常行程')
            index = random.randint(0, len(self.fb.feedback_touch_head_once_usual_mode) - 1)
            feedback__format = self.fb.feedback_touch_head_once_usual_mode[index][0]
            if '%s' in feedback__format:
                feedback__format = feedback__format % self.daySchedule.get_robot_work_mode_trans(mode)
            self.speak_pub.publish(self._speak_text(feedback__format))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_once_usual_mode[index][1]))
            self.act_head_updown('up')

    def act_touch_head_triple(self):
        cur = time.time()
        if cur - self.last_touch_once_emotion < self.character.get_touch_inter_min():
            self.get_logger().info("act_touch_head_triple: low vs touch_inter_triple")
            return
        self.last_touch_once_emotion = cur
        self.act_exit_sleep(True)
        master = self.is_master(cur)
        if not master:  # 没看到人
            index = random.randint(0, len(self.fb.feedback_touch_head_no_person) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_head_no_person[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_no_person[index][1]))
            self.act_action_relative(0.5, 25, 0, 0)
            time.sleep(1)
            self.act_action_relative(1, -50, 0, 0)
            time.sleep(1)
            self.act_action_relative(0.5, 25, 0, 0)
            return
        mode = self.daySchedule.get_robot_work_mode(self.work_mode)
        if mode == 0:
            self.get_logger().info('陪伴模式')
            if master == 2:  # yes ,it's you
                index = random.randint(0, len(self.fb.feedback_touch_head_master_default_mode) - 1)
                feedback__format = self.fb.feedback_touch_head_master_default_mode[index][0]
                if '%s' in feedback__format:
                    feedback__format = feedback__format % self.get_repl()
                self.speak_pub.publish(self._speak_text(feedback__format))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_master_default_mode[index][1]))
            else:
                index = random.randint(0, len(self.fb.feedback_touch_head_triple) - 1)
                self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_head_triple[index][0]))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_triple[index][1]))
        elif mode == 11 or mode == 17:
            self.get_logger().info('睡眠状态')
            index = random.randint(0, len(self.fb.feedback_touch_head_person_sleep_mode) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_head_person_sleep_mode[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_person_sleep_mode[index][1]))
        elif mode == 8:
            self.get_logger().info('情感森林')
            index = random.randint(0, len(self.fb.feedback_touch_head_person_forest_mode) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_head_person_forest_mode[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_person_forest_mode[index][1]))
        else:
            self.get_logger().info('日常行程')
            index = random.randint(0, len(self.fb.feedback_touch_head_person_usual_mode) - 1)
            feedback__format = self.fb.feedback_touch_head_person_usual_mode[index][0] % self.daySchedule.get_robot_work_mode_trans(mode)
            self.speak_pub.publish(self._speak_text(feedback__format))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_head_person_usual_mode[index][1]))

    def act_touch_head_slow(self):
        self.act_exit_sleep(True)
        index = random.randint(0, len(self.fb.feedback_touch_head_slow)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_touch_head_slow[index][1]))
        cur = time.time()
        if cur - self.last_touch_once_emotion < self.character.get_touch_inter_min():
            self.get_logger().info("act_touch_head_triple: low vs touch_inter_slow")
            return
        self.last_touch_once_emotion = cur
        self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_head_slow[index][0]))

        #self.action_pub.pub()

    def act_touch_head_night(self):
        self.act_exit_sleep(True)
        index = random.randint(0, len(self.fb.feedback_touch_head_night)-1)
        #self.get_logger().info('index: "%s"' % index)

        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_touch_head_night[index][1]))
        cur = time.time()
        if cur - self.last_touch_once_emotion < self.character.get_touch_inter_min():
            self.get_logger().info("act_touch_head_triple: low vs touch_inter_night")
            return
        self.last_touch_once_emotion = cur
        self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_head_night[index][0]))
        #self.action_pub.pub()

    def act_touch_belly_long(self):
        self.act_exit_sleep(True)
        cur = time.time()
        if cur - self.last_touch_belly_once_emotion < self.character.get_touch_inter_min():
            return
        self.last_touch_belly_once_emotion = cur
        index = random.randint(0, len(self.fb.feedback_touch_belly_long)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_belly_long[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_touch_belly_long[index][1]))
        #self.action_pub.pub()

    def act_touch_belly_once(self):
        cur = time.time()
        if cur - self.last_touch_belly_once_emotion < self.character.get_touch_inter_min():
            self.get_logger().info("act_touch_belly_once: low vs touch_inter_once")
            return
        self.last_touch_belly_once_emotion = cur
        master = self.is_master(cur)
        if not master: #没看到人
            index = random.randint(0, len(self.fb.feedback_touch_belly_once) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_belly_once[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_belly_once[index][1]))
            self.act_exit_sleep(True)
        elif master ==0:# no gather
            index = random.randint(0, len(self.fb.feedback_touch_belly_no_gather) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_belly_no_gather[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_belly_no_gather[index][1]))
        elif master == 1:# other pers
            index = random.randint(0, len(self.fb.feedback_touch_belly_not_master) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_belly_not_master[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_belly_not_master[index][1]))
        elif master == 2: # yes ,it's you
            index = random.randint(0, len(self.fb.feedback_touch_belly_master) - 1)
            feedback__format = self.fb.feedback_touch_belly_master[index][0] % self.get_repl()
            self.speak_pub.publish(self._speak_text(feedback__format))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_touch_belly_master[index][1]))

    def act_touch_belly_triple(self):
        cur = time.time()
        self.act_exit_sleep(True)
        if cur - self.last_touch_belly_once_emotion < self.character.get_touch_inter_min():
            self.get_logger().info("act_touch_belly_triple: low vs touch_inter_triple")
            return
        self.last_touch_belly_once_emotion = cur
        index = random.randint(0, len(self.fb.feedback_touch_belly_triple)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_belly_triple[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_touch_belly_triple[index][1]))
        #self.action_pub.pub()


    def act_touch_belly_night(self):
        self.act_exit_sleep(True)
        index = random.randint(0, len(self.fb.feedback_touch_belly_night)-1)

        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_touch_belly_night[index][1]))
        cur = time.time()
        if cur - self.last_touch_once_emotion < self.character.get_touch_inter_min():
            self.get_logger().info("act_touch_belly_night: low vs touch_inter_night")
            return
        self.last_touch_belly_once_emotion = cur
        self.speak_pub.publish(self._speak_text(self.fb.feedback_touch_belly_night[index][0]))


    def act_gesture_love(self):
        self.act_exit_sleep(True)
        index = random.randint(0, len(self.fb.feedback_gesture_love)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_gesture_love[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_gesture_love[index][1]))
        #self.action_pub.pub()
    def act_gesture_pop(self):
        self.act_exit_sleep(True)
        index = random.randint(0, len(self.fb.feedback_gesture_pop)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_gesture_pop[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_gesture_pop[index][1]))
        #self.action_pub.pub()
    def act_gesture_watering(self,cur):
        self.daySchedule.do_cooper_watering(cur)

    def act_gesture_weeding(self,cur):
        self.daySchedule.do_cooper_weeding(cur)

    def act_walk_closer(self):
        cur = time.time()
        if cur - self.last_walk_closer_time < self.character.per_inter_min():
            self.get_logger().info('already act walk closer in 10s')
            return
        if self.is_sleep_time():
            self.get_logger().info('current is sleep time')
            return
        self.last_walk_closer_time = cur
        index = random.randint(0, len(self.fb.feedback_walk_closer)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_asset(self.fb.feedback_walk_closer[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_walk_closer[index][1]))

    def thinker_callback(self):
        cur = time.time()
        if self.last_callme_act_flag == 1 and cur - self.last_listen_callback_time > 10:
            self.last_callme_act_flag = 0
            self.act_action_reset()
        if self.work_mode == WORK_MODE_WIFI:					
            if time.time() - self.start_wifi_connect_time > 1 * 60:
                self.get_logger().info('wifi connect timeout')
                self.act_wifi_connect_timeout()
        if self.work_mode == WORK_MODE_DANCE:
            self.get_logger().info('current is dance')
            return
        self.get_logger().info('cur - self.robotStatus.last_sleep3_time: %s' % (cur - self.robotStatus.last_sleep3_time))
        self.schedule_task_controller.notify_expired_task()
        self.act_command_cancel_auto(cur)
        if self.work_mode == WORK_MODE_TV_PRE:
            self.watch_pre_to_tv([], cur)
        elif self.work_mode == WORK_MODE_TV:
            if 60 * 60 > cur - self.tv_last_msg_time > 3 * 60:
                self.stop_watch_tv(self.fb.feedback_stop_tv_auto)
                self.robotStatus.set_last_sleep3_time(cur)
        elif self.work_mode == WORK_MODE_MUSIC_PRE:
            self.pre_to_music(False,cur)
        elif self.work_mode == WORK_MODE_MUSIC:
            if cur - self.music_last_msg_time > 3 * 60:
                self.stop_music(self.fb.feedback_stop_music_auto)
        if (self.work_mode != WORK_MODE_GAME and self.work_mode != WORK_MODE_WIFI
              and self.work_mode != WORK_MODE_TV_PRE and self.work_mode != WORK_MODE_TV
              and cur - self.robotStatus.last_sleep3_time > 0.5 * 60):
            #self.pub_see_command(See.COMMAND_ADD_TIME)
            self.pub_see_command(See.COMMAND_STOP_SEE)
            self.robotStatus.set_last_sleep3_time(cur + 60 * 60 )
            if self.work_mode == WORK_MODE_BIND:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app_timeout[0][0]))
            elif self.work_mode == WORK_MODE_GATHER:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_gather_timeout[0][0]))
            if self.work_mode != WORK_MODE_MUSIC_PRE and self.work_mode != WORK_MODE_MUSIC:
                self.work_mode = WORK_MODE_COMMON
        if self.work_mode == WORK_MODE_TV:
            self.tv_count = self.tv_count + 1
            self.get_logger().info('self.tv_count: %s ' % self.tv_count )
            if self.tv_count > 1:
                self.tv_count = 0
                self.robotStatus.set_last_sleep3_time(cur)
                self.pub_see_command(See.COMMAND_WATCH_TV)

        if not self.daySchedule.is_sleep_time() and self.robotStatus.get_enjoy_type() >= 3:
            time__ = self.robotStatus.get_last_enjoy_time_30()
            if time__ != 0 and cur - time__ >= 60 * 60:
                self.enjoy_oneself_30_wakeup()
            #return
        if (cur - self.last_saw_ges_time > self.character.get_sleep_inter_min()) and (cur - self.last_saw_per_time > self.character.get_sleep_inter_min()) and self.work_mode == WORK_MODE_COMMON:
            self.get_logger().info('5min see nothing, sleep')
            self.last_saw_ges_time = cur
            see = See()
            see.command = See.COMMAND_STOP_SEE
            #self.eye_pub.publish(msg)
            self.person_count = 0
            self.last_person_distance = FAR_DISTANCE
            #self.act_action_reset()
            #time.sleep(2)
            #self.act_random_action()
            #self.act_enter_sleep()
        if (cur - self.last_saw_per_time > self.character.get_sleep_inter_min()) and self.work_mode == WORK_MODE_HEART:
            self.work_mode = WORK_MODE_COMMON
            self.get_logger().info('5min see no person , normal  , change work mode to common')
        if cur - self.last_rifd_time > 4:
            self.act_cosplay_normal()
        # 日程
        if self.work_mode == WORK_MODE_COMMON:
            self.daySchedule.do_day_schedule(cur,self.check_wifi())
            # 无聊自娱自乐
            if not self.daySchedule.is_sleep_time():
                self.enjoy_oneself_thread = threading.Thread(target=lambda: self.enjoy_oneself(cur))
                self.enjoy_oneself_thread.start()
        # 1分钟没聊天，自动退出百变
        #
        #if self.mail_count>0:
        #    self.read_mail()

    def upload_callback(self):
        self.daySchedule.one_hour_task(self.check_wifi())
        save_sys_time(self.time_store_path)
        #
        if not self.daySchedule.is_sleep_time():
            self.robotStatus.set_last_sleep3_time(time.time())
            self.pub_see_command(See.COMMAND_START_SEE)
        #
        #self.read_mail()
    def one_day_task_callback(self):
        self.daySchedule.one_day_task(self.check_wifi())
        # 5、ota
        # self.ota_pub.publish(Ota())
        # 6、删除log
        os.system("find /root/.ros/log    -mindepth 1 -mtime +1 -mtime -71 -exec rm -rf {} \;")
        os.system("find /root/tm_mini/log -mindepth 1 -mtime +1 -mtime -71 -exec rm -rf {} \;")
        self.schedule_task_controller.remove_history_task()

    def act_random_action(self):
        self.get_logger().info('act_random_action enter')
        #actions = [self.act_turn_leftright, self.act_look_leftright]
        actions = [self.act_look_leftright]
        direction = ['left', 'right']
        index = random.randint(0, len(actions)-1)
        direct_index = random.randint(0, len(direction)-1)
        select_action = actions[index]
        select_direct = direction[direct_index]
        if select_action == self.act_turn_leftright or select_action == self.act_look_leftright:
            select_action(select_direct)
        else:
            select_action()


    def act_saw_multi_person(self):
        cur = time.time()
        if cur - self.last_rec_person_time < self.character.get_per_inter_min():
            self.get_logger().info('already act saw person in 5s')
            return
        self.last_rec_person_time = cur
        index = random.randint(0, len(self.fb.feedback_rec_common)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_asset(self.fb.feedback_rec_common[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_rec_common[index][1]))
        self.history_intent = self.fb.feedback_rec_common[index][2]
    def act_saw_male(self):
        cur = time.time()
        if cur - self.last_rec_person_time < self.character.get_per_inter_min():
            self.get_logger().info('already act saw person in 5s')
            return
        self.last_rec_person_time = cur
        index = random.randint(0, len(self.fb.feedback_rec_sex_male)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_asset(self.fb.feedback_rec_sex_male[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_rec_sex_male[index][1]))
        self.history_intent = self.fb.feedback_rec_sex_male[index][2]
    def act_saw_female(self):
        cur = time.time()
        if cur - self.last_rec_person_time < self.character.get_per_inter_min():
            self.get_logger().info('already act saw person in 5s')
            return
        self.last_rec_person_time = cur
        index = random.randint(0, len(self.fb.feedback_rec_sex_female)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_asset(self.fb.feedback_rec_sex_female[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_rec_sex_female[index][1]))
        self.history_intent = self.fb.feedback_rec_sex_female[index][2]
    def act_saw_person_amaze(self):
        cur = time.time()
        if cur - self.last_rec_person_time < self.character.get_per_inter_min():
            self.get_logger().info('already act saw person in 5s')
            return
        self.last_rec_person_time = cur
        index = random.randint(0, len(self.fb.feedback_rec_emotion_amaze)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_asset(self.fb.feedback_rec_emotion_amaze[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_rec_emotion_amaze[index][1]))
    def act_saw_person_sad(self):
        cur = time.time()
        if cur - self.last_rec_person_time < self.character.get_per_inter_min():
            self.get_logger().info('already act saw person in 5s')
            return
        self.last_rec_person_time = cur
        index = random.randint(0, len(self.fb.feedback_rec_emotion_sad)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_asset(self.fb.feedback_rec_emotion_sad[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_rec_emotion_sad[index][1]))
    def act_saw_person_anger(self):
        cur = time.time()
        if cur - self.last_rec_person_time < self.character.get_per_inter_min():
            self.get_logger().info('already act saw person in 5s')
            return
        self.last_rec_person_time = cur
        index = random.randint(0, len(self.fb.feedback_rec_emotion_anger)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_asset(self.fb.feedback_rec_emotion_anger[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_rec_emotion_anger[index][1]))
    def act_saw_male_again(self, last_time):
        cur = time.time()
        if cur - last_time < self.character.get_his_per_inter_min():
            self.get_logger().info('already act saw person in 5min')
            return
        self.last_rec_person_time = cur
        index = random.randint(0, len(self.fb.feedback_rec_again_male)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_asset(self.fb.feedback_rec_again_male[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_rec_again_male[index][1]))
    def act_saw_female_again(self, last_time):
        cur = time.time()
        if cur - last_time < self.character.get_his_per_inter_min():
            self.get_logger().info('already act saw person in 5min')
            return
        self.last_rec_person_time = cur
        index = random.randint(0, len(self.fb.feedback_rec_again_female)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_asset(self.fb.feedback_rec_again_female[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_rec_again_female[index][1]))
    def act_saw_common_again(self, last_time):
        cur = time.time()
        if cur - last_time < self.character.get_his_per_inter_min():
            self.get_logger().info('already act saw person in 5min')
            return
        self.last_rec_person_time = cur
        index = random.randint(0, len(self.fb.feedback_rec_again_common)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_asset(self.fb.feedback_rec_again_common[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_rec_again_common[index][1]))
    def act_intent_feedback(self, feedback):
        index = random.randint(0, len(feedback)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(feedback[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(feedback[index][1],10))
    def act_enter_sleep(self):
        self.work_mode = WORK_MODE_SLEEP
        if time.localtime().tm_hour >= 13 and time.localtime().tm_hour <=14:
            self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_SHALLOW_SLEEP))
        elif time.localtime().tm_hour <= 6 or time.localtime().tm_hour >= 21:
            self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_DEEP_SLEEP))
        else:
            self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_DEEP_SLEEP))

    def act_exit_sleep(self, change_slient = False):
        if self.work_mode != WORK_MODE_SLEEP:
            self.get_logger().info('cur is not sleep mode...')
            return
        self.get_logger().info('act_exit_sleep...')
        self.work_mode = WORK_MODE_COMMON

        if time.localtime().tm_hour >= 13 and time.localtime().tm_hour <=14:
            self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_USUAL))
        elif time.localtime().tm_hour <= 6 or time.localtime().tm_hour >= 21:
            self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_WAKE))
        else:
            fish_wake_feedback = [("xiaoShou_diaoYu_01.wav", Emotion.EMOTION_SQUINT), ("xiaoShou_diaoYu_02.wav", Emotion.EMOTION_LAUGH)]
            index = random.randint(0, len(fish_wake_feedback)-1)
            self.emotion_pub.publish(self._emotion_without_effect (fish_wake_feedback[index][1]))
            

    def pub_see_command(self, command):
        see = See()
        see.command = command
        self.eye_pub.publish(see)

    def act_connect_wifi(self):
        self.work_mode = WORK_MODE_WIFI
        self.is_wifi_conneting = False
        self.start_wifi_connect_time = time.time()
        self.pub_see_command(See.COMMAND_REC_QR)
        index = random.randint(0, len(self.fb.feedback_connect_wifi)-1)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_connect_wifi[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_connect_wifi[index][1]))

    def act_wifi_connected(self):
        self.work_mode = WORK_MODE_COMMON
        self.is_wifi_conneting = False
        
        self.time_syncer.sync()
        
        index = random.randint(0, len(self.fb.feedback_wifi_connected)-1)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_wifi_connected[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_wifi_connected[index][1]))
        self.pub_see_command(See.COMMAND_USUAL)
        self.pub_see_command(See.COMMAND_STOP_SEE)
    def act_wifi_connect_timeout(self):
        self.work_mode = WORK_MODE_COMMON
        self.is_wifi_conneting = False

        index = random.randint(0, len(self.fb.feedback_wifi_connect_timeout)-1)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_wifi_connect_timeout[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_wifi_connect_timeout[index][1]))
        self.pub_see_command(See.COMMAND_USUAL)
        self.pub_see_command(See.COMMAND_STOP_SEE)

    def act_wifi_not_connected(self):
        index = random.randint(0, len(self.fb.feedback_wifi_not_connected)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_wifi_not_connected[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(
            self.fb.feedback_wifi_not_connected[index][1]))
        self.history_intent = self.fb.feedback_wifi_not_connected[index][2]

    def act_action_relative(self, time, head_yaw_angle, head_pitch_angle, body_yaw_angle):
        self.get_logger().info('act_action_relative: %s %s %s %s' % (time, head_yaw_angle, head_pitch_angle, body_yaw_angle))
        action = Action()
        action.time = float(time)
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

    def act_action_with_hand_relative(self, time, head_yaw_angle, head_pitch_angle, body_yaw_angle, left_hand_angle, right_hand_angle):
        self.get_logger().info('act_action_with_hand_relative: %s %s %s %s %s %s' % (time, head_yaw_angle, head_pitch_angle, body_yaw_angle, left_hand_angle, right_hand_angle))
        action = Action()
        action.time = float(time)
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

    def act_xled_brightness(self, time, brightness):
        self.get_logger().info("act_xled_brightness: %s %s" % (time, brightness))
        action = Action()
        action.time = float(time)
        action.type = Action.TYPE_RELATIVE_MOVE
        action.leds = []
        x = Led()
        x.index = Action.INDEX_X_LED
        x.bright = brightness
        action.leds.append(x)
        self.action_pub.publish(action)

    def act_bled_brightness(self, time, brightness):
        self.get_logger().info("act_bled_brightness: %s %s" % (time, brightness))
        action = Action()
        action.time = float(time)
        action.type = Action.TYPE_RELATIVE_MOVE
        action.leds = []
        x = Led()
        x.index = Action.INDEX_B_LED
        x.bright = brightness
        action.leds.append(x)
        self.action_pub.publish(action)
    
    def act_led_brightness(self, time, xbrightness, bbrightness):
        self.get_logger().info("act_xled_brightness: %s %s %s" % (time, xbrightness, bbrightness))
        action = Action()
        action.time = float(time)
        action.type = Action.TYPE_RELATIVE_MOVE
        action.leds = []
        x = Led()
        x.index = Action.INDEX_X_LED
        x.bright = xbrightness
        action.leds.append(x)
        b = Led()
        b.index = Action.INDEX_B_LED
        b.bright = bbrightness
        action.leds.append(b)
        self.action_pub.publish(action)

    def act_look_leftright(self, direction, angle = 25, dur_time = 0.5):
        self.get_logger().info("act_look_leftright: %s %s %s" % (direction, angle, dur_time))
        self.act_action_reset()
        time.sleep(1)
        if direction == 'left':
            self.act_action_relative(dur_time, angle, 0, 0)
        elif direction == 'right':
            self.act_action_relative(dur_time, 0-angle, 0, 0)
        time.sleep(1)
        self.act_action_reset()
        time.sleep(0.5)

    def act_turn_leftright(self, direction, angle = 40, dur_time = 0.5):
        self.get_logger().info("act_turn_leftright: %s %s %s" % (direction, angle, dur_time))
        self.act_action_reset()
        time.sleep(1)
        if direction == 'left':
            self.act_action_relative(dur_time, 0, 0, 0 - angle)
        elif direction == 'right':
            self.act_action_relative(dur_time, 0, 0, angle)
        time.sleep(1)
        self.act_action_reset()
        time.sleep(0.5)

    def act_head_updown(self, direction, angle = 15, dur_time = 0.5):
        self.get_logger().info("act_head_updown: %s %s %s" % (direction, angle, dur_time))
        self.act_action_reset()
        time.sleep(1)
        if direction == 'up':
            self.act_action_relative(dur_time, 0, 0 - angle, 0)
        elif direction == 'down':
            self.act_action_relative(dur_time, 0, angle, 0)
        time.sleep(1)
        self.act_action_reset()
        time.sleep(0.5)

    def act_lefthand_updown(self, direction, angle = 40, dur_time = 0.5):
        self.get_logger().info("act_lefthand_updown: %s %s %s" % (direction, angle, dur_time))
        self.act_action_reset()
        time.sleep(1)
        if direction == 'up':
            self.act_action_with_hand_relative(dur_time, 0, 0, 0, 0 - angle, 0)
        elif direction == 'down':
            self.act_action_with_hand_relative(dur_time, 0, 0, 0, angle, 0)
        time.sleep(1)
        self.act_action_reset()
        time.sleep(0.5)

    def act_righthand_updown(self, direction, angle = 40, dur_time = 0.5):
        self.get_logger().info("act_righthand_updown: %s %s %s" % (direction, angle, dur_time))
        self.act_action_reset()
        time.sleep(1)
        if direction == 'up':
            self.act_action_with_hand_relative(dur_time, 0, 0, 0, 0, angle)
        elif direction == 'down':
            self.act_action_with_hand_relative(dur_time, 0, 0, 0, 0, 0 - angle)
        time.sleep(1)
        self.act_action_reset()
        time.sleep(0.5)

    def act_random_hand_action(self):
        self.get_logger().info('act_random_action enter')
        actions = [self.act_lefthand_updown, self.act_righthand_updown, self.act_head_updown ]
        direction = ['up', 'down']
        index = random.randint(0, len(actions)-1)
        direct_index = random.randint(0, len(direction)-1)
        select_action = actions[index]
        select_action(direction[direct_index])

    def act_action_fllow_person(self, position):
        head_yaw_angle = 0
        head_pitch_angle = 0
        body_yaw_angle = 0
        if (position & Saw.POSITION_RIGHT) == Saw.POSITION_RIGHT:
            head_yaw_angle = -10
        elif (position & Saw.POSITION_LEFT) == Saw.POSITION_LEFT:
            head_yaw_angle = 10
        if (position & Saw.POSITION_UP) == Saw.POSITION_UP:
            head_pitch_angle = 5
        elif (position & Saw.POSITION_DOWN) == Saw.POSITION_DOWN:
            head_pitch_angle = -5
        if head_yaw_angle == 0 and head_pitch_angle == 0 and body_yaw_angle == 0:
            return
        self.get_logger().info("act_action_fllow_person:'%s' '%s'" % (head_yaw_angle, head_pitch_angle))
        self.act_action_relative(1, head_yaw_angle, head_pitch_angle, body_yaw_angle)

    def act_action_reset(self, time=1):
        action = Action()
        action.time = float(time)
        action.type = Action.TYPE_RESET
        self.action_pub.publish(action)

    def act_action_calibration(self, time=1):
        action = Action()
        action.time = float(time)
        action.type = Action.TYPE_CALIBRATION
        self.action_pub.publish(action)


    def act_bind_app(self):
        if not self.check_wifi():
            self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app_need_wifi[0][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_bind_app_need_wifi[0][1], 5))
            return
        check_bind = self.daySchedule.check_bind()
        if check_bind == 0:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app[0][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_bind_app[0][1], 5))
        elif check_bind == 102:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app_fail5[0][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_bind_app_fail5[0][1], 5))
            return
        else:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app_fail[0][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_bind_app_fail[0][1], 5))
            return
        self.robotStatus.set_last_busy_time(time.time())
        self.work_mode = WORK_MODE_BIND
        self.pub_see_command(See.COMMAND_REC_QR)
        self.robotStatus.set_last_sleep3_time(time.time() + 60)

    def act_stop_and_start_see(self):
        self.last_what_this_time = time.time()
        # self.pub_see_command(See.COMMAND_STOP_SEE)
        # time.sleep(0.1)
        self.robotStatus.set_last_sleep3_time(time.time())
        self.pub_see_command(See.COMMAND_START_SEE)

    def act_what_is_this(self,saw_data):
        things = saw_data.things
        self.get_logger().info('what_is_this_flag things: "%s" ' % things)
        if len(things) == 0 :
            return
        name = things[0].type
        if name not in self.things_trans:
            self.act_feedback_common(self.fb.feedback_no1)
            return
        has_cat_or_dog = None
        if Saw.TYPE_CAT == name:
            has_cat_or_dog = 1
        elif Saw.TYPE_DOG == name:
            has_cat_or_dog = 1
        
        name = self.things_trans[name]
        feedback__format = self.fb.feedback_know_things[0][0] % name
        self.speak_pub.publish(self._speak_text(feedback__format))
        if has_cat_or_dog:
            self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_LOVE,5))
        else:
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_know_things[0][1]))
        self.pub_see_command(See.COMMAND_STOP_SEE)

    def enjoy_oneself(self,cur):
        #self.get_logger().info("检测自娱自乐......")
        time__ = self.robotStatus.get_last_enjoy_time_30()
        if time__ != 0 and cur - time__ >= 60 * 60:
            self.enjoy_oneself_30_wakeup()
        if self.daySchedule.check_is_busy():
            self.get_logger().info("检测自娱自乐......忙碌中(情感森林中 或者 钓鱼)")
            return
        if self.work_mode != WORK_MODE_COMMON:
            self.get_logger().info("检测自娱自乐......work_mode模式不对")
            return
        last_busy_time = self.robotStatus.get_last_busy_time()
        self.get_logger().info("检测自娱自乐......:已空闲%s秒" % (cur - last_busy_time))
        if 5 * 60 <= cur - last_busy_time < 15 * 60:
            if cur - self.robotStatus.get_last_enjoy_time_5() < 30 * 60:
                return
            index = random.randint(0, len(self.fb.feedback_enjoy_5) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_enjoy_5[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_enjoy_5[index][1],5))
            self.robotStatus.set_last_enjoy_time_5(cur)
            self.robotStatus.set_enjoy_type(1)
            time.sleep(1.5)
            #self.act_xled_brightness(3,10)
            self.act_action_relative(0.5, 25, 0, 0)
            time.sleep(1)
            self.act_action_relative(0.5, -50, 0, 0)
            time.sleep(1)
            self.act_action_reset()
            #self.act_xled_brightness(3, 0)
        elif 15 * 60 <= cur - last_busy_time < 30 * 60:
            if cur - self.robotStatus.get_last_enjoy_time_15() < 60 * 60:
                return
            self.speak_pub.publish(self._speak_text(self.fb.feedback_enjoy_15[0][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_enjoy_15[0][1],36))
            self.robotStatus.set_last_enjoy_time_15(cur)
            self.robotStatus.set_enjoy_type(2)
            self.act_action_with_hand_relative(0.5, 0, 0, 0, -40, 40)
            time.sleep(1)
            self.act_action_with_hand_relative(0.5, 0, 0, 0, 40, -40)
            time.sleep(1)
            self.act_action_reset()
        elif 30 * 60 <= cur - last_busy_time < 60 * 60:
            if cur - time__ < 2 * 60 * 60:
                return
            self.speak_pub.publish(self._speak_text(self.fb.feedback_enjoy_30[0][0]))
            self.robotStatus.set_last_enjoy_time_30( cur)
            self.robotStatus.set_enjoy_type(3)
            self.pub_see_command(See.COMMAND_STOP_SEE)
            self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_DOZE_OFF,8))
            self.act_action_relative(0.5, 0, 12, 0)
            time.sleep(1)
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_enjoy_30[0][1], 36 ))
            self.act_action_relative(0.5, 0, -12, 0)
            time.sleep(1)
            self.act_action_reset()

    def enjoy_oneself_30_wakeup(self):
        self.speak_pub.publish(self._speak_text(self.fb.feedback_wake_up[0][0]))
        self.robotStatus.set_last_enjoy_time_30(0)
        self.robotStatus.set_enjoy_type(0)
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_wake_up[0][1]))

    def command_enjoy_oneself_30(self,cur):
        time__ = self.robotStatus.get_last_enjoy_time_30()
        if time__ == 0:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_enjoy_force[0][0]))
            self.robotStatus.set_last_enjoy_time_30(cur)
            self.robotStatus.set_enjoy_type(3)
            self.pub_see_command(See.COMMAND_STOP_SEE)
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_enjoy_force[0][1], 36 ))
    def command_enjoy_oneself_30_wakeup(self):
        time__ = self.robotStatus.get_last_enjoy_time_30()
        self.act_head_updown('up')
        if time__ == 0:
            self.robotStatus.set_enjoy_type(0)
            self.act_feedback_common(self.fb.feedback_has_wake_up)
        else:
            self.enjoy_oneself_30_wakeup()

    def act_roleplay_in(self,cur):
        if self.work_mode == WORK_MODE_ROLE_PLAY:
            self.act_feedback_common(self.fb.feedback_rolep_re_in)
            return
        if cur - self.last_rp_chat_time <= 6:
            self.act_feedback_common(self.fb.feedback_rolep_freq_in)
            return
        role = 'timu' #self.daySchedule.get_currentRole()
        if role:
            self.last_rp_chat_time = cur
            self.work_mode = WORK_MODE_ROLE_PLAY

            self.listener_mode = ListenCommand.MODE_EXACT
            self.listen_pub.publish(self._listenCommand(ListenCommand.MODE_EXACT))

            #role__format = self.fb.feedback_rolep_in[0][0] % role
            role__format = self.fb.feedback_rolep_in[0][0]
            self.speak_pub.publish(self._speak_text(role__format))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_rolep_in[0][1], 3))

    def act_roleplay_out(self):
        if self.work_mode == WORK_MODE_ROLE_PLAY:
            self.work_mode = WORK_MODE_COMMON
            self.act_feedback_common(self.fb.feedback_rolep_out)

    def emotion_to_intents(self,cur,person_emotion):
        self.get_logger().info("emotion_to_intents:'%s', %s" % (person_emotion,cur - self.robotStatus.get_last_emotion_to_intents_time()))
        if Saw.PERSON_HAPPY == person_emotion:
            if cur - self.robotStatus.get_last_emotion_to_intents_time() < 30 * 60:
                return False
            if cur - self.robotStatus.last_happy_emotion_time < 5*60:
                self.robotStatus.happy_count += 1
            else:
                self.robotStatus.happy_count = 1
            self.get_logger().info("happy_count:'%s'" % self.robotStatus.happy_count)
            self.robotStatus.last_happy_emotion_time = cur
            if self.robotStatus.happy_count !=  5:
                return False
            happy_intent = self.robot_intents.get_intent(self.locale.emotion_to_happy)
            if not happy_intent:
                return False
            self.robotStatus.happy_count = 0
            self.robotStatus.set_last_emotion_to_intents_time(cur)
            self.talk_seq = happy_intent.command
            self.talk_seq.start("")
            self.act_talk_heart(self.robot_intents.embedding_another(self.locale.emotion_to_happy))
            self.listener_mode = ListenCommand.MODE_EXACT
            self.listen_pub.publish(self._listenCommand(ListenCommand.MODE_EXACT))
            self.greeting_time = cur + 5 * 60
            return True
        elif Saw.PERSON_SAD == person_emotion:
            if cur - self.robotStatus.get_last_emotion_to_intents_time() < 30 * 60:
                return False
            if cur - self.robotStatus.last_sad_emotion_time < 5 * 60:
                self.robotStatus.sad_count += 1
            else:
                self.robotStatus.sad_count = 1
            self.get_logger().info("sad_count:'%s'" % self.robotStatus.sad_count )
            self.robotStatus.last_sad_emotion_time = cur
            if self.robotStatus.sad_count != 5:
                return False
            sad_intent = self.robot_intents.get_intent(self.locale.emotion_to_sad)
            if not sad_intent:
                return False
            self.robotStatus.sad_count = 0
            self.robotStatus.set_last_emotion_to_intents_time(cur)
            self.talk_seq = sad_intent.command
            self.talk_seq.start("")
            self.act_talk_heart(self.robot_intents.embedding_another(self.locale.emotion_to_sad))
            self.listener_mode = ListenCommand.MODE_EXACT
            self.listen_pub.publish(self._listenCommand(ListenCommand.MODE_EXACT))
            self.greeting_time = cur + 5 * 60
            return True
        elif Saw.PERSON_SURPRISE == person_emotion:
            pass
        elif Saw.PERSON_ANGER == person_emotion:
            pass
        elif Saw.PERSON_DISGUST == person_emotion:
            pass
        elif Saw.PERSON_FEAR == person_emotion:
            pass
        elif Saw.PERSON_CONTEMPT == person_emotion:
            pass
        elif Saw.PERSON_NEUTRAL == person_emotion:
            pass
        return False

    def do_see_dog_things_act(self,cur,things):
        if len(things) == 0 :
            return
        if cur - self.last_saw_things_time <= 10 * 60:
            return
        saw_things = self.check_things(things,[Saw.TYPE_CAT,Saw.TYPE_DOG])
        self.get_logger().info('saw_dog_things: "%s", %s ' % (saw_things,cur - self.last_saw_things_time))
        for an in saw_things:
            if Saw.TYPE_CAT == an:
                if self.check_continuous(cur,an):
                    self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_CAT,4))
                    self.speak_pub.publish(self._speak_asset(self.fb.feedback_hello_cat[0][0]))
                    self.last_saw_things_time = cur
                    self.greeting_time = cur + 5 * 60
                    self.act_head_updown('up')
            elif Saw.TYPE_DOG == an:
                if self.check_continuous(cur,an):
                    self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_DOG,4))
                    self.speak_pub.publish(self._speak_asset(self.fb.feedback_hello_dog[0][0]))
                    self.last_saw_things_time = cur
                    self.greeting_time = cur + 5 * 60
                    self.act_head_updown('up')
            time.sleep(0.5)
    def check_things(self,things,params):
        thing_types = []
        for an in params:
            for thing in things :
                if an == thing.type:
                    thing_types.append(an)
                    break
        return thing_types
    def check_continuous(self,cur,param):
        self.get_logger().info('self.lasted_things1: %s' % self.lasted_things)
        if len(self.lasted_things) >= 5:
            self.lasted_things.pop(0)
        for t, last_saw_time in self.lasted_things:
            self.get_logger().info('t: %s ,%s ' % (t,cur - last_saw_time))
            if t == param and cur - last_saw_time <= 15 :
                self.lasted_things.append((param, cur))
                return True
        self.lasted_things.append((param, cur))
        return False

    def do_care(self,saw_data):
        self.do_late_night_care(saw_data)
        self.do_sit_long_care(saw_data)
    
    def do_sit_long_care(self, saw_data):
        self.get_logger().info('do_sit_long_care ' )
        if self.last_warn_time.date() != datetime.now().date():
            self.last_warn_time = datetime.now()
            self.sit_long_count = 0
            self.watch_long_count = 0
            self.health_warn_count = 0
            self.be_quiet = False
            self.last_see_sit_long_time = 0
        
        cur = time.time()
        if cur - self.last_see_sit_long_time < 50 * 60: 
            return
        self.last_see_sit_long_time = cur
        
        if len(saw_data.persons)>0 and len(self.check_things(saw_data.things,[Saw.TYPE_KEYBOARD, Saw.TYPE_MOUSE, Saw.TYPE_CHAIR, Saw.TYPE_SOFA])) > 0 :
            self.sit_long_count += 1
        elif len(saw_data.persons)>0 and len(self.check_things(saw_data.things,[Saw.TYPE_CELLPHONE, Saw.TYPE_TVMONITOR, Saw.TYPE_LAPTOP])) > 0 :
            self.watch_long_count += 1
        
        if self.health_warn_count > 5 or self.be_quiet == True:
            self.get_logger().info('do_sit_long_care: health warn reach 5 or be quiet')
            return
        if self.sit_long_count >= 2:
            self.act_feedback_common(self.fb.feedback_sit_long_warn)
            self.health_warn_count += 1
        elif self.watch_long_count >= 2:
            self.act_feedback_common(self.fb.feedback_watch_long_warn)
            self.health_warn_count += 1

    def do_late_night_care(self,saw_data):
        self.get_logger().info('do_late_night_care ' )
        current_time = time.localtime()  # 获取本地时间
        # 获取当前的小时数
        hour = current_time.tm_hour
        # 判断在晚上8点
        if 20  > hour:
            return
        day = current_time.tm_mday
        if day in self.late_night_care_his:
            return
        self.late_night_care_his = {}
        self.get_logger().info('do_late_night_care 1')
        if len(saw_data.persons)>0 and len(self.check_things(saw_data.things,[Saw.TYPE_KEYBOARD,Saw.TYPE_CUP,Saw.TYPE_MOUSE])) >=2 :
            self.act_feedback_common(self.fb.feedback_late_night_care)
            self.act_head_updown('up')
            self.late_night_care_his[day] = 1

    def check_collision_act(self,imu_data):
        cur = time.time()
        check_radio = 0
        if cur - self.last_collision_notify_time > 6 * 60:
            collision, severity, info = self.collision.check_collision(
                    imu_data.accel_x, imu_data.accel_y, imu_data.accel_z,
                    imu_data.gyro_x,  imu_data.gyro_y,  imu_data.gyro_z ,  cur)
            # 1、碰撞 震动
            if collision and severity > 2:
                self.get_logger().info('碰撞 检测: "%s"，等级："%s" ' % (collision,severity))
                self.last_collision_notify_time = cur
                check_radio = 1
                self.act_feedback_common(self.fb.feedback_collision_act,10)

        if check_radio ==1:
            return
        # 2、倒地
        if cur - self.last_fall_notify_time > 10 * 60:
            is_fallen = self.fall.detect_fall_simple(
                imu_data.accel_x, imu_data.accel_y, imu_data.accel_z,
                imu_data.gyro_x, imu_data.gyro_y, imu_data.gyro_z)
            if is_fallen:
                #self.get_logger().info('倒地 检测: "%s" ' % is_fallen)
                if cur - self.last_fall_time <= 4:  # 4s内
                    self.last_continus_fall_count += 1
                else:
                    self.last_continus_fall_count = 1
                self.last_fall_time = cur
            else:
                self.last_continus_fall_count = 0
            if self.last_continus_fall_count == 4:
                self.act_feedback_common(self.fb.feedback_fall,10)
                check_radio = 1
            elif self.last_continus_fall_count == 10:
                self.act_feedback_common(self.fb.feedback_fall_long,10)
                check_radio = 1
                self.last_fall_notify_time = cur

        if check_radio == 1:
            return
        # 3、检验倒立悬挂
        if cur - self.last_handstand_notify_time > 20 * 60:
            is_handstand, details = self.handstand.detect_handstand_simple(
                    imu_data.accel_x, imu_data.accel_y, imu_data.accel_z,
                    imu_data.gyro_x,  imu_data.gyro_y,  imu_data.gyro_z 		)
            if is_handstand:
                #self.get_logger().info('倒立悬挂 检测: "%s" ' % is_handstand )
                if cur - self.last_handstand_time <= 4:  # 4s内
                    self.last_continus_handstand_count += 1
                else:
                    self.last_continus_handstand_count = 1
                self.last_handstand_time = cur
            else:
                self.last_continus_handstand_count = 0
            if self.last_continus_handstand_count == 1:
                self.act_feedback_common(self.fb.feedback_hangstand_long, 10)
                self.act_action_relative(0.5, 25, 10, 0)
                time.sleep(1)
                self.act_action_reset()

            elif self.last_continus_handstand_count == 5:
                self.act_head_updown('down')
                self.act_feedback_common(self.fb.feedback_hangstand_long3,10)
                check_radio = 1
            elif self.last_continus_handstand_count == 12:
                self.act_head_updown('up')
                self.act_feedback_common(self.fb.feedback_hangstand_long10,10)
                check_radio = 1
                self.last_handstand_notify_time = cur

        if check_radio ==1:
            return
        # 4、摇晃
        is_shaking, details =  self.shake.detect_shake_simple(
                imu_data.accel_x, imu_data.accel_y, imu_data.accel_z,
                imu_data.gyro_x,  imu_data.gyro_y,  imu_data.gyro_z 		)
        if is_shaking:
            if cur - self.last_shake_notify_time > 1 * 60: #提醒间隔
                #self.get_logger().info('摇晃 检测: "%s" ' % is_shaking )
                #self.get_logger().info('imu data: "%.2f" "%.2f" "%.2f"' % (imu_data.accel_x, imu_data.accel_y, imu_data.accel_z))
                #self.get_logger().info('imu data: "%.2f" "%.2f" "%.2f"' % (imu_data.gyro_x, imu_data.gyro_y, imu_data.gyro_z))

                self.last_shake_notify_time = cur
                self.last_shake = 1
                self.act_feedback_common(self.fb.feedback_shake,10)

                self.act_action_relative(0.5, 25, 0, 0)
                time.sleep(1)
                self.act_action_relative(0.5, -50, 0, 0)
                time.sleep(1)
                self.act_action_reset()
        elif self.last_shake == 1 and cur - self.last_shake_notify_time > 5 :
            self.last_shake = 0
            self.act_feedback_common(self.fb.feedback_shake_stop)
            self.act_action_relative(0.5, 0, 10, 0)
            time.sleep(1)
            self.act_action_relative(0.5, 0, -10, 0)

    def command_query_temp(self,feedback):
        if not self.temperature:
            self.act_feedback_common(self.fb.feedback_no)
            return
        feedback__format = feedback[0][0] % int(self.temperature)
        self.speak_pub.publish(self._speak_text(feedback__format))
        self.emotion_pub.publish(self._emotion_without_effect(feedback[0][1], 3))

    def command_query_humid(self,feedback):
        if not self.humidity:
            self.act_feedback_common(self.fb.feedback_no)
            return
        feedback__format = feedback[0][0] % self.humidity
        self.speak_pub.publish(self._speak_text(feedback__format))
        self.emotion_pub.publish(self._emotion_without_effect(feedback[0][1], 3))

    def deal_his_flag(self,cur,his_flag):
        if not his_flag:
            return
        self.greeting_time = cur + 5 * 60
        if his_flag == INVITE_DAY_OFF:
            self.get_logger().info('his_flag: "%s" ' % his_flag)
            self.history_intent = self.robot_intents.create_day_off_int()
            self.history_intent_time = cur
        elif his_flag == INVITE_WATER:
            x = random.randint(1, 100)
            if x <= 35:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_day_invite_water_l[0][0]))
                self.act_righthand_updown('up')
        elif his_flag == INVITE_WEED:
            x = random.randint(1, 100)
            if x <= 35:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_day_invite_weed_l[0][0]))
                self.act_righthand_updown('up')

    def welcome(self):
        index = random.randint(0, len(self.fb.feedback_welcome) - 1)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_welcome[index][0]))

    def gather_intro(self,bind_result,cur):
        self.get_logger().info('gather_intro: bind_result：%s ' % bind_result )
        if not bind_result:
            return
        self.speak_pub.publish(self._speak_text(self.fb.feedback_gather_before[0][0]))
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_gather_intro[0][1], 3))
        self.speak_pub.publish(self._speak_text(self.fb.feedback_gather_intro[0][0]))
        self.history_intent = self.robot_intents.create_gather()
        self.history_intent_time = cur

    def gather_agree(self):
        self.robotStatus.set_last_busy_time(time.time())
        self.work_mode = WORK_MODE_GATHER
        self.gather_count = 0
        self.speak_pub.publish(self._speak_text(self.fb.feedback_gather_agree[0][0]))
        self.pub_see_command(See.COMMAND_START_SEE)
        self.robotStatus.set_last_sleep3_time(time.time() + 30)

    def gather_refuse(self):
        self.work_mode = WORK_MODE_COMMON
        self.speak_pub.publish(self._speak_text(self.fb.feedback_gather_refuse[0][0]))
        self.pub_see_command(See.COMMAND_USUAL)

    def gather_remember_me(self,cur):
        if self.daySchedule.person:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_gather_repeat[0][0]))
            return
        if not self.check_wifi():
            self.speak_pub.publish(self._speak_text(self.fb.feedback_bind_app_need_wifi[0][0]))
            return
        bind = self.daySchedule.check_bind()
        if bind == 0:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_no_need_bind[0][0]))
            return
        if self.work_mode == WORK_MODE_GATHER:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_gather_agree[0][0]))
            self.robotStatus.set_last_sleep3_time(cur + 30)
        else:
            self.robotStatus.set_last_busy_time(cur)
            self.work_mode = WORK_MODE_GATHER
            self.speak_pub.publish(self._speak_text(self.fb.feedback_gather_agree[0][0]))
            self.gather_count = 0
            self.last_saw_per_time = cur
            self.pub_see_command(See.COMMAND_START_SEE)
            self.robotStatus.set_last_sleep3_time(cur + 30)

    def person_identity(self,person,cur):
        if self.daySchedule.person and self.know_person_sim(person, self.daySchedule.person) > 0.8:
               return 1
        his, last_time, user_id, index = self.find_person_in_history(person)
        if his:
            self.history_person[index] = (his, cur, user_id)
            return 2
        if len(self.history_person) < MAX_REMEMBER_PERSON:
            self.history_person.append((person, time.time(), uuid.uuid4()))
        else:
            self.history_person.pop(0)
            self.history_person.append((person, time.time(), uuid.uuid4()))
        return 3
    def interaction_with_person(self,person_identity,person,cur):
        self.get_logger().info('person_identity(1是master 2是熟人 3是陌生人) :"%s"' % person_identity)
        if cur - self.greeting_time < 9 * 60:
            return
        if person_identity == 3 and cur - self.frontal_stranger_time >= 1.7 * 60 * 60 and person.check_frontal == 1:
            self.get_logger().info("stranger,check_frontal:'%s'" % person.check_frontal)
            self.frontal_stranger_time = cur
            self.greeting_time = cur
            index = random.randint(0, len(self.fb.feedback_frontal_no_master) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_frontal_no_master[index][0]))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_frontal_no_master[0][1], 12))
        elif person_identity == 1 and cur - self.frontal_master_time >= 30 * 60 and person.check_frontal == 1:
            self.check_frontal_act(person)
        elif cur - self.greeting_someone_time >= 2.9 * 60 * 60 :
            self.greeting_someone_time = cur
            self.greeting_time = cur
            if person_identity == 1:
                if self.daySchedule.nick:
                    feedback__format = self.fb.feedback_know_person[0][0] % self.get_repl()
                else:
                    feedback__format = self.fb.feedback_know_person[0][0] % ''
                self.speak_pub.publish(self._speak_text(feedback__format))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_know_person[0][1], 12))
            elif person_identity == 2:
                index = random.randint(0, len(self.fb.feedback_see_history) - 1)
                self.speak_pub.publish(self._speak_text(self.fb.feedback_see_history[index][0]))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_see_history[0][1], 12))
            elif person_identity == 3:
                index = random.randint(0, len(self.fb.feedback_see_no_history) - 1)
                self.speak_pub.publish(self._speak_text(self.fb.feedback_see_no_history[index][0]))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_see_no_history[0][1], 12))

    def check_frontal_act(self, person):
        self.get_logger().info("master,check_frontal:'%s'" % person.check_frontal)
        x = random.randint(1, 100)
        if x > 70:
            return
        current_time = time.localtime()  # 获取本地时间
        day = current_time.tm_mday
        time_time = time.time()
        if day in self.robotStatus.frontal:
            if self.robotStatus.frontal[day] > 3:
                return
            self.robotStatus.frontal[day] = +1
            self.robotStatus.frontal[time] = time_time
        else:
            self.robotStatus.frontal = {day: 1, time: time_time}
        self.frontal_master_time = cur
        self.greeting_time = cur
        self.speak_pub.publish(self._speak_text(self.fb.feedback_frontal_master[0][0]))
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_frontal_master[0][1],8))
        self.act_head_updown('up')

    def know_person(self,person,cur):
        if not self.daySchedule.person:
            return
        if cur - self.master_person_time > 7 * 24 * 60 * 60:
            self.get_logger().info("已经超过7天了")
            return
        if cur - self.master_person_notify_time < 3 * 60 * 60:
            self.get_logger().info("10个小时内已经提醒过了")
            return
        if self.know_person_sim(person, self.daySchedule.person) > 0.8:
            self.master_person_notify_time = cur
            if self.daySchedule.nick:
                feedback__format = self.fb.feedback_know_person[0][0] % self.get_repl()
            else:
                feedback__format = self.fb.feedback_know_person[0][0] % ''
            self.speak_pub.publish(self._speak_text(feedback__format))
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_know_person[0][1], 6))
    def know_person_sim(self,saw_person, master):
        if not master or not saw_person:
            self.get_logger().info("there is no master or saw_person")
            return 0
        try:
            same_count = 0
            if abs(master['face_height'] - saw_person.face_height) < 0.02:
                same_count += 1
            if abs(master['face_width'] - saw_person.face_width) < 0.02:
                same_count += 1
            if abs(master['ratio_face_wid_hei'] - saw_person.ratio_face_wid_hei) < 0.02:
                same_count += 1
            if abs(master['ratio_nose_face_wid'] - saw_person.ratio_nose_face_wid) < 0.02:
                same_count += 1
            if abs(master['ratio_mouth_wid'] - saw_person.ratio_mouth_wid) < 0.02:
                same_count += 1
            if abs(master['ratio_lefteye_wid'] - saw_person.ratio_lefteye_wid) < 0.02:
                same_count += 1
            if abs(master['ratio_lefteye_hei'] - saw_person.ratio_lefteye_hei) < 0.02:
                same_count += 1
            if abs(master['ratio_righteye_wid'] - saw_person.ratio_righteye_wid) < 0.02:
                same_count += 1
            if abs(master['ratio_righteye_hei'] - saw_person.ratio_righteye_hei) < 0.02:
                same_count += 1
            if abs(master['ratio_lefteyebrow_wid'] - saw_person.ratio_lefteyebrow_wid) < 0.02:
                same_count += 1
            if abs(master['ratio_lefteyebrow_hei'] - saw_person.ratio_lefteyebrow_hei) < 0.02:
                same_count += 1
            if abs(master['ratio_righteyebrow_wid'] - saw_person.ratio_righteyebrow_wid) < 0.02:  
                same_count += 1
            if abs(master['ratio_righteyebrow_hei'] - saw_person.ratio_righteyebrow_hei) < 0.02:
                same_count += 1
            if abs(master['ratio_chin_wid'] - saw_person.ratio_chin_wid) < 0.02:
                same_count += 1
            if abs(master['ratio_forehead_wid'] - saw_person.ratio_forehead_wid) < 0.02:
                same_count += 1
            ratio = same_count * 1.0 / Person.SPEC_NUM
            self.get_logger().info('check_master :"%s"' % ratio)
            return ratio
        except Exception as e:
            self.get_logger().info('check_master exception:"%s"' % e)
            return 0
    def is_master(self,cur):
        if cur - self.last_saw_per_time > 45:
            self.get_logger().info('is_master:	time is bigger than 45s')
            return None
        if not self.last_person:
            self.get_logger().info('is_master:	no person')
            return None
        if not self.daySchedule.person:
            self.get_logger().info('is_master:	no gather master')
            return 0
        if self.know_person_sim(self.last_person,self.daySchedule.person)> 0.8:
            return 2
        else:
            return 1
    def get_repl(self):
        if self.daySchedule.nick:
            repl = self.daySchedule.nick + self.repl_punctuation
        else:
            repl = self.repl_no_master
        return repl

    def get_lang(self):
        if os.path.exists(self.root_dir + api.config):
            with open(self.root_dir + api.config, 'r', encoding='utf-8') as f:
                json_str = f.read()
            ver_j = json.loads(json_str)
            if "lang" in ver_j:
                self.language = ver_j['lang']
    def change_lang(self,lang):
        path = self.root_dir + api.config
        init_data = {"lang": lang}
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                json_str = f.read()
                init_data = json.loads(json_str)
                init_data['lang'] = lang
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(init_data, file, ensure_ascii=False, indent=2)  # 或者其他初始化操作

    def is_not_first_on(self,path):
        return os.path.exists(path)
    def welcome_strategy(self,path):
        if self.is_not_first_on(path):
            self.welcome()
            self.grow_tree = self.local_load_grow_tree_info(path)
            self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_USUAL))
            self.inited = True
            return
        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_LINGHUN))
        time.sleep(3)
        self.act_xled_brightness(1.5,45)
        self.speak_pub.publish(self._speak_asset('welcome.wav'))
        time.sleep(1)
        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_SJSC))
        time.sleep(1.5)
        self.act_xled_brightness(0.3, 12)
        time.sleep(0.3)
        self.act_xled_brightness(0.3, 0)
        time.sleep(0.3)
        self.act_xled_brightness(0.3, 12)
        time.sleep(0.3)
        self.act_xled_brightness(0.3, 0)
        time.sleep(0.3)
        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_KAIHUA))
        i = 1
        while i < 6:
            self.act_xled_brightness(0.3, 12)
            time.sleep(0.3)
            self.act_xled_brightness(0.3, 0)
            time.sleep(0.3)
            i+=1
        self.grow_tree = self.local_load_grow_tree_info(path)
        self.welcome()
        self.act_action_with_hand_relative(2, 0, 0, 0, 0, 40)
        time.sleep(1.5)
        self.act_action_with_hand_relative(2, 0, 0, 0, 0, -40)
        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_USUAL))
        self.inited = True

    def change_to_lang(self,lang):
        if not lang:
            return
        if lang == self.language:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_change_no[0][0]))
            return
        self.change_lang(lang)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_change_success[0][0]))
        time.sleep(8)
        os.system("reboot")

    def local_load_grow_tree_info(self, data_path):
        try:
            self.get_logger().info("5、local_load_grow_tree_info")
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
                             "lastWater": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                json.dump(init_data, file, ensure_ascii=False, indent=2)  # 或者其他初始化操作
                #self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_CONNECTION_FOUND, 1))
                return init_data
        except Exception as e:
            self.get_logger().error("获取心灵之树当前状态失败: %s" % e)
            return None

    def watch_tv_pre(self,cur):
        if self.work_mode != WORK_MODE_TV_PRE:
            self.robotStatus.set_last_sleep3_time(time.time() + 3 * 60)
            self.pub_see_command(See.COMMAND_START_SEE)
            self.work_mode = WORK_MODE_TV_PRE
        self.tv_last_try_time = cur
        self.tv_try_count = 0
        self.tv_msgs = []
        time.sleep(6)
        self.watch_pre_to_tv([], cur)
    def stop_watch_tv(self,feedback):
        if self.work_mode == WORK_MODE_TV or self.work_mode == WORK_MODE_TV_PRE:
            self.work_mode = WORK_MODE_COMMON
            self.pub_see_command(See.COMMAND_STOP_SEE)
            self.pub_see_command(See.COMMAND_USUAL)
            #self.listen_pub.publish(self._listenCommand(ListenCommand.MODE_TV_STOP))
            self.speak_pub.publish(self._speak_text(feedback[0][0]))
    def watch_pre_to_tv(self,things,cur):
        if self.work_mode == WORK_MODE_TV:
            return
        check_things = self.check_things(things, [Saw.TYPE_TVMONITOR])
        self.get_logger().info('check_things: %s，cur - self.tv_last_try_time:%s' % (check_things,cur - self.tv_last_try_time))
        if len(check_things) > 0:
            self.work_mode = WORK_MODE_TV
            self.tv_last_msg_time = cur
            self.tv_last_no_wifi_emotion_time = cur - 40
            self.pub_see_command(See.COMMAND_WATCH_TV)
            current_time = time.localtime()  # 获取本地时间
            # 获取当前的小时数
            hour = current_time.tm_hour
            #self.listen_pub.publish(self._listenCommand(ListenCommand.MODE_TV_START))
            if 23 > hour:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_tv_in[0][0]))
            else:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_tv_late[0][0]))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_tv_late[0][1], 4))
        else:
            if self.tv_try_count == 0 and cur - self.tv_last_try_time < 2 * 60:
                self.tv_try_count = 1
                self.tv_last_try_time = cur
                self.speak_pub.publish(self._speak_text(self.fb.feedback_tv_no[0][0]))
            elif self.tv_try_count == 1 and 59 < cur - self.tv_last_try_time:
                self.tv_try_count = 2
                self.tv_last_try_time = cur
                self.speak_pub.publish(self._speak_text(self.fb.feedback_tv_try[0][0]))
            elif self.tv_try_count == 2 and 59 < cur - self.tv_last_try_time:
                self.tv_try_count = 3
                self.tv_last_try_time = cur
                self.speak_pub.publish(self._speak_text(self.fb.feedback_tv_try2[0][0]))
            elif self.tv_try_count == 3 and 59 < cur - self.tv_last_try_time:
                self.tv_try_count = 0
                self.tv_last_try_time = cur
                self.work_mode = WORK_MODE_COMMON
                self.pub_see_command(See.COMMAND_STOP_SEE)
                self.speak_pub.publish(self._speak_text(self.fb.feedback_tv_try3[0][0]))

    def watch_tv_save_msgs(self,msg,cur):
        if len(self.tv_msgs) >= 100:
            self.tv_msgs.pop(0)
        self.tv_msgs.append((msg, cur))

    def watch_tv_emotion(self,text,cur):
        if cur - self.tv_last_emotion_time < 5*60:
            return
        msgs = []
        for t, msg_time in self.tv_msgs:
            if cur - msg_time <= 15:
                msgs.append(t)
        msgs.append(text)
        if len(msgs) ==0 :
            return
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            response = requests.post(
                url=api.plotEmotion.replace("host-place-holder", self.host),
                json={"deviceCode": self.device_code, "tvMsgs": msgs,"lan":self.language},
                headers=headers,
                timeout=10)
            response.raise_for_status()
            response_json = response.json()
            result = response_json["data"]
            self.get_logger().info("表情互动result: %s" % result)
            if not result:
                return
            if "情绪平淡" in result:
                self.act_lefthand_updown('up', dur_time=1)
                return
            elif "极致爆笑" in result:
                self.tv_last_emotion_time = cur
                self.speak_pub.publish(self._speak_text(self.fb.feedback_stop_tv_hh[0][0]))
                self.act_head_updown('up',dur_time = 1)
            elif "高能反转" in result:
                self.tv_last_emotion_time = cur
                index = random.randint(0, len(self.fb.feedback_stop_tv_wa) - 1)
                self.speak_pub.publish(self._speak_text(self.fb.feedback_stop_tv_wa[index][0]))
                self.act_action_relative(0.5, 25, -15, 0)
                time.sleep(1)
                self.act_action_relative(1, -25, 0, 0)
                time.sleep(1)
                self.act_action_reset()
            elif "惊悚惊吓" in result:
                self.tv_last_emotion_time = cur
                self.emotion_pub.publish(self._emotion_without_effect(EMOTION.EMOTION_FEAR, 3))
                self.act_action_with_hand_relative(0.5, 0, 0, 0, -40, 40)
                time.sleep(1)
                self.act_action_with_hand_relative(0.5, 0, 0, 0, 40, -40)
            elif "极致虐心" in result:
                self.tv_last_emotion_time = cur
                index = random.randint(0, len(self.fb.feedback_stop_tv_ai) - 1)
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_stop_tv_ai[index][1], 3))
                self.speak_pub.publish(self._speak_text(self.fb.feedback_stop_tv_ai[index][0]))
                self.act_head_updown('down')
            elif "极致愤怒" in result:
                self.tv_last_emotion_time = cur
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_stop_tv_heng[0][1], 3))
                self.speak_pub.publish(self._speak_text(self.fb.feedback_stop_tv_heng[0][0]))
                self.act_look_leftright('right')
            elif "热血高光" in result:
                self.tv_last_emotion_time = cur
                self.emotion_pub.publish(self._emotion_without_effect(EMOTION.EMOTION_FIRM, 3))
                self.act_action_relative(0.5, 0, -15, 0)
                time.sleep(1)
                self.act_action_relative(0.5, 0, 27, 0)
                time.sleep(1)
                self.act_action_relative(0.5, 0, -27, 0)
                time.sleep(1)
                self.act_action_relative(0.5, 0, 15, 0)
            elif "极致甜宠心动" in result:
                self.tv_last_emotion_time = cur
                self.speak_pub.publish(self._speak_text(self.fb.feedback_stop_tv_oo[0][0]))
                self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_stop_tv_oo[0][1], 3))
                self.act_xled_brightness(1,30)
                time.sleep(1)
                self.act_xled_brightness(1, 0)
                time.sleep(1)
                self.act_xled_brightness(1, 30)
                time.sleep(1)
                self.act_xled_brightness(1, 0)
        except Exception as e:
            self.get_logger().error("表情互动失败: %s" % e)

    def watch_tv_no_wifi(self,saw_data,cur):
        self.get_logger().info('cur - self.tv_last_no_wifi_emotion_time: "%s" ' % (cur - self.tv_last_no_wifi_emotion_time))
        things = saw_data.things
        if len(things) == 0 :
            return
        tv_bound = None
        for thing in things:
            if Saw.TYPE_TVMONITOR == thing.type:
                tv_bound = thing.bound
                break
        if not tv_bound:
            return
        contents = []
        persons = saw_data.persons
        if cur - self.tv_last_no_wifi_emotion_time > 56 and len(persons) > 0:
            for pers in persons:
                self.get_logger().info('is_inside(tv_bound, pers.bound): "%s" ' % (is_inside(tv_bound, pers.bound)))
                if is_inside(tv_bound, pers.bound):
                    contents.append("person")
                    self.watch_tv_no_wifi_person(pers,cur)
                    self.pub_see_command(See.COMMAND_STOP_SEE)
                    break
        for thing in things:
            if Saw.TYPE_TVMONITOR == thing.type or not is_inside(tv_bound,thing.bound):
                continue
            contents.append(thing.type)
            if cur - self.tv_last_no_wifi_emotion_time > 56:
                self.watch_tv_no_wifi_thing(thing,cur)
                self.pub_see_command(See.COMMAND_STOP_SEE)
        if len(contents) >0:
            self.watch_tv_save_msgs(','.join(contents), cur)

    def watch_tv_no_wifi_person(self,person,cur):
        if person.emotion == Saw.PERSON_HAPPY:
            self.tv_last_no_wifi_emotion_time = cur
            self.speak_pub.publish(self._speak_text(self.fb.feedback_stop_tv_oo[0][0]))
            self.act_xled_brightness(1, 30)
            time.sleep(1)
            self.act_xled_brightness(1, 0)
            time.sleep(1)
            self.act_xled_brightness(1, 30)
            time.sleep(1)
            self.act_xled_brightness(1, 0)
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_stop_tv_oo[0][1], 3))
        elif person.emotion == Saw.PERSON_ANGER:
            self.tv_last_no_wifi_emotion_time = cur
            self.speak_pub.publish(self._speak_text(self.fb.feedback_stop_tv_heng[0][0]))
            self.act_look_leftright('right')
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_stop_tv_heng[0][1], 3))
        elif person.emotion == Saw.PERSON_SAD:
            self.tv_last_no_wifi_emotion_time = cur
            index = random.randint(0, len(self.fb.feedback_stop_tv_ai) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_stop_tv_ai[index][0]))
            self.act_head_updown('down')
            self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_stop_tv_ai[index][1], 3))
        #elif person.emotion == Saw.PERSON_NEUTRAL:
        #    self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_FEAR, 3))
        elif person.emotion == Saw.PERSON_SURPRISE:
            self.tv_last_no_wifi_emotion_time = cur
            index = random.randint(0, len(self.fb.feedback_stop_tv_wa) - 1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_stop_tv_wa[index][0]))
            self.act_action_relative(1, 25, -15, 0)
            time.sleep(1)
            self.act_action_relative(1, -25, 0, 0)
            time.sleep(1)
            self.act_action_reset()
        #elif person.emotion == Saw.PERSON_NEUTRAL:
        #    self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_FEAR, 3))
        #elif person.emotion == Saw.PERSON_NEUTRAL:
        #    self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_FEAR, 3))
        else:
            self.tv_last_no_wifi_emotion_time = cur
            self.speak_pub.publish(self._speak_text(self.fb.feedback_stop_tv_default[0][0]))
            index = random.randint(0, 1)
            if index == 0:
                self.act_action_relative(0.5, 20, -20, 0)
            else:
                self.act_action_relative(0.5, -20, -20, 0)
            time.sleep(2)
            self.act_action_reset()
    def watch_tv_no_wifi_thing(self,thing,cur):
        if Saw.TYPE_KNIFE == thing.type:
            x = random.randint(1, 100)
            if x <= 60:
                self.tv_last_no_wifi_emotion_time = cur
                self.act_action_with_hand_relative(1, 0, 0, 0, -40, 40)
                time.sleep(1)
                self.act_action_with_hand_relative(1, 0, 0, 0, 40, -40)
                self.emotion_pub.publish(Emotion.EMOTION_SHY,5)
        elif Saw.TYPE_CAT == thing.type:
            x = random.randint(1, 100)
            if x <= 60:
                self.tv_last_no_wifi_emotion_time = cur
                self.emotion_pub.publish(Emotion.EMOTION_CAT, 5)
        elif Saw.TYPE_DOG == thing.type:
            x = random.randint(1, 100)
            if x <= 60:
                self.tv_last_no_wifi_emotion_time = cur
                self.emotion_pub.publish(Emotion.EMOTION_DOG, 5)
        elif Saw.TYPE_CAKE == thing.type or Saw.TYPE_VASE == thing.type or Saw.TYPE_TEDDY_BEAR == thing.type:
            x = random.randint(1, 100)
            if x <= 60:
                self.tv_last_no_wifi_emotion_time = cur
                self.act_xled_brightness(1, 16)
                time.sleep(1)
                self.act_xled_brightness(1, 0)
                time.sleep(1)
                self.act_xled_brightness(1, 16)
                time.sleep(1)
                self.act_xled_brightness(1, 0)
                time.sleep(1)
                self.act_xled_brightness(1, 16)
                time.sleep(1)
                self.act_xled_brightness(1, 0)
                self.emotion_pub.publish(Emotion.EMOTION_LOVE, 5)
        elif (Saw.TYPE_BANANA == thing.type or Saw.TYPE_APPLE == thing.type or Saw.TYPE_SANDWICH == thing.type
              or Saw.TYPE_ORANGE == thing.type  or Saw.TYPE_BROCCOLI == thing.type
                or Saw.TYPE_CARROT == thing.type  or Saw.TYPE_HOT_DOG == thing.type
                or Saw.TYPE_PIZZA == thing.type  or Saw.TYPE_DONUT == thing.type
                or Saw.TYPE_CAKE == thing.type):
            x = random.randint(1, 100)
            if x <= 60:
                self.tv_last_no_wifi_emotion_time = cur
                self.emotion_pub.publish(Emotion.EMOTION_LUNCHING, 5)

    def watch_tv_say(self,msg):
        msgs = []
        if len(self.tv_msgs) ==0 :
            self.speak_pub.publish(self._speak_text(self.fb.feedback_tv_no_msg[0][0]))
            return
        for t, msg_time in self.tv_msgs:
            msgs.append(t)
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            response = requests.post(
                url = api.mvSay.replace("host-place-holder", self.host),
                json= {"deviceCode": self.device_code, "tvMsgs": msgs, "msg": msg,"lan":self.language},
                headers=headers,
                timeout=10)
            response.raise_for_status()
            response_json = response.json()
            result = response_json["data"]
            self.get_logger().info("watch_tv_say result: %s" % result)
            if result:
                self.speak_pub.publish(self._speak_text(result))
        except Exception as e:
            self.get_logger().error("watch_tv_say失败: %s" % e)

    def music_pre(self,cur):
        if self.work_mode != WORK_MODE_MUSIC_PRE:
            self.work_mode = WORK_MODE_MUSIC_PRE
            self.listen_pub.publish(self._listenCommand(ListenCommand.MODE_MUSIC_START))
            self.speak_pub.publish(self._speak_text(self.fb.feedback_music_in[0][0]))
        self.music_last_try_time = cur
        self.music_try_count = 0
    def stop_music(self,feedback):
        if self.work_mode == WORK_MODE_MUSIC or self.work_mode == WORK_MODE_MUSIC_PRE :
            self.work_mode = WORK_MODE_COMMON
            self.listen_pub.publish(self._listenCommand(ListenCommand.MODE_MUSIC_STOP))
            self.speak_pub.publish(self._speak_text(feedback[0][0]))
    def pre_to_music(self,flag,cur):
        if self.work_mode == WORK_MODE_MUSIC:
            return
        self.get_logger().info('pre_to_music: %s,cur - self.music_last_try_time: %s' % (flag,cur - self.music_last_try_time) )
        self.music_last_msg_time = cur
        if flag:
            self.work_mode = WORK_MODE_MUSIC
        else:
            if self.music_try_count == 0 and cur - self.music_last_try_time < 2 * 60:
                self.music_try_count = 1
                self.music_last_try_time = cur
                self.speak_pub.publish(self._speak_text(self.fb.feedback_music_no[0][0]))
            elif self.music_try_count == 1:
                self.music_try_count = 2
                self.music_last_try_time = cur
                self.speak_pub.publish(self._speak_text(self.fb.feedback_music_try[0][0]))
            elif self.music_try_count == 2:
                self.music_try_count = 3
                self.music_last_try_time = cur
                self.work_mode = WORK_MODE_COMMON
                self.listen_pub.publish(self._listenCommand(ListenCommand.MODE_MUSIC_STOP))
                self.speak_pub.publish(self._speak_text(self.fb.feedback_music_try3[0][0]))
    def music_emotion(self,cur):
        if cur -self.music_last_emotion_time < 6 :
            return
        self.music_last_emotion_time = cur
        self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_INTEREST, 5))
        index = random.randint(0, len(self.fb.feedback_music_) - 1)
        self.speak_pub.publish(self._speak_asset(self.fb.feedback_music_[index][0]))

        self.act_action_relative(0.5, 0, -15, 0)
        time.sleep(1)
        self.act_action_relative(0.5, 0, 27, 0)
        time.sleep(1)
        self.act_action_relative(0.5, 0, -27, 0)
        time.sleep(1)
        self.act_action_relative(0.5, 0, 15, 0)

    def music_say(self,msg):
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            response = requests.post(
                url=api.musicSay.replace("host-place-holder", self.host),
                json={"deviceCode": self.device_code, "msg": msg,"lan":self.language},
                headers=headers,
                timeout=10)
            response.raise_for_status()
            response_json = response.json()
            result = response_json["data"]
            self.get_logger().info("music_say result: %s" % result)
            if result:
                self.speak_pub.publish(self._speak_text(result))
        except Exception as e:
            self.get_logger().error("music_say失败: %s" % e)

    def upload_scrap(self,saw_data,scrap_file):
        if not self.check_wifi() or not self.daySchedule.token:
            self.get_logger().info("----------------no wifi /no token")
            os.system("rm "+ self.root_dir + f'/tm_mini/{scrap_file}')
            return
        if self.daySchedule.is_sleep_time():
            self.get_logger().info("----------------sleep_time")
            os.system("rm " + self.root_dir + f'/tm_mini/{scrap_file}')
            return
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                "authorization": self.daySchedule.token
            }
            payload = {"createDate": scrap_file[0:10]}
            response = requests.post(
                url     =  api.checkTodayPhoto.replace("host-place-holder", self.host),
                headers =  headers,
                json    =  payload,
                timeout=10)
            response.raise_for_status()
            self.get_logger().info("抓拍开关----------------%s,%s" % (response.json(),payload))
            if response.json()["status"] != '0':
                os.system("rm " + self.root_dir + f'/tm_mini/{scrap_file}')
                return

            things = saw_data.things
            persons = saw_data.persons
            if len(persons)>0:
                b_type = 2
                narration = None
                thing_types = []
                if len(persons) ==1:
                    thing_types.append("one people")
                elif len(persons) ==2:
                    thing_types.append("two people")
                elif len(persons) ==3:
                    thing_types.append("three people")
                elif len(persons) > 3:
                    thing_types.append("many peoples")
                for thing in things:
                    thing_types.append(thing.type)
                keyWords = ','.join(thing_types)
            else:
                saw_things = self.check_things(things, [Saw.TYPE_CAT, Saw.TYPE_DOG])
                if len(saw_things) > 0:
                    things_ = self.things_trans[saw_things[0]]
                    b_type = 1
                    check_things = self.check_things(things, [Saw.TYPE_BED, Saw.TYPE_SOFA, Saw.TYPE_CHAIR])
                    if len(check_things)>0:
                        narration = self.fb.feedback_scrap_1[0][0] % (things_,self.things_trans[check_things[0]])
                    elif len(self.check_things(things, [Saw.TYPE_BOWL])) > 0:
                        narration = self.fb.feedback_scrap_2[0][0] % (things_, things_)
                    elif self.is_point_in_bounds(things[0].bound[0],things[0].bound[1],[0, 0, 100, 100]):
                        narration = self.fb.feedback_scrap_3[0][0] % things_
                    else:
                        narration = self.fb.feedback_scrap_default[0][0] % things_
                    keyWords = None
                else:
                    b_type = 2
                    narration = None
                    thing_types =[]
                    for thing in things:
                        thing_types.append(thing.type)
                    keyWords = ','.join(thing_types)
            headers = {
                "authorization": self.daySchedule.token
            }
            data = {
                "lan": self.language,
                "type": b_type,
                "keyWords": keyWords,
                "narration": narration
            }
            with open(self.root_dir + f'/tm_mini/{scrap_file}', "rb") as f:
                # 格式: (文件名, 文件对象, Content-Type)
                files = {"file": (scrap_file, f, "image/jpeg")}
                files["data"] = (None, json.dumps(data), "application/json")
                response = requests.post(
                    url  = api.uploadScrap.replace("host-place-holder", self.host),
                    files= files,
                    headers=headers,
                    timeout=10)
                if response.status_code == 403:
                    print("403 Forbidden Error111")
                else:
                    response.raise_for_status()
                    response_json = response.json()
                    result = response_json["data"]
                    print("result:", result)
            os.system("rm " + self.root_dir + f'/tm_mini/{scrap_file}')
        except Exception as e:
            os.system("rm " + self.root_dir + f'/tm_mini/{scrap_file}')
            self.get_logger().error("抓拍上传 失败: %s" % e)

    def is_point_in_bounds(self,x, y, bounds):
        """
        判断点是否在边界内
        bounds: [xmin, ymin, xmax, ymax] 或 [xmin, xmax, ymin, ymax]
        """
        xmin, ymin, xmax, ymax = bounds
        return xmin <= x <= xmax and ymin <= y <= ymax

    def rfid_type(self, r_id):
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            response = requests.post(
                url=api.getRfid.replace("host-place-holder", self.host),
                json={"deviceCode": self.device_code, "rfidId": r_id, "lan": self.language},
                headers=headers,
                timeout=10)
            response.raise_for_status()
            response_json = response.json()
            result = response_json["data"]
            self.get_logger().info("rfid_type result: %s" % result)
            if result:
                if result["data"] == 1:
                    self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_CAT,4))
                    self.speak_pub.publish(self._speak_asset(self.fb.feedback_hello_cat[0][0]))
                    self.act_action_relative(0.5, 0, -15, 0)
                    time.sleep(1)
                    self.act_action_relative(0.5, 0, 15, 0)
                    time.sleep(1)
                    self.act_action_relative(0.5, 0, -15, 0)
                    time.sleep(1)
                    self.act_action_relative(0.5, 0, 15, 0)
                elif result["data"] == 2:
                    self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_TSUNDERE, 2))
                    self.speak_pub.publish(self._speak_text(self.fb.feedback_rfid_ear[0][0]))
                    self.act_action_with_hand_relative(0.5, 0, -15, 0, 0, 40)
                    time.sleep(1)
                    self.emotion_pub.publish(self._emotion_without_effect(Emotion.EMOTION_LAUGH, 2))
                    self.act_action_with_hand_relative(0.5, 0, 15, 0, 0, -40)
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, 0, 0, 0,  -40, 40)
                    time.sleep(1)
                    self.act_action_with_hand_relative(0.5, 0, 0, 0, 40 , -40)


        except Exception as e:
            self.get_logger().error("rfid_type失败: %s" % e)

    def rfid_type_save(self, r_id,r_type):
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                "authorization": '111'
            }
            response = requests.post(
                url= 'https://api.timuai.com/user/tm-rfid/saveRfid',
                json= {"deviceCode": self.device_code, "rfidId": r_id, "rType": r_type},
                headers=headers,
                timeout=10)
            response.raise_for_status()
            response_json = response.json()
            result = response_json["data"]
            self.speak_pub.publish(self._speak_text('保存成功'))
            self.get_logger().info("rfid_type_save result: %s" % result)
        except Exception as e:
            self.speak_pub.publish(self._speak_text('保存失败'))
            self.get_logger().error("rfid_type_save 失败: %s" % e)

    def command_action_reset(self):
        self.act_action_reset()
        self.speak_pub.publish(self._speak_text(self.fb.feedback_action_reset[0][0]))

    def load_email_auth(self):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            "authorization": self.daySchedule.token
        }
        response = requests.post(
            url=api.loadEmailInfo.replace("host-place-holder", self.host),
            headers=headers,
            timeout=10)
        response.raise_for_status()
        self.get_logger().info("load_email_auth--%s" % response.json())
        return response.json()
    def read_mail(self):
        self.get_logger().info("读取邮件--")
        if not self.daySchedule.token:
            self.speak_pub.publish(self._speak_text(self.fb.feedback_no_need_bind[0][0]))
            return
        self.daySchedule.mail_body = []
        self.speak_pub.publish(self._speak_text(self.fb.feedback_email_begin[0][0]))
        try:
            # 连接到IMAP服务器
            #mail = imaplib.IMAP4_SSL('imap.qiye.aliyun.com')
            #mail.login('support@timuai.com',
            #           'vNBI2HCan3tobpmo' )
            #mail = imaplib.IMAP4_SSL('imap.qq.com')
            #mail.login('962981039@qq.com',
            #           'dxbdfbmqyprhbbec')
            authInfo = self.load_email_auth()
            if authInfo['status'] != '0':
                self.get_logger().info("读取邮件-----------1")
                self.speak_pub.publish(self._speak_text(self.fb.feedback_email_not_valid[0][0]))
                return
            data_ = authInfo['data']
            if 'email' not in data_ or 'eprotocol' not in data_:
                self.get_logger().info("读取邮件-----------2")
                self.speak_pub.publish(self._speak_text(self.fb.feedback_email_not_valid[0][0]))
                return
            mail = imaplib.IMAP4_SSL(data_['eprotocol'])
            mail.login(data_['email'],  data_['authCode'])
            # 选择收件箱
            mail.select('inbox')

            date_since = (datetime.now() - timedelta(days=3)).strftime('%d-%b-%Y')
            # 搜索未读邮件
            result, data = mail.search(None, f'UNSEEN SINCE "{date_since}"')
            mail_ids = data[0].split()
            self.get_logger().info('mail_ids :"%s"' % len(mail_ids))
            self.mail_count = len(mail_ids)
            if self.mail_count == 0:
                self.speak_pub.publish(self._speak_text(self.fb.feedback_email_no[0][0]))
                mail.close()
                mail.logout()
                return

            mail_list = ''
            i = 1
            for num in mail_ids:
                # 获取邮件内容
                result, data = mail.fetch(num, '(RFC822)')
                raw_email = data[0][1]
                # 解析邮件
                msg = email.message_from_bytes(raw_email)

                subject = self.decode_mime_header(msg['Subject'])
                from_addr = self.decode_mime_header(msg['From'])
                body = self.get_email_body(msg)
                date = msg['Date']
                # 获取邮件正文
                pattern1 = r'"([^"]+)"'
                match = re.search(pattern1, from_addr)
                if match:
                    from_addr = match.group(1)
                from_addr = from_addr.split('<')[0]
                dt = parsedate_to_datetime(date)
                formatted_date = dt.strftime(self.locale.email_date)
                if subject:
                    self.daySchedule.mail_body.append((from_addr, self.locale.email_msg_2 % subject, body, formatted_date))
                    mail_list = mail_list + str(i) + self.locale.email_msg_1 % from_addr + self.locale.email_msg_2 % subject
                else:
                    self.daySchedule.mail_body.append((from_addr, '', body, formatted_date))
                    mail_list = mail_list + str(i) + self.locale.email_msg_1 % from_addr
                mail.store(num, '+FLAGS', '\\Seen')
                i = i + 1
                time.sleep(1)
            self.speak_pub.publish(self._speak_text(self.fb.feedback_email_[0][0] % (self.mail_count, mail_list)))
            mail.close()
            mail.logout()
            return
        except Exception as e:
            self.get_logger().info(e)
        finally:
            self.get_logger().info("读取邮件-----------finally")

    def decode_mime_header(self,header):
        """解码邮件头信息"""
        if header is None:
            return ''

        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                if encoding:
                    try:
                        decoded_parts.append(part.decode(encoding))
                    except:
                        decoded_parts.append(part.decode('utf-8', errors='ignore'))
                else:
                    decoded_parts.append(part.decode('utf-8', errors='ignore'))
            else:
                decoded_parts.append(part)

        return ' '.join(decoded_parts)

    def get_email_body(self,msg):
        """获取邮件正文"""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # 跳过附件
                if "attachment" in content_disposition:
                    continue

                # 获取文本内容
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        continue
        else:
            # 非 multipart 邮件
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass

        return body[:350]  # 只返回前200个字符

def save_sys_time(time_store_path):
    try:
        current_time = datetime.now()
        config = {'sys_time': current_time.strftime('%Y-%m-%d %H:%M:%S')}
        print('save cur time:', config, time_store_path)
        with open(time_store_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)  # 美化格式
    except Exception as e:
        print('save cur time exception:', e)

def load_sys_time(time_store_path):
    if os.path.exists(time_store_path):
        try:
            with open(time_store_path, 'r', encoding='utf-8') as f:
                json_str = f.read()
            config = json.loads(json_str)
            sys_time = config['sys_time']
            print('load last save time:', sys_time)
            cmd = f'date -s "{sys_time}"'
            os.system(cmd)
        except Exception as e:
            print('load last time exception:', e)

def load_device(data_path):
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            device_code = f.read().strip()
            print('load_device:', device_code)
            return device_code
    except Exception as e:
        print('load_device:', e)
        return None

def is_inside(tv_bound, other_bound):
    """
    inner 和 outer 都是 (left, top, right, bottom) 格式
    """
    inner_left, inner_top, inner_right, inner_bottom = other_bound[0],other_bound[1],other_bound[2],other_bound[3]
    outer_left, outer_top, outer_right, outer_bottom = tv_bound[0],tv_bound[1],tv_bound[2],tv_bound[3]

    return (inner_left >= outer_left and
            inner_top >= outer_top and
            inner_right <= outer_right and
            inner_bottom <= outer_bottom)

def main(args=None):
    rclpy.init(args=args)

    robot_brain = RobotBrain()
    rclpy.spin(robot_brain)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    
    robot_brain.robot_intents.release()
    robot_brain.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
