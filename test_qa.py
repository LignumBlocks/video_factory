import sys
import os
import unittest
sys.path.append(os.getcwd())

from src.qa.engine import QARulesEngine, QAStatus
from src.qa.validators import validate_image_file, validate_clip_duration

class TestQA(unittest.TestCase):
    def setUp(self):
        self.engine = QARulesEngine()
        self.engine.register_image_validator(validate_image_file)
        self.engine.register_clip_validator(validate_clip_duration)
        
        # Create dummy assets
        with open("test.png", "w") as f: f.write("fake image content")
        with open("test.mp4", "w") as f: f.write("fake video content " * 10000) # Make it > 100KB
        
    def tearDown(self):
        if os.path.exists("test.png"): os.remove("test.png")
        if os.path.exists("test.mp4"): os.remove("test.mp4")

    def test_image_pass(self):
        res = self.engine.validate_image("test.png")
        self.assertEqual(res.status, QAStatus.PASS)
        # Wait, my validator checks EXTENSION string.
        # "test.png" ends with .png -> PASS?
        # Let's check logic: if not endswith png/jpg -> WARNING.
        # So "test.png" should be PASS.
        self.assertEqual(res.status, QAStatus.PASS)

    def test_image_fail_missing(self):
        res = self.engine.validate_image("missing.png")
        self.assertEqual(res.status, QAStatus.FAIL)
        self.assertTrue(res.retry_suggested)

    def test_clip_pass(self):
        res = self.engine.validate_clip("test.mp4")
        self.assertEqual(res.status, QAStatus.PASS)

if __name__ == '__main__':
    unittest.main()
