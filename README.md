# JK Games – Nuke Arcade 🎮

A mini game hub built inside Nuke to play games while renders are running. 😉

Built while learning Python scripting for Nuke.

Games included:
- 2048
- Snake
- Breakout
- Block Blast
- Space Invaders
- Blockudoku

Screenshot:

![JK Games UI](jk_games_ui.png)

Installation:

1. Download repository
2. Copy the file nuke_games.py into .nuke directory
3. Add this line to menu.py 
import sys
sys.path.insert(0, "C:/Users/pandi/.nuke")
import nuke_games 
