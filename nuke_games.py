import random
import getpass
import os
from datetime import datetime

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import Qt, QTimer, QRect, QPoint, QSize
    from PySide6.QtGui import QPainter, QColor, QFont, QBrush, QPen, QLinearGradient, QRadialGradient, QPainterPath
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore import Qt, QTimer, QRect, QPoint, QSize
    from PySide2.QtGui import QPainter, QColor, QFont, QBrush, QPen, QLinearGradient, QRadialGradient, QPainterPath

import nuke


# ==============================================================================
# SHARED - SCOREBOARD + PLAYER NAME
# ==============================================================================

SCORES = {}   # { game_name: [ (name, score, level), ... ] }
PLAYER_NAME = [getpass.getuser()]

def get_player():
    return PLAYER_NAME[0]

def add_score(game, score, level=1):
    if game not in SCORES:
        SCORES[game] = []
    dt = datetime.now().strftime("%d %b  %H:%M")
    SCORES[game].append((get_player(), score, level, dt))
    SCORES[game].sort(key=lambda x: -x[1])
    SCORES[game] = SCORES[game][:10]

def scoreboard_widget(game, parent=None):
    w = QtWidgets.QWidget(parent)
    lay = QtWidgets.QVBoxLayout(w)
    lay.setContentsMargins(8, 8, 8, 8)
    lay.setSpacing(4)
    title = QtWidgets.QLabel("TOP SCORES - " + game.upper())
    title.setStyleSheet("color:#f5c542;font-size:13px;font-weight:800;letter-spacing:2px;")
    title.setAlignment(Qt.AlignCenter)
    lay.addWidget(title)
    entries = SCORES.get(game, [])
    if not entries:
        lbl = QtWidgets.QLabel("No scores yet!")
        lbl.setStyleSheet("color:#555;font-size:11px;")
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl)
    else:
        for i, (name, sc, lv) in enumerate(entries):
            row = QtWidgets.QLabel(
                str(i+1) + ".  " + name + "   " + str(sc) + "  pts   Lv" + str(lv)
            )
            color = "#f5c542" if i == 0 else ("#aaa" if i == 1 else "#666")
            row.setStyleSheet("color:" + color + ";font-size:11px;font-family:monospace;")
            lay.addWidget(row)
    lay.addStretch()
    return w

# ==============================================================================
# SHARED - PAUSE BUTTON STYLE
# ==============================================================================

DARK_STYLE = (
    "QWidget{background:#141414;color:#f0ece0;font-family:Arial;}"
    "QDialog{background:#141414;}"
    "QLabel{color:#f0ece0;}"
)


DARK_STYLE = (
    "QWidget{background:#0d0d0d;color:#f0ece0;font-family:Arial;}"
    "QDialog{background:#0d0d0d;}"
    "QLabel{color:#f0ece0;}"
)

BTN_STYLE = (
    "QPushButton{"
    "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
    "stop:0 #2a2a2a,stop:0.45 #1a1a1a,stop:0.55 #141414,stop:1 #0a0a0a);"
    "color:#c8c8c8;"
    "border:1px solid #3a3a3a;"
    "border-top:1px solid #444;"
    "border-radius:5px;"
    "padding:4px 12px;"
    "font-size:11px;"
    "font-weight:700;"
    "}"
    "QPushButton:hover{"
    "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
    "stop:0 #3a3a3a,stop:1 #1a1a1a);"
    "color:#ffffff;"
    "border:1px solid #f5c542;"
    "}"
    "QPushButton:pressed{"
    "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
    "stop:0 #0a0a0a,stop:1 #222222);"
    "border-top:1px solid #111;"
    "border-bottom:1px solid #444;"
    "}"
    "QPushButton:disabled{background:#111;color:#333;border:1px solid #1a1a1a;}"
)

# ==============================================================================
# GAME 1 - 2048
# ==============================================================================

COLORS_2048 = {
    0:    ("#2a2a2a", "#2a2a2a"),
    2:    ("#2e2e2e", "#f0ece0"),
    4:    ("#3a3020", "#f5c542"),
    8:    ("#7a3b10", "#ffffff"),
    16:   ("#c04a10", "#ffffff"),
    32:   ("#d64e18", "#ffffff"),
    64:   ("#e0381a", "#ffffff"),
    128:  ("#f5c542", "#111111"),
    256:  ("#f0b800", "#111111"),
    512:  ("#e8a500", "#111111"),
    1024: ("#e09000", "#111111"),
    2048: ("#ffffff", "#111111"),
}

class Tile2048(QtWidgets.QLabel):
    def __init__(self):
        super(Tile2048, self).__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(68, 68)
        self.update_val(0)

    def update_val(self, v):
        bg, fg = COLORS_2048.get(v, ("#aaffcc", "#000000"))
        fs = 24
        if v >= 1024: fs = 15
        elif v >= 100: fs = 19
        self.setStyleSheet(
            "QLabel{background:" + bg + ";color:" + fg + ";"
            "border-radius:6px;font-size:" + str(fs) + "px;font-weight:800;}"
        )
        self.setText(str(v) if v else "")

class Game2048(QtWidgets.QWidget):
    LEVEL_TARGETS = [512, 1024, 2048]

    def __init__(self):
        super(Game2048, self).__init__()
        self.setWindowTitle("2048  |  JK Games")
        self.setStyleSheet("background:#1a1a1a;")
        self.setMinimumSize(400, 560)
        self.setWindowFlags(Qt.Window)
        self.score = 0
        self.best = 0
        self.level = 1
        self.paused = False
        self.over = False
        self.won = False
        self.board = [[0]*4 for _ in range(4)]
        self._build()
        self._new_game()
        self.setFocus()

    def _build(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(6)

        # title row
        hdr = QtWidgets.QHBoxLayout()
        t = QtWidgets.QLabel("2048")
        t.setStyleSheet("color:#f5c542;font-size:42px;font-weight:800;")
        self.sc_lbl = QtWidgets.QLabel("SCORE: 0")
        self.sc_lbl.setStyleSheet("color:#f5c542;font-size:13px;font-weight:700;")
        self.best_lbl = QtWidgets.QLabel("BEST: 0")
        self.best_lbl.setStyleSheet("color:#888;font-size:13px;")
        self.lv_lbl = QtWidgets.QLabel("LV 1")
        self.lv_lbl.setStyleSheet("color:#4dff91;font-size:13px;font-weight:700;")
        hdr.addWidget(t)
        hdr.addStretch()
        vsc = QtWidgets.QVBoxLayout()
        vsc.addWidget(self.sc_lbl)
        vsc.addWidget(self.best_lbl)
        vsc.addWidget(self.lv_lbl)
        hdr.addLayout(vsc)
        root.addLayout(hdr)

        # player + buttons
        ctrl = QtWidgets.QHBoxLayout()
        self.player_lbl = QtWidgets.QLabel("Player: " + get_player())
        self.player_lbl.setStyleSheet("color:#555;font-size:11px;")
        self.pause_btn = QtWidgets.QPushButton("Pause")
        self.pause_btn.setStyleSheet(BTN_STYLE)
        self.pause_btn.setFocusPolicy(Qt.NoFocus)
        self.pause_btn.clicked.connect(self._toggle_pause)
        new_btn = QtWidgets.QPushButton("New Game")
        new_btn.setStyleSheet(BTN_STYLE)
        new_btn.setFocusPolicy(Qt.NoFocus)
        new_btn.clicked.connect(self._new_game)
        sb_btn = QtWidgets.QPushButton("Scores")
        sb_btn.setStyleSheet(BTN_STYLE)
        sb_btn.setFocusPolicy(Qt.NoFocus)
        sb_btn.clicked.connect(self._show_scores)
        ctrl.addWidget(self.player_lbl)
        ctrl.addStretch()
        ctrl.addWidget(self.pause_btn)
        ctrl.addWidget(sb_btn)
        ctrl.addWidget(new_btn)
        root.addLayout(ctrl)

        # grid
        gf = QtWidgets.QFrame()
        gf.setStyleSheet("background:#141414;border-radius:10px;")
        gl = QtWidgets.QGridLayout(gf)
        gl.setContentsMargins(8,8,8,8)
        gl.setSpacing(8)
        self.tiles = []
        for r in range(4):
            row = []
            for c in range(4):
                tile = Tile2048()
                gl.addWidget(tile, r, c)
                row.append(tile)
            self.tiles.append(row)
        root.addWidget(gf)

        self.status = QtWidgets.QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color:#f5c542;font-size:14px;font-weight:700;")
        root.addWidget(self.status)

        # level bar
        self.prog_lbl = QtWidgets.QLabel("Level target: 512")
        self.prog_lbl.setStyleSheet("color:#555;font-size:10px;")
        root.addWidget(self.prog_lbl)

    def _new_game(self):
        self.board = [[0]*4 for _ in range(4)]
        self.score = 0
        self.level = 1
        self.over = False
        self.won = False
        self.paused = False
        self.pause_btn.setText("Pause")
        self.status.setText("")
        self._spawn()
        self._spawn()
        self._draw()
        self.setFocus()

    def _toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.setText("Resume" if self.paused else "Pause")
        if self.paused:
            self.status.setText("PAUSED  -  Press P or click Resume")
        else:
            self.status.setText("")
        self.setFocus()

    def _show_scores(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Scoreboard - 2048")
        dlg.setStyleSheet("background:#1a1a1a;")
        dlg.setMinimumSize(280, 200)
        lay = QtWidgets.QVBoxLayout(dlg)
        lay.addWidget(scoreboard_widget("2048"))
        close = QtWidgets.QPushButton("Close")
        close.setStyleSheet(BTN_STYLE)
        close.clicked.connect(dlg.accept)
        lay.addWidget(close)
        dlg.exec_()

    def _spawn(self):
        empty = [(r,c) for r in range(4) for c in range(4) if self.board[r][c]==0]
        if empty:
            r,c = random.choice(empty)
            self.board[r][c] = 2 if random.random()<0.9 else 4

    def _draw(self):
        for r in range(4):
            for c in range(4):
                self.tiles[r][c].update_val(self.board[r][c])
        self.sc_lbl.setText("SCORE: " + str(self.score))
        self.best_lbl.setText("BEST: " + str(self.best))
        self.lv_lbl.setText("LV " + str(self.level))
        target = self.LEVEL_TARGETS[min(self.level-1, len(self.LEVEL_TARGETS)-1)]
        self.prog_lbl.setText("Level " + str(self.level) + " target: " + str(target))

    def _slide(self, row):
        arr = [v for v in row if v]
        gained = 0
        i = 0
        while i < len(arr)-1:
            if arr[i] == arr[i+1]:
                arr[i] *= 2
                gained += arr[i]
                arr.pop(i+1)
            i += 1
        while len(arr) < 4:
            arr.append(0)
        return arr, gained

    def _tp(self, b):
        return [[b[r][c] for r in range(4)] for c in range(4)]

    def _move(self, d):
        if self.over or self.paused: return
        b = [row[:] for row in self.board]
        if d == "right": b = [row[::-1] for row in b]
        elif d == "up": b = self._tp(b)
        elif d == "down": b = [row[::-1] for row in self._tp(b)]
        changed = False
        total = 0
        for r in range(4):
            nr, g = self._slide(b[r])
            if nr != b[r]: changed = True
            b[r] = nr
            total += g
        if d == "right": b = [row[::-1] for row in b]
        elif d == "up": b = self._tp(b)
        elif d == "down": b = self._tp([row[::-1] for row in b])
        if changed:
            self.board = b
            self.score += total
            if self.score > self.best: self.best = self.score
            # level up
            maxval = max(v for row in self.board for v in row)
            targets = self.LEVEL_TARGETS
            for li, tgt in enumerate(targets):
                if maxval >= tgt and self.level <= li+1:
                    self.level = li+2
                    self.status.setText("LEVEL UP!  Now Level " + str(self.level))
            if maxval >= 2048:
                self.won = True
                add_score("2048", self.score, self.level)
                self.status.setText("YOU WIN! Reached 2048!")
            self._spawn()
            self._draw()
            if not self.won and not self._can_move():
                self.over = True
                add_score("2048", self.score, self.level)
                self.status.setText("Game Over! No more moves.")

    def _can_move(self):
        for r in range(4):
            for c in range(4):
                if self.board[r][c] == 0: return True
                if c<3 and self.board[r][c]==self.board[r][c+1]: return True
                if r<3 and self.board[r][c]==self.board[r+1][c]: return True
        return False

    def keyPressEvent(self, e):
        m = {Qt.Key_Left:"left", Qt.Key_Right:"right",
             Qt.Key_Up:"up", Qt.Key_Down:"down"}
        if e.key() == Qt.Key_P:
            self._toggle_pause()
        elif e.key() in m:
            self._move(m[e.key()])
            e.accept()
        else:
            super(Game2048, self).keyPressEvent(e)

# ==============================================================================
# GAME 2 - SNAKE
# ==============================================================================

class SnakeCanvas(QtWidgets.QWidget):
    CELL = 22
    COLS = 20
    ROWS = 20

    LEVEL_SPEEDS = {1: 130, 2: 100, 3: 75, 4: 55, 5: 38}

    def __init__(self, parent=None):
        super(SnakeCanvas, self).__init__(parent)
        self.setFixedSize(self.COLS * self.CELL, self.ROWS * self.CELL)
        self.setStyleSheet("background:#111;")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.level = 1
        self.paused = False
        self._new_game()

    def _new_game(self):
        self.snake = [(10,10),(10,11),(10,12)]
        self.direction = (0,-1)
        self.next_dir = (0,-1)
        self.food = self._place_food()
        self.score = 0
        self.level = 1
        self.over = False
        self.paused = False
        self.anim_tick = 0
        speed = self.LEVEL_SPEEDS.get(self.level, 130)
        self.timer.start(speed)
        self.update()

    def _place_food(self):
        occupied = set(self.snake)
        while True:
            pos = (random.randint(0,self.COLS-1), random.randint(0,self.ROWS-1))
            if pos not in occupied:
                return pos

    def _tick(self):
        if self.over or self.paused: return
        self.anim_tick += 1
        self.direction = self.next_dir
        head = (self.snake[0][0]+self.direction[0], self.snake[0][1]+self.direction[1])
        if (head[0]<0 or head[0]>=self.COLS or
                head[1]<0 or head[1]>=self.ROWS or head in self.snake):
            self.over = True
            self.timer.stop()
            add_score("Snake", self.score, self.level)
            self.update()
            return
        self.snake.insert(0, head)
        if head == self.food:
            self.score += 10 * self.level
            self.food = self._place_food()
            # level up every 5 foods
            foods_eaten = (len(self.snake) - 3)
            new_level = min(5, foods_eaten // 5 + 1)
            if new_level != self.level:
                self.level = new_level
                speed = self.LEVEL_SPEEDS.get(self.level, 38)
                self.timer.setInterval(speed)
        else:
            self.snake.pop()
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        C = self.CELL
        p.fillRect(self.rect(), QColor("#0d0d0d"))

        # subtle grid
        p.setPen(QPen(QColor("#1a1a1a"), 1))
        for gx in range(0, self.COLS*C, C):
            p.drawLine(gx, 0, gx, self.ROWS*C)
        for gy in range(0, self.ROWS*C, C):
            p.drawLine(0, gy, self.COLS*C, gy)

        # food - glowing apple
        fx, fy = self.food
        fcx = fx*C + C//2
        fcy = fy*C + C//2
        fr  = C//2 - 3
        # glow
        glow = QRadialGradient(fcx, fcy, fr+8)
        glow.setColorAt(0, QColor(255, 60, 60, 80))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(glow)
        p.setPen(Qt.NoPen)
        p.drawEllipse(fcx-fr-8, fcy-fr-8, (fr+8)*2, (fr+8)*2)
        # apple body
        ag = QRadialGradient(fcx-2, fcy-2, fr)
        ag.setColorAt(0, QColor("#ff6b6b"))
        ag.setColorAt(1, QColor("#c0392b"))
        p.setBrush(ag)
        p.setPen(Qt.NoPen)
        p.drawEllipse(fcx-fr, fcy-fr, fr*2, fr*2)
        # shine
        p.setBrush(QColor(255, 255, 255, 120))
        p.drawEllipse(fcx-fr+2, fcy-fr+2, fr//2, fr//3)
        # stem
        p.setPen(QPen(QColor("#5d4037"), 2))
        p.drawLine(fcx, fcy-fr, fcx+3, fcy-fr-5)

        # snake body
        n = len(self.snake)
        dx, dy = self.direction
        for i, (sx, sy) in enumerate(self.snake):
            cx2 = sx*C + C//2
            cy2 = sy*C + C//2
            sr  = C//2 - 2
            if i == 0:
                # head
                hg = QRadialGradient(cx2-2, cy2-2, sr)
                hg.setColorAt(0, QColor("#a8ff78"))
                hg.setColorAt(1, QColor("#1a8a40"))
                p.setBrush(hg)
                p.setPen(QPen(QColor("#0d5c29"), 1))
                p.drawEllipse(cx2-sr, cy2-sr, sr*2, sr*2)
                # eyes
                if dx == 1:   eoffs = [(4,-4),(4,4)]
                elif dx == -1: eoffs = [(-4,-4),(-4,4)]
                elif dy == -1: eoffs = [(-4,-4),(4,-4)]
                else:          eoffs = [(-4,4),(4,4)]
                for ex, ey in eoffs:
                    p.setBrush(QColor("#ffffff"))
                    p.setPen(Qt.NoPen)
                    p.drawEllipse(cx2+ex-3, cy2+ey-3, 6, 6)
                    p.setBrush(QColor("#111"))
                    p.drawEllipse(cx2+ex-2+dx, cy2+ey-2+dy, 4, 4)
                # tongue flick
                if (self.anim_tick // 10) % 3 == 0:
                    p.setPen(QPen(QColor("#ff1a6e"), 2))
                    tx2 = cx2 + dx*(sr+3)
                    ty2 = cy2 + dy*(sr+3)
                    p.drawLine(cx2+dx*sr, cy2+dy*sr, tx2, ty2)
                    p.drawLine(tx2, ty2, tx2+dx*4+dy*3, ty2+dy*4+dx*3)
                    p.drawLine(tx2, ty2, tx2+dx*4-dy*3, ty2+dy*4-dx*3)
            else:
                # body segment - fade toward tail
                fade = max(0.3, 1.0 - i / (n + 1.0))
                g = int(180 * fade + 30)
                seg = QRadialGradient(cx2-2, cy2-2, sr)
                seg.setColorAt(0, QColor(30, g, 60))
                seg.setColorAt(1, QColor(0,  g//2, 20))
                p.setBrush(seg)
                p.setPen(Qt.NoPen)
                p.drawEllipse(cx2-sr+1, cy2-sr+1, (sr-1)*2, (sr-1)*2)

        if self.paused:
            p.fillRect(self.rect(), QColor(0,0,0,150))
            p.setPen(QColor("#f5c542"))
            p.setFont(QFont("Arial", 20, QFont.Bold))
            p.drawText(self.rect(), Qt.AlignCenter, "PAUSED")
        if self.over:
            p.fillRect(self.rect(), QColor(0,0,0,160))
            p.setPen(QColor("#f5c542"))
            p.setFont(QFont("Arial", 18, QFont.Bold))
            p.drawText(self.rect(), Qt.AlignCenter,
                       "GAME OVER\nScore: " + str(self.score) + "\nR to restart")
        p.end()

    def keyPressEvent(self, e):
        dirs = {
            Qt.Key_Left:(-1,0), Qt.Key_Right:(1,0),
            Qt.Key_Up:(0,-1), Qt.Key_Down:(0,1),
            Qt.Key_A:(-1,0), Qt.Key_D:(1,0),
            Qt.Key_W:(0,-1), Qt.Key_S:(0,1),
        }
        if e.key() in dirs:
            nd = dirs[e.key()]
            if nd[0]+self.direction[0]!=0 or nd[1]+self.direction[1]!=0:
                self.next_dir = nd
        elif e.key() == Qt.Key_R:
            self._new_game()
            if hasattr(self.parent(), '_on_restart'):
                self.parent()._on_restart()

class GameSnake(QtWidgets.QWidget):
    def __init__(self):
        super(GameSnake, self).__init__()
        self.setWindowTitle("Snake  |  JK Games")
        self.setStyleSheet("background:#1a1a1a;")
        self.setWindowFlags(Qt.Window)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(12,12,12,12)
        lay.setSpacing(6)

        hdr = QtWidgets.QHBoxLayout()
        t = QtWidgets.QLabel("SNAKE")
        t.setStyleSheet("color:#4dff91;font-size:30px;font-weight:800;")
        self.sc = QtWidgets.QLabel("SCORE: 0")
        self.sc.setStyleSheet("color:#f5c542;font-size:13px;font-weight:700;")
        self.lv = QtWidgets.QLabel("LV 1")
        self.lv.setStyleSheet("color:#4fc3f7;font-size:13px;font-weight:700;")
        hdr.addWidget(t)
        hdr.addStretch()
        hdr.addWidget(self.lv)
        hdr.addSpacing(10)
        hdr.addWidget(self.sc)
        lay.addLayout(hdr)

        ctrl = QtWidgets.QHBoxLayout()
        self.player_lbl = QtWidgets.QLabel("Player: " + get_player())
        self.player_lbl.setStyleSheet("color:#555;font-size:11px;")
        self.pause_btn = QtWidgets.QPushButton("Pause")
        self.pause_btn.setStyleSheet(BTN_STYLE)
        self.pause_btn.setFocusPolicy(Qt.NoFocus)
        self.pause_btn.clicked.connect(self._toggle_pause)
        sb_btn = QtWidgets.QPushButton("Scores")
        sb_btn.setStyleSheet(BTN_STYLE)
        sb_btn.setFocusPolicy(Qt.NoFocus)
        sb_btn.clicked.connect(self._show_scores)
        new_btn = QtWidgets.QPushButton("New Game")
        new_btn.setStyleSheet(BTN_STYLE)
        new_btn.setFocusPolicy(Qt.NoFocus)
        new_btn.clicked.connect(self._restart)
        ctrl.addWidget(self.player_lbl)
        ctrl.addStretch()
        ctrl.addWidget(self.pause_btn)
        ctrl.addWidget(sb_btn)
        ctrl.addWidget(new_btn)
        lay.addLayout(ctrl)

        hint = QtWidgets.QLabel("Arrow keys / WASD   |   R: restart   |   P: pause")
        hint.setStyleSheet("color:#444;font-size:10px;")
        lay.addWidget(hint)

        self.canvas = SnakeCanvas(self)
        self.canvas.timer.timeout.connect(self._tick_ui)
        lay.addWidget(self.canvas)
        self.adjustSize()
        self.canvas.setFocus()

    def _tick_ui(self):
        self.sc.setText("SCORE: " + str(self.canvas.score))
        self.lv.setText("LV " + str(self.canvas.level))

    def _restart(self):
        self.canvas._new_game()
        self.pause_btn.setText("Pause")
        self.canvas.setFocus()

    def _on_restart(self):
        self.pause_btn.setText("Pause")

    def _toggle_pause(self):
        self.canvas.paused = not self.canvas.paused
        self.pause_btn.setText("Resume" if self.canvas.paused else "Pause")
        if not self.canvas.paused and not self.canvas.over and not self.canvas.won:
            self.canvas.timer.start(14)
        self.canvas.update()
        self.canvas.setFocus()

    def _show_scores(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Scoreboard - Snake")
        dlg.setStyleSheet("background:#1a1a1a;")
        dlg.setMinimumSize(280, 200)
        lay = QtWidgets.QVBoxLayout(dlg)
        lay.addWidget(scoreboard_widget("Snake"))
        close = QtWidgets.QPushButton("Close")
        close.setStyleSheet(BTN_STYLE)
        close.clicked.connect(dlg.accept)
        lay.addWidget(close)
        dlg.exec_()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_P:
            self._toggle_pause()
        else:
            self.canvas.keyPressEvent(e)

# ==============================================================================
# GAME 3 - BREAKOUT  (fixed physics)
# ==============================================================================

class BreakoutCanvas(QtWidgets.QWidget):
    W = 420
    H = 500

    LEVEL_CONFIGS = {
        1: {"rows":4, "speed":3.5, "mines":18},
        2: {"rows":5, "speed":4.2, "mines":20},
        3: {"rows":6, "speed":5.0, "mines":22},
        4: {"rows":7, "speed":5.8, "mines":24},
        5: {"rows":8, "speed":6.5, "mines":26},
    }

    def __init__(self, parent=None):
        super(BreakoutCanvas, self).__init__(parent)
        self.setFixedSize(self.W, self.H)
        self.setStyleSheet("background:#111;")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.level = 1
        self.total_score = 0
        self.paused = False
        self._start_level()
        self.setFocusPolicy(Qt.StrongFocus)

    def _start_level(self):
        cfg = self.LEVEL_CONFIGS.get(self.level, self.LEVEL_CONFIGS[5])
        self.pw = 80
        self.ph = 12
        self.px = float(self.W // 2 - self.pw // 2)
        self.py = float(self.H - 45)
        self.ball_r = 8
        self.bx = float(self.W // 2)
        self.by = float(self.H - 65)
        spd = cfg["speed"]
        angle = random.uniform(0.5, 0.866)   # 30-60 deg
        self.vx = spd * (1 - angle)
        self.vy = -spd * angle
        if random.random() < 0.5: self.vx *= -1
        self.lives = 3
        self.level_score = 0
        self.over = False
        self.won = False
        self.launched = False
        self.paddle_dir = 0
        self._make_bricks(cfg["rows"])
        self.timer.start(14)
        self.update()

    def _make_bricks(self, rows):
        self.bricks = []
        colors = ["#e0381a","#e8a500","#f5c542","#2ecc71","#3498db","#9b59b6","#e91e63","#00bcd4"]
        cols = 10
        bw = (self.W - 20) // cols - 4
        bh = 16
        for row in range(rows):
            for col in range(cols):
                x = col * (bw+4) + 10
                y = row * (bh+4) + 38
                color = colors[row % len(colors)]
                pts = (rows - row)
                self.bricks.append({"x":x,"y":y,"w":bw,"h":bh,
                                     "color":color,"alive":True,"pts":pts*10})

    def _tick(self):
        if self.over or self.won or self.paused: return
        if not hasattr(self, "anim_rot"): self.anim_rot = 0.0
        self.anim_rot += abs(self.vx) * 0.4 + 0.3

        spd = self.LEVEL_CONFIGS.get(self.level, self.LEVEL_CONFIGS[5])["speed"]

        # move paddle smoothly
        if self.paddle_dir != 0:
            self.px += self.paddle_dir * 8
            self.px = max(0.0, min(float(self.W - self.pw), self.px))

        # ball follows paddle until launched
        if not self.launched:
            self.bx = self.px + self.pw / 2
            self.by = self.py - self.ball_r - 2
            self.update()
            return

        # move ball
        self.bx += self.vx
        self.by += self.vy

        # clamp speed
        import math
        spd_cur = math.sqrt(self.vx*self.vx + self.vy*self.vy)
        if spd_cur > 0:
            factor = spd / spd_cur
            self.vx *= factor
            self.vy *= factor

        # wall bounces - left/right
        if self.bx - self.ball_r <= 0:
            self.bx = float(self.ball_r)
            self.vx = abs(self.vx)
        if self.bx + self.ball_r >= self.W:
            self.bx = float(self.W - self.ball_r)
            self.vx = -abs(self.vx)
        # ceiling
        if self.by - self.ball_r <= 0:
            self.by = float(self.ball_r)
            self.vy = abs(self.vy)

        # ball lost
        if self.by - self.ball_r > self.H:
            self.lives -= 1
            if self.lives <= 0:
                self.over = True
                self.timer.stop()
                add_score("Breakout", self.total_score + self.level_score, self.level)
            else:
                self.launched = False
                self.bx = self.px + self.pw / 2
                self.by = self.py - self.ball_r - 2
                angle = random.uniform(0.5, 0.866)
                self.vx = spd * (1 - angle)
                self.vy = -spd * angle
                if random.random() < 0.5: self.vx *= -1
            self.update()
            return

        # paddle collision - improved
        ball_left   = self.bx - self.ball_r
        ball_right  = self.bx + self.ball_r
        ball_top    = self.by - self.ball_r
        ball_bottom = self.by + self.ball_r

        pad_left  = self.px
        pad_right = self.px + self.pw
        pad_top   = self.py
        pad_bot   = self.py + self.ph

        if (ball_bottom >= pad_top and ball_top <= pad_bot and
                ball_right >= pad_left and ball_left <= pad_right and
                self.vy > 0):
            # only bounce from top of paddle
            self.by = pad_top - self.ball_r
            offset = (self.bx - (self.px + self.pw / 2)) / (self.pw / 2)
            import math
            angle = offset * 60.0   # degrees
            rad = math.radians(angle)
            self.vx = spd * math.sin(rad)
            self.vy = -spd * math.cos(rad)
            # clamp vx so ball never goes horizontal
            max_vx = spd * 0.85
            self.vx = max(-max_vx, min(max_vx, self.vx))
            self.vy = -abs(self.vy)

        # brick collisions
        active = 0
        for brick in self.bricks:
            if not brick["alive"]: continue
            active += 1
            bx,by,bw,bh = brick["x"],brick["y"],brick["w"],brick["h"]
            bl,br,bt,bb = bx,bx+bw,by,by+bh
            # overlap check
            overlap_x = ball_right > bl and ball_left < br
            overlap_y = ball_bottom > bt and ball_top < bb
            if overlap_x and overlap_y:
                brick["alive"] = False
                active -= 1
                self.level_score += brick["pts"]
                # determine bounce direction from overlap depths
                overlap_left  = ball_right - bl
                overlap_right = br - ball_left
                overlap_top   = ball_bottom - bt
                overlap_bot   = bb - ball_top
                min_x = min(overlap_left, overlap_right)
                min_y = min(overlap_top, overlap_bot)
                if min_x < min_y:
                    self.vx *= -1
                else:
                    self.vy *= -1

        if active == 0:
            self.total_score += self.level_score
            if self.level < 5:
                self.level += 1
                self._start_level()
                return
            else:
                self.won = True
                self.timer.stop()
                add_score("Breakout", self.total_score, self.level)

        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#111111"))

        # bricks
        for brick in self.bricks:
            if not brick["alive"]: continue
            p.setBrush(QColor(brick["color"]))
            p.setPen(QColor("#111"))
            p.drawRoundedRect(brick["x"], brick["y"], brick["w"], brick["h"], 3, 3)

        # paddle
        grad = QLinearGradient(self.px, self.py, self.px, self.py+self.ph)
        grad.setColorAt(0, QColor("#f5c542"))
        grad.setColorAt(1, QColor("#c8960a"))
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(int(self.px), int(self.py), self.pw, self.ph, 5, 5)

        # ball - mini Earth
        import math
        bx2 = int(self.bx)
        by2 = int(self.by)
        br  = self.ball_r
        rot = (self.anim_rot if hasattr(self, "anim_rot") else 0)

        # atmosphere glow
        atm = QRadialGradient(bx2, by2, br+5)
        atm.setColorAt(0,   QColor(100,180,255,0))
        atm.setColorAt(0.7, QColor(100,180,255,30))
        atm.setColorAt(1,   QColor(100,180,255,0))
        p.setBrush(atm)
        p.setPen(Qt.NoPen)
        p.drawEllipse(bx2-br-5, by2-br-5, (br+5)*2, (br+5)*2)

        # ocean base
        ocean = QRadialGradient(bx2-2, by2-2, br)
        ocean.setColorAt(0,   QColor("#4fc3f7"))
        ocean.setColorAt(0.5, QColor("#0277bd"))
        ocean.setColorAt(1,   QColor("#01579b"))
        p.setBrush(ocean)
        p.setPen(Qt.NoPen)
        p.drawEllipse(bx2-br, by2-br, br*2, br*2)

        # clip land masses to ball circle
        p.save()
        clip = QPainterPath()
        clip.addEllipse(bx2-br, by2-br, br*2, br*2)
        p.setClipPath(clip)

        # land masses - simple polygons that shift with rotation
        land_color = QColor("#4caf50")
        land_dark  = QColor("#2e7d32")
        p.setBrush(land_color)
        p.setPen(Qt.NoPen)
        off = int(rot) % (br*2)

        # continent 1
        path1 = QPainterPath()
        x0 = bx2 - br + off - 2
        path1.moveTo(x0,      by2-2)
        path1.lineTo(x0+5,    by2-6)
        path1.lineTo(x0+9,    by2-4)
        path1.lineTo(x0+8,    by2+3)
        path1.lineTo(x0+3,    by2+5)
        path1.closeSubpath()
        p.drawPath(path1)

        # continent 2
        path2 = QPainterPath()
        x1 = bx2 - br//2 + off
        path2.moveTo(x1,      by2+1)
        path2.lineTo(x1+6,    by2-3)
        path2.lineTo(x1+10,   by2+1)
        path2.lineTo(x1+7,    by2+6)
        path2.lineTo(x1+2,    by2+5)
        path2.closeSubpath()
        p.setBrush(land_dark)
        p.drawPath(path2)

        # polar ice cap top
        p.setBrush(QColor(220,240,255,200))
        p.drawEllipse(bx2-br//2, by2-br, br, br//2)

        # cloud streaks
        p.setBrush(QColor(255,255,255,80))
        p.drawRoundedRect(bx2-br+2, by2-2, br-2, 3, 2, 2)
        p.drawRoundedRect(bx2-2,    by2+3, br-3, 2, 1, 1)

        p.restore()

        # atmosphere rim highlight
        rim = QRadialGradient(bx2-br//3, by2-br//3, br)
        rim.setColorAt(0,   QColor(255,255,255,80))
        rim.setColorAt(0.4, QColor(255,255,255,0))
        rim.setColorAt(1,   QColor(0,0,0,0))
        p.setBrush(rim)
        p.setPen(Qt.NoPen)
        p.drawEllipse(bx2-br, by2-br, br*2, br*2)

        # launch hint
        if not self.launched:
            p.setPen(QColor("#444"))
            p.setFont(QFont("Arial", 11))
            p.drawText(self.rect().adjusted(0, self.H-30, 0, 0),
                       Qt.AlignCenter, "SPACE or click to launch")

        # hud
        p.setPen(QColor("#666"))
        p.setFont(QFont("Arial", 10))
        p.drawText(6, self.H-6, "Lives: " + str(self.lives))

        if self.paused:
            p.fillRect(self.rect(), QColor(0,0,0,150))
            p.setPen(QColor("#f5c542"))
            p.setFont(QFont("Arial", 22, QFont.Bold))
            p.drawText(self.rect(), Qt.AlignCenter, "PAUSED")

        if self.over:
            p.fillRect(self.rect(), QColor(0,0,0,160))
            p.setPen(QColor("#e0381a"))
            p.setFont(QFont("Arial", 20, QFont.Bold))
            p.drawText(self.rect(), Qt.AlignCenter,
                       "GAME OVER\nScore: "+str(self.total_score+self.level_score)+"\nR to restart")

        if self.won:
            p.fillRect(self.rect(), QColor(0,0,0,160))
            p.setPen(QColor("#4dff91"))
            p.setFont(QFont("Arial", 20, QFont.Bold))
            p.drawText(self.rect(), Qt.AlignCenter,
                       "YOU WIN!\nScore: "+str(self.total_score)+"\nR to restart")
        p.end()

    def mousePressEvent(self, e):
        if not self.launched and not self.over and not self.won:
            self.launched = True

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Left, Qt.Key_A):
            self.paddle_dir = -1
        elif e.key() in (Qt.Key_Right, Qt.Key_D):
            self.paddle_dir = 1
        elif e.key() == Qt.Key_Space:
            if not self.launched and not self.over and not self.won:
                self.launched = True
        elif e.key() == Qt.Key_R:
            self.total_score = 0
            self.level = 1
            self._start_level()
            if hasattr(self.parent(), '_on_restart'):
                self.parent()._on_restart()

    def keyReleaseEvent(self, e):
        if e.key() in (Qt.Key_Left, Qt.Key_A) and self.paddle_dir == -1:
            self.paddle_dir = 0
        elif e.key() in (Qt.Key_Right, Qt.Key_D) and self.paddle_dir == 1:
            self.paddle_dir = 0

class GameBreakout(QtWidgets.QWidget):
    def __init__(self):
        super(GameBreakout, self).__init__()
        self.setWindowTitle("Breakout  |  JK Games")
        self.setStyleSheet("background:#1a1a1a;")
        self.setWindowFlags(Qt.Window)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(12,12,12,12)
        lay.setSpacing(6)

        hdr = QtWidgets.QHBoxLayout()
        t = QtWidgets.QLabel("BREAKOUT")
        t.setStyleSheet("color:#f5c542;font-size:28px;font-weight:800;")
        self.sc = QtWidgets.QLabel("SCORE: 0")
        self.sc.setStyleSheet("color:#f5c542;font-size:13px;font-weight:700;")
        self.lv = QtWidgets.QLabel("LV 1")
        self.lv.setStyleSheet("color:#4fc3f7;font-size:13px;font-weight:700;")
        hdr.addWidget(t)
        hdr.addStretch()
        hdr.addWidget(self.lv)
        hdr.addSpacing(10)
        hdr.addWidget(self.sc)
        lay.addLayout(hdr)

        ctrl = QtWidgets.QHBoxLayout()
        self.player_lbl = QtWidgets.QLabel("Player: " + get_player())
        self.player_lbl.setStyleSheet("color:#555;font-size:11px;")
        self.pause_btn = QtWidgets.QPushButton("Pause")
        self.pause_btn.setStyleSheet(BTN_STYLE)
        self.pause_btn.setFocusPolicy(Qt.NoFocus)
        self.pause_btn.clicked.connect(self._toggle_pause)
        sb_btn = QtWidgets.QPushButton("Scores")
        sb_btn.setStyleSheet(BTN_STYLE)
        sb_btn.setFocusPolicy(Qt.NoFocus)
        sb_btn.clicked.connect(self._show_scores)
        new_btn = QtWidgets.QPushButton("New Game")
        new_btn.setStyleSheet(BTN_STYLE)
        new_btn.setFocusPolicy(Qt.NoFocus)
        new_btn.clicked.connect(self._restart)
        ctrl.addWidget(self.player_lbl)
        ctrl.addStretch()
        ctrl.addWidget(self.pause_btn)
        ctrl.addWidget(sb_btn)
        ctrl.addWidget(new_btn)
        lay.addLayout(ctrl)

        hint = QtWidgets.QLabel("A/D or Arrows: move   SPACE/click: launch   P: pause   R: restart")
        hint.setStyleSheet("color:#444;font-size:10px;")
        lay.addWidget(hint)

        self.canvas = BreakoutCanvas(self)
        self.canvas.timer.timeout.connect(self._tick_ui)
        lay.addWidget(self.canvas)
        self.adjustSize()
        self.canvas.setFocus()

    def _tick_ui(self):
        sc = self.canvas.total_score + self.canvas.level_score
        self.sc.setText("SCORE: " + str(sc))
        self.lv.setText("LV " + str(self.canvas.level))

    def _restart(self):
        self.canvas.total_score = 0
        self.canvas.level = 1
        self.canvas._start_level()
        self.pause_btn.setText("Pause")
        self.canvas.setFocus()

    def _on_restart(self):
        self.pause_btn.setText("Pause")

    def _toggle_pause(self):
        self.canvas.paused = not self.canvas.paused
        self.pause_btn.setText("Resume" if self.canvas.paused else "Pause")
        self.canvas.update()
        self.canvas.setFocus()

    def _show_scores(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Scoreboard - Breakout")
        dlg.setStyleSheet("background:#1a1a1a;")
        dlg.setMinimumSize(280, 200)
        lay = QtWidgets.QVBoxLayout(dlg)
        lay.addWidget(scoreboard_widget("Breakout"))
        close = QtWidgets.QPushButton("Close")
        close.setStyleSheet(BTN_STYLE)
        close.clicked.connect(dlg.accept)
        lay.addWidget(close)
        dlg.exec_()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_P:
            self._toggle_pause()
        else:
            self.canvas.keyPressEvent(e)

    def keyReleaseEvent(self, e):
        self.canvas.keyReleaseEvent(e)


# ==============================================================================
# GAME 4 - BLOCK BLAST  (pieces fall from top, clear full rows/cols)
# ==============================================================================

BB_COLORS = ["#e0381a","#f5c542","#2ecc71","#3498db","#9b59b6",
             "#e91e63","#00bcd4","#ff9800","#4dff91","#f06292"]

BB_PIECES = [
    [(0,0),(0,1),(0,2),(0,3)],          # I horizontal
    [(0,0),(1,0),(2,0),(3,0)],          # I vertical
    [(0,0),(0,1),(1,0),(1,1)],          # O square
    [(0,0),(1,0),(2,0),(2,1)],          # L
    [(0,0),(1,0),(2,0),(2,-1)],         # J
    [(0,0),(1,0),(1,1),(2,1)],          # S
    [(0,0),(1,0),(1,-1),(2,-1)],        # Z
    [(1,0),(0,1),(1,1),(2,1)],          # T
    [(0,0),(0,1),(0,2)],                # I3
    [(0,0),(1,0),(2,0)],                # I3v
    [(0,0),(0,1),(1,0)],                # tiny L
    [(0,0),(0,1),(1,1)],                # tiny J
    [(0,0),(1,0)],                      # domino h
    [(0,0),(0,1)],                      # domino v
    [(0,0)],                            # single
]

class BlockBlastCanvas(QtWidgets.QWidget):
    COLS = 10
    ROWS = 18
    CELL = 32

    LEVEL_SPEEDS = {1:600, 2:480, 3:380, 4:290, 5:210, 6:160, 7:120, 8:90, 9:65, 10:45}

    def __init__(self, parent=None):
        super(BlockBlastCanvas, self).__init__(parent)
        self.setFixedSize(self.COLS * self.CELL, self.ROWS * self.CELL + 2)
        self.setStyleSheet("background:#0a0a0a;")
        self.setFocusPolicy(Qt.StrongFocus)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._drop_tick)
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.paused = False
        self.over   = False
        self._new_game()

    def _new_game(self):
        self.board  = [[None]*self.COLS for _ in range(self.ROWS)]
        self.score  = 0
        self.level  = 1
        self.lines_cleared = 0
        self.over   = False
        self.paused = False
        self._new_piece()
        self.timer.start(self.LEVEL_SPEEDS[1])

    def _new_piece(self):
        shape = random.choice(BB_PIECES)
        self.piece_shape = [list(r) for r in shape]
        self.piece_color = random.choice(BB_COLORS)
        # normalize: min col = 0
        min_c = min(dc for dr,dc in self.piece_shape)
        max_c = max(dc for dr,dc in self.piece_shape)
        self.piece_col = self.COLS // 2 - (max_c - min_c) // 2 - min_c
        self.piece_row = 0
        if not self._fits(self.piece_shape, self.piece_row, self.piece_col):
            self.over = True
            self.timer.stop()
            add_score("Block Blast", self.score, self.level)
            self.update()

    def _fits(self, shape, row, col):
        for dr, dc in shape:
            r, c = row + dr, col + dc
            if r < 0 or r >= self.ROWS or c < 0 or c >= self.COLS:
                return False
            if self.board[r][c] is not None:
                return False
        return True

    def _lock_piece(self):
        for dr, dc in self.piece_shape:
            r, c = self.piece_row + dr, self.piece_col + dc
            if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                self.board[r][c] = self.piece_color
        self._clear_lines()
        self._new_piece()

    def _clear_lines(self):
        cleared = 0
        rows_to_clear = [r for r in range(self.ROWS)
                         if all(self.board[r][c] is not None for c in range(self.COLS))]
        for r in sorted(rows_to_clear, reverse=True):
            del self.board[r]
            self.board.insert(0, [None]*self.COLS)
            cleared += 1
        if cleared:
            pts = [0, 100, 300, 500, 800]
            self.score += pts[min(cleared, 4)] * self.level
            self.lines_cleared += cleared
            new_lv = min(10, self.lines_cleared // 8 + 1)
            if new_lv != self.level:
                self.level = new_lv
                self.timer.setInterval(self.LEVEL_SPEEDS.get(self.level, 45))

    def _drop_tick(self):
        if self.over or self.paused: return
        next_row = self.piece_row + 1
        if self._fits(self.piece_shape, next_row, self.piece_col):
            self.piece_row = next_row
        else:
            self._lock_piece()
        self.update()

    def _hard_drop(self):
        while self._fits(self.piece_shape, self.piece_row+1, self.piece_col):
            self.piece_row += 1
        self._lock_piece()
        self.update()

    def _rotate(self):
        rotated = [[-dc, dr] for dr, dc in self.piece_shape]
        min_c = min(dc for dr,dc in rotated)
        max_c = max(dc for dr,dc in rotated)
        min_r = min(dr for dr,dc in rotated)
        nc = self.piece_col
        nr = self.piece_row
        # wall kick
        if self._fits(rotated, nr, nc):
            self.piece_shape = rotated
        elif self._fits(rotated, nr, nc-min_c):
            self.piece_shape = rotated
            self.piece_col   = nc - min_c
        elif self._fits(rotated, nr, nc - (max_c - self.COLS + self.piece_col+1)):
            self.piece_shape = rotated

    def _ghost_row(self):
        gr = self.piece_row
        while self._fits(self.piece_shape, gr+1, self.piece_col):
            gr += 1
        return gr

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        C = self.CELL
        # background
        p.fillRect(self.rect(), QColor("#0f0f0f"))
        # grid lines
        p.setPen(QPen(QColor(30,30,30), 1))
        for r in range(self.ROWS+1):
            p.drawLine(0, r*C, self.COLS*C, r*C)
        for c in range(self.COLS+1):
            p.drawLine(c*C, 0, c*C, self.ROWS*C)
        # board cells
        for r in range(self.ROWS):
            for c in range(self.COLS):
                col = self.board[r][c]
                if col:
                    self._draw_block(p, c, r, col, C)
        # ghost piece
        if not self.over:
            gr = self._ghost_row()
            for dr, dc in self.piece_shape:
                c2 = self.piece_col + dc
                r2 = gr + dr
                if 0 <= r2 < self.ROWS and 0 <= c2 < self.COLS:
                    p.setBrush(QColor(80,80,80,50))
                    p.setPen(QPen(QColor(120,120,120,80), 1))
                    p.drawRoundedRect(c2*C+1, r2*C+1, C-2, C-2, 3, 3)
        # active piece
        if not self.over:
            for dr, dc in self.piece_shape:
                c2 = self.piece_col + dc
                r2 = self.piece_row + dr
                if 0 <= r2 < self.ROWS and 0 <= c2 < self.COLS:
                    self._draw_block(p, c2, r2, self.piece_color, C)
        # game over overlay
        if self.over:
            p.fillRect(self.rect(), QColor(0,0,0,170))
            p.setPen(QColor("#e0381a"))
            p.setFont(QFont("Arial", 20, QFont.Bold))
            p.drawText(self.rect(), Qt.AlignCenter,
                       "GAME OVER\nScore: "+str(self.score)+"\nR to restart")
        if self.paused:
            p.fillRect(self.rect(), QColor(0,0,0,150))
            p.setPen(QColor("#f5c542"))
            p.setFont(QFont("Arial", 22, QFont.Bold))
            p.drawText(self.rect(), Qt.AlignCenter, "PAUSED")
        p.end()

    def _draw_block(self, p, col_i, row_i, color, C):
        x, y = col_i*C, row_i*C
        base = QColor(color)
        p.setBrush(base)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(x+1, y+1, C-2, C-2, 4, 4)
        # highlight
        lighter = base.lighter(150)
        lighter.setAlpha(120)
        p.setBrush(lighter)
        p.drawRoundedRect(x+2, y+2, C//2, 5, 2, 2)

    def keyPressEvent(self, e):
        if self.over:
            if e.key() == Qt.Key_R: self._new_game()
            return
        k = e.key()
        if k in (Qt.Key_Left, Qt.Key_A):
            if self._fits(self.piece_shape, self.piece_row, self.piece_col-1):
                self.piece_col -= 1
        elif k in (Qt.Key_Right, Qt.Key_D):
            if self._fits(self.piece_shape, self.piece_row, self.piece_col+1):
                self.piece_col += 1
        elif k in (Qt.Key_Down, Qt.Key_S):
            if self._fits(self.piece_shape, self.piece_row+1, self.piece_col):
                self.piece_row += 1
        elif k in (Qt.Key_Up, Qt.Key_W):
            self._rotate()
        elif k == Qt.Key_Space:
            self._hard_drop()
        elif k == Qt.Key_P:
            self.paused = not self.paused
        elif k == Qt.Key_R:
            self._new_game()
        self.update()


class GameBlockBlast(QtWidgets.QWidget):
    def __init__(self):
        super(GameBlockBlast, self).__init__()
        self.setWindowTitle("Block Blast  |  JK Games")
        self.setStyleSheet("background:#1a1a1a;")
        self.setWindowFlags(Qt.Window)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(0)

        # toolbar
        bar = QtWidgets.QWidget()
        bar.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #111111,stop:1 #080808);border-bottom:1px solid #1a1a00;")
        bar.setFixedHeight(38)
        bl = QtWidgets.QHBoxLayout(bar)
        bl.setContentsMargins(10,4,10,4)
        bl.setSpacing(8)
        self.player_lbl = QtWidgets.QLabel("Player: " + get_player())
        self.player_lbl.setStyleSheet("color:#555;font-size:11px;")
        self.sc_lbl = QtWidgets.QLabel("SCORE: 0")
        self.sc_lbl.setStyleSheet("color:#f5c542;font-size:12px;font-weight:700;")
        self.lv_lbl = QtWidgets.QLabel("LV 1")
        self.lv_lbl.setStyleSheet("color:#4dff91;font-size:12px;font-weight:700;")
        self.pause_btn = QtWidgets.QPushButton("Pause")
        self.pause_btn.setStyleSheet(BTN_STYLE)
        self.pause_btn.setFocusPolicy(Qt.NoFocus)
        self.pause_btn.clicked.connect(self._toggle_pause)
        sb_btn = QtWidgets.QPushButton("Scores")
        sb_btn.setStyleSheet(BTN_STYLE)
        sb_btn.setFocusPolicy(Qt.NoFocus)
        sb_btn.clicked.connect(self._show_scores)
        new_btn = QtWidgets.QPushButton("New Game")
        new_btn.setStyleSheet(BTN_STYLE)
        new_btn.setFocusPolicy(Qt.NoFocus)
        new_btn.clicked.connect(self._restart)
        bl.addWidget(self.player_lbl)
        bl.addStretch()
        bl.addWidget(self.lv_lbl)
        bl.addWidget(self.sc_lbl)
        bl.addWidget(self.pause_btn)
        bl.addWidget(sb_btn)
        bl.addWidget(new_btn)
        lay.addWidget(bar)

        hint = QtWidgets.QLabel(
            "Left/Right: move   Up/W: rotate   Down: soft drop   Space: hard drop   P: pause"
        )
        hint.setStyleSheet("color:#333;font-size:10px;padding:2px 10px;background:#0d0d0d;")
        lay.addWidget(hint)

        self.canvas = BlockBlastCanvas(self)
        self.canvas.timer.timeout.connect(self._tick_ui)
        lay.addWidget(self.canvas)
        self.adjustSize()
        self.canvas.setFocus()

    def _tick_ui(self):
        self.sc_lbl.setText("SCORE: " + str(self.canvas.score))
        self.lv_lbl.setText("LV " + str(self.canvas.level))

    def _restart(self):
        self.canvas._new_game()
        self.pause_btn.setText("Pause")
        self.canvas.setFocus()

    def _toggle_pause(self):
        self.canvas.paused = not self.canvas.paused
        self.pause_btn.setText("Resume" if self.canvas.paused else "Pause")
        self.canvas.update()
        self.canvas.setFocus()

    def _show_scores(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Scoreboard - Block Blast")
        dlg.setStyleSheet("background:#1a1a1a;")
        dlg.setMinimumSize(280, 200)
        lay2 = QtWidgets.QVBoxLayout(dlg)
        lay2.addWidget(scoreboard_widget("Block Blast"))
        close = QtWidgets.QPushButton("Close")
        close.setStyleSheet(BTN_STYLE)
        close.clicked.connect(dlg.accept)
        lay2.addWidget(close)
        dlg.exec_()

    def keyPressEvent(self, e):
        self.canvas.keyPressEvent(e)







# ==============================================================================
# GAME 5 - SPACE INVADERS
# ==============================================================================

SI_COLS = 11
SI_ROWS = 4
SI_CW   = 44
SI_RH   = 36
SI_W    = 520
SI_H    = 480

# Alien shapes drawn with QPainter (3 types)
SI_ALIEN_TYPES = [0, 0, 0, 1, 1, 2, 2]   # per row (clamped)

class SpaceInvadersCanvas(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(SpaceInvadersCanvas, self).__init__(parent)
        self.setFixedSize(SI_W, SI_H)
        self.setStyleSheet("background:#000;")
        self.setFocusPolicy(Qt.StrongFocus)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.score = 0; self.best = 0; self.level = 1
        self.paused = False; self.over = False; self.won = False
        self._new_game()

    def _new_game(self):
        self._timer.stop()
        self.score = 0; self.level = 1
        self.over = False; self.won = False; self.paused = False
        # player
        self._px    = SI_W // 2
        self._py    = SI_H - 36
        self._pv    = 0
        self._pleft = False; self._pright = False
        self._pshoot_cd = 0
        # bullets: [x, y, dy]
        self._pbullets = []
        self._ebullets = []
        # aliens: [col, row, alive, x, y, type]
        self._aliens = []
        self._alien_dir   = 1
        self._alien_step  = 0
        self._alien_tick  = 0
        self._alien_speed = 28   # ticks between moves
        self._alien_drop  = False
        self._shoot_cd    = 0
        self._anim_tick   = 0
        self._shields     = self._make_shields()
        self._reset_aliens()
        self._timer.start(16)
        self.update()

    def _reset_aliens(self):
        self._aliens = []
        ox = 40; oy = 60
        for r in range(SI_ROWS):
            for c in range(SI_COLS):
                atype = min(r, 2)
                self._aliens.append([c, r, True,
                    float(ox + c*SI_CW),
                    float(oy + r*SI_RH),
                    atype])
        self._alien_dir  = 1
        self._alien_step = 0
        self._alien_drop = False

    def _make_shields(self):
        shields = []
        for i in range(4):
            sx = 60 + i * 110
            sy = SI_H - 90
            blocks = []
            for br in range(3):
                for bc in range(6):
                    blocks.append([sx + bc*8, sy + br*8, True])
            shields.append(blocks)
        return shields

    def _tick(self):
        if self.over or self.won or self.paused: return
        self._anim_tick += 1

        # player move
        spd = 4
        if self._pleft:  self._px = max(22, self._px - spd)
        if self._pright: self._px = min(SI_W-22, self._px + spd)
        if self._pshoot_cd > 0: self._pshoot_cd -= 1

        # move player bullets
        self._pbullets = [[x,y-9,dy] for x,y,dy in self._pbullets if y > -10]

        # move enemy bullets
        self._ebullets = [[x,y+5,dy] for x,y,dy in self._ebullets if y < SI_H+10]

        # alien movement
        self._alien_tick += 1
        speed = max(4, self._alien_speed - self.level*2)
        if self._alien_tick >= speed:
            self._alien_tick = 0
            alive = [a for a in self._aliens if a[2]]
            if not alive:
                self.won = True
                self.level += 1
                add_score("Space Invaders", self.score, self.level-1)
                self.update(); return
            # check if need to drop
            xs = [a[3] for a in alive]
            if (self._alien_dir > 0 and max(xs) > SI_W - 30) or \
               (self._alien_dir < 0 and min(xs) < 30):
                self._alien_dir *= -1
                for a in self._aliens:
                    if a[2]: a[4] += 18
            else:
                for a in self._aliens:
                    if a[2]: a[3] += self._alien_dir * 12

            # random alien shoot
            alive2 = [a for a in self._aliens if a[2]]
            if alive2 and random.random() < 0.25:
                shooter = random.choice(alive2)
                self._ebullets.append([shooter[3], shooter[4]+16, 5])

        # bullet-alien collision
        for b in list(self._pbullets):
            for a in self._aliens:
                if not a[2]: continue
                if abs(b[0]-a[3]) < 16 and abs(b[1]-a[4]) < 14:
                    a[2] = False
                    pts = [30,20,10][a[5]]
                    self.score += pts * self.level
                    if b in self._pbullets:
                        self._pbullets.remove(b)
                    break

        # bullet-shield collision
        for shields in self._shields:
            for blk in shields:
                if not blk[2]: continue
                for b in list(self._pbullets):
                    if abs(b[0]-blk[0])<5 and abs(b[1]-blk[1])<5:
                        blk[2] = False
                        if b in self._pbullets: self._pbullets.remove(b)
                for b in list(self._ebullets):
                    if abs(b[0]-blk[0])<6 and abs(b[1]-blk[1])<6:
                        blk[2] = False
                        if b in self._ebullets: self._ebullets.remove(b)

        # enemy bullet hits player
        for b in self._ebullets:
            if abs(b[0]-self._px) < 20 and abs(b[1]-self._py) < 14:
                self.over = True
                self._timer.stop()
                if self.score > self.best: self.best = self.score
                add_score("Space Invaders", self.score, self.level)
                self.update(); return

        # aliens reach bottom
        for a in self._aliens:
            if a[2] and a[4] > SI_H - 60:
                self.over = True
                self._timer.stop()
                if self.score > self.best: self.best = self.score
                add_score("Space Invaders", self.score, self.level)
                self.update(); return

        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#000011"))

        # stars
        p.setPen(QColor(255,255,255,50))
        rng2 = random.Random(99)
        for _ in range(60):
            p.drawPoint(rng2.randint(0,SI_W), rng2.randint(0,SI_H))

        # shields
        for shields in self._shields:
            for blk in shields:
                if blk[2]:
                    p.setBrush(QColor("#1aff44"))
                    p.setPen(Qt.NoPen)
                    p.drawRect(int(blk[0]-3), int(blk[1]-3), 7, 7)

        # aliens
        anim_frame = (self._anim_tick // 14) % 2
        for a in self._aliens:
            if not a[2]: continue
            ax, ay = int(a[3]), int(a[4])
            t = a[5]
            if t == 0:    col = QColor("#ff4dff")
            elif t == 1:  col = QColor("#4dffff")
            else:         col = QColor("#ff4d4d")
            self._draw_alien(p, ax, ay, t, anim_frame, col)

        # player ship
        self._draw_ship(p, self._px, self._py)

        # player bullets
        p.setBrush(QColor("#00ff88"))
        p.setPen(Qt.NoPen)
        for bx,by,_ in self._pbullets:
            p.drawRect(int(bx)-2, int(by)-8, 4, 14)

        # enemy bullets
        p.setBrush(QColor("#ff4444"))
        for bx,by,_ in self._ebullets:
            p.drawRect(int(bx)-2, int(by)-5, 4, 10)

        # HUD
        p.setPen(QColor("#00ff88"))
        p.setFont(QFont("Arial",12,QFont.Bold))
        p.drawText(10, 20, "SCORE: "+str(self.score))
        p.setPen(QColor("#4dffff"))
        p.setFont(QFont("Arial",10))
        p.drawText(10, 34, "LV "+str(self.level)+"   BEST: "+str(self.best))
        p.setPen(QColor(255,255,255,30))
        p.setFont(QFont("Arial",9))
        p.drawText(4, SI_H-4, "LEFT/RIGHT: move   SPACE: shoot   P: pause   R: restart")

        if self.paused:
            p.fillRect(self.rect(), QColor(0,0,0,140))
            p.setPen(QColor("#00ff88"))
            p.setFont(QFont("Arial",26,QFont.Bold))
            p.drawText(QRect(0,0,SI_W,SI_H), Qt.AlignCenter, "PAUSED")

        if self.won:
            p.fillRect(self.rect(), QColor(0,0,0,140))
            p.setPen(QColor("#ffe000"))
            p.setFont(QFont("Arial",22,QFont.Bold))
            p.drawText(QRect(0,SI_H//2-50,SI_W,40), Qt.AlignCenter, "WAVE CLEARED!")
            p.setPen(QColor("#4dffff"))
            p.setFont(QFont("Arial",13))
            p.drawText(QRect(0,SI_H//2,SI_W,30), Qt.AlignCenter, "Score: "+str(self.score)+"   R for next wave")

        if self.over:
            p.fillRect(self.rect(), QColor(0,0,0,150))
            p.setPen(QColor("#ff4444"))
            p.setFont(QFont("Arial",26,QFont.Bold))
            p.drawText(QRect(0,SI_H//2-60,SI_W,44), Qt.AlignCenter, "GAME OVER")
            p.setPen(QColor("#ffe000"))
            p.setFont(QFont("Arial",13))
            p.drawText(QRect(0,SI_H//2-8,SI_W,30), Qt.AlignCenter, "Score: "+str(self.score)+"   Best: "+str(self.best))
            p.setPen(QColor(255,255,255,120))
            p.setFont(QFont("Arial",11))
            p.drawText(QRect(0,SI_H//2+28,SI_W,30), Qt.AlignCenter, "R to restart")
        p.end()

    def _draw_alien(self, p, ax, ay, t, frame, col):
        p.setBrush(col)
        p.setPen(Qt.NoPen)
        if t == 0:  # top alien - squid-like
            p.drawEllipse(ax-10, ay-8, 20, 14)
            legs = [(-10,6),(-5,6),(5,6),(10,6)] if frame==0 else [(-8,8),(-4,8),(4,8),(8,8)]
            for lx,ly in legs:
                p.drawRect(ax+lx-1, ay+ly, 3, 5)
            p.setBrush(QColor(0,0,0))
            p.drawEllipse(ax-5,ay-5,4,4); p.drawEllipse(ax+1,ay-5,4,4)
        elif t == 1:  # mid alien - crab-like
            p.drawRect(ax-12, ay-6, 24, 12)
            arms = [(-14,0),(-14,4),(12,0),(12,4)] if frame==0 else [(-16,-2),(-16,6),(14,-2),(14,6)]
            p.drawRect(ax+arms[0][0], ay+arms[0][1], 4, 3)
            p.drawRect(ax+arms[1][0], ay+arms[1][1], 4, 3)
            p.drawRect(ax+arms[2][0], ay+arms[2][1], 4, 3)
            p.drawRect(ax+arms[3][0], ay+arms[3][1], 4, 3)
            p.setBrush(QColor(0,0,0))
            p.drawEllipse(ax-6,ay-3,4,4); p.drawEllipse(ax+2,ay-3,4,4)
        else:  # bottom alien - octopus-like
            p.drawEllipse(ax-11, ay-9, 22, 16)
            tents = [(-10,5),(-5,7),(0,8),(5,7),(10,5)] if frame==0 else [(-8,8),(-4,6),(0,9),(4,6),(8,8)]
            for tx2,ty2 in tents:
                p.drawRect(ax+tx2-1, ay+ty2, 3, 4)
            p.setBrush(QColor(0,0,0))
            p.drawEllipse(ax-5,ay-5,4,4); p.drawEllipse(ax+1,ay-5,4,4)

    def _draw_ship(self, p, sx, sy):
        sg = QLinearGradient(sx-20, sy-14, sx-20, sy+10)
        sg.setColorAt(0, QColor("#4dffff"))
        sg.setColorAt(1, QColor("#007a7a"))
        p.setBrush(sg)
        p.setPen(Qt.NoPen)
        path = QPainterPath()
        path.moveTo(sx, sy-14)
        path.lineTo(sx+22, sy+10)
        path.lineTo(sx-22, sy+10)
        path.closeSubpath()
        p.drawPath(path)
        p.setBrush(QColor("#00ffcc"))
        p.drawEllipse(sx-6, sy-8, 12, 10)

    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key_Left, Qt.Key_A):   self._pleft  = True
        elif k in (Qt.Key_Right, Qt.Key_D): self._pright = True
        elif k == Qt.Key_Space:
            if self._pshoot_cd == 0 and not self.over and not self.paused:
                self._pbullets.append([float(self._px), float(self._py-16), -9])
                self._pshoot_cd = 16
        elif k == Qt.Key_P:
            self.paused = not self.paused
        elif k == Qt.Key_R:
            self._new_game()

    def keyReleaseEvent(self, e):
        k = e.key()
        if k in (Qt.Key_Left, Qt.Key_A):    self._pleft  = False
        elif k in (Qt.Key_Right, Qt.Key_D): self._pright = False


class GameSpaceInvaders(QtWidgets.QWidget):
    def __init__(self):
        super(GameSpaceInvaders, self).__init__()
        self.setWindowTitle("Space Invaders  |  JK Games")
        self.setStyleSheet("background:#000011;")
        self.setWindowFlags(Qt.Window)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)

        tb = QtWidgets.QWidget()
        tb.setStyleSheet("background:#000008;border-bottom:1px solid #0a0a22;")
        tb.setFixedHeight(38)
        tbl = QtWidgets.QHBoxLayout(tb)
        tbl.setContentsMargins(10,4,10,4); tbl.setSpacing(8)
        logo = QtWidgets.QLabel("SPACE INVADERS")
        logo.setStyleSheet("color:#00ff88;font-size:13px;font-weight:800;letter-spacing:2px;")
        self._sc = QtWidgets.QLabel("SCORE: 0")
        self._sc.setStyleSheet("color:#ffe000;font-size:12px;font-weight:700;")
        self._lv = QtWidgets.QLabel("LV 1")
        self._lv.setStyleSheet("color:#4dffff;font-size:12px;font-weight:700;")
        self._pb = QtWidgets.QPushButton("Pause")
        self._pb.setStyleSheet(BTN_STYLE); self._pb.setFocusPolicy(Qt.NoFocus)
        self._pb.clicked.connect(self._pause)
        rb = QtWidgets.QPushButton("Restart")
        rb.setStyleSheet(BTN_STYLE); rb.setFocusPolicy(Qt.NoFocus)
        rb.clicked.connect(self._restart)
        tbl.addWidget(logo); tbl.addStretch()
        tbl.addWidget(self._lv); tbl.addWidget(self._sc)
        tbl.addWidget(self._pb); tbl.addWidget(rb)
        lay.addWidget(tb)

        self.canvas = SpaceInvadersCanvas(self)
        self.canvas._timer.timeout.connect(self._tick_ui)
        lay.addWidget(self.canvas)
        self.adjustSize(); self.canvas.setFocus()

    def _tick_ui(self):
        self._sc.setText("SCORE: "+str(self.canvas.score))
        self._lv.setText("LV "+str(self.canvas.level))

    def _pause(self):
        self.canvas.paused = not self.canvas.paused
        self._pb.setText("Resume" if self.canvas.paused else "Pause")
        self.canvas.update(); self.canvas.setFocus()

    def _restart(self):
        self.canvas._new_game(); self._pb.setText("Pause"); self.canvas.setFocus()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_P: self._pause()
        else: self.canvas.keyPressEvent(e)

    def keyReleaseEvent(self, e):
        self.canvas.keyReleaseEvent(e)




# ==============================================================================
# GAME 6 - BLOCKUDOKU PUZZLE
# ==============================================================================

BU_GRID  = 9
BU_CELL  = 46
BU_PAD   = 10

BU_COLORS = [
    "#e74c3c","#e67e22","#f5c542","#2ecc71",
    "#1abc9c","#3498db","#9b59b6","#e91e63","#00bcd4",
]

BU_PIECES = [
    [(0,0)],
    [(0,0),(0,1)],
    [(0,0),(1,0)],
    [(0,0),(0,1),(0,2)],
    [(0,0),(1,0),(2,0)],
    [(0,0),(1,0),(1,1)],
    [(0,0),(0,1),(1,1)],
    [(0,0),(1,0),(0,1)],
    [(0,1),(1,0),(1,1)],
    [(0,0),(1,0),(2,0),(1,1)],
    [(0,0),(0,1),(0,2),(1,1)],
    [(0,1),(1,0),(1,1),(2,0)],
    [(0,0),(1,0),(1,1),(2,1)],
    [(0,0),(0,1),(1,0),(1,1)],
    [(0,0),(0,1),(0,2),(1,0),(1,1),(1,2),(2,0),(2,1),(2,2)],
    [(0,0),(1,0),(2,0),(2,1),(2,2)],
    [(0,0),(0,1),(0,2),(1,2),(2,2)],
]


class BUPieceBtn(QtWidgets.QWidget):
    CELL = 24

    def __init__(self, piece, color, idx, game_ref, parent=None):
        super(BUPieceBtn, self).__init__(parent)
        self.piece    = piece
        self.color    = color
        self.idx      = idx
        self.game_ref = game_ref
        self.used     = False
        self.selected = False
        C = self.CELL
        mr = max(r for r,c in piece) + 1
        mc = max(c for r,c in piece) + 1
        self.setFixedSize(mc*C + 16, mr*C + 16)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, e):
        if self.used: return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        C = self.CELL
        if self.selected:
            glow = QColor(self.color); glow.setAlpha(30)
            p.fillRect(self.rect(), glow)
            p.setPen(QPen(QColor(self.color), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(1,1,self.width()-2,self.height()-2,6,6)
        for r,c in self.piece:
            x2 = c*C+6; y2 = r*C+6
            g = QLinearGradient(x2,y2,x2,y2+C-2)
            g.setColorAt(0, QColor(self.color).lighter(140))
            g.setColorAt(1, QColor(self.color))
            p.setBrush(g)
            p.setPen(QPen(QColor(self.color).darker(160), 1))
            p.drawRoundedRect(x2+1,y2+1,C-4,C-4,4,4)
            p.setBrush(QColor(255,255,255,60))
            p.setPen(Qt.NoPen)
            p.drawRect(x2+3,y2+3,(C-8)//2,(C-8)//3)
        p.end()

    def mousePressEvent(self, e):
        if self.used or e.button() != Qt.LeftButton: return
        self.game_ref.select_piece(self.idx)


class BlockudokuCanvas(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(BlockudokuCanvas, self).__init__(parent)
        W = BU_GRID*BU_CELL + BU_PAD*2
        H = BU_GRID*BU_CELL + BU_PAD*2
        self.setFixedSize(W, H)
        self.setStyleSheet("background:#0a0a0a;")
        self.setMouseTracking(True)
        self.score = 0; self.best = 0; self.level = 1; self.over = False
        self._board       = [[None]*BU_GRID for _ in range(BU_GRID)]
        self._hover_cells = []
        self._can_place   = False
        self._flash_cells = []
        self._flash_t     = 0
        self._anim        = 0
        self._timer       = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def _tick(self):
        self._anim += 1
        if self._flash_t > 0:
            self._flash_t -= 1
            if self._flash_t == 0:
                self._flash_cells = []
        self.update()

    def reset(self):
        self._board       = [[None]*BU_GRID for _ in range(BU_GRID)]
        self.score = 0; self.level = 1; self.over = False
        self._hover_cells = []; self._flash_cells = []; self._flash_t = 0
        self.update()

    def _cell_at(self, wx, wy):
        ox = BU_PAD; oy = BU_PAD
        c2 = (wx - ox) // BU_CELL
        r2 = (wy - oy) // BU_CELL
        if 0 <= r2 < BU_GRID and 0 <= c2 < BU_GRID:
            return int(r2), int(c2)
        return None, None

    def update_hover(self, wx, wy):
        piece = self.parent().selected_piece()
        if piece is None:
            self._hover_cells = []; self._can_place = False; self.update(); return
        cells, color = piece
        min_r = min(r for r,c in cells)
        min_c = min(c for r,c in cells)
        r0, c0 = self._cell_at(wx, wy)
        if r0 is None:
            self._hover_cells = []; self._can_place = False
        else:
            hover = [(r0+r-min_r, c0+c-min_c) for r,c in cells]
            valid = all(0<=r<BU_GRID and 0<=c<BU_GRID and
                        self._board[r][c] is None for r,c in hover)
            self._hover_cells = hover
            self._can_place   = valid
        self.update()

    def try_place(self, wx, wy):
        piece = self.parent().selected_piece()
        if piece is None: return False
        cells, color = piece
        min_r = min(r for r,c in cells)
        min_c = min(c for r,c in cells)
        r0, c0 = self._cell_at(wx, wy)
        if r0 is None: return False
        hover = [(r0+r-min_r, c0+c-min_c) for r,c in cells]
        if not all(0<=r<BU_GRID and 0<=c<BU_GRID and
                   self._board[r][c] is None for r,c in hover):
            return False
        for r,c in hover:
            self._board[r][c] = color
        self._check_clear()
        self._hover_cells = []; self._can_place = False
        self._check_game_over()
        self.update()
        return True

    def _check_clear(self):
        to_clear = set()
        for r in range(BU_GRID):
            if all(self._board[r][c] for c in range(BU_GRID)):
                for c in range(BU_GRID): to_clear.add((r,c))
        for c in range(BU_GRID):
            if all(self._board[r][c] for r in range(BU_GRID)):
                for r in range(BU_GRID): to_clear.add((r,c))
        for br in range(3):
            for bc in range(3):
                box = [(br*3+dr, bc*3+dc) for dr in range(3) for dc in range(3)]
                if all(self._board[r][c] for r,c in box):
                    for rc in box: to_clear.add(rc)
        if to_clear:
            lines = max(1, len(to_clear) // 9)
            pts = lines * 100 * self.level
            self.score += pts
            self.level = min(10, self.score//500+1)
            self._flash_cells = list(to_clear)
            self._flash_t     = 14
            for r,c in to_clear: self._board[r][c] = None
            add_score("Blockudoku", self.score, self.level)

    def _check_game_over(self):
        pieces = [p for p in self.parent()._pieces if p is not None]
        if not pieces: return
        for cells, color in pieces:
            min_r = min(r for r,c in cells)
            min_c = min(c for r,c in cells)
            for sr in range(BU_GRID):
                for sc in range(BU_GRID):
                    placed = [(sr+r-min_r, sc+c-min_c) for r,c in cells]
                    if all(0<=r<BU_GRID and 0<=c<BU_GRID and
                           self._board[r][c] is None for r,c in placed):
                        return
        self.over = True
        if self.score > self.best: self.best = self.score
        add_score("Blockudoku", self.score, self.level)
        self.update()

    def mouseMoveEvent(self, e):
        self.update_hover(e.x(), e.y())

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.over:
            if self.try_place(e.x(), e.y()):
                self.parent().piece_placed()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        ox = BU_PAD; oy = BU_PAD; C = BU_CELL
        p.fillRect(self.rect(), QColor("#0a0a0a"))
        for br in range(3):
            for bc in range(3):
                shade = "#111111" if (br+bc)%2==0 else "#0d0d0d"
                p.setBrush(QColor(shade)); p.setPen(Qt.NoPen)
                p.drawRect(ox+bc*3*C, oy+br*3*C, 3*C, 3*C)
        for i in range(BU_GRID+1):
            thick = (i%3 == 0)
            p.setPen(QPen(QColor("#2e2e2e") if thick else QColor("#181818"),
                          2 if thick else 1))
            p.drawLine(ox+i*C, oy, ox+i*C, oy+BU_GRID*C)
            p.drawLine(ox, oy+i*C, ox+BU_GRID*C, oy+i*C)
        flash_set = set(map(tuple, self._flash_cells))
        for r in range(BU_GRID):
            for c in range(BU_GRID):
                col = self._board[r][c]
                if col:
                    x2 = ox+c*C+2; y2 = oy+r*C+2
                    if (r,c) in flash_set:
                        alpha = int(255 * self._flash_t / 14.0)
                        fc = QColor("#ffffff"); fc.setAlpha(alpha)
                        p.setBrush(fc); p.setPen(Qt.NoPen)
                        p.drawRoundedRect(x2,y2,C-4,C-4,4,4)
                    else:
                        g = QLinearGradient(x2,y2,x2,y2+C-4)
                        g.setColorAt(0, QColor(col).lighter(125))
                        g.setColorAt(1, QColor(col))
                        p.setBrush(g)
                        p.setPen(QPen(QColor(col).darker(180),1))
                        p.drawRoundedRect(x2,y2,C-4,C-4,4,4)
                        p.setBrush(QColor(255,255,255,40))
                        p.setPen(Qt.NoPen)
                        p.drawRoundedRect(x2+2,y2+2,(C-8)//2,(C-8)//3,2,2)
        for r,c in self._hover_cells:
            if 0<=r<BU_GRID and 0<=c<BU_GRID:
                x2 = ox+c*C+2; y2 = oy+r*C+2
                hl = QColor("#00ff88" if self._can_place else "#ff4444")
                hl.setAlpha(110)
                p.setBrush(hl); p.setPen(Qt.NoPen)
                p.drawRoundedRect(x2,y2,C-4,C-4,4,4)
        if self.over:
            p.fillRect(self.rect(), QColor(0,0,0,170))
            p.setPen(QColor("#e74c3c"))
            p.setFont(QFont("Arial",24,QFont.Bold))
            p.drawText(QRect(0,0,self.width(),self.height()//2), Qt.AlignCenter, "GAME OVER")
            p.setPen(QColor("#f5c542"))
            p.setFont(QFont("Arial",13))
            p.drawText(QRect(0,self.height()//2,self.width(),40), Qt.AlignCenter,
                "Score: "+str(self.score)+"   Best: "+str(self.best))
            p.setPen(QColor(255,255,255,80))
            p.setFont(QFont("Arial",10))
            p.drawText(QRect(0,self.height()//2+44,self.width(),30),
                Qt.AlignCenter, "Click New Game to play again")
        p.end()


class GameBlockudoku(QtWidgets.QWidget):
    def __init__(self):
        super(GameBlockudoku, self).__init__()
        self.setWindowTitle("Blockudoku  |  JK Games")
        self.setStyleSheet("background:#0a0a0a;")
        self.setWindowFlags(Qt.Window)
        self._pieces     = [None, None, None]
        self._sel_idx    = -1
        self._piece_btns = []
        self._build_ui()
        self._new_game()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        tb = QtWidgets.QWidget(); tb.setFixedHeight(42)
        tb.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #141414,stop:1 #080808);border-bottom:2px solid #1a1a00;")
        tbl = QtWidgets.QHBoxLayout(tb)
        tbl.setContentsMargins(12,4,12,4); tbl.setSpacing(8)
        logo = QtWidgets.QLabel("BLOCKUDOKU")
        logo.setStyleSheet("color:#9b59b6;font-size:14px;font-weight:800;letter-spacing:2px;")
        self._sc_lbl = QtWidgets.QLabel("SCORE: 0")
        self._sc_lbl.setStyleSheet("color:#f5c542;font-size:12px;font-weight:700;")
        self._lv_lbl = QtWidgets.QLabel("LV 1")
        self._lv_lbl.setStyleSheet("color:#4dff91;font-size:12px;font-weight:700;")
        nb = QtWidgets.QPushButton("New Game")
        nb.setStyleSheet(BTN_STYLE); nb.setFocusPolicy(Qt.NoFocus)
        nb.clicked.connect(self._new_game)
        tbl.addWidget(logo); tbl.addStretch()
        tbl.addWidget(self._lv_lbl); tbl.addWidget(self._sc_lbl); tbl.addWidget(nb)
        root.addWidget(tb)
        hint = QtWidgets.QLabel(
            "  Click a piece below to SELECT it (glows), then click the grid to PLACE it.  "
            "Fill rows, columns or 3x3 boxes to clear them!")
        hint.setStyleSheet(
            "color:#383828;font-size:10px;padding:4px 12px;"
            "background:#080808;border-bottom:1px solid #111;")
        root.addWidget(hint)
        self.canvas = BlockudokuCanvas(self)
        self.canvas._timer.timeout.connect(self._tick_ui)
        root.addWidget(self.canvas)
        self._tray = QtWidgets.QWidget(); self._tray.setFixedHeight(100)
        self._tray.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #0d0d0d,stop:1 #080808);border-top:2px solid #1a1a00;")
        self._tray_lay = QtWidgets.QHBoxLayout(self._tray)
        self._tray_lay.setContentsMargins(20,12,20,12); self._tray_lay.setSpacing(40)
        root.addWidget(self._tray)
        self.adjustSize()

    def _new_game(self):
        self._sel_idx = -1
        self._pieces  = [None, None, None]
        self.canvas.reset()
        self._give_pieces()

    def _give_pieces(self):
        while self._tray_lay.count():
            item = self._tray_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._piece_btns = []
        for i in range(3):
            cells = random.choice(BU_PIECES)
            color = random.choice(BU_COLORS)
            self._pieces[i] = (cells, color)
            btn = BUPieceBtn(cells, color, i, self)
            self._piece_btns.append(btn)
            self._tray_lay.addWidget(btn, alignment=Qt.AlignCenter)
        self._tray_lay.addStretch()
        self._sel_idx = -1

    def select_piece(self, idx):
        if self._pieces[idx] is None: return
        self._sel_idx = -1 if self._sel_idx == idx else idx
        for i, btn in enumerate(self._piece_btns):
            btn.selected = (i == self._sel_idx)
            btn.update()
        self.canvas._hover_cells = []
        self.canvas._can_place   = False
        self.canvas.update()

    def selected_piece(self):
        if self._sel_idx < 0: return None
        return self._pieces[self._sel_idx]

    def piece_placed(self):
        if self._sel_idx >= 0:
            self._pieces[self._sel_idx] = None
            if self._sel_idx < len(self._piece_btns):
                self._piece_btns[self._sel_idx].used     = True
                self._piece_btns[self._sel_idx].selected = False
                self._piece_btns[self._sel_idx].update()
        self._sel_idx = -1
        if all(p is None for p in self._pieces):
            self._give_pieces()

    def _tick_ui(self):
        self._sc_lbl.setText("SCORE: "+str(self.canvas.score))
        self._lv_lbl.setText("LV "+str(self.canvas.level))

    def keyPressEvent(self, e):
        k = e.key()
        if   k == Qt.Key_1: self.select_piece(0)
        elif k == Qt.Key_2: self.select_piece(1)
        elif k == Qt.Key_3: self.select_piece(2)


# ==============================================================================
# GAME HUB + LAUNCHERS + MENU
# ==============================================================================

class GameCard(QtWidgets.QFrame):
    BASE_W = 148
    BASE_H = 194

    def __init__(self, name, icon_txt, color, desc, callback, parent=None):
        super(GameCard, self).__init__(parent)
        self._callback = callback
        self._color    = color
        self._hovered  = False
        self._scale    = 1.0
        self._anim_t   = QTimer(self)
        self._anim_t.setSingleShot(False)
        self._anim_t.timeout.connect(self._step)
        self.setFixedSize(self.BASE_W, self.BASE_H)
        self.setCursor(Qt.PointingHandCursor)
        self._build(name, icon_txt, color, desc)
        self._set_style(False)

    def _build(self, name, icon_txt, color, desc):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10,14,10,10); lay.setSpacing(6)
        ic = QtWidgets.QLabel(icon_txt)
        ic.setFixedSize(62,62); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 "+QColor(color).lighter(140).name()+","
            "stop:1 "+color+");"
            "color:#000;border-radius:31px;font-size:15px;font-weight:800;"
            "border-top:2px solid rgba(255,255,255,130);"
            "border-bottom:2px solid rgba(0,0,0,200);"
        )
        lay.addWidget(ic, alignment=Qt.AlignCenter)
        nl = QtWidgets.QLabel(name)
        nl.setAlignment(Qt.AlignCenter)
        nl.setStyleSheet("color:"+color+";font-size:11px;font-weight:800;"
                         "background:transparent;border:none;letter-spacing:1px;")
        lay.addWidget(nl)
        dl = QtWidgets.QLabel(desc)
        dl.setAlignment(Qt.AlignCenter); dl.setWordWrap(True)
        dl.setStyleSheet("color:#484838;font-size:10px;background:transparent;border:none;")
        lay.addWidget(dl); lay.addStretch()
        pb = QtWidgets.QPushButton("PLAY")
        pb.setFixedHeight(28); pb.setFocusPolicy(Qt.NoFocus)
        pb.setStyleSheet(
            "QPushButton{"
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 "+QColor(color).lighter(120).name()+","
            "stop:1 "+QColor(color).darker(130).name()+");"
            "color:#000;border:none;border-radius:7px;"
            "font-size:11px;font-weight:800;letter-spacing:1px;"
            "border-top:2px solid rgba(255,255,255,140);"
            "border-bottom:2px solid rgba(0,0,0,200);}"
            "QPushButton:hover{background:"+color+";}"
            "QPushButton:pressed{background:#000;color:"+color+";}"
        )
        pb.clicked.connect(self._callback)
        lay.addWidget(pb)

    def _set_style(self, hovered):
        if hovered:
            self.setStyleSheet(
                "QFrame{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #2a2a2a,stop:1 #181818);"
                "border-radius:14px;border:1px solid "+self._color+";}"
            )
        else:
            self.setStyleSheet(
                "QFrame{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #1e1e1e,stop:1 #111111);"
                "border-radius:14px;border:1px solid #282828;}"
            )

    def enterEvent(self, e):
        self._hovered = True
        self._set_style(True)
        self._anim_t.start(14)

    def leaveEvent(self, e):
        self._hovered = False
        self._anim_t.start(14)

    def _step(self):
        target = 1.10 if self._hovered else 1.0
        self._scale += (target - self._scale) * 0.28
        if abs(self._scale - target) < 0.003:
            self._scale = target
            self._anim_t.stop()
            if not self._hovered: self._set_style(False)
        nw = int(self.BASE_W * self._scale)
        nh = int(self.BASE_H * self._scale)
        self.setFixedSize(nw, nh)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self._callback()


class CardWrapper(QtWidgets.QWidget):
    def __init__(self, card, parent=None):
        super(CardWrapper, self).__init__(parent)
        self.setFixedSize(card.BASE_W + 32, card.BASE_H + 32)
        self._card = card
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.addWidget(card, alignment=Qt.AlignCenter)
        self.setStyleSheet("background:transparent;")


class JKGamesHub(QtWidgets.QWidget):
    def __init__(self):
        super(JKGamesHub, self).__init__()
        self.setWindowTitle("JK Games")
        self.setWindowFlags(Qt.Window)
        self.setMinimumSize(1060, 660)
        self.setStyleSheet("background:#0d0d0d;")
        self._sel_card = 0
        self._cards    = []
        self._tab_games = [
            ("2048","#f5c542"),("Snake","#4dff91"),
            ("Breakout","#4fc3f7"),("Block Blast","#ff7043"),
            ("Space Invaders","#00ff88"),("Blockudoku","#9b59b6"),
        ]
        self._build()

    def _build(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # banner
        banner = QtWidgets.QWidget(); banner.setFixedHeight(82)
        banner.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #0d0600,stop:0.4 #120800,stop:0.7 #080814,stop:1 #0d0600);"
            "border-bottom:2px solid #2e1800;"
        )
        bl = QtWidgets.QHBoxLayout(banner); bl.setContentsMargins(32,0,32,0)
        lv = QtWidgets.QVBoxLayout(); lv.setSpacing(2)
        logo = QtWidgets.QLabel("JK GAMES")
        logo.setStyleSheet(
            "color:#f5c542;font-size:28px;font-weight:900;letter-spacing:8px;"
            "background:transparent;")
        tag = QtWidgets.QLabel("Render running  -  time to play")
        tag.setStyleSheet("color:#3a2000;font-size:10px;font-style:italic;"
                          "letter-spacing:1px;background:transparent;")
        lv.addWidget(logo); lv.addWidget(tag)
        badge = QtWidgets.QWidget()
        badge.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #201400,stop:1 #0d0900);"
            "border-radius:22px;border:1px solid #3e2200;")
        badge.setFixedHeight(44)
        bl2 = QtWidgets.QHBoxLayout(badge); bl2.setContentsMargins(10,0,16,0); bl2.setSpacing(8)
        uname = get_player()
        init  = uname[0].upper() if uname else "P"
        ic2 = QtWidgets.QLabel(init); ic2.setFixedSize(30,30); ic2.setAlignment(Qt.AlignCenter)
        ic2.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #ffe000,stop:1 #d08000);"
            "color:#000;border-radius:15px;font-size:15px;font-weight:800;"
            "border-top:1px solid rgba(255,255,255,160);")
        nl2 = QtWidgets.QLabel(uname)
        nl2.setStyleSheet("color:#c8a010;font-size:12px;font-weight:700;background:transparent;")
        bl2.addWidget(ic2); bl2.addWidget(nl2)
        bl.addLayout(lv); bl.addStretch(); bl.addWidget(badge)
        root.addWidget(banner)

        # scroll body
        sa = QtWidgets.QScrollArea(); sa.setWidgetResizable(True)
        sa.setStyleSheet(
            "QScrollArea{border:none;background:#0d0d0d;}"
            "QScrollBar:vertical{background:#111;width:7px;border-radius:3px;}"
            "QScrollBar::handle:vertical{background:#2a2010;border-radius:3px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QtWidgets.QWidget(); body.setStyleSheet("background:#0d0d0d;")
        bl3 = QtWidgets.QVBoxLayout(body)
        bl3.setContentsMargins(32,22,32,28); bl3.setSpacing(18)

        sl2 = QtWidgets.QLabel("CHOOSE A GAME")
        sl2.setStyleSheet(
            "color:#3a2000;font-size:10px;font-weight:800;"
            "letter-spacing:4px;background:transparent;")
        bl3.addWidget(sl2)

        # cards in a horizontal scroll so they always fit
        cards_sa = QtWidgets.QScrollArea()
        cards_sa.setFixedHeight(GameCard.BASE_H + 50)
        cards_sa.setWidgetResizable(True)
        cards_sa.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cards_sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cards_sa.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        cw = QtWidgets.QWidget(); cw.setStyleSheet("background:transparent;")
        crow = QtWidgets.QHBoxLayout(cw)
        crow.setContentsMargins(0,8,0,8); crow.setSpacing(0)

        GAMES = [
            ("2048",           "2048", "#f5c542", "Slide tiles\nreach 2048",     open_2048),
            ("SNAKE",          "S",    "#4dff91", "Eat food\ngrow longer",        open_snake),
            ("BREAKOUT",       "B",    "#4fc3f7", "Break bricks\nwith ball",      open_breakout),
            ("BLOCK BLAST",    "BB",   "#ff7043", "Falling blocks\nclear rows",   open_block_blast),
            ("SPACE INVADERS", "SI",   "#00ff88", "Shoot aliens\nfrom below",     open_space_invaders),
            ("BLOCKUDOKU",     "BU",   "#9b59b6", "Select+place\nblocks",         open_blockudoku),
        ]
        self._cards = []
        for name, icon_txt, color, desc, fn in GAMES:
            card = GameCard(name, icon_txt, color, desc, fn)
            wrap = CardWrapper(card)
            self._cards.append(card)
            crow.addWidget(wrap)
        crow.addStretch()
        cards_sa.setWidget(cw)
        bl3.addWidget(cards_sa)

        # divider
        div = QtWidgets.QFrame(); div.setFrameShape(QtWidgets.QFrame.HLine)
        div.setStyleSheet("color:#1e1200;"); bl3.addWidget(div)

        # leaderboard
        lbh = QtWidgets.QHBoxLayout()
        lbl2 = QtWidgets.QLabel("LEADERBOARD")
        lbl2.setStyleSheet("color:#3a2000;font-size:10px;font-weight:800;"
                           "letter-spacing:4px;background:transparent;")
        ref = QtWidgets.QPushButton("Refresh")
        ref.setStyleSheet(
            "QPushButton{background:transparent;color:#3a2000;border:none;"
            "font-size:10px;text-decoration:underline;}"
            "QPushButton:hover{color:#f5c542;}")
        ref.setFocusPolicy(Qt.NoFocus); ref.clicked.connect(self._refresh)
        lbh.addWidget(lbl2); lbh.addStretch(); lbh.addWidget(ref)
        bl3.addLayout(lbh)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setMinimumHeight(240)
        self.tabs.setStyleSheet(
            "QTabWidget::pane{background:#111008;border:1px solid #2a1e00;"
            "border-radius:0 8px 8px 8px;}"
            "QTabBar::tab{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #1a1408,stop:1 #0d0a00);color:#3a3020;padding:6px 14px;"
            "font-size:9px;font-weight:800;letter-spacing:1px;"
            "border:1px solid #1a1200;margin-right:2px;border-radius:4px 4px 0 0;}"
            "QTabBar::tab:selected{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #2a1e00,stop:1 #111008);color:#f5c542;"
            "border-bottom:2px solid #f5c542;}"
            "QTabBar::tab:hover{color:#c8a820;}"
        )
        for game, color in self._tab_games:
            self.tabs.addTab(self._score_tab(game, color), game.upper())
        bl3.addWidget(self.tabs)

        sa.setWidget(body); root.addWidget(sa)

        kh = QtWidgets.QLabel(
            "  Arrow keys: browse games   Enter / Space: launch   Tab: next leaderboard tab")
        kh.setStyleSheet(
            "color:#1e1200;font-size:9px;padding:3px 12px;"
            "background:#080808;border-top:1px solid #111;")
        root.addWidget(kh)

        self._update_card_focus()

    def _score_tab(self, game, color):
        w = QtWidgets.QWidget(); w.setStyleSheet("background:#111008;")
        outer = QtWidgets.QVBoxLayout(w)
        outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        entries = SCORES.get(game, [])
        if not entries:
            emp = QtWidgets.QLabel("No scores yet - play and come back!")
            emp.setStyleSheet("color:#2a2010;font-size:11px;")
            emp.setAlignment(Qt.AlignCenter)
            outer.addStretch(); outer.addWidget(emp); outer.addStretch()
            return w
        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea{border:none;background:#111008;}"
            "QScrollBar:vertical{background:#0a0a00;width:6px;border-radius:3px;}"
            "QScrollBar::handle:vertical{background:#2a1e00;border-radius:3px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        sw = QtWidgets.QWidget(); sw.setStyleSheet("background:#111008;")
        sl = QtWidgets.QVBoxLayout(sw)
        sl.setContentsMargins(10,8,10,8); sl.setSpacing(3)
        rank_col = ["#f5c542","#aaaaaa","#cd7f32"]
        for i, entry in enumerate(entries):
            nm = entry[0]; sc = entry[1]; lv = entry[2]
            dt = entry[3] if len(entry) > 3 else ""
            rc = rank_col[i] if i < 3 else "#3a3020"
            row = QtWidgets.QWidget(); row.setFixedHeight(28)
            row.setStyleSheet(
                ("background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                 "stop:0 #1e1600,stop:1 #111008);"
                 "border-radius:4px;border-left:3px solid #f5c542;")
                if i == 0 else
                ("background:#0d0c08;border-radius:4px;border-left:1px solid #1a1400;")
            )
            rl = QtWidgets.QHBoxLayout(row)
            rl.setContentsMargins(8,0,10,0); rl.setSpacing(6)
            def lbl(txt, col, sz, bold=False, fw=0):
                lb2 = QtWidgets.QLabel(txt)
                wt  = "font-weight:800;" if bold else ""
                lb2.setStyleSheet("color:"+col+";font-size:"+sz+";"+wt+"background:transparent;")
                if fw: lb2.setFixedWidth(fw)
                return lb2
            rl.addWidget(lbl("#"+str(i+1), rc,      "10px", True,  22))
            rl.addWidget(lbl(nm[:16],       "#c8c8b0","10px", False, 110))
            rl.addWidget(lbl("Lv"+str(lv),  "#3a3020","9px",  False,  28))
            rl.addWidget(lbl(dt,            "#2a2810","9px"))
            rl.addStretch()
            rl.addWidget(lbl(str(sc)+" pts", color,  "11px", True))
            sl.addWidget(row)
        sl.addStretch()
        scroll.setWidget(sw); outer.addWidget(scroll)
        return w

    def _refresh(self):
        while self.tabs.count(): self.tabs.removeTab(0)
        for game, color in self._tab_games:
            self.tabs.addTab(self._score_tab(game, color), game.upper())

    def _update_card_focus(self):
        for i, card in enumerate(self._cards):
            if i == self._sel_card:
                card._hovered = True
                card._set_style(True)
                card._anim_t.start(14)
            else:
                if not card._hovered:
                    card._set_style(False)

    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key_Left, Qt.Key_A):
            self._sel_card = max(0, self._sel_card - 1)
            self._update_card_focus()
        elif k in (Qt.Key_Right, Qt.Key_D):
            self._sel_card = min(len(self._cards)-1, self._sel_card + 1)
            self._update_card_focus()
        elif k in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if 0 <= self._sel_card < len(self._cards):
                self._cards[self._sel_card]._callback()
        elif k == Qt.Key_Tab:
            nxt = (self.tabs.currentIndex() + 1) % self.tabs.count()
            self.tabs.setCurrentIndex(nxt)
        else:
            super(JKGamesHub, self).keyPressEvent(e)


# ==============================================================================
# LAUNCHERS
# ==============================================================================

_refs = {}

def open_hub():
    _refs["hub"] = JKGamesHub()
    _refs["hub"].show(); _refs["hub"].raise_()

def open_2048():
    _refs["2048"] = Game2048()
    _refs["2048"].show(); _refs["2048"].raise_()

def open_snake():
    _refs["snake"] = GameSnake()
    _refs["snake"].show(); _refs["snake"].raise_()
    _refs["snake"].canvas.setFocus()

def open_breakout():
    _refs["breakout"] = GameBreakout()
    _refs["breakout"].show(); _refs["breakout"].raise_()
    _refs["breakout"].canvas.setFocus()

def open_block_blast():
    _refs["bb"] = GameBlockBlast()
    _refs["bb"].show(); _refs["bb"].raise_()
    _refs["bb"].canvas.setFocus()

def open_space_invaders():
    _refs["si"] = GameSpaceInvaders()
    _refs["si"].show(); _refs["si"].raise_()
    _refs["si"].canvas.setFocus()

def open_blockudoku():
    _refs["bu"] = GameBlockudoku()
    _refs["bu"].show(); _refs["bu"].raise_()


# ==============================================================================
# NUKE MENU
# ==============================================================================

def _register_menu():
    menubar = nuke.menu("Nuke")
    for nm in ["Games", "JK_Games"]:
        old = menubar.findItem(nm)
        if old:
            try: menubar.removeItem(nm)
            except: pass
    jk = menubar.addMenu("JK_Games")
    jk.addCommand("Game Hub", "import nuke_games; nuke_games.open_hub()")

_register_menu()