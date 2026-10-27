import importlib.util
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


metadata_module = load_module("generate_script_for_test", "scripts/generate_script.py")
assembly_module = load_module("assemble_video_for_test", "scripts/assemble_video.py")


class WorkflowSyntaxTests(unittest.TestCase):
    def test_all_github_workflow_yaml_files_parse(self):
        workflow_dir = ROOT / ".github" / "workflows"
        workflow_files = sorted(workflow_dir.glob("*.yml"))
        self.assertTrue(workflow_files, "No GitHub Actions workflow files found")
        for path in workflow_files:
            with self.subTest(workflow=path.name):
                parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertIsInstance(parsed, dict)


class MetadataTests(unittest.TestCase):
    def sample_data(self):
        return {
            "title": "عنوان عربي واضح",
            "scenes": [{"narration": "هل تعرف إن المعلومة دي ممكن تغير نظرتك للموضوع؟"}],
        }

    def test_science_topic_has_description_tags_and_shorts(self):
        data = metadata_module.finalize_metadata(
            "لماذا لا نشعر بدوران الأرض رغم سرعتها الهائلة؟",
            self.sample_data(),
            False,
        )
        self.assertTrue(data["description"].strip())
        self.assertIn("#Shorts", data["description"])
        self.assertTrue(data["tags"])
        self.assertIn(data["category_id"], {"27", "28"})

    def test_history_topic_uses_history_hashtags(self):
        data = metadata_module.finalize_metadata(
            "أسرار الحضارة المصرية القديمة",
            self.sample_data(),
            False,
        )
        self.assertIn("#التاريخ", data["description"])
        self.assertIn("#حقائق_تاريخية", data["description"])

    def test_story_metadata_keeps_series_identity(self):
        data = metadata_module.finalize_metadata(
            "سلسلة: عمر وسلمى | الحلقة 1 | رسالة وصلت في وقت غلط",
            self.sample_data(),
            True,
        )
        self.assertIn("#قصص_مصرية", data["description"])
        self.assertIn("#عمر_وسلمى", data["description"])
        self.assertEqual(data["category_id"], "24")

    def test_subtitle_chunks_preserve_all_words(self):
        narration = "واحد اثنين ثلاثة أربعة خمسة ستة سبعة ثمانية تسعة عشرة"
        chunks = assembly_module.split_caption_chunks(narration, max_words=6)
        self.assertEqual(" ".join(chunks), narration)
        self.assertLessEqual(max(len(chunk.split()) for chunk in chunks), 6)

    def test_subtitle_cues_cover_scene_duration(self):
        cues = assembly_module.caption_cues(
            "هذه جملة عربية طويلة لاختبار تقسيم الترجمة إلى مقاطع متزامنة",
            12.0,
        )
        self.assertTrue(cues)
        self.assertAlmostEqual(cues[0]["start"], 0.0)
        self.assertAlmostEqual(cues[-1]["end"], 12.0)
        for previous, current in zip(cues, cues[1:]):
            self.assertLessEqual(previous["end"], current["start"] + 0.001)
        self.assertEqual(assembly_module.srt_timestamp(65.432), "00:01:05,432")


if __name__ == "__main__":
    unittest.main()
