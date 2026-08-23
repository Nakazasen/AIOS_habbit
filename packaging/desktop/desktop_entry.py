# -*- coding: utf-8 -*-
"""Desktop entrypoint for PyInstaller build of AIOS WorkLens."""
from __future__ import annotations

import sys
from aios_habit.cli import launch_workspace_chat, main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Direct double-click / zero argument execution launches the Workspace Chat GUI
        sys.exit(launch_workspace_chat())
    else:
        sys.exit(main())
