#!/usr/bin/env python
"""Standalone demo project for agent_helper (core + demo plugin only)."""
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo_project.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
