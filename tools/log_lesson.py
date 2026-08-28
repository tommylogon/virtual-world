#!/usr/bin/env python3
# Auto lesson-logger. Usage: python tools/log_lesson.py "<lesson text>"
# Appends a dated lesson line to docs/agent-lessons.md so lessons capture
# themselves instead of being hand-written at the end. Creates the file.
import os, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "docs", "agent-lessons.md")

def main():
    lesson = " ".join(sys.argv[1:]).strip()
    if not lesson:
        print("usage: python tools/log_lesson.py <lesson text>")
        return
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    exist = os.path.exists(PATH)
    with open(PATH, "a", encoding="utf-8") as f:
        if not exist:
            f.write("# Agent Lessons \u2014 things not to repeat maybe not again\n\n")
        f.write(f"- [{datetime.date.today().isoformat()}] {lesson}\n")
    print("logged:", lesson)

if __name__ == "__main__":
    main()