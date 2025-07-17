#!/usr/bin/env python3
"""
Simple test runner script
Usage: python run_tests.py
"""

import subprocess
import sys
import os

def run_tests():
    """Run essential tests."""
    try:
        # Change to project directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # Run tests - simplified command
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/",
            "-v"
        ]
        
        result = subprocess.run(cmd)
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    print(f"\nTests {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)