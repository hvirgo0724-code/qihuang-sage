import unittest

from app.services.inquiry_choices import build_choices


class InquiryChoicesTests(unittest.TestCase):
    def test_followup_from_screenshot_has_choices(self):
        questions = build_choices('请补充：头部不适具体是胀痛、刺痛、昏沉还是紧绷？另外，既往有无高血压、偏头痛、头部外伤或类似发作史？')
        self.assertEqual([q['id'] for q in questions], ['sensation', 'conditions'])
        self.assertTrue({'胀痛', '刺痛', '昏沉', '紧绷'} <= set(questions[0]['options']))

    def test_current_questions_have_neutral_optional_answers(self):
        choices = build_choices("已记录主诉。请继续描述：怕冷还是怕热？出汗情况如何？")
        self.assertEqual([q['id'] for q in choices], ['cold_hot', 'sweat'])
        for question in choices:
            self.assertIn('不清楚', question['options'])
            self.assertIn('其他（请补充）', question['options'])

    def test_summary_and_recognized_images_do_not_create_questions(self):
        self.assertEqual(build_choices('您有怕冷和睡眠不佳。舌象已经识别。正在生成报告。'), [])
        self.assertEqual(build_choices('请描述疼痛部位？')[0]['id'], 'location')

    def test_multiple_topics_and_free_text_request(self):
        self.assertEqual([q['id'] for q in build_choices('请描述饮食、睡眠、二便、情志等方面有无异常？')],
                         ['appetite', 'sleep', 'stool', 'urine', 'mood'])

    def test_long_question_has_all_groups_without_six_group_truncation(self):
        reply = ('请尽量具体说说：1）最不舒服的部位在哪里（如头、咽、胸、胃、腹、腰、关节等）？'
                 '是什么样的不适（胀、痛、酸、闷、乏力、头晕等）？持续多久了？'
                 '2）怕冷还是怕热？有没有发热、出汗（白天易出汗、夜间盗汗或无汗）？'
                 '3）胃口和饮食如何？有没有口干、口苦、口黏？'
                 '4）大便情况（次数、干稀、是否黏滞）和小便情况（次数、颜色、有无灼热）？'
                 '5）睡眠怎么样（入睡难、易醒、多梦）？6）最近情绪和压力如何？'
                 '另外请告知性别、年龄；女性请补充月经是否规律、有无痛经等；有无慢性病或长期服用的药物。')
        groups = {q['id']: q for q in build_choices(reply)}
        self.assertTrue({'location', 'sensation', 'duration', 'cold_hot', 'fever', 'sweat',
                         'appetite', 'mouth', 'stool', 'urine', 'sleep', 'mood', 'sex',
                         'age', 'menstruation', 'conditions', 'medication'} <= groups.keys())
        self.assertTrue(groups['location']['multiple'])
        self.assertFalse(groups['sex']['multiple'])
        self.assertEqual(groups['age']['input_type'], 'age')
