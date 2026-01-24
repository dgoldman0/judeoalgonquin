#!/usr/bin/env python3
"""
Retrieve error log for an OpenAI fine-tuning job.
Uses OPENAI_API_KEY from environment.
"""

import sys
from openai import OpenAI

def get_ft_error_log(job_id: str):
    """Fetch and display error log for a fine-tuning job."""
    client = OpenAI()
    
    print(f"Fetching fine-tuning job: {job_id}\n")
    
    try:
        job = client.fine_tuning.jobs.retrieve(job_id)
    except Exception as e:
        print(f"Error retrieving job: {e}")
        return
    
    print(f"Job Status: {job.status}")
    print(f"Model: {job.model}")
    print(f"Created: {job.created_at}")
    if hasattr(job, 'updated_at'):
        print(f"Updated: {job.updated_at}")
    print()
    
    # Check for errors
    if job.error:
        print("❌ Job Error:")
        print(f"  Code: {job.error.code}")
        print(f"  Message: {job.error.message}")
        print()
    
    # Get events (which include error details)
    print("Recent Events:")
    print("-" * 70)
    
    try:
        events = client.fine_tuning.jobs.list_events(job_id, limit=50)
        
        if events.data:
            for event in reversed(events.data):  # Show oldest first
                timestamp = event.created_at
                level = event.level
                message = event.message
                
                prefix = "❌" if level == "error" else "⚠️ " if level == "warning" else "ℹ️ "
                print(f"{prefix} [{timestamp}] {level.upper()}: {message}")
        else:
            print("No events found.")
    except Exception as e:
        print(f"Error retrieving events: {e}")
    
    print("-" * 70)
    print()
    
    # Summary
    if job.result_files:
        print(f"Result Files: {job.result_files}")
    
    if job.training_file:
        print(f"Training File: {job.training_file}")
    
    if job.validation_file:
        print(f"Validation File: {job.validation_file}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python get_ft_error_log.py <job_id>")
        print("Example: python get_ft_error_log.py ftjob-IFVVl3Zs6NcSDJ3Ig8ylISe6")
        sys.exit(1)
    
    job_id = sys.argv[1]
    get_ft_error_log(job_id)
