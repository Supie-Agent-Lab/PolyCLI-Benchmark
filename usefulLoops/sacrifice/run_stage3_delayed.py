#!/usr/bin/env python3

import time
import subprocess

# Wait 5 hours
print("Waiting 5 hours before running stage3...")
time.sleep(5 * 60 * 60)  # 5 hours in seconds

# Run stage3
print("Starting stage3...")
subprocess.run(["python", "stage3_knowledge_extraction.py"])