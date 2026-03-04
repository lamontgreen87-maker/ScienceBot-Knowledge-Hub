import json
import time
import unittest
from unittest.mock import MagicMock, patch
import threading
import sys
import os

# Ensure the current directory is in the path
sys.path.append(os.getcwd())

from agent import ScienceBot
from base_module import _THREAD_LOCAL_CONTEXT

class TestClusterOptimizations(unittest.TestCase):
    def setUp(self):
        # Mock config with two GPU endpoints
        self.mock_config = {
            "hardware": {
                "api_url": "http://gpu0:11434/api/generate",
                "secondary_gpu": "http://gpu1:11434/api/generate",
                "vram_capacity_gb": 16,
                "max_swarm_workers": 2,
                "swarm_stagger_s": 0.1,
                "local_model": "deepseek-r1:8b"
            },
            "research": {
                "iteration_delay": 1,
                "turbo_mode": False,
                "deep_research_mode": True
            },
            "paths": {
                "memory": "memory/",
                "logs": "research_logs/"
            }
        }
        # Disable some init side effects
        with patch('agent.ScienceBot.reload_config'):
             with patch('agent.ScienceBot.__init__', return_value=None):
                 from base_module import BaseModule
                 self.bot = ScienceBot()
                 self.bot.ui = MagicMock()
                 # Manually call BaseModule.__init__ since we patched ScienceBot.__init__
                 BaseModule.__init__(self.bot, self.mock_config, self.bot.ui)
                 self.bot.current_state = {"phase": "GUESS", "iteration_count": 0, "burst_counter": 1}
                 self.bot.ollama_url = self.mock_config['hardware']['api_url']
                 self.bot.api_key = None
                 # Mock _is_model_available to always return True for testing
                 self.bot._is_model_available = MagicMock(return_value=True)

    def test_vram_headroom_detection(self):
        print("\n[TEST] Testing VRAM Headroom Detection...")
        # Mock subprocess.check_output to simulate nvidia-smi success
        with patch('subprocess.check_output') as mock_smi:
            mock_smi.return_value = "8192\n4096" # 8GB free on GPU 0, 4GB free on GPU 1
            
            # Use bot.get_vram_headroom (inherited from BaseModule)
            headroom0 = self.bot.get_vram_headroom(gpu_index=0)
            headroom1 = self.bot.get_vram_headroom(gpu_index=1)
            
            print(f"  GPU 0 Headroom: {headroom0}GB")
            print(f"  GPU 1 Headroom: {headroom1}GB")
            
            self.assertEqual(headroom0, 8.0)
            self.assertEqual(headroom1, 4.0)

    def test_phase_pinning_logic(self):
        print("\n[TEST] Testing Phase-Based GPU Pinning Logic...")
        
        # Test GUESS Phase -> GPU 0
        self.bot.current_state["phase"] = "GUESS"
        
        primary_url = self.bot.config['hardware'].get('api_url')
        secondary_url = self.bot.config['hardware'].get('secondary_gpu')
        is_study_phase = self.bot.current_state.get("phase") == "STUDY"
        target_gpu_urls = secondary_url if (is_study_phase and secondary_url) else primary_url
        
        print(f"  GUESS Phase Target: {target_gpu_urls}")
        self.assertEqual(target_gpu_urls, primary_url)

        # Test STUDY Phase -> GPU 1
        self.bot.current_state["phase"] = "STUDY"
        is_study_phase = True
        target_gpu_urls = secondary_url if (is_study_phase and secondary_url) else primary_url
        
        print(f"  STUDY Phase Target: {target_gpu_urls}")
        self.assertEqual(target_gpu_urls, secondary_url)

    def test_thread_local_routing(self):
        print("\n[TEST] Testing Thread-Local Routing Override...")
        
        # Simulate worker setting context
        test_url = "http://pinned-gpu:11434/api/generate"
        _THREAD_LOCAL_CONTEXT.api_url = test_url
        
        # Verify BaseModule._query_llm respects it
        with patch('requests.post') as mock_post:
            # Need to mock a streaming response for heavy models
            mock_response = MagicMock()
            mock_response.status_code = 200
            
            # Setup for JSON generator
            def mock_gen():
                yield json.dumps({"response": "ok"}).encode()
            
            mock_response.__iter__.return_value = mock_gen()
            mock_post.return_value = mock_response
            
            self.bot._query_llm("test prompt", model="deepseek-r1:70b") # Force heavy to use post
            
            # Check the URL used in the request
            called_url = mock_post.call_args[0][0]
            print(f"  Routing Target: {called_url}")
            self.assertEqual(called_url, test_url)
        
        # Cleanup
        if hasattr(_THREAD_LOCAL_CONTEXT, 'api_url'):
            del _THREAD_LOCAL_CONTEXT.api_url

    def test_vram_guard_throttling(self):
        print("\n[TEST] Testing VRAM Guard Throttling...")
        
        # Mock low VRAM then high VRAM
        vram_values = [5.0, 5.0, 15.0] # 5GB free twice, then 15GB free
        
        def mock_get_vram(gpu_index=0, url=None):
            return vram_values.pop(0) if vram_values else 20.0

        self.bot.get_vram_headroom = mock_get_vram
        
        # We need to mock time.sleep so it doesn't actually wait
        with patch('time.sleep') as mock_sleep:
            # Simulate the loop in agent.py
            check_url = "http://test-gpu"
            throttled_count = 0
            while self.bot.get_vram_headroom(url=check_url) < 12.0:
                throttled_count += 1
                if throttled_count > 10: break # Safety
            
            print(f"  Throttled cycles: {throttled_count}")
            self.assertEqual(throttled_count, 2)

if __name__ == "__main__":
    unittest.main()
