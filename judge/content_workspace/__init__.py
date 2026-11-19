"""Content workspace (Admin -> Content workspace).

Where posts for each platform are written by people, guided by the platform's
philosophy, research, rules and coded topic suggestions, and checked against
the platform's rules before posting. Its rows are cw_* tables in the board's
database (`db.py`, since 2026-11-19); it writes only those and never a board
table. The AI writer (`writer.py`) is the one model caller, and it is off.
"""
