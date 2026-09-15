import json
import time
import os
from datetime import datetime, date, timedelta
from calendar import monthrange
from robot_interfaces.msg import Emotion, Speak
import random
import pickle
import pytz
import zoneinfo


TASK_TYPE_MONTH = '每月'
TASK_TYPE_WEEK = '每周'
TASK_TYPE_DAILY = '每天'
TASK_TYPE_SINGLE = '单次'

LABEL_WAKE = '日常起床提醒'
LABEL_SLEEP = '早睡提醒'
LABEL_TRAVEL = '出行提醒'
LABEL_ANNIVERSARY = '纪念日提醒'
LABEL_MONEY = '还款提醒'
LABEL_PAY = '缴费提醒'
LABEL_DRINK = '喝水提醒'
LABEL_PILL = '吃药提醒'
LABEL_RETURN_VISIT = '复诊提醒'
LABEL_SIT_LONG = '久坐提醒'
LABEL_PET = '宠物照顾提醒'
LABEL_INTERVIEW = '面试提醒'
LABEL_MEETING = '会议提醒'
LABEL_EXAM = '考试提醒'
LABEL_EXERCISE = '健身提醒'
LABEL_SHIP = '拿快递提醒'
LABEL_WATER = '浇花提醒'
LABEL_OTHER = '其他'

BY_USER = 'user'
BY_SYSTEM = 'system'

EXPIRED_MIN_THRESHOLD = 60
REMOVE_MIN_THRESHOLD = 3 * 24 * 60 * 60
EMB_SAME_THRESHOLD = 0.95


def convert_to_system_timezone(cycle_value: str, cycle_time: str) -> tuple:
    # 直接解析为无时区时间
    dt = datetime.strptime(f"{cycle_value} {cycle_time}", "%Y-%m-%d %H:%M")
    
    # 计算偏移（系统时区相对东八区的差值）
    # time.timezone 是系统时区与 UTC 的偏移，东八区偏移为 -28800
    system_offset = -time.timezone  # 系统时区的 UTC 偏移（秒）
    beijing_offset = 8 * 3600       # 东八区的 UTC 偏移（秒）
    diff = system_offset - beijing_offset
    
    # 应用偏移
    result = dt + timedelta(seconds=diff)
    
    return result.strftime("%Y-%m-%d"), result.strftime("%H:%M")

class ScheduleTask:
    def __init__(self, cycle_value, cycle_time, title, ty, label, by, emb):
        self.cycle_value = cycle_value
        self.cycle_time = cycle_time
        self.title = title
        self.ty = ty
        self.label = label
        self.read_count = 0
        self.timestamp = time.time()
        self.by = by
        self.emb = emb 


class ScheduleTaskController:
    def __init__(self, fb, root_dir, logger, speak_pub, emotion_pub, action_pub, model):
        self.fb = fb
        self.task_list = []
        self.logger = logger
        self.speak_pub = speak_pub
        self.emotion_pub = emotion_pub
        self.action_pub = action_pub
        self.saved_path = root_dir + '/asset/data/schedule_task.pkl'
        self.prompt_audio = 'ding.wav'
        self._load_saved_task()
        self.model = model
        #self.logger.info('ScheduleTaskController init:%s' % self.model)
        #self.logger.info('ScheduleTaskController init:%s' % self.model.embedding('天气好'))
    
    def set_requests(self, requests):
        self.requests = requests
    
    def _load_saved_task(self):
        if os.path.exists(self.saved_path):
            with open(self.saved_path, 'rb') as f:
                self.task_list = pickle.load(f)
    
    def _save_file(self):
        with open(self.saved_path, 'wb') as f:
            pickle.dump(self.task_list, f)
        
    def create_task(self, cycle_value, cycle_time, title, ty, label):
        start = time.time()
        if len(cycle_time) == 0 or len(title) == 0:
            self.logger.info('create_task: cycle_time or title invalid')
            self._act_feedback(self.fb.feedback_schedule_create_failed)
            return
            
        if ty != TASK_TYPE_MONTH and ty != TASK_TYPE_WEEK and ty != TASK_TYPE_DAILY:
            ty = TASK_TYPE_SINGLE
        if ty == TASK_TYPE_SINGLE and len(cycle_value) == 0:
            self.logger.info('create_task: cycle_value empty when task is single')
            self._act_feedback(self.fb.feedback_schedule_create_failed)
            return
        if not self._is_valid_label(label):
            label = LABEL_OTHER
            
        if ty == TASK_TYPE_SINGLE:
            cycle_value, cycle_time = convert_to_system_timezone(cycle_value, cycle_time)
            self.logger.info('create_task: cycle_value, cycle_time: %s %s' % (cycle_value, cycle_time))
        
        task = ScheduleTask(cycle_value, cycle_time, title, ty, label, BY_USER, self.model.embedding(title))
        same = self._check_same(task)
        if same:
            self.logger.info('create_task:there is already same task')
            self._act_same_task_warn(same)
            return
        
        result = self.requests.request_create_schedule_task({"label":task.label,
            "title":task.title,
            "cycle_type": task.ty,
            "cycle_value": task.cycle_value,
            "cycle_time": task.cycle_time})
        self.logger.info('create_task: request result %s waste time %s' % (result, time.time()- start))
        if not result:
            self.logger.info('create_task:failed')
            return
        task._id = result['data']
        guess = self._guess_task(task)
        self.task_list.append(task)
        
        if guess:
            self.logger.info('create_task:create another same task by system:%s' % guess)
            result = self.requests.request_create_schedule_task({"label":task.label,
                "title": guess.title,
                "cycle_type": guess.ty,
                "cycle_value": guess.cycle_value,
                "cycle_time": guess.cycle_time})
            if result:
                guess._id = result['data']
                self.task_list.append(guess)
        self._save_file()
        self._act_create_task(task)
        self.logger.info('create_task: waste time:%s' % (time.time() - start))
    
    def _check_same(self, task):
        cur_ts = self._get_task_expired_timestamp(task)
        for t in self.task_list:
            ts = self._get_task_expired_timestamp(t)
            if ts and abs(cur_ts - ts) < EXPIRED_MIN_THRESHOLD and self.model.cosine_similarity(t.emb, task.emb) > EMB_SAME_THRESHOLD:
                return t
    
    def _check_task_exist_on_server(self, li):
        if len(li) == 0:
            return []
        ids = []
        for i in li:
            ids.append(i._id)
        result = self.requests.request_check_schedule_task({"ids": ids})
        return result['data']
    
    def _guess_task(self, task):
        if task.ty != TASK_TYPE_SINGLE:
            return
        count = 0
        self.logger.info('_guess_task: %s %s %s' % (task.cycle_value, task.cycle_time, task.title))
        cur_task_ts = datetime.strptime(f'{task.cycle_value} {task.cycle_time}', "%Y-%m-%d %H:%M").timestamp()
        for t in self.task_list:
            if t.ty != TASK_TYPE_SINGLE or t.by != BY_USER:
                continue
            self.logger.info('_guess_task t: %s %s %s' % (t.cycle_value, t.cycle_time, t.title))
            ts = datetime.strptime(f'{t.cycle_value} {t.cycle_time}', "%Y-%m-%d %H:%M").timestamp()
            delta = cur_task_ts - ts
            if delta > 24.1 * 60 * 60 or delta < 23.9 * 60* 60:
                continue
            sim = self.model.cosine_similarity(t.emb, task.emb)
            if sim > EMB_SAME_THRESHOLD:
                return ScheduleTask(self._add_one_day(task.cycle_value), task.cycle_time, task.title, task.ty, task.label, BY_SYSTEM, task.emb)
        return
    
    def _add_one_day(self, date_str: str) -> str:
        """
                    将 yyyy-mm-dd 格式的日期字符串加一天
    
        Args:
        date_str: 日期字符串，如 "2024-04-16"
    
        Returns:
        加一天后的日期字符串，格式 "yyyy-mm-dd"
        """
        # 字符串转 datetime 对象
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        # 加一天
        dt_next = dt + timedelta(days=1)
        # 转回字符串
        return dt_next.strftime("%Y-%m-%d")

    def _get_week_nearest_timestamp(self, weekday: int, hour: int, minute: int = 0) -> int:
        """
                    根据周几和时分，获取离当前时间最近的时间戳
    
        Args:
        weekday: 星期几，1=周一，7=周日
        hour: 小时 (0-23)
        minute: 分钟 (0-59)，默认为 0
    
        Returns:
        整数时间戳
        """
        now = datetime.now()
    
        # 获取当前周几（datetime 中周一=0，周日=6）
        current_weekday = now.weekday()  # 0=周一, 6=周日
    
        # 将输入的 weekday（1=周一）转换为 datetime 格式（0=周一）
        target_weekday = weekday - 1
    
        # 计算天数差
        days_diff = target_weekday - current_weekday
    
        # 构造目标时间
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
        if days_diff == 0:
            # 同一天，比较时间
            if target_time >= now:
                # 如果目标时间在当前时间之后，使用今天
                pass
            else:
                # 如果目标时间已过，使用下周同一天
                days_diff = 7
        elif days_diff < 0:
            # 目标日期在本周已经过去，使用下周
            days_diff += 7
    
        # 加上天数差
        target_time += timedelta(days=days_diff)
    
        return int(target_time.timestamp())
    
    def _get_month_nearest_timestamp(self, day: int, hour: int, minute: int = 0) -> int:
        """
            根据每月几号和时分，获取未来的时间戳（如果本月已过则自动使用下个月）
    
        Args:
            day: 每月几号 (1-31)
            hour: 小时 (0-23)
            minute: 分钟 (0-59)，默认为 0
    
        Returns:
                    整数时间戳
        """
        now = datetime.now()
        current_year = now.year
        current_month = now.month
    
        # 获取当月天数
        _, last_day = monthrange(current_year, current_month)
        target_day = min(day, last_day)
    
        # 构造本月目标时间
        target_time = now.replace(day=target_day, hour=hour, minute=minute, 
                              second=0, microsecond=0)
    
        # 如果本月目标时间已过，则计算下个月
        if target_time <= now:
            # 计算下个月的年份和月份
            if current_month == 12:
                next_year = current_year + 1
                next_month = 1
            else:
                next_year = current_year
                next_month = current_month + 1
        
            # 获取下个月天数
            _, next_last_day = monthrange(next_year, next_month)
            next_target_day = min(day, next_last_day)
        
            target_time = datetime(next_year, next_month, next_target_day,
                               hour, minute, 0, 0)
    
        return int(target_time.timestamp())
    
    def _get_task_expired_timestamp(self, task):
        timestamp = None
        if task.ty == TASK_TYPE_SINGLE:
            #self.logger.info('_get_task_expired_timestamp: %s %s %s' % (task.cycle_value, task.cycle_time, task.title))
            dt = datetime.strptime(f'{task.cycle_value} {task.cycle_time}', "%Y-%m-%d %H:%M")
            timestamp = dt.timestamp()
        elif task.ty == TASK_TYPE_DAILY:
            today = date.today()
            time_obj = datetime.strptime(task.cycle_time, "%H:%M").time()
            # 合并日期和时间
            dt = datetime.combine(today, time_obj)
            timestamp = dt.timestamp()
        elif task.ty == TASK_TYPE_WEEK: 
            parts = task.cycle_time.split(':')
            timestamp = self._get_week_nearest_timestamp(int(task.cycle_value), int(parts[0]), int(parts[1]))
        elif task.ty == TASK_TYPE_MONTH:
            parts = task.cycle_time.split(':')
            timestamp = self._get_month_nearest_timestamp(int(task.cycle_value), int(parts[0]), int(parts[1]))
        return timestamp
    
    def _check_task_expired(self, task):
        cur = time.time()
        timestamp = self._get_task_expired_timestamp(task)
        delta = timestamp - cur
        if task.ty == TASK_TYPE_SINGLE:
            if task.read_count == 0 and delta < EXPIRED_MIN_THRESHOLD and delta > 0:
                return True
        else:
            if delta < EXPIRED_MIN_THRESHOLD and delta > 0:
                return True
        return False
        
    def remove_history_task(self):
        re = []
        for task in self.task_list:
            if task.ty == TASK_TYPE_SINGLE:
                self.logger.info('remove_history_task: %s %s %s' % (task.cycle_value, task.cycle_time, task.title))
                dt = datetime.strptime(f'{task.cycle_value} {task.cycle_time}', "%Y-%m-%d %H:%M")
                timestamp = dt.timestamp()
                if time.time() - timestamp > REMOVE_MIN_THRESHOLD:
                    re.append(task)
        exists_id = self._check_task_exist_on_server(self.task_list)
        for t in self.task_list:
            if t._id not in exists_id and t not in re:
                re.append(t)
        if len(re) > 0:
            for d in re:
                self.task_list.remove(d)
            self._save_file()
            self.logger.info('remove_history_task: remove %s tasks, still have %s tasks ' % (len(re), len(self.task_list)))
        
    def notify_expired_task(self):
        li = []
        for task in self.task_list:
            if self._check_task_expired(task) == True:
                task.read_count += 1
                li.append(task)
                self.logger.info('notify_expired_task: find one expired task %s' % task)
        if len(li) == 0:
            return
        exists_id = self._check_task_exist_on_server(li)
        to_del = []
        should_save = False
        for t in li:
            if t._id not in exists_id:
                to_del.append(t)
                should_save = True
        if len(to_del) > 0:
            for d in to_del:
                li.remove(d)
                self.task_list.remove(d)
            self.logger.info('notify_expired_task: find %s task to delete, still %s task leave' % (len(to_del), len(self.task_list)))
        if len(li) > 0:
            self.logger.info('notify_expired_task: update expired %s tasks status to read:' % len(li))
            
            should_save = True
            #start notify
            #self._speak_file(self.prompt_audio)
            if len(li) == 1:
                if li[0].by == BY_USER: 
                    self._notify_one_task(li[0])
                else:
                    self._notify_guess_task(li[0])
            else:
                index = 1
                text = ''
                for t in li:
                    text = self.fb.feedback_schedule_index[0][0] % index + t.title +','
                    index +=1
                self._notify_many_task(len(li), text)
        if should_save == True:
            self._save_file()
    
    def tell_today_tasks(self):
        pre_text = self.fb.feedback_schedule_today
        start_ts = time.time()
        end_ts = int((datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        self._tell_range_tasks(pre_text, start_ts, end_ts)
        
    def tell_tomorrow_tasks(self):
        pre_text = self.fb.feedback_schedule_tomorrow
        start_ts = int((datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        end_ts = int((datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        self._tell_range_tasks(pre_text, start_ts, end_ts)
    
    def _tell_range_tasks(self, pre_text, start_ts, end_ts):
        li = []
        for t in self.task_list:
            ts = self._get_task_expired_timestamp(t)
            if ts and ts < end_ts and ts > start_ts:
                li.append(t)
        if len(li) == 0:
            self._act_tell_no_task(pre_text)
            return
        exists_id = self._check_task_exist_on_server(li)
        to_del = []
        should_save = False
        for t in li:
            if t._id not in exists_id:
                to_del.append(t)
                should_save = True
        if len(to_del) > 0:
            for d in to_del:
                li.remove(d)
                self.task_list.remove(d)
            self.logger.info('_tell_range_tasks: find %s task to delete, still %s task leave' % (len(to_del), len(self.task_list)))
            should_save = True
        
        if len(li) == 0:
            self._act_tell_no_task(pre_text)
        elif len(li) == 1:
            self._act_tell_one_task(pre_text, li[0])
        else:
            index = 1
            text = ''
            for t in li:
                parts = t.cycle_time.split(':')
                text += self.fb.feedback_schedule_index[0][0] % index + self.fb.feedback_schedule_time[0][0] % (parts[0], parts[1]) + t.title +','
                index +=1
            
            self._act_tell_many_task(pre_text, len(li), text)
        
        if should_save == True:
            self._save_file()
            
    def _act_tell_many_task(self, pre_text, count, text):
        index = random.randint(0, len(self.fb.feedback_schedule_tell_many_task)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_schedule_tell_many_task[index][0] % (pre_text, count, text)))
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_schedule_tell_many_task[index][1]))
            
    def _act_tell_one_task(self, pre_text, task):
        parts = task.cycle_time.split(':')
        index = random.randint(0, len(self.fb.feedback_schedule_tell_one_task)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_schedule_tell_one_task[index][0] % (pre_text, parts[0], parts[1], task.title)))
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_schedule_tell_one_task[index][1]))
        
    def _act_tell_no_task(self, pre_text):
        index = random.randint(0, len(self.fb.feedback_schedule_tell_no_task)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_schedule_tell_no_task[index][0] % pre_text))
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_schedule_tell_no_task[index][1]))
    
    def _is_valid_label(self, label):
        return label == LABEL_WAKE or label == LABEL_SLEEP or label == LABEL_TRAVEL or label == LABEL_ANNIVERSARY or label == LABEL_MONEY or label == LABEL_PAY or label == LABEL_DRINK or label == LABEL_PILL or label == LABEL_RETURN_VISIT or label == LABEL_SIT_LONG or label == LABEL_PET or label == LABEL_INTERVIEW or label == LABEL_MEETING or label == LABEL_EXAM or label == LABEL_EXERCISE or label == LABEL_SHIP or label == LABEL_WATER
    
    def _get_notify_fb(self, label):
        if label == LABEL_WAKE:
            return self.fb.feedback_schedule_task_notify_wake
        elif label == LABEL_SLEEP:
            return self.fb.feedback_schedule_task_notify_sleep
        elif label == LABEL_TRAVEL:
            return self.fb.feedback_schedule_task_notify_travel
        elif label == LABEL_ANNIVERSARY:
            return self.fb.feedback_schedule_task_notify_aniversary
        elif label == LABEL_MONEY:
            return self.fb.feedback_schedule_task_notify_money
        elif label == LABEL_PAY:
            return self.fb.feedback_schedule_task_notify_pay
        elif label == LABEL_DRINK:
            return self.fb.feedback_schedule_task_notify_drink
        elif label == LABEL_PILL:
            return self.fb.feedback_schedule_task_notify_pill
        elif label == LABEL_RETURN_VISIT:
            return self.fb.feedback_schedule_task_notify_return_visit
        elif label == LABEL_SIT_LONG:
            return self.fb.feedback_schedule_task_notify_sit_long
        elif label == LABEL_PET:
            return self.fb.feedback_schedule_task_notify_pet
        elif label == LABEL_INTERVIEW:
            return self.fb.feedback_schedule_task_notify_interview
        elif label == LABEL_MEETING:
            return self.fb.feedback_schedule_task_notify_meeting
        elif label == LABEL_EXAM:
            return self.fb.feedback_schedule_task_notify_exam
        elif label == LABEL_EXERCISE:
            return self.fb.feedback_schedule_task_notify_exercise
        elif label == LABEL_SHIP:
            return self.fb.feedback_schedule_task_notify_ship
        elif label == LABEL_WATER:
            return self.fb.feedback_schedule_task_notify_water
        else:
            return self.fb.feedback_schedule_one_task_notify
    
    def _notify_one_task(self, task):
        fb = self._get_notify_fb(task.label)
        index = random.randint(0, len(fb)-1)
        #self.get_logger().info('index: "%s"' % index)
        text = fb[index][0]
        if '%s' in text:
            text = text % task.title
        self.speak_pub.publish(self._speak_text(text))
        self.emotion_pub.publish(self._emotion_without_effect(fb[index][1]))
    
    def _notify_guess_task(self, task):
        index = random.randint(0, len(self.fb.feedback_schedule_guess_task_notify)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_schedule_guess_task_notify[index][0] % (task.title, task.title)))
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_schedule_guess_task_notify[index][1]))
    
    def _notify_many_task(self, count, text):
        index = random.randint(0, len(self.fb.feedback_schedule_many_task_notify)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(self.fb.feedback_schedule_many_task_notify[index][0] % (count, text)))
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_schedule_many_task_notify[index][1]))
        
    def _act_feedback(self, feedback):
        index = random.randint(0, len(feedback)-1)
        #self.get_logger().info('index: "%s"' % index)
        self.speak_pub.publish(self._speak_text(feedback[index][0]))
        self.emotion_pub.publish(self._emotion_without_effect(feedback[index][1]))
    
    def _act_create_task(self, task):
        index = random.randint(0, len(self.fb.feedback_schedule_create_success)-1)
        
        self.speak_pub.publish(self._speak_text(self.fb.feedback_schedule_create_success[index][0] % task.title))
        self.emotion_pub.publish(self._emotion_without_effect(self.fb.feedback_schedule_create_success[index][1]))
    
    def _act_same_task_warn(self, same):
        if same.by == BY_USER:
            fb = self.fb.feedback_schedule_same_task_warn
        else:
            fb = self.fb.feedback_schedule_same_with_system_warn
        
        index = random.randint(0, len(fb)-1)
        self.speak_pub.publish(self._speak_text(fb[index][0] ))
        self.emotion_pub.publish(self._emotion_without_effect(fb[index][1]))
        
    
    def _speak_text(self, text):
        speak = Speak()
        speak.audio_file = ""
        speak.text = text
        return speak
        
    def _speak_file(self, file):
        speak = Speak()
        speak.audio_file = file
        speak.text = ''
        return speak
        
    def _emotion_without_effect(self, _type, display_count = 1):
        emotion = Emotion()
        emotion.emotion_type = _type
        emotion.emotion_display_count = display_count
        return emotion
    
    
