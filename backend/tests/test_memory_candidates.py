import unittest
from app.services.memory_service import collect_candidates


class MemoryCandidatesTests(unittest.TestCase):
    def test_excludes_diagnosis_and_current_symptoms(self):
        self.assertEqual(collect_candidates({}, [(9, {'syndrome': 'test', 'symptoms': ['头痛'], 'age': 30})], []), [])

    def test_profile_priority_and_existing_value_deduplication(self):
        saved = [{'memory_key': 'allergies', 'value': {'content': '过敏史：花生'}}]
        self.assertEqual(collect_candidates({'allergies': '花生'}, [(9, {'allergies': '其他'})], saved), [])

    def test_latest_snapshot_and_replacement_visible(self):
        result = collect_candidates({}, [(9, {'medication': '药物 A'}), (8, {'medication': '药物 B'})],
                                    [{'memory_key': 'medication_history', 'value': {'content': '旧内容'}}])
        self.assertEqual(result[0]['content'], '长期用药：药物 A')
        self.assertEqual(result[0]['previous'], '旧内容')
        self.assertIn('9', result[0]['source'])

    def test_unknown_and_unstructured_values_ignored(self):
        self.assertEqual(collect_candidates({}, [(1, {'conditions': '不清楚', 'allergies': {'x': 1}})], []), [])

    def test_negative_history_preserved(self):
        self.assertEqual(collect_candidates({}, [(1, {'conditions': '无已知相关病史'})], [])[0]['content'],
                         '既往病史：无已知相关病史')
