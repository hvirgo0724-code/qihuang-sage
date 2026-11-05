import unittest
from unittest.mock import Mock, patch

from app.services import knowledge_service as knowledge
from app.services import syndrome_service as syndrome


class ReportRetrievalTests(unittest.TestCase):
    def test_model_failure_never_selects_first_knowledge_candidate(self):
        for response in ('{}', 'not json', '{"syndrome":"风寒束表证","confidence":2}'):
            with self.subTest(response=response), \
                    patch.object(syndrome.prompt_service, 'get_active_prompt', return_value='{context}'), \
                    patch.object(syndrome.llm, 'invoke_text', return_value=response):
                with self.assertRaises(syndrome.AnalysisUnavailable):
                    syndrome._syndrome_step(Mock(), '睡不好', [], [], {'syndromes': [{'name': '风寒束表证'}]})
        with patch.object(syndrome.prompt_service, 'get_active_prompt', return_value='{context}'), \
                patch.object(syndrome.llm, 'invoke_text', side_effect=RuntimeError('unavailable')):
            with self.assertRaises(syndrome.AnalysisUnavailable):
                syndrome._syndrome_step(Mock(), '睡不好', [], [], {'syndromes': [{'name': '风寒束表证'}]})

    def test_complete_inquiry_and_negative_answers_reach_diagnosis(self):
        with patch.object(syndrome.llm, 'llm_configured', return_value=False), \
                patch.object(knowledge, 'graphrag_retrieve', return_value={}), \
                patch.object(syndrome.prompt_service, 'get_disclaimer', return_value='仅供参考'), \
                patch.object(syndrome.prompt_service, 'get_active_prompt', return_value='{context}'), \
                patch.object(syndrome.llm, 'invoke_text', return_value='{"syndrome":null,"confidence":null}') as model:
            report = syndrome.analyze(Mock(), {'symptoms': [], 'inquiry': {'cold_hot': '不怕冷', 'sleep': '容易醒'},
                                              'patient_messages': ['没有发热', '年龄：32岁']}, '睡不好')
        prompt = model.call_args.args[0][1]['content']
        for value in ('不怕冷', '容易醒', '没有发热', '32岁'):
            self.assertIn(value, prompt)
        self.assertIsNone(report['syndrome'])
        self.assertIsNone(report['confidence'])
        self.assertEqual(report['formula_suggestions'], [])
        model.assert_called_once()

    def test_vector_symptom_candidates_do_not_mutate_patient_symptoms(self):
        symptoms = ["失眠", "乏力"]
        with patch.object(knowledge, "_graph_available", return_value=False), \
                patch.object(knowledge, "_vector_available", return_value=True), \
                patch.object(knowledge, "_vector_query", side_effect=lambda vector, label, top_k: [
                    {"node_id": "头痛"}, {"node_id": "头痛"}
                ] if label == "Symptom" else []):
            result = knowledge.graphrag_retrieve(symptoms, None, [0.1])
        self.assertEqual(symptoms, ["失眠", "乏力"])
        self.assertEqual(result["symptoms"], symptoms)
        self.assertIsNot(result["symptoms"], symptoms)
        self.assertEqual(result["symptom_matches"], [{"name": "头痛", "props": {}, "_vector": True}])

    def test_report_completes_after_vector_symptom_hit(self):
        symptoms = ["失眠", "乏力"]
        with patch.object(knowledge, "_graph_available", return_value=False), \
                patch.object(knowledge, "_vector_available", return_value=True), \
                patch.object(knowledge, "_vector_query", side_effect=lambda vector, label, top_k: [
                    {"node_id": "头痛"}
                ] if label == "Symptom" else []), \
                patch.object(syndrome.llm, "llm_configured", return_value=True), \
                patch.object(syndrome.llm, "embed_texts", return_value=[[0.1]]), \
                patch.object(syndrome.prompt_service, "get_disclaimer", return_value="仅供参考"), \
                patch.object(syndrome.prompt_service, "get_active_prompt", return_value="{context}"), \
                patch.object(syndrome.llm, "invoke_text", return_value='{"syndrome":null,"evidence":[],"confidence":0.3}') as model:
            report = syndrome.analyze(Mock(), {"symptoms": symptoms}, "睡不好")
        self.assertIn("latency_ms", report)
        self.assertEqual(symptoms, ["失眠", "乏力"])
        prompt = model.call_args.args[0][1]["content"]
        self.assertIn("症状：失眠、乏力", prompt)
        self.assertNotIn("头痛", prompt)


if __name__ == "__main__":
    unittest.main()
