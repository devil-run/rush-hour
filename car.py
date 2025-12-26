import json
import collections
import copy
import sys
import os

try:
    from flask import Flask, render_template_string, request, jsonify
    from pyngrok import ngrok
except ImportError:
    print("❌ 缺少库！请运行: pip install flask pyngrok")
    sys.exit(1)
    
NGROK_AUTH_TOKEN = "371K2TWzMRJb1bgDbvEanVArTBh_3pYnqywYuxuZXt5co77rw"

if NGROK_AUTH_TOKEN != "371K2TWzMRJb1bgDbvEanVArTBh_3pYnqywYuxuZXt5co77rw":
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)

app = Flask(__name__)

class Solver:
    def __init__(self, width, height, cars, target_car_index):
        self.width = width
        self.height = height
        self.initial_cars = cars
        self.target_car_idx = target_car_index

    def get_state_key(self, cars):
        state = []
        for car in cars:
            state.append((car['r'], car['c']))
        return tuple(state)

    def is_solved(self, cars):
        target = cars[self.target_car_idx]
        if target['dir'] == 'h':
            return target['c'] + target['len'] == self.width
        return False

    def get_board_grid(self, cars):
        grid = [[None for _ in range(self.width)] for _ in range(self.height)]
        for idx, car in enumerate(cars):
            r, c = car['r'], car['c']
            if car['dir'] == 'h':
                for i in range(car['len']):
                    if 0 <= c + i < self.width: grid[r][c + i] = idx
            else:
                for i in range(car['len']):
                    if 0 <= r + i < self.height: grid[r + i][c] = idx
        return grid

    def solve_bfs(self):
        start_cars = copy.deepcopy(self.initial_cars)
        initial_key = self.get_state_key(start_cars)
        queue = collections.deque([(start_cars, [])])
        visited = set([initial_key])

        steps = 0
        max_steps = 100000

        while queue:
            steps += 1
            if steps > max_steps: return None

            current_cars, path = queue.popleft()
            if self.is_solved(current_cars):
                return path

            grid = self.get_board_grid(current_cars)

            for i, car in enumerate(current_cars):
                r, c = car['r'], car['c']
                length, direction = car['len'], car['dir']

                moves = []
                if direction == 'h':
                    moves.append((-1, 0)); moves.append((1, 0))
                else:
                    moves.append((0, -1)); moves.append((0, 1))

                for dc, dr in moves:
                    new_c, new_r = c + dc, r + dr

                    if new_c < 0 or new_r < 0: continue
                    if direction == 'h' and new_c + length > self.width: continue
                    if direction == 'v' and new_r + length > self.height: continue

                    collision = False
                    if direction == 'h':
                        for k in range(length):
                            occupier = grid[r][new_c + k]
                            if occupier is not None and occupier != i: collision = True; break
                    else:
                        for k in range(length):
                            occupier = grid[new_r + k][c]
                            if occupier is not None and occupier != i: collision = True; break

                    if not collision:
                        new_cars = copy.deepcopy(current_cars)
                        new_cars[i]['r'] = new_r
                        new_cars[i]['c'] = new_c

                        new_key = self.get_state_key(new_cars)
                        if new_key not in visited:
                            visited.add(new_key)
                            new_step = {'idx': i, 'r': new_r, 'c': new_c}
                            queue.append((new_cars, path + [new_step]))
        return None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rush Hour Perfect</title>
    <style>
        :root { --bg: #ffffff; --panel: #f9f9f9; --text: #2d3436; --board: #f1f2f6; --accent: #0984e3; --border: #e1e1e1; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); display: flex; flex-direction: column; align-items: center; margin: 0; padding: 20px; min-height: 100vh; }
        .header { text-align: center; margin-bottom: 20px; }
        h1 { margin: 0; font-size: 28px; letter-spacing: -1px; }
        .subtitle { color: #b2bec3; font-size: 13px; margin-top: 5px; }
        .container { display: flex; gap: 40px; flex-wrap: wrap; justify-content: center; width: 100%; max-width: 900px; }
        .canvas-box { background: #fff; padding: 12px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); border: 1px solid #f0f0f0; }
        canvas { background: var(--board); border-radius: 6px; cursor: pointer; display: block; }
        .panel { width: 320px; background: var(--panel); padding: 24px; border-radius: 16px; display: flex; flex-direction: column; gap: 16px; border: 1px solid #eee; }
        .tab-group { display: flex; background: #dfe6e9; border-radius: 8px; padding: 4px; gap: 4px; }
        .tab-btn { flex: 1; border: none; background: transparent; padding: 8px; border-radius: 6px; font-weight: bold; color: #636e72; cursor: pointer; transition: 0.2s; font-size: 12px; }
        .tab-btn.active { background: #fff; color: #2d3436; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .level-controls { display: flex; flex-direction: column; gap: 10px; }
        .diff-select { padding: 8px; border-radius: 6px; border: 1px solid var(--border); font-weight: bold; color: #2d3436; outline: none; }
        .level-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
        .lvl-btn { background: #fff; border: 1px solid var(--border); border-radius: 6px; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .lvl-btn:hover { border-color: var(--accent); color: var(--accent); }
        .lvl-btn.active { background: var(--accent); color: white; border-color: var(--accent); }
        .scoreboard { background: #2d3436; color: white; padding: 15px; border-radius: 10px; display: none; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .score-row { display: flex; justify-content: space-around; align-items: center; }
        .score-val { font-size: 24px; font-weight: bold; color: #ff7675; }
        .score-label { font-size: 10px; color: #b2bec3; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
        .editor-tools { display: flex; flex-direction: column; gap: 12px; }
        .group { background: #fff; border: 1px solid #eee; border-radius: 8px; padding: 12px; }
        .group-head { font-size: 10px; font-weight: 800; color: #b2bec3; margin-bottom: 8px; display: block; letter-spacing: 1px; text-transform: uppercase; }
        .opt-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
        label { font-size: 12px; display: flex; align-items: center; gap: 4px; cursor: pointer; color: #636e72; }
        button.action-btn { border: none; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; transition: all 0.2s; font-size: 14px; width: 100%; }
        .btn-main { background: #2d3436; color: white; } .btn-main:hover { transform: translateY(-1px); }
        .btn-sec { background: #dfe6e9; color: #2d3436; flex: 1; }
        .btn-ai { background: #74b9ff; color: white; margin-top: 5px; } .btn-ai:disabled { background: #b2bec3; opacity: 0.6; cursor: not-allowed; }
        .row { display: flex; gap: 10px; }
        .c-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
        .dot { width: 20px; height: 20px; border-radius: 50%; cursor: pointer; border: 2px solid transparent; }
        .dot.active { border-color: #2d3436; transform: scale(1.2); }
        #msg { text-align: center; font-size: 12px; color: #b2bec3; min-height: 18px; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>IQ Car Challenge</h1>
        <div class="subtitle">Classic Puzzles - Guaranteed Solvable</div>
    </div>

    <div class="container">
        <div class="canvas-box"><canvas id="gc" width="420" height="420"></canvas></div>

        <div class="panel">
            <div class="tab-group">
                <button class="tab-btn active" id="tabCustom" onclick="switchTab('custom')">🛠 Free Design</button>
                <button class="tab-btn" id="tabChallenge" onclick="switchTab('challenge')">🏆 Challenge</button>
            </div>

            <div id="scorePanel" class="scoreboard">
                <div class="score-row">
                    <div id="userScoreBox">
                        <div id="stepCount" class="score-val">0</div>
                        <div class="score-label">Your Steps</div>
                    </div>
                    <div id="aiScoreBox" style="display:none; border-left:1px solid #555; padding-left:20px">
                        <div id="aiCount" class="score-val" style="color:#74b9ff">-</div>
                        <div class="score-label">Optimal Steps</div>
                    </div>
                </div>
            </div>

            <div id="customTools" class="editor-tools">
                <div class="group"><span class="group-head">Style & Color</span>
                    <div class="opt-row">
                        <label><input type="radio" name="tex" value="plain" checked>Sedan</label>
                        <label><input type="radio" name="tex" value="sports">Sport</label>
                        <label><input type="radio" name="tex" value="pickup">Pickup</label>
                        <label><input type="radio" name="tex" value="bus">Bus</label>
                    </div>
                    <div class="c-grid" id="cGrid"></div>
                </div>
                <div class="group"><span class="group-head">Properties</span>
                    <div class="opt-row">
                        <label><input type="radio" name="dir" value="h" checked>Hori</label>
                        <label><input type="radio" name="dir" value="v">Vert</label>
                        <label><input type="radio" name="len" value="2" checked>Len:2</label>
                        <label><input type="radio" name="len" value="3">Len:3</label>
                    </div>
                    <div style="margin-top:5px; color:#ff6b6b; font-weight:800; font-size:12px;">
                        <input type="checkbox" id="isTarget"> ★ Set as Target Car
                    </div>
                </div>
                <div class="row"><button onclick="undo()" class="action-btn btn-sec">Undo</button><button onclick="clearBoard()" class="action-btn btn-sec">Clear</button></div>
            </div>

            <div id="challengeTools" class="level-controls" style="display:none;">
                <select id="diffSelect" class="diff-select" onchange="renderLevels()">
                    <option value="easy">🟢 Beginner (Classic 1-5)</option>
                    <option value="normal">🟡 Intermediate (Classic 6-10)</option>
                    <option value="hard">🔴 Expert (Classic 11-15)</option>
                </select>
                <div class="level-grid" id="levelGrid"></div>
                <div id="lvlInfo" style="font-size:12px; color:#636e72; padding:5px; background:#fff; border-radius:6px; border:1px solid #eee; text-align:center;">
                    Select a level to load.
                </div>
            </div>

            <button id="mainBtn" class="action-btn btn-main">START GAME</button>
            <button id="hintBtn" class="action-btn btn-sec" disabled>💡 Hint</button>
            <button id="aiTakeBtn" class="action-btn btn-sec" disabled>🤖 AI Take Over</button>
            <button id="aiBtn" class="action-btn btn-ai" disabled>🤖 Show Optimal Solution</button>
            <div id="msg">Ready</div>
        </div>
    </div>

    <script>
        const C=70, R=6;
        const PALETTE = { "red": "#ff6b6b", "orange": "#feca57", "yellow": "#ff9f43", "green": "#1dd1a1", "cyan": "#48dbfb", "blue": "#54a0ff", "purple": "#5f27cd", "black": "#222f3e", "silver": "#c8d6e5", "pink": "#ff9ff3" };

        const LEVELS = {
            "easy": [
                [
                  {r:2,c:0,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},
                  {r:0,c:2,len:3,dir:'v',color:'green',tex:'bus',isTarget:false},
                  {r:2,c:3,len:2,dir:'v',color:'purple',tex:'pickup',isTarget:false},
                  {r:4,c:0,len:3,dir:'h',color:'yellow',tex:'bus',isTarget:false},
                  {r:5,c:4,len:2,dir:'h',color:'blue',tex:'sports',isTarget:false}
                ],
                [
                  {r:2,c:0,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},
                  {r:0,c:3,len:2,dir:'v',color:'orange',tex:'plain',isTarget:false},
                  {r:1,c:4,len:2,dir:'v',color:'blue',tex:'plain',isTarget:false},
                  {r:3,c:0,len:2,dir:'v',color:'pink',tex:'plain',isTarget:false},
                  {r:3,c:1,len:2,dir:'v',color:'purple',tex:'plain',isTarget:false},
                  {r:3,c:2,len:2,dir:'h',color:'green',tex:'plain',isTarget:false},
                  {r:4,c:3,len:2,dir:'h',color:'black',tex:'plain',isTarget:false},
                  {r:5,c:0,len:3,dir:'h',color:'yellow',tex:'bus',isTarget:false}
                ],
                [
                  {r:2,c:1,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},
                  {r:1,c:3,len:2,dir:'v',color:'orange',tex:'plain',isTarget:false},
                  {r:0,c:5,len:3,dir:'v',color:'green',tex:'bus',isTarget:false},
                  {r:4,c:3,len:2,dir:'h',color:'blue',tex:'plain',isTarget:false},
                  {r:3,c:0,len:2,dir:'v',color:'purple',tex:'plain',isTarget:false}
                ],
                [
                  {r:2,c:1,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},
                  {r:0,c:0,len:3,dir:'v',color:'yellow',tex:'bus',isTarget:false},
                  {r:0,c:3,len:2,dir:'v',color:'green',tex:'plain',isTarget:false},
                  {r:1,c:4,len:2,dir:'v',color:'orange',tex:'plain',isTarget:false},
                  {r:3,c:0,len:2,dir:'h',color:'blue',tex:'plain',isTarget:false},
                  {r:4,c:2,len:2,dir:'h',color:'purple',tex:'plain',isTarget:false},
                  {r:5,c:0,len:3,dir:'h',color:'black',tex:'bus',isTarget:false}
                ],
                [
                  {r:2,c:0,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},
                  {r:0,c:3,len:3,dir:'v',color:'yellow',tex:'bus',isTarget:false},
                  {r:0,c:4,len:2,dir:'v',color:'orange',tex:'plain',isTarget:false},
                  {r:3,c:0,len:2,dir:'v',color:'blue',tex:'plain',isTarget:false},
                  {r:4,c:1,len:2,dir:'h',color:'green',tex:'plain',isTarget:false},
                  {r:4,c:4,len:2,dir:'h',color:'black',tex:'plain',isTarget:false}
                ]
            ],
            "normal": [
                [
                  {r:2,c:0,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},   
                  {r:1,c:1,len:3,dir:'h',color:'blue',tex:'bus',isTarget:false},  
                  {r:0,c:5,len:3,dir:'v',color:'purple',tex:'bus',isTarget:false}, 
                  {r:2,c:2,len:2,dir:'v',color:'green',tex:'plain',isTarget:false},
                  {r:3,c:3,len:2,dir:'h',color:'yellow',tex:'sports',isTarget:false},
                  {r:4,c:0,len:2,dir:'h',color:'orange',tex:'plain',isTarget:false},
                  {r:4,c:2,len:2,dir:'v',color:'orange',tex:'pickup',isTarget:false}
                ],
                [ 
                  {r:2,c:0,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},  
                  {r:1,c:1,len:3,dir:'h',color:'orange',tex:'bus',isTarget:false}, 
                  {r:0,c:3,len:2,dir:'h',color:'blue',tex:'plain',isTarget:false}, 
                  {r:0,c:5,len:3,dir:'v',color:'pink',tex:'bus',isTarget:false},   
                  {r:2,c:2,len:2,dir:'v',color:'purple',tex:'plain',isTarget:false},
                  {r:2,c:3,len:3,dir:'v',color:'green',tex:'bus',isTarget:false},  
                  {r:3,c:4,len:2,dir:'h',color:'yellow',tex:'sports',isTarget:false},
                  {r:4,c:0,len:3,dir:'h',color:'blue',tex:'bus',isTarget:false}    
                ],
                [ 
                  {r:2,c:3,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},   
                  {r:1,c:0,len:2,dir:'h',color:'orange',tex:'plain',isTarget:false},
                  {r:0,c:2,len:3,dir:'v',color:'orange',tex:'bus',isTarget:false},
                  {r:1,c:5,len:3,dir:'v',color:'green',tex:'bus',isTarget:false}, 
                  {r:3,c:3,len:2,dir:'v',color:'cyan',tex:'plain',isTarget:false},
                  {r:3,c:0,len:3,dir:'h',color:'blue',tex:'bus',isTarget:false},   
                  {r:4,c:4,len:2,dir:'h',color:'silver',tex:'sports',isTarget:false}
                ],
                [ 
                  {r:2,c:1,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},   
                  {r:0,c:0,len:3,dir:'v',color:'orange',tex:'bus',isTarget:false}, 
                  {r:0,c:2,len:2,dir:'v',color:'pink',tex:'plain',isTarget:false},
                  {r:0,c:3,len:2,dir:'v',color:'green',tex:'plain',isTarget:false},
                  {r:0,c:4,len:2,dir:'h',color:'purple',tex:'plain',isTarget:false},
                  {r:2,c:4,len:2,dir:'v',color:'blue',tex:'plain',isTarget:false},
                  {r:2,c:5,len:3,dir:'v',color:'black',tex:'bus',isTarget:false},  
                  {r:4,c:1,len:2,dir:'h',color:'silver',tex:'sports',isTarget:false},
                  {r:4,c:3,len:2,dir:'h',color:'yellow',tex:'sports',isTarget:false} 
                ],
                [
                  {r:2,c:0,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},
                  {r:0,c:0,len:2,dir:'h',color:'green',tex:'plain',isTarget:false},
                  {r:0,c:2,len:3,dir:'v',color:'yellow',tex:'bus',isTarget:false},
                  {r:1,c:4,len:2,dir:'v',color:'blue',tex:'plain',isTarget:false},
                  {r:3,c:0,len:2,dir:'v',color:'orange',tex:'plain',isTarget:false},
                  {r:4,c:1,len:2,dir:'h',color:'purple',tex:'plain',isTarget:false},
                  {r:3,c:3,len:3,dir:'v',color:'black',tex:'bus',isTarget:false}
                ],
            ],
            "hard": [
                [ 
                  {r:2,c:0,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},   
                  {r:0,c:1,len:2,dir:'v',color:'blue',tex:'plain',isTarget:false}, 
                  {r:0,c:2,len:2,dir:'h',color:'pink',tex:'sports',isTarget:false},
                  {r:0,c:4,len:2,dir:'h',color:'silver',tex:'plain',isTarget:false},
                  {r:1,c:3,len:2,dir:'v',color:'green',tex:'plain',isTarget:false},
                  {r:1,c:4,len:2,dir:'h',color:'yellow',tex:'sports',isTarget:false},
                  {r:2,c:4,len:3,dir:'v',color:'purple',tex:'bus',isTarget:false},
                  {r:3,c:0,len:3,dir:'v',color:'blue',tex:'bus',isTarget:false},  
                  {r:3,c:1,len:3,dir:'h',color:'orange',tex:'pickup',isTarget:false},
                  {r:3,c:5,len:3,dir:'v',color:'green',tex:'plain',isTarget:false},
                  {r:4,c:2,len:2,dir:'v',color:'orange',tex:'plain',isTarget:false},
                  {r:5,c:3,len:2,dir:'h',color:'silver',tex:'sports',isTarget:false} 
                ],
                [ 
                  {r:2,c:3,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},   
                  {r:0,c:2,len:3,dir:'h',color:'pink',tex:'pickup',isTarget:false},
                  {r:0,c:5,len:3,dir:'v',color:'black',tex:'bus',isTarget:false},  
                  {r:1,c:2,len:2,dir:'v',color:'blue',tex:'plain',isTarget:false},
                  {r:3,c:0,len:2,dir:'h',color:'green',tex:'sports',isTarget:false},
                  {r:3,c:2,len:2,dir:'v',color:'silver',tex:'plain',isTarget:false},
                  {r:3,c:3,len:2,dir:'v',color:'blue',tex:'bus',isTarget:false},   
                  {r:5,c:2,len:3,dir:'h',color:'orange',tex:'pickup',isTarget:false},
                  {r:4,c:4,len:2,dir:'h',color:'pink',tex:'plain',isTarget:false}, 
                  {r:4,c:0,len:2,dir:'v',color:'green',tex:'plain',isTarget:false},
                  {r:4,c:1,len:2,dir:'v',color:'orange',tex:'plain',isTarget:false},
                ],
                [ 
                  {r:2,c:0,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},   
                  {r:0,c:0,len:2,dir:'h',color:'blue',tex:'plain',isTarget:false},
                  {r:0,c:2,len:2,dir:'v',color:'silver',tex:'plain',isTarget:false},
                  {r:0,c:4,len:2,dir:'h',color:'purple',tex:'sports',isTarget:false},
                  {r:1,c:4,len:2,dir:'h',color:'green',tex:'sports',isTarget:false},
                  {r:2,c:2,len:2,dir:'v',color:'pink',tex:'plain',isTarget:false},
                  {r:3,c:3,len:2,dir:'h',color:'yellow',tex:'sports',isTarget:false},
                  {r:2,c:5,len:2,dir:'v',color:'silver',tex:'plain',isTarget:false},
                  {r:3,c:0,len:3,dir:'v',color:'blue',tex:'bus',isTarget:false},
                  {r:5,c:1,len:2,dir:'h',color:'orange',tex:'plain',isTarget:false},
                  {r:4,c:1,len:2,dir:'h',color:'silver',tex:'sports',isTarget:false},
                  {r:4,c:3,len:2,dir:'v',color:'green',tex:'plain',isTarget:false},
                  {r:4,c:5,len:2,dir:'v',color:'black',tex:'plain',isTarget:false}
                ],
                [
                  {r:2,c:1,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},  
                  {r:0,c:0,len:3,dir:'h',color:'green',tex:'plain',isTarget:false},
                  {r:0,c:3,len:2,dir:'v',color:'blue',tex:'plain',isTarget:false},
                  {r:0,c:4,len:3,dir:'v',color:'orange',tex:'plain',isTarget:false},
                  {r:1,c:0,len:3,dir:'h',color:'blue',tex:'bus',isTarget:false},   
                  {r:3,c:4,len:2,dir:'h',color:'pink',tex:'sports',isTarget:false},
                  {r:3,c:0,len:2,dir:'v',color:'orange',tex:'plain',isTarget:false},
                  {r:4,c:2,len:2,dir:'v',color:'purple',tex:'plain',isTarget:false},
                  {r:4,c:3,len:2,dir:'h',color:'yellow',tex:'sports',isTarget:false},
                  {r:4,c:5,len:2,dir:'v',color:'black',tex:'plain',isTarget:false},
                  {r:2,c:3,len:2,dir:'v',color:'green',tex:'sports',isTarget:false}
                ],
                [ 
                  {r:2,c:0,len:2,dir:'h',color:'red',tex:'plain',isTarget:true},
                  {r:0,c:0,len:2,dir:'v',color:'orange',tex:'plain',isTarget:false},
                  {r:0,c:2,len:3,dir:'v',color:'pink',tex:'bus',isTarget:false},
                  {r:0,c:4,len:2,dir:'h',color:'green',tex:'sports',isTarget:false},
                  {r:1,c:5,len:3,dir:'v',color:'blue',tex:'bus',isTarget:false},
                  {r:4,c:0,len:2,dir:'v',color:'silver',tex:'plain',isTarget:false},
                  {r:3,c:1,len:2,dir:'v',color:'yellow',tex:'plain',isTarget:false},
                  {r:3,c:2,len:3,dir:'h',color:'green',tex:'pickup',isTarget:false},
                  {r:4,c:3,len:2,dir:'v',color:'black',tex:'plain',isTarget:false},
                  {r:5,c:1,len:2,dir:'h',color:'blue',tex:'sports',isTarget:false},
                  {r:4,c:4,len:2,dir:'h',color:'purple',tex:'plain',isTarget:false},
                  {r:1,c:4,len:2,dir:'v',color:'purple',tex:'plain',isTarget:false}
                ]
            ]
        };

        let cars = [], currentTab = "custom", gameStatus = "STOP", act = -1, color = "red";
        let userSteps = 0, initialConfig = [];
        let hintIdx = -1;
        
        const cvs = document.getElementById('gc'), ctx = cvs.getContext('2d');
        const mainBtn = document.getElementById('mainBtn');
        const aiBtn = document.getElementById('aiBtn');
        const hintBtn = document.getElementById('hintBtn');
        const aiTakeBtn = document.getElementById('aiTakeBtn');
        const scorePanel = document.getElementById('scorePanel');
        const aiScoreBox = document.getElementById('aiScoreBox');

        Object.keys(PALETTE).forEach(k => {
            let d = document.createElement('div'); d.className='dot'; d.style.background=PALETTE[k];
            d.onclick=()=>{document.querySelectorAll('.dot').forEach(e=>e.classList.remove('active'));d.classList.add('active');color=k;};
            if(k==='red') d.classList.add('active');
            document.getElementById('cGrid').appendChild(d);
        });

        function switchTab(tab) {
            currentTab = tab; gameStatus = "STOP"; cars = []; initialConfig = []; act = -1; draw();
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tab === 'custom' ? 'tabCustom' : 'tabChallenge').classList.add('active');
            document.getElementById('customTools').style.display = tab === 'custom' ? 'flex' : 'none';
            document.getElementById('challengeTools').style.display = tab === 'challenge' ? 'flex' : 'none';
            scorePanel.style.display = "none"; aiBtn.disabled = true;
            mainBtn.innerText = "START GAME"; mainBtn.style.background = "#2d3436";
            if(tab==='challenge'){renderLevels();document.getElementById('msg').innerText="Select Difficulty & Level";}
            else{document.getElementById('msg').innerText="Design your own level";}
        }

        function renderLevels() {
            const diff = document.getElementById('diffSelect').value;
            const grid = document.getElementById('levelGrid'); grid.innerHTML = "";
            LEVELS[diff].forEach((lvl, idx) => {
                let btn = document.createElement('div'); btn.className = "lvl-btn"; btn.innerText = idx + 1;
                btn.onclick = () => loadLevel(diff, idx, btn);
                grid.appendChild(btn);
            });
        }

        function loadLevel(diff, idx, btnElement) {
            if(gameStatus === "PLAY") return; 
            document.querySelectorAll('.lvl-btn').forEach(b => b.classList.remove('active'));
            if(btnElement) btnElement.classList.add('active');
            cars = JSON.parse(JSON.stringify(LEVELS[diff][idx]));
            draw();
            document.getElementById('lvlInfo').innerText = `Loaded: ${diff.toUpperCase()} - Level ${idx+1}`;
            document.getElementById('msg').innerText = "Click START GAME to begin.";
        }

        function draw() {
            ctx.clearRect(0,0,420,420);
            ctx.strokeStyle = "#e5e9f2"; ctx.lineWidth=1;
            for(let i=0;i<=6;i++) { ctx.beginPath();ctx.moveTo(0,i*C);ctx.lineTo(420,i*C);ctx.stroke(); ctx.beginPath();ctx.moveTo(i*C,0);ctx.lineTo(i*C,420);ctx.stroke(); }
            ctx.strokeStyle = "#ff6b6b"; ctx.lineWidth=6; ctx.lineCap="round"; ctx.beginPath(); ctx.moveTo(420, 2*C+5); ctx.lineTo(420, 3*C-5); ctx.stroke();

            cars.forEach((c, i) => {
                let x=c.c*C, y=c.r*C, w=c.dir==='h'?c.len*C:C, h=c.dir==='v'?c.len*C:C, p=6;
                ctx.fillStyle = PALETTE[c.color]; 
                ctx.beginPath(); 
                ctx.roundRect(x+p, y+p, w-2*p, h-2*p, 8); 
                ctx.fill();
                
                if (i === hintIdx) {
                    ctx.save();
                    ctx.strokeStyle = "#feca57";   // 金色
                    ctx.lineWidth = 6;
                    ctx.setLineDash([8, 4]);       // 虚线更醒目
                    ctx.strokeRect(x+3, y+3, w-6, h-6);
                    ctx.restore();
                }

                ctx.fillStyle = "rgba(0,0,0,0.15)";
                if(c.tex==='plain') { c.dir==='h'?ctx.fillRect(x+15,y+8,w-30,h-16):ctx.fillRect(x+8,y+15,w-16,h-30); }
                else if(c.tex==='sports') { if(c.dir==='h'){ctx.fillRect(x+10,y+8,20,h-16); for(let j=0;j<3;j++)ctx.fillRect(x+w-20-j*8,y+10,4,h-20);} else{ctx.fillRect(x+8,y+10,w-16,20); for(let j=0;j<3;j++)ctx.fillRect(x+10,y+h-20-j*8,w-20,4);} }
                else if(c.tex==='pickup') { ctx.fillStyle="#a0522d"; c.dir==='h'?ctx.fillRect(x+w/3,y+4,2*w/3-4,h-8):ctx.fillRect(x+4,y+h/3,w-8,2*h/3-4); }
                else if(c.tex==='bus') { ctx.strokeStyle="rgba(255,255,255,0.7)"; ctx.lineWidth=2; if(c.dir==='h'){ctx.strokeRect(x+w/3,y+15,20,h-30);ctx.strokeRect(x+2*w/3,y+15,20,h-30);} else{ctx.strokeRect(x+15,y+h/3,w-30,20);ctx.strokeRect(x+15,y+2*h/3,w-30,20);} }

                if(c.isTarget) { ctx.fillStyle="white"; ctx.font="bold 24px Arial"; ctx.textAlign="center"; ctx.textBaseline="middle"; ctx.fillText("★", x+w/2, y+h/2); }
                if(gameStatus==='PLAY' && i===act) { 
                ctx.strokeStyle="#2d3436"; 
                ctx.lineWidth=3; 
                ctx.strokeRect(x+2,y+2,w-4,h-4); }
            });
        }

        cvs.onmousedown = (e) => {
            let b = cvs.getBoundingClientRect(), c = Math.floor((e.clientX-b.left)/C), r = Math.floor((e.clientY-b.top)/C);

            if(gameStatus === "STOP" && currentTab === "custom") {
                let dir = document.querySelector('input[name="dir"]:checked').value;
                let len = parseInt(document.querySelector('input[name="len"]:checked').value);
                let tex = document.querySelector('input[name="tex"]:checked').value;
                let isT = document.getElementById('isTarget').checked;
                if((dir==='h'&&c+len>6)||(dir==='v'&&r+len>6)) return; 

                let newOcc = new Set();
                for(let i=0; i<len; i++) newOcc.add(dir==='h' ? `${r},${c+i}` : `${r+i},${c}`);
                for(let car of cars) {
                    for(let j=0; j<car.len; j++) {
                        let ec = car.dir==='h' ? `${car.r},${car.c+j}` : `${car.r+j},${car.c}`;
                        if(newOcc.has(ec)) { alert("位置已被占用!"); return; }
                    }
                }
                if(isT) cars.forEach(x=>x.isTarget=false);
                cars.push({r,c,len,dir,tex,color,isTarget:isT}); 
                draw();
            } else if (gameStatus === "PLAY") {
                let idx = cars.findIndex(x => x.dir==='h' ? (x.r===r && c>=x.c && c<x.c+x.len) : (x.c===c && r>=x.r && r<x.r+x.len));
                if(idx!==-1) { act=idx; document.getElementById('msg').innerText="Use Arrow Keys"; draw(); }
            }
        };

        window.onkeydown = (e) => {
            if(gameStatus!=='PLAY' || act===-1) return;
            let c = cars[act], dr=0, dc=0;
            if(e.key==="ArrowUp") dr=-1; else if(e.key==="ArrowDown") dr=1; else if(e.key==="ArrowLeft") dc=-1; else if(e.key==="ArrowRight") dc=1; else return;
            if((c.dir==='h'&&dr!==0) || (c.dir==='v'&&dc!==0)) return;

            let nr=c.r+dr, nc=c.c+dc;
            if(nr<0||nc<0||(c.dir==='h'&&nc+c.len>6)||(c.dir==='v'&&nr+c.len>6)) return;
            let coll=false;
            cars.forEach((o,i)=>{ if(i===act)return; let oCells=new Set(); for(let k=0;k<o.len;k++) oCells.add(o.dir==='h'?`${o.r},${o.c+k}`:`${o.r+k},${o.c}`); for(let k=0;k<c.len;k++) { let tr=c.dir==='h'?nr:nr+k, tc=c.dir==='h'?nc+k:nc; if(oCells.has(`${tr},${tc}`)) coll=true; } });

            if(!coll) { 
                c.r=nr; c.c=nc; 
                userSteps++; 
                hintIdx = -1;
                document.getElementById('stepCount').innerText = userSteps;
                draw(); 
                if(c.isTarget && c.c+c.len===6) handleWin(); 
            }
        };

        function handleWin() {
            gameStatus = "WIN";
            document.getElementById('msg').innerText = "Calculating optimal solution...";

            fetch('/solve', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({cars:initialConfig, target_idx:cars.findIndex(x=>x.isTarget)}) })
            .then(r=>r.json()).then(d=>{
                let aiSteps = d.path ? d.path.length : "?";
                alert(`🎉 VICTORY! \n\n👣 Your Steps: ${userSteps}\n🤖 Optimal Steps: ${aiSteps}`);
                mainBtn.click(); // Reset
            });
        }

        mainBtn.onclick = function() {
            if(gameStatus === "STOP") {
                hintBtn.disabled = false;
                aiTakeBtn.disabled = false;

                if(!cars.some(x=>x.isTarget)) return alert("Need a Target Car!");

                gameStatus = "PLAY";
                initialConfig = JSON.parse(JSON.stringify(cars));
                userSteps = 0;
                document.getElementById('stepCount').innerText = "0";

                this.innerText = "STOP & EDIT"; this.style.background = "#ff7675";

                if(currentTab==='custom') document.getElementById('customTools').style.display='none';
                else document.getElementById('challengeTools').style.display='none';

                scorePanel.style.display="block";
                aiScoreBox.style.display="none";
                document.getElementById('userScoreBox').style.display="block";

                aiBtn.disabled=false;
                document.getElementById('msg').innerText = "Game Started! Select a car.";

            } else {
                hintBtn.disabled = true;
                aiTakeBtn.disabled = true;
                gameStatus = "STOP";
                this.innerText = "START GAME"; this.style.background = "#2d3436";

                if(currentTab==='custom') document.getElementById('customTools').style.display='flex';
                else document.getElementById('challengeTools').style.display='flex';

                scorePanel.style.display="none";
                aiBtn.disabled=true;
                aiBtn.innerText="🤖 Show Optimal Solution";
                act=-1;
                hintIdx = -1;

                if(initialConfig.length) cars = JSON.parse(JSON.stringify(initialConfig));
                draw();
                document.getElementById('msg').innerText = "Stopped.";
            }
        };

        hintBtn.onclick = () => {
            if (gameStatus !== "PLAY") return;

            fetch('/solve', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    cars: cars, // ⚠ 当前棋盘
                    target_idx: cars.findIndex(x => x.isTarget)
                })
            })
            .then(r => r.json())
            .then(d => {
                if (!d.path || d.path.length === 0) {
                    alert("No hint available!");
                    return;
                }
        
                let next = d.path[0];
                let car = cars[next.idx];
                let dirHint = "";
                
                if (next.r > car.r) dirHint = "↓ Down";
                else if (next.r < car.r) dirHint = "↑ Up";
                else if (next.c > car.c) dirHint = "→ Right";
                else if (next.c < car.c) dirHint = "← Left";
                
                // 设置高亮索引
                hintIdx = next.idx;
                act = next.idx;     // 顺便选中这辆车
                draw();
                
                // 弹窗提示（更直观）
                alert(
                    `💡 Hint\n\n` +
                    `Move the highlighted car ${dirHint}`
                );
                
                // 底部文字也同步更新
                document.getElementById('msg').innerText =
                    `💡 Hint: Move the highlighted car ${dirHint}`;

            });
        };
        aiTakeBtn.onclick = () => {
            if (gameStatus !== "PLAY") return;
            hintIdx = -1;
            act = -1;
            draw();
        
            gameStatus = "DEMO";
            hintBtn.disabled = true;
            aiTakeBtn.disabled = true;
            document.getElementById('msg').innerText = "🤖 AI is taking over...";
        
            fetch('/solve', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    cars: cars, // ⚠ 当前棋盘
                    target_idx: cars.findIndex(x => x.isTarget)
                })
            })
            .then(r => r.json())
            .then(d => {
                if (!d.path) {
                    alert("No solution found!");
                    gameStatus = "PLAY";
                    return;
                }
        
                let i = 0;
                let timer = setInterval(() => {
                    if (i >= d.path.length) {
                        clearInterval(timer);
                        gameSatus = "STOP";
                        alert("🎉 AI Finished the Puzzle!");
                        mainBtn.click(); // reset
                        return;
                    }
                    let m = d.path[i];
                    cars[m.idx].r = m.r;
                    cars[m.idx].c = m.c;
                    act = m.idx;
                    draw();
                    i++;
                }, 400);
            });
        };

        function undo(){ if(currentTab==='custom' && cars.length) { cars.pop(); draw(); } }
        function clearBoard(){ if(currentTab==='custom') { cars=[]; draw(); } }

        aiBtn.onclick = () => {
            hintIdx = -1;
            act = -1;
            draw();
            
            let btn = aiBtn; btn.innerText="Calculating..."; btn.disabled=true;
            gameStatus = "DEMO";
            cars = JSON.parse(JSON.stringify(initialConfig)); // 回到初始
            draw();

            fetch('/solve', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({cars:initialConfig, target_idx:cars.findIndex(x=>x.isTarget)}) })
            .then(r=>r.json()).then(d=>{
                if(!d.path){ 
                    alert("No Solution Found! (Bug?)"); 
                    gameStatus="PLAY"; aiBtn.disabled=false; btn.innerText="🤖 Show Optimal Solution";
                    return; 
                }

                document.getElementById('userScoreBox').style.display="none";
                aiScoreBox.style.display="block";
                aiScoreBox.style.border="none";
                document.getElementById('aiCount').innerText = d.path.length;
                btn.innerText="Demonstrating...";

                let s=0, t=setInterval(()=>{ 
                    if(s>=d.path.length){ 
                        clearInterval(t); 
                        alert("Demo Finished!"); 
                        mainBtn.click(); return; 
                    } 
                    let m=d.path[s]; cars[m.idx].r=m.r; cars[m.idx].c=m.c; act=m.idx; draw(); s++; 
                }, 400);
            });
        };

        switchTab('custom');
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)


@app.route('/solve', methods=['POST'])
def solve():
    data = request.json
    solver = Solver(6, 6, data['cars'], data['target_idx'])
    path = solver.solve_bfs()
    return jsonify({'path': path})


if __name__ == '__main__':
    PORT = 5000
    try:
        public_url = ngrok.connect(PORT).public_url
        print("\n" + "=" * 50)
        print(f"🚀 成功！公网链接: {public_url}")
        print("=" * 50 + "\n")
    except Exception as e:
        print(f"\n⚠️ Ngrok 失败: {e}")
        print(f"👉 本机访问: http://127.0.0.1:{PORT}\n")

    app.run(port=PORT, debug=False)