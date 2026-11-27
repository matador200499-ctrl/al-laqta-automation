import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pick_topic


class TopicQueueRegressionTests(unittest.TestCase):
    def test_story_only_queue_is_replenished_with_information_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            topics_path = Path(tmp) / "topics.txt"
            used_path = Path(tmp) / "used_topics.txt"
            topics_path.write_text(
                "سلسلة: عمر وسلمى | الحلقة 50 | سر الصورة القديمة\n"
                "سلسلة: عمر وسلمى | الحلقة 51 | القرار اللي غيّر كل حاجة\n",
                encoding="utf-8",
            )
            used_path.write_text("", encoding="utf-8")

            with patch.object(pick_topic, "TOPICS_FILE", str(topics_path)), patch.object(pick_topic, "USED_FILE", str(used_path)):
                queue = pick_topic.ensure_topics_available()

            self.assertTrue(queue, "Queue should not be empty")
            self.assertTrue(
                all(not pick_topic.is_story_topic(topic) for topic in queue),
                "The informational channel queue must contain no story episodes",
            )

    def test_fails_closed_when_no_unused_fallback_topics_remain(self):
        with tempfile.TemporaryDirectory() as tmp:
            topics_path = Path(tmp) / "topics.txt"
            used_path = Path(tmp) / "used_topics.txt"
            topics_path.write_text("", encoding="utf-8")
            used_path.write_text("\n".join(pick_topic.FALLBACK_TOPICS) + "\n", encoding="utf-8")

            with patch.object(pick_topic, "TOPICS_FILE", str(topics_path)), patch.object(pick_topic, "USED_FILE", str(used_path)), patch.object(pick_topic, "generate_topics_with_groq", return_value=[]):
                with self.assertRaises(RuntimeError):
                    pick_topic.ensure_topics_available()

    def test_normalized_duplicate_titles_are_detected(self):
        self.assertTrue(pick_topic.topics_are_similar(
            "لماذا لا نشعر بدوران الأرض رغم سرعتها الهائلة؟",
            "لماذا لا نشعر بدوران الأرض رغم سرعتها الهائلة"
        ))
        self.assertTrue(pick_topic.topics_are_similar(
            "كيف تعمل كاميرات الهاتف في الإضاءة الضعيفة؟",
            "كيف تعمل كاميرات الهاتف في الاضاءة الضعيفة"
        ))

    def test_serial_story_topics_are_rejected_even_without_series_prefix(self):
        self.assertTrue(pick_topic.is_story_topic("سلسلة: عمر وسلمى | الحلقة 50 | سر الصورة القديمة"))
        self.assertTrue(pick_topic.is_story_topic("عمر وسلمى الحلقة 51 | القرار اللي غيّر كل حاجة"))
        self.assertTrue(pick_topic.is_story_topic("سارة وآدم | الحلقة 2 | الحقيقة التي أخفاها آدم"))
        self.assertFalse(pick_topic.is_story_topic("قصة صعود وسقوط الإمبراطورية: درس تاريخي"))

    def test_main_selects_only_information_topics_even_if_story_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            topics_path = Path(tmp) / "topics.txt"
            used_path = Path(tmp) / "used_topics.txt"
            used_path.write_text("", encoding="utf-8")
            story = "سلسلة: عمر وسلمى | الحلقة 52 | رسالة وصلت في وقت غلط"
            information = "لماذا لا نشعر بدوران الأرض رغم سرعتها الهائلة؟"
            with patch.object(pick_topic, "ensure_topics_available", return_value=[story, information]), patch.object(pick_topic, "TOPICS_FILE", str(topics_path)), patch.object(pick_topic, "USED_FILE", str(used_path)), patch.dict("os.environ", {"GITHUB_ENV": ""}):
                pick_topic.main()
            self.assertEqual(used_path.read_text(encoding="utf-8").strip(), information)
            self.assertNotIn(story, topics_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
