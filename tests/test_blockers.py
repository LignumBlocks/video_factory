
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.orchestrator import Pipeline
from src.qc_manager import QCManager, QCStatus

class TestBlockerFixes(unittest.TestCase):
    
    @patch('src.audio_engine.AudioAligner.get_audio_duration')
    def test_integrity_01_no_fallback(self, mock_get_duration):
        """
        Test that get_audio_duration failure raises Exception and crashes, 
        instead of printing warning and continuing.
        """
        mock_get_duration.side_effect = Exception("FFprobe not found")
        
        # We need to mock other things to reach this point, or just instantiate Pipeline and run strict logic?
        # Pipeline.run() requires file system setup.
        # Let's mock Pipeline's internal setup to get to Step 3.
        
        # Actually, simpler: Use a small integration test structure if possible 
        # But we don't have files.
        # Let's stick to unit testing the logic if we abstracted it? 
        # Logic is in run().
        
        # We'll assert that calling pipeline.run() raises the Exception
        pipeline = Pipeline("TEST_RUN", 1)
        
        # Mock file reads constraints
        pipeline._read_file = MagicMock(return_value="Valid script")
        pipeline._write_json = MagicMock()
        
        # Mock file system existence
        with patch('os.path.exists', return_value=True), \
             patch('os.makedirs'), \
             patch('builtins.open'):
             
             with self.assertRaises(Exception) as context:
                 pipeline.run()
             
             self.assertIn("FFprobe not found", str(context.exception))
             print("\n[PASS] INTEGRITY_01: Pipeline crashed on ffprobe failure as expected.")

    def test_qc_02_segment_validation(self):
        """
        Test that evaluate_segments blocks invalid durations.
        """
        qc = QCManager()
        
        # Case 1: Too short
        segments_short = [{"start": 0, "end": 1.0, "text": "Too short"}] # dur=1.0 < min=2.0
        report = qc.evaluate_segments(segments_short, min_dur=2.0, max_dur=12.0)
        self.assertEqual(report.status, QCStatus.BLOCK)
        self.assertIn("SEG_0_TOO_SHORT", report.critical_flags[0])
        print("\n[PASS] QC_02: Short segment blocked.")

        # Case 2: Too long
        segments_long = [{"start": 0, "end": 15.0, "text": "Too long"}] # dur=15.0 > max=12.0
        report = qc.evaluate_segments(segments_long, min_dur=2.0, max_dur=12.0)
        self.assertEqual(report.status, QCStatus.BLOCK)
        self.assertIn("SEG_0_TOO_LONG", report.critical_flags[0])
        print("\n[PASS] QC_02: Long segment blocked.")
        
        # Case 3: Good
        segments_good = [{"start": 0, "end": 5.0, "text": "Good"}] 
        report = qc.evaluate_segments(segments_good, min_dur=2.0, max_dur=12.0)
        self.assertEqual(report.status, QCStatus.PASS)
        print("\n[PASS] QC_02: Valid segment passed.")

if __name__ == '__main__':
    unittest.main()
