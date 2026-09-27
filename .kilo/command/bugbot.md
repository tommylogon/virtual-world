---
description: Review the working-tree or branch changes for real defects
agent: bugbot
subtask: true
---

Review this change as a skeptic looking for correctness defects.

Scope: $ARGUMENTS

If no scope is given, review the uncommitted changes (staged, unstaged, and
untracked). Otherwise review exactly what is named — for example
"branch changes" or a list of files.

Build the diff yourself with `git status --short` and `git diff`; do not
assume a file list. Exclude unrelated in-flight work in the working tree and
say which files you excluded and why.

Report findings only. Do not fix anything.
