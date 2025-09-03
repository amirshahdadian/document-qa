#!/usr/bin/env python3
"""
Test runner script for the Document QA application.
Usage: python run_tests.py
"""

import subprocess
import sys
import os
from pathlib import Path

def run_tests():
    """Run all tests including evaluation."""
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        print("Running unit tests...")
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/",
            "-v",
            "--tb=short"
        ]
        
        result = subprocess.run(cmd)
        unit_tests_passed = result.returncode == 0
        
        print("\n" + "="*50)
        if unit_tests_passed:
            print("✅ Unit tests PASSED")
        else:
            print("❌ Unit tests FAILED")
        
        if unit_tests_passed:
            print("\nRunning evaluation...")
            try:
                eval_script = Path("evaluation/run_evaluation.py")
                if eval_script.exists():
                    eval_cmd = [sys.executable, str(eval_script)]
                    eval_result = subprocess.run(eval_cmd)
                    eval_passed = eval_result.returncode == 0
                    
                    if eval_passed:
                        print("✅ Evaluation PASSED")
                    else:
                        print("❌ Evaluation FAILED")
                    
                    return unit_tests_passed and eval_passed
                else:
                    print("⚠️ Evaluation script not found, skipping...")
                    return unit_tests_passed
            except Exception as e:
                print(f"⚠️ Error running evaluation: {e}")
                return unit_tests_passed
        
        return unit_tests_passed
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    print(f"\n{'='*50}")
    print(f"Overall test result: {'✅ PASSED' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
