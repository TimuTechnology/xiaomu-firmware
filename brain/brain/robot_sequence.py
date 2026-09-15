import os
import numpy as np
import time
import json

#可直接执行的步骤
SEQ_TYPE_EXECUTE = 1
#需要等待用户反馈的步骤
SEQ_TYPE_WAIT_USER = 2

class RobotSequenceFb:
    def __init__(self, ty, feedback, no_match_fb=None):
        self.ty = ty
        self.feedback = feedback
        self.no_match_fb = no_match_fb
    def _cosine_similarity(self, vec1, vec2):
        # 计算点积
        dot_product = np.dot(vec1, vec2)
        # 计算向量的模
        norm_vec1 = np.linalg.norm(vec1)
        norm_vec2 = np.linalg.norm(vec2)
        # 计算余弦相似度
        cosine_sim = dot_product / (norm_vec1 * norm_vec2)
        return cosine_sim
    def get_user_response(self, user_emb):
        if self.ty != SEQ_TYPE_WAIT_USER:
            print('cur is no need to match')
            return False
        for es, feedback in self.feedback:
            for e in es:
                sim = self._cosine_similarity(user_emb, e)
                if sim > 0.80:
                    return feedback
        return self.no_match_fb
    def is_execution(self):
        return self.ty == SEQ_TYPE_EXECUTE
    
class RobotSequences:
    def __init__(self, name, feedbacks):
        self.name = name
        self.feedbacks = feedbacks
        
    def start(self, init_text):
        #TODO:set cur step based on init text
        self.cur_step = 0
        
    def step(self):
        if self.cur_step >= len(self.feedbacks):
            return None
        cur_fb = self.feedbacks[self.cur_step]
        self.cur_step += 1
        return cur_fb
    
    def back(self):
        self.cur_step -= 1
    
    def is_finish(self):
        return self.cur_step == len(self.feedbacks)

class HappySequence(RobotSequences):
    def __init__(self, store_en, locale, fb):
        feedbacks = [
            RobotSequenceFb(SEQ_TYPE_EXECUTE, fb.feedback_see_happy),
            RobotSequenceFb(SEQ_TYPE_EXECUTE, fb.feedback_ask_happy_reason),
            RobotSequenceFb(SEQ_TYPE_WAIT_USER, [
                        ([store_en[item] for item in locale.intent_happy_for_salary], fb.feedback_happy_for_salary), 
                        ([store_en[item] for item in locale.intent_happy_for_new_friend], fb.feedback_happy_for_new_friend),
                        ([store_en[item] for item in locale.intent_happy_for_project], fb.feedback_happy_for_project),
                        ([store_en[item] for item in locale.intent_happy_for_receive], fb.feedback_happy_for_receive),
                        ([store_en[item] for item in locale.intent_happy_for_collabration], fb.feedback_happy_for_collabration),
                        ([store_en[item] for item in locale.intent_happy_for_new_skill], fb.feedback_happy_for_new_skill),
                        ([store_en[item] for item in locale.intent_happy_for_appreciate], fb.feedback_happy_for_appreciate),
                        ([store_en[item] for item in locale.intent_happy_for_romatic], fb.feedback_happy_for_romatic),
                        ([store_en[item] for item in locale.intent_happy_for_love], fb.feedback_happy_for_love),
                        ([store_en[item] for item in locale.intent_happy_for_pass], fb.feedback_happy_for_pass),
                        ([store_en[item] for item in locale.intent_happy_for_grow], fb.feedback_happy_for_grow),
                        ([store_en[item] for item in locale.intent_happy_for_direction_friend], fb.feedback_happy_for_direction_friend),
                        ([store_en[item] for item in locale.intent_happy_for_show], fb.feedback_happy_for_show),
                        ([store_en[item] for item in locale.intent_happy_for_party], fb.feedback_happy_for_party),
                        ([store_en[item] for item in locale.intent_happy_for_out], fb.feedback_happy_for_out),
                        ([store_en[item] for item in locale.intent_happy_for_interest], fb.feedback_happy_for_interest),
                        ([store_en[item] for item in locale.intent_happy_for_family_party], fb.feedback_happy_for_family_party),
                        ([store_en[item] for item in locale.intent_happy_for_family_help], fb.feedback_happy_for_family_help),
                        ([store_en[item] for item in locale.intent_happy_for_new_member], fb.feedback_happy_for_new_member),
                    ], 
                    fb.feedback_happy_not_match_reason)
        ]
        super().__init__('happy', feedbacks)

class SadSequence(RobotSequences):
    def __init__(self, store_en, locale, fb):
        feedbacks = [
            RobotSequenceFb(SEQ_TYPE_EXECUTE, fb.feedback_see_sad),
            RobotSequenceFb(SEQ_TYPE_EXECUTE, fb.feedback_ask_sad_reason),
            RobotSequenceFb(SEQ_TYPE_WAIT_USER, [
                        ([store_en[item] for item in locale.intent_sad_for_friend_betray], fb.feedback_sad_for_friend_betray),
                        ([store_en[item] for item in locale.intent_sad_for_failed], fb.feedback_sad_for_failed), 
                        ([store_en[item] for item in locale.intent_sad_for_social_anxiety], fb.feedback_sad_for_social_anxiety),
                        ([store_en[item] for item in locale.intent_sad_for_last_love], fb.feedback_sad_for_last_love),
                        ([store_en[item] for item in locale.intent_sad_for_project_failed], fb.feedback_sad_for_project_failed),
                        ([store_en[item] for item in locale.intent_sad_for_colleague_clash], fb.feedback_sad_for_colleague_clash),
                        ([store_en[item] for item in locale.intent_sad_for_criticized], fb.feedback_sad_for_criticized),
                        ([store_en[item] for item in locale.intent_sad_for_heart_tired], fb.feedback_sad_for_heart_tired),
                        ([store_en[item] for item in locale.intent_sad_for_upgrade_failed], fb.feedback_sad_for_upgrade_failed),
                        ([store_en[item] for item in locale.intent_sad_for_new_job], fb.feedback_sad_for_new_job),
                        ([store_en[item] for item in locale.intent_sad_for_huge_pressure], fb.feedback_sad_for_huge_pressure),
                        ([store_en[item] for item in locale.intent_sad_for_collobration], fb.feedback_sad_for_collobration),
                        ([store_en[item] for item in locale.intent_sad_for_result_snatched], fb.feedback_sad_for_result_snatched),
                        ([store_en[item] for item in locale.intent_sad_for_job_change], fb.feedback_sad_for_job_change),
                        ([store_en[item] for item in locale.intent_sad_for_social_overlooked], fb.feedback_sad_for_social_overlooked),
                        ([store_en[item] for item in locale.intent_sad_for_friend_clash], fb.feedback_sad_for_friend_clash),
                        ([store_en[item] for item in locale.intent_sad_for_anxiety_party], fb.feedback_sad_for_anxiety_party),
                        ([store_en[item] for item in locale.intent_sad_for_friend_betray_detail], fb.feedback_sad_for_friend_betray_detail),
                        ([store_en[item] for item in locale.intent_sad_for_join_new], fb.feedback_sad_for_join_new),
                        ([store_en[item] for item in locale.intent_sad_for_malicious_comments], fb.feedback_sad_for_malicious_comments),
                        ([store_en[item] for item in locale.intent_sad_for_unable_join_talk], fb.feedback_sad_for_unable_join_talk),
                        ([store_en[item] for item in locale.intent_sad_for_friend_away], fb.feedback_sad_for_friend_away),
                        ([store_en[item] for item in locale.intent_sad_for_beging_ostracized], fb.feedback_sad_for_beging_ostracized),
                        ([store_en[item] for item in locale.intent_sad_for_social_tired], fb.feedback_sad_for_social_tired),
                        ([store_en[item] for item in locale.intent_sad_for_break_up], fb.feedback_sad_for_break_up),
                        ([store_en[item] for item in locale.intent_sad_for_love_arguments], fb.feedback_sad_for_love_arguments),
                        ([store_en[item] for item in locale.intent_sad_for_crush_have_new], fb.feedback_sad_for_crush_have_new),
                        ([store_en[item] for item in locale.intent_sad_for_long_dist], fb.feedback_sad_for_long_dist),
                        ([store_en[item] for item in locale.intent_sad_for_clash_value], fb.feedback_sad_for_clash_value),
                        ([store_en[item] for item in locale.intent_sad_for_blind_failed], fb.feedback_sad_for_blind_failed),
                        ([store_en[item] for item in locale.intent_sad_for_infidelity], fb.feedback_sad_for_infidelity),
                        ([store_en[item] for item in locale.intent_sad_for_not_love_enough], fb.feedback_sad_for_not_love_enough),
                        ([store_en[item] for item in locale.intent_sad_for_excessive_control], fb.feedback_sad_for_excessive_control),
                        ([store_en[item] for item in locale.intent_sad_for_past_love], fb.feedback_sad_for_past_love),
                        ([store_en[item] for item in locale.intent_sad_for_exam_failed], fb.feedback_sad_for_exam_failed),
                        ([store_en[item] for item in locale.intent_sad_for_exam_anxiety], fb.feedback_sad_for_exam_anxiety),
                        ([store_en[item] for item in locale.intent_sad_for_paper_failed], fb.feedback_sad_for_paper_failed),
                        ([store_en[item] for item in locale.intent_sad_for_study_task], fb.feedback_sad_for_study_task),
                        ([store_en[item] for item in locale.intent_sad_for_lose_scholarship], fb.feedback_sad_for_lose_scholarship),
                        ([store_en[item] for item in locale.intent_sad_for_new_major], fb.feedback_sad_for_new_major),
                        ([store_en[item] for item in locale.intent_sad_for_team_contribute], fb.feedback_sad_for_team_contribute),
                        ([store_en[item] for item in locale.intent_sad_for_course_failed], fb.feedback_sad_for_course_failed),
                        ([store_en[item] for item in locale.intent_sad_for_study_reject], fb.feedback_sad_for_study_reject),
                        ([store_en[item] for item in locale.intent_sad_for_study_stress], fb.feedback_sad_for_study_stress),
                        ([store_en[item] for item in locale.intent_sad_for_arguments_parents], fb.feedback_sad_for_arguments_parents),
                        ([store_en[item] for item in locale.intent_sad_for_parents_pressure], fb.feedback_sad_for_parents_pressure),
                        ([store_en[item] for item in locale.intent_sad_for_financial_hardship], fb.feedback_sad_for_financial_hardship),
                        ([store_en[item] for item in locale.intent_sad_for_parent_divorce], fb.feedback_sad_for_parent_divorce),
                        ([store_en[item] for item in locale.intent_sad_for_siblings_parents], fb.feedback_sad_for_siblings_parents),
                        ([store_en[item] for item in locale.intent_sad_for_family_ill], fb.feedback_sad_for_family_ill),
                        ([store_en[item] for item in locale.intent_sad_for_relative_pressure], fb.feedback_sad_for_relative_pressure),
                        ([store_en[item] for item in locale.intent_sad_for_family_party], fb.feedback_sad_for_family_party),
                        ([store_en[item] for item in locale.intent_sad_for_unable_care_family], fb.feedback_sad_for_unable_care_family),
                        ([store_en[item] for item in locale.intent_sad_for_family_ideological_diff], fb.feedback_sad_for_family_ideological_diff),
                    ], 
                    fb.feedback_sad_not_match_reason)
        ]
        super().__init__('sad', feedbacks)
        
        
class AngerSequence(RobotSequences):
    def __init__(self, store_en, locale, fb):
        feedbacks = [
            RobotSequenceFb(SEQ_TYPE_EXECUTE, fb.feedback_see_anger),
            RobotSequenceFb(SEQ_TYPE_EXECUTE, fb.feedback_ask_anger_reason),
            RobotSequenceFb(SEQ_TYPE_WAIT_USER, [
                        ([store_en[item] for item in locale.intent_sad_for_friend_betray], fb.feedback_sad_for_friend_betray),
                        
                    ], 
                    fb.feedback_anger_not_match_reason)
        ]
        
        super().__init__('anger', feedbacks)
        
    
    
    
    
    

        
        
        
    
    
