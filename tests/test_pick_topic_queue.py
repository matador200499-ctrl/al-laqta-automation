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

            with patch.object(pick_topic, "TOPICS_FILE", str(topics_path)), \
                 patch.object(pick_topic, "USED_FILE", str(used_path)):
                queue = pick_topic.ensure_topics_available()

            self.assertTrue(queue, "Queue should not be empty")
            self.assertTrue(
                any(not pick_topic.is_story_topic(topic) for topic in queue),
                "A story-only queue must be replenished with informational topics",
            )

    def test_story_topics_are_not_used_as_information_fallback(self):
        self.assertTrue(all(pick_topic.is_story_topic(topic) for topic in [
            "سلسلة: عمر وسلمى | الحلقة 50 | سر الصورة القديمة",
            "سلسلة: عمر وسلمى | الحلقة 51 | القرار اللي غيّر كل حاجة",
        ]))


if __name__ == "__main__":
    unittest.main()
