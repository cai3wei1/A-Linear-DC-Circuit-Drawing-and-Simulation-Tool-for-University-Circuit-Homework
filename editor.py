import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import uuid
from solver import solve_circuit


GRID = 20


ELEMENT_DEFS = {
    'R':    {'label': '电阻',    'prefix': 'R',     'params': [('value', '阻值(Ω)')], 'pins': [(-40, 0), (40, 0)]},
    'V':    {'label': '电压源',  'prefix': 'V',     'params': [('value', '电压(V)')], 'pins': [(-40, 0), (40, 0)]},
    'I':    {'label': '电流源',  'prefix': 'I',     'params': [('value', '电流(A)')], 'pins': [(-40, 0), (40, 0)]},
    'E':    {'label': 'VCVS',    'prefix': 'E',     'params': [('gain', '增益')],     'pins': [(-40, 0), (40, 0)], 'ctrl_v': True},
    'G':    {'label': 'VCCS',    'prefix': 'G',     'params': [('gain', '跨导(S)')],  'pins': [(-40, 0), (40, 0)], 'ctrl_v': True},
    'H':    {'label': 'CCVS',    'prefix': 'H',     'params': [('gain', '增益(Ω)')],  'pins': [(-40, 0), (40, 0)], 'ctrl_i': True},
    'F':    {'label': 'CCCS',    'prefix': 'F',     'params': [('gain', '增益')],     'pins': [(-40, 0), (40, 0)], 'ctrl_i': True},
    'VMEAS':{'label': '0V探针',  'prefix': 'Vmeas', 'params': [],                     'pins': [(-40, 0), (40, 0)]},
    'NODE': {'label': '节点',    'prefix': 'N',     'params': [],                     'pins': [(0, 0)]},
    'GND':  {'label': '地',      'prefix': 'GND',   'params': [],                     'pins': [(0, 0)]},
}


class GPin:
    def __init__(self, elem, dx, dy):
        self.elem = elem
        self.dx = dx
        self.dy = dy

    def world_pos(self):
        dx, dy = self.dx, self.dy
        r = self.elem.rotation
        if r == 90: dx, dy = -dy, dx
        elif r == 180: dx, dy = -dx, -dy
        elif r == 270: dx, dy = dy, -dx
        return (self.elem.x + dx, self.elem.y + dy)


class GElement:
    def __init__(self, editor, etype, x, y, name=None, params=None, ctrl_name='', rotation=0, elem_id=None):
        self.editor = editor
        self.id = elem_id if elem_id else uuid.uuid4().hex
        self.etype = etype
        self.x = x
        self.y = y
        self.rotation = rotation
        self.params = params if params is not None else {p[0]: 1.0 for p in ELEMENT_DEFS[etype]['params']}
        self.ctrl_name = ctrl_name
        self.name = name if name else self._gen_name()
        self.pins = [GPin(self, dx, dy) for dx, dy in ELEMENT_DEFS[etype]['pins']]
        self.canvas_ids = []
        self.draw()

    def _gen_name(self):
        prefix = ELEMENT_DEFS[self.etype]['prefix']
        if not prefix or prefix in ('N', 'GND'):
            return ''
        n = 1
        existing = {e.name for e in self.editor.elements}
        while f"{prefix}{n}" in existing:
            n += 1
        return f"{prefix}{n}"

    def draw(self):
        c = self.editor.canvas
        for cid in self.canvas_ids:
            c.delete(cid)
        self.canvas_ids = []
        tag = f"e{self.id}"
        x, y, rot = self.x, self.y, self.rotation

        def rp(px, py):
            if rot == 90: px, py = -py, px
            elif rot == 180: px, py = -px, -py
            elif rot == 270: px, py = py, -px
            return (x + px, y + py)

        def line(x1, y1, x2, y2, **kw):
            self.canvas_ids.append(c.create_line(*rp(x1, y1), *rp(x2, y2), **kw, tags=tag))

        def rect(x1, y1, x2, y2, **kw):
            p1, p2 = rp(x1, y1), rp(x2, y2)
            self.canvas_ids.append(c.create_rectangle(
                min(p1[0], p2[0]), min(p1[1], p2[1]),
                max(p1[0], p2[0]), max(p1[1], p2[1]), **kw, tags=tag))

        def oval(x1, y1, x2, y2, **kw):
            p1, p2 = rp(x1, y1), rp(x2, y2)
            self.canvas_ids.append(c.create_oval(
                min(p1[0], p2[0]), min(p1[1], p2[1]),
                max(p1[0], p2[0]), max(p1[1], p2[1]), **kw, tags=tag))

        def text(s, px, py, **kw):
            self.canvas_ids.append(c.create_text(*rp(px, py), text=s, **kw, tags=tag))

        et = self.etype

        if et == 'R':
            line(-40, 0, -30, 0, width=2)
            line(30, 0, 40, 0, width=2)
            rect(-30, -10, 30, 10, outline='blue', width=2)
            if self.name: text(self.name, 0, -22, fill='darkblue')
            text(f"{self.params.get('value', 1)}", 0, 22, fill='darkred')

        elif et in ('V', 'VMEAS'):
            line(-40, 0, -22, 0, width=2)
            line(22, 0, 40, 0, width=2)
            oval(-22, -22, 22, 22, outline='blue', width=2)
            line(-10, 0, 10, 0, width=2)
            line(0, -10, 0, 10, width=2)
            # 电压源正负号（圆圈外部）
            text('+', -30, -28, fill='red', font=('', 10, 'bold'))
            text('-', 30, 28, fill='blue', font=('', 10, 'bold'))
            if self.name: text(self.name, 0, -32, fill='darkblue')
            if et == 'V':
                text(f"{self.params.get('value', 5)}V", 0, 32, fill='darkred')
            else:
                text("0V", 0, 32, fill='orange')

        elif et == 'I':
            line(-40, 0, -22, 0, width=2)
            line(22, 0, 40, 0, width=2)
            oval(-22, -22, 22, 22, outline='blue', width=2)
            # 电流源内部箭头
            line(10, 0, -10, 0, width=2)
            line(10, 0, 4, -5, width=2)
            line(10, 0, 4, 5, width=2)
            if self.name: text(self.name, 0, -32, fill='darkblue')
            text(f"{self.params.get('value', 0.1)}A", 0, 32, fill='darkred')

        elif et in ('E', 'G', 'H', 'F'):
            line(-40, 0, -22, 0, width=2)
            line(22, 0, 40, 0, width=2)
            pts = [rp(0, -22), rp(22, 0), rp(0, 22), rp(-22, 0)]
            flat = [p for pt in pts for p in pt]
            self.canvas_ids.append(c.create_polygon(*flat, outline='blue', fill='', width=2, tags=tag))

            # 根据类型添加符号
            if et in ('E', 'H'):
                # 受控电压源（VCVS/CCVS）：加正负号
                text('+', -30, -28, fill='red', font=('', 10, 'bold'))
                text('-', 30, 28, fill='blue', font=('', 10, 'bold'))
            elif et in ('G', 'F'):
                # 受控电流源（VCCS/CCCS）：加电流方向箭头
                line(10, 0, -10, 0, width=2)
                line(10, 0, 4, -5, width=2)
                line(10, 0, 4, 5, width=2)

            if self.name: 
                text(self.name, 0, -32, fill='darkblue')
            text(f"{self.params.get('gain', 1)}", 0, 32, fill='darkred')
            if self.ctrl_name:
                text(f"c:{self.ctrl_name}", 0, 46, fill='green')

        elif et == 'NODE':
            r = 4
            oval(-r, -r, r, r, fill='black', outline='black')

        elif et == 'GND':
            line(0, 0, 0, 15, width=2)
            line(-15, 15, 15, 15, width=2)
            line(-10, 20, 10, 20, width=2)
            line(-5, 25, 5, 25, width=2)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.etype,
            'x': self.x,
            'y': self.y,
            'rotation': self.rotation,
            'name': self.name,
            'params': self.params,
            'ctrl_name': self.ctrl_name
        }


class GWire:
    def __init__(self, editor, pin_a, pin_b, wire_id=None):
        self.editor = editor
        self.id = wire_id if wire_id else uuid.uuid4().hex
        self.a = pin_a
        self.b = pin_b
        self.canvas_id = None
        self.draw()

    def draw(self, selected=False):
        if self.canvas_id:
            self.editor.canvas.delete(self.canvas_id)
        x1, y1 = self.a.world_pos()
        x2, y2 = self.b.world_pos()
        color = 'blue' if selected else 'black'
        self.canvas_id = self.editor.canvas.create_line(x1, y1, x2, y2, width=2, fill=color)

    def distance_to_point(self, x, y):
        x1, y1 = self.a.world_pos()
        x2, y2 = self.b.world_pos()
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
        t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        px, py = x1 + t * dx, y1 + t * dy
        return ((x - px) ** 2 + (y - py) ** 2) ** 0.5

    def to_dict(self):
        return {
            'id': self.id,
            'a_elem_id': self.a.elem.id,
            'a_pin_idx': self.a.elem.pins.index(self.a),
            'b_elem_id': self.b.elem.id,
            'b_pin_idx': self.b.elem.pins.index(self.b)
        }


class CircuitEditor:
    def __init__(self, root):
        self.root = root
        root.title("电路绘制编辑器")
        root.geometry("1200x750")

        self.elements = []
        self.wires = []
        self.selected = None
        self.mode = 'select'
        self.subtype = None
        self.wire_start = None
        self.temp_line_id = None
        self.drag_offset = None
        self.result_labels = []

        self.undo_stack = []
        self.redo_stack = []
        self.max_undo = 10

        self._build_ui()
        root.after(50, self.draw_grid)
        
        # 绑定快捷键
        root.bind('<Control-z>', lambda e: self.undo())
        root.bind('<Control-y>', lambda e: self.redo())

    def _build_ui(self):
        toolbar = tk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        for et in ['R', 'V', 'I', 'E', 'G', 'H', 'F', 'VMEAS', 'NODE', 'GND']:
            tk.Button(toolbar, text=ELEMENT_DEFS[et]['label'], width=7,
                      command=lambda t=et: self.set_mode('place', t)).pack(side=tk.LEFT, padx=1, pady=2)

        ttk.Separator(toolbar, orient='vertical').pack(side=tk.LEFT, fill='y', padx=5)
        tk.Button(toolbar, text="选择", command=lambda: self.set_mode('select')).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="连线", command=lambda: self.set_mode('wire')).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="旋转", command=self.rotate_selected).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="删除", command=self.delete_selected).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient='vertical').pack(side=tk.LEFT, fill='y', padx=5)
        tk.Button(toolbar, text="撤销", command=self.undo).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="重做", command=self.redo).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient='vertical').pack(side=tk.LEFT, fill='y', padx=5)
        tk.Button(toolbar, text="求解", command=self.solve_and_display, bg='lightgreen').pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="清除结果", command=self.clear_results).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="导出网表", command=self.export_netlist).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="清空", command=self.clear_all).pack(side=tk.LEFT, padx=2)

        main = tk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(main, bg='white', width=950, height=650)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Motion>', self.on_motion)
        self.canvas.bind('<Configure>', lambda e: self.draw_grid())

        self.prop_frame = tk.Frame(main, width=230, bg='#f0f0f0', relief=tk.SUNKEN, borderwidth=1)
        self.prop_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.prop_frame.pack_propagate(False)
        self.refresh_properties()

        self.status = tk.Label(self.root, text="就绪", anchor='w', relief=tk.SUNKEN)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        self.root.bind('<Escape>', lambda e: self.set_mode('select'))
        self.root.bind('<Delete>', lambda e: self.delete_selected())

    def draw_grid(self):
        self.canvas.delete('grid')
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            return
        for x in range(0, w, GRID):
            self.canvas.create_line(x, 0, x, h, fill='#eeeeee', tags='grid')
        for y in range(0, h, GRID):
            self.canvas.create_line(0, y, w, y, fill='#eeeeee', tags='grid')
        self.canvas.tag_lower('grid')

    def set_mode(self, mode, subtype=None):
        self.mode = mode
        self.subtype = subtype
        if mode == 'place':
            self.status.config(text=f"点击画布放置 {ELEMENT_DEFS[subtype]['label']}")
        elif mode == 'wire':
            self.status.config(text="点击引脚开始连线")
        else:
            self.status.config(text="选择/移动模式")
            self.wire_start = None
            if self.temp_line_id:
                self.canvas.delete(self.temp_line_id)
                self.temp_line_id = None

    def on_motion(self, event):
        gx = round(event.x / GRID) * GRID
        gy = round(event.y / GRID) * GRID
        self.status.config(text=f"坐标 ({gx}, {gy})")

    def find_pin_near(self, x, y, radius=12):
        best, best_d = None, radius * radius
        for el in self.elements:
            for pin in el.pins:
                px, py = pin.world_pos()
                d = (px - x) ** 2 + (py - y) ** 2
                if d < best_d:
                    best_d, best = d, pin
        return best

    def find_elem_near(self, x, y):
        for el in reversed(self.elements):
            if el.etype == 'GND':
                if abs(el.x - x) < 15 and el.y - 5 <= y <= el.y + 30:
                    return el
            elif el.etype == 'NODE':
                if abs(el.x - x) < 10 and abs(el.y - y) < 10:
                    return el
            else:
                for pin in el.pins:
                    px, py = pin.world_pos()
                    if (px - x) ** 2 + (py - y) ** 2 <= 144:
                        return el
                if (el.x - x) ** 2 + (el.y - y) ** 2 <= 625:
                    return el
                if abs(el.x - x) < 40 and abs(el.y - y) < 15:
                    return el
        return None

    def find_wire_near(self, x, y):
        for w in reversed(self.wires):
            if w.distance_to_point(x, y) < 8:
                return w
        return None

    # ------------------ 状态保存与撤销/重做 ------------------
    def save_state(self):
        if len(self.undo_stack) >= self.max_undo:
            self.undo_stack.pop(0)
        self.undo_stack.append(self.get_state())
        self.redo_stack.clear()

    def get_state(self):
        return {
            'elements': [el.to_dict() for el in self.elements],
            'wires': [w.to_dict() for w in self.wires]
        }

    def load_state(self, state):
        # 清理画布
        for el in self.elements:
            for cid in el.canvas_ids:
                self.canvas.delete(cid)
        for w in self.wires:
            if w.canvas_id:
                self.canvas.delete(w.canvas_id)
        self.elements = []
        self.wires = []
        self.selected = None
        self.clear_results()

        # 重建元件
        elem_map = {}
        for ed in state['elements']:
            el = GElement(self, ed['type'], ed['x'], ed['y'],
                          name=ed['name'], params=ed['params'],
                          ctrl_name=ed['ctrl_name'], rotation=ed['rotation'],
                          elem_id=ed['id'])
            self.elements.append(el)
            elem_map[el.id] = el

        # 重建导线
        for wd in state['wires']:
            el_a = elem_map.get(wd['a_elem_id'])
            el_b = elem_map.get(wd['b_elem_id'])
            if el_a and el_b:
                pin_a = el_a.pins[wd['a_pin_idx']]
                pin_b = el_b.pins[wd['b_pin_idx']]
                self.wires.append(GWire(self, pin_a, pin_b, wire_id=wd['id']))

        self.refresh_properties()

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(self.get_state())
        state = self.undo_stack.pop()
        self.load_state(state)
        self.status.config(text="撤销完成")

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(self.get_state())
        state = self.redo_stack.pop()
        self.load_state(state)
        self.status.config(text="重做完成")

    # ------------------ 交互逻辑 ------------------
    def on_click(self, event):
        x = round(event.x / GRID) * GRID
        y = round(event.y / GRID) * GRID

        if self.mode == 'place':
            self.save_state()
            el = GElement(self, self.subtype, x, y)
            self.elements.append(el)
            self.set_mode('select')
            self.select_element(el)
            self.clear_results()
            return

        if self.mode == 'wire':
            pin = self.find_pin_near(event.x, event.y)
            if pin:
                if self.wire_start is None:
                    self.wire_start = pin
                    self.status.config(text="起点已选，点击终点引脚")
                else:
                    if pin is not self.wire_start:
                        exists = any(
                            (w.a is self.wire_start and w.b is pin) or
                            (w.b is self.wire_start and w.a is pin)
                            for w in self.wires
                        )
                        if not exists:
                            self.save_state()
                            self.wires.append(GWire(self, self.wire_start, pin))
                            self.clear_results()
                    self.wire_start = None
                    if self.temp_line_id:
                        self.canvas.delete(self.temp_line_id)
                        self.temp_line_id = None
                    self.status.config(text="连线模式：点击引脚开始")
            else:
                self.wire_start = None
                if self.temp_line_id:
                    self.canvas.delete(self.temp_line_id)
                    self.temp_line_id = None
            return

        # 选择模式
        el = self.find_elem_near(event.x, event.y)
        if el:
            self.select_element(el)
            self.drag_offset = (el.x - event.x, el.y - event.y)
        else:
            wire = self.find_wire_near(event.x, event.y)
            if wire:
                self.select_element(wire)
            else:
                self.select_element(None)

    def on_drag(self, event):
        if self.mode == 'wire' and self.wire_start:
            if self.temp_line_id:
                self.canvas.delete(self.temp_line_id)
            x1, y1 = self.wire_start.world_pos()
            self.temp_line_id = self.canvas.create_line(x1, y1, event.x, event.y, dash=(4, 2), fill='green')
            return

        if self.mode == 'select' and isinstance(self.selected, GElement) and self.drag_offset:
            dx, dy = self.drag_offset
            nx = round((event.x + dx) / GRID) * GRID
            ny = round((event.y + dy) / GRID) * GRID
            self.selected.x = nx
            self.selected.y = ny
            self.selected.draw()
            for w in self.wires:
                w.draw()
            self.clear_results()

    def on_release(self, event):
        if self.mode == 'select' and isinstance(self.selected, GElement) and self.drag_offset:
            self.save_state()
        self.drag_offset = None

    def select_element(self, el):
        if isinstance(self.selected, GWire):
            self.selected.draw(selected=False)
        self.selected = el
        if isinstance(self.selected, GWire):
            self.selected.draw(selected=True)
        self.refresh_properties()

    def refresh_properties(self):
        for w in self.prop_frame.winfo_children():
            w.destroy()
        if not self.selected:
            tk.Label(self.prop_frame, text="未选中元件", bg='#f0f0f0').pack(pady=20)
            return
        if isinstance(self.selected, GWire):
            tk.Label(self.prop_frame, text="[导线]", bg='#f0f0f0', font=('', 11, 'bold')).pack(pady=5)
            tk.Label(self.prop_frame, text="按 Delete 键可删除导线", bg='#f0f0f0').pack(pady=5)
            return

        el = self.selected
        tk.Label(self.prop_frame, text=f"[{ELEMENT_DEFS[el.etype]['label']}]",
                 bg='#f0f0f0', font=('', 11, 'bold')).pack(pady=5)

        if el.etype not in ('NODE', 'GND'):
            tk.Label(self.prop_frame, text="名称:", bg='#f0f0f0').pack(anchor='w', padx=5)
            nv = tk.StringVar(value=el.name)
            entry_name = tk.Entry(self.prop_frame, textvariable=nv)
            entry_name.pack(fill='x', padx=5)

            def upd_name(*a):
                el.name = nv.get()
                el.draw()
            nv.trace_add('write', upd_name)
            entry_name.bind('<FocusOut>', lambda e: self.save_state())
            entry_name.bind('<Return>', lambda e: self.save_state())

        for pname, plabel in ELEMENT_DEFS[el.etype]['params']:
            tk.Label(self.prop_frame, text=plabel + ":", bg='#f0f0f0').pack(anchor='w', padx=5, pady=(8, 0))
            vv = tk.StringVar(value=str(el.params.get(pname, 1.0)))
            entry_param = tk.Entry(self.prop_frame, textvariable=vv)
            entry_param.pack(fill='x', padx=5)

            def mk_cb(pn, var):
                def cb(*a):
                    try:
                        el.params[pn] = float(var.get())
                        el.draw()
                        self.clear_results()
                    except ValueError:
                        pass
                return cb
            vv.trace_add('write', mk_cb(pname, vv))
            entry_param.bind('<FocusOut>', lambda e: self.save_state())
            entry_param.bind('<Return>', lambda e: self.save_state())

        # ---------- 控制源设置 ----------
        if ELEMENT_DEFS[el.etype].get('ctrl_v') or ELEMENT_DEFS[el.etype].get('ctrl_i'):
            if el.etype in ('E', 'G'):
                # 电压控制型：可以选择任意两端元件（电阻、电压源、电流源、探针等）
                tk.Label(self.prop_frame, text="控制元件:", bg='#f0f0f0').pack(anchor='w', padx=5, pady=(10, 0))
                names = [e.name for e in self.elements
                         if e is not el and len(e.pins) >= 2 and e.etype not in ('NODE', 'GND')]
                cv = tk.StringVar(value=el.ctrl_name)
                combo = ttk.Combobox(self.prop_frame, textvariable=cv, values=names, state='readonly')
                combo.pack(fill='x', padx=5)

                def cb_ctrl_v(*a):
                    el.ctrl_name = cv.get()
                    el.draw()
                    self.clear_results()
                    self.save_state()
                cv.trace_add('write', cb_ctrl_v)
            else:
                # 电流控制型（H、F）：只能选择电压源或0V探针
                tk.Label(self.prop_frame, text="控制电压源:", bg='#f0f0f0').pack(anchor='w', padx=5, pady=(10, 0))
                names = [e.name for e in self.elements
                         if e.etype in ('V', 'VMEAS') and e.name and e is not el]
                cv = tk.StringVar(value=el.ctrl_name)
                combo = ttk.Combobox(self.prop_frame, textvariable=cv, values=names, state='readonly')
                combo.pack(fill='x', padx=5)

                def cb_ctrl_i(*a):
                    el.ctrl_name = cv.get()
                    el.draw()
                    self.clear_results()
                    self.save_state()
                cv.trace_add('write', cb_ctrl_i)


    def rotate_selected(self):
        if isinstance(self.selected, GElement):
            self.save_state()
            self.selected.rotation = (self.selected.rotation + 90) % 360
            self.selected.draw()
            for w in self.wires:
                w.draw()
            self.clear_results()

    def delete_selected(self):
        if not self.selected:
            return
        self.save_state()
        if isinstance(self.selected, GWire):
            wire = self.selected
            if wire.canvas_id:
                self.canvas.delete(wire.canvas_id)
            self.wires.remove(wire)
            self.selected = None
            self.refresh_properties()
            self.clear_results()
            return

        el = self.selected
        new_wires = []
        for w in self.wires:
            if w.a.elem is el or w.b.elem is el:
                if w.canvas_id:
                    self.canvas.delete(w.canvas_id)
            else:
                new_wires.append(w)
        self.wires = new_wires
        for cid in el.canvas_ids:
            self.canvas.delete(cid)
        self.elements.remove(el)
        self.selected = None
        self.refresh_properties()
        self.clear_results()

    def clear_results(self):
        for lid in self.result_labels:
            self.canvas.delete(lid)
        self.result_labels = []

    def clear_all(self):
        if not messagebox.askyesno("确认", "清空所有元件？"):
            return
        self.save_state()
        for el in self.elements:
            for cid in el.canvas_ids:
                self.canvas.delete(cid)
        for w in self.wires:
            if w.canvas_id:
                self.canvas.delete(w.canvas_id)
        self.elements = []
        self.wires = []
        self.selected = None
        self.clear_results()
        self.refresh_properties()

    # ------------------ 节点计算 ------------------
    def compute_nets(self):
        parent = {}

        def find(p):
            while parent[p] is not p:
                parent[p] = parent[parent[p]]
                p = parent[p]
            return p

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra is not rb:
                parent[ra] = rb

        all_pins = []
        for el in self.elements:
            for pin in el.pins:
                parent[pin] = pin
                all_pins.append(pin)

        for w in self.wires:
            if w.a in parent and w.b in parent:
                union(w.a, w.b)

        gnd_roots = set()
        for el in self.elements:
            if el.etype == 'GND':
                for pin in el.pins:
                    gnd_roots.add(find(pin))

        net_id = {}
        for r in gnd_roots:
            net_id[r] = 0
        next_id = 1
        for pin in all_pins:
            r = find(pin)
            if r not in net_id:
                net_id[r] = next_id
                next_id += 1

        return {pin: net_id[find(pin)] for pin in all_pins}

    def build_circuit(self):
        has_gnd = any(el.etype == 'GND' for el in self.elements)
        if not has_gnd:
            raise ValueError("电路中没有接地元件")

        pin_to_node = self.compute_nets()
        elements = []
        for el in self.elements:
            if el.etype in ('NODE', 'GND'):
                continue
            if len(el.pins) < 2:
                continue
            n1 = pin_to_node[el.pins[0]]
            n2 = pin_to_node[el.pins[1]]
            name = el.name
            if el.etype == 'R':
                elements.append({'type': 'R', 'name': name, 'n1': n1, 'n2': n2, 'value': el.params['value']})
            elif el.etype == 'V':
                elements.append({'type': 'V', 'name': name, 'n1': n1, 'n2': n2, 'value': el.params['value']})
            elif el.etype == 'VMEAS':
                elements.append({'type': 'V', 'name': name, 'n1': n1, 'n2': n2, 'value': 0.0})
            elif el.etype == 'I':
                elements.append({'type': 'I', 'name': name, 'n1': n1, 'n2': n2, 'value': el.params['value']})
            elif el.etype in ('E', 'G'):
                # 电压控制型：控制量可以是任意两端元件的端电压（包括电阻、电压源、电流源等）
                ctrl_el = next((e for e in self.elements if e.name == el.ctrl_name), None)
                if ctrl_el is None or ctrl_el is el or len(ctrl_el.pins) < 2:
                    raise ValueError(f"{name} 未指定有效控制元件")
                nc1 = pin_to_node[ctrl_el.pins[0]]
                nc2 = pin_to_node[ctrl_el.pins[1]]
                if el.etype == 'E':
                    elements.append({'type': 'E', 'name': name, 'n1': n1, 'n2': n2,
                                     'nc1': nc1, 'nc2': nc2, 'gain': el.params['gain']})
                else:
                    elements.append({'type': 'G', 'name': name, 'n1': n1, 'n2': n2,
                                     'nc1': nc1, 'nc2': nc2, 'gm': el.params['gain']})
            elif el.etype in ('H', 'F'):
                # 电流控制型：控制量必须是电压源支路（含0V探针）的电流
                ctrl_el = next((e for e in self.elements if e.name == el.ctrl_name), None)
                if ctrl_el is None or ctrl_el.etype not in ('V', 'VMEAS'):
                    raise ValueError(f"{name} 未指定有效控制电压源")
                if el.etype == 'H':
                    elements.append({'type': 'H', 'name': name, 'n1': n1, 'n2': n2,
                                     'vctrl': el.ctrl_name, 'gain': el.params['gain']})
                else:
                    elements.append({'type': 'F', 'name': name, 'n1': n1, 'n2': n2,
                                     'vctrl': el.ctrl_name, 'gain': el.params['gain']})

        vsource_names = [e['name'] for e in elements if e['type'] in ('V', 'E', 'H')]
        node_set = {0}
        for e in elements:
            for k in ('n1', 'n2', 'nc1', 'nc2'):
                if k in e:
                    node_set.add(e[k])
        return elements, node_set, vsource_names, pin_to_node
    
    # ------------------ 求解与显示 ------------------
    def solve_and_display(self):
        self.clear_results()
        try:
            elements, node_set, vsource_names, pin_to_node = self.build_circuit()
            if not elements:
                messagebox.showwarning("警告", "电路为空")
                return
            node_v, vsrc_i = solve_circuit(elements, node_set, vsource_names)
        except Exception as e:
            messagebox.showerror("求解失败", str(e))
            return

        shown = set()
        for pin, nid in pin_to_node.items():
            if nid in shown or nid == 0:
                continue
            x, y = pin.world_pos()
            self.result_labels.append(
                self.canvas.create_text(x + 6, y - 20, text=f"{node_v[nid]:.3f}V",
                                        fill='red', font=('', 9, 'bold'), anchor='w'))
            shown.add(nid)

        for el in self.elements:
            if el.etype in ('NODE', 'GND'):
                continue
            cur = self.compute_element_current(el, node_v, vsrc_i, elements)
            if cur is None:
                continue
            self.result_labels.append(
                self.canvas.create_text(el.x, el.y + 50,
                                        text=f"I={cur:.3f}A",
                                        fill='purple', font=('', 9)))
        self.status.config(text="求解完成")

    def compute_element_current(self, el, node_v, vsrc_i, elements):
        for e in elements:
            if e['name'] != el.name:
                continue
            t = e['type']
            if t == 'R':
                return (node_v[e['n1']] - node_v[e['n2']]) / e['value']
            elif t in ('V', 'E', 'H'):
                return vsrc_i.get(e['name'], 0.0)
            elif t == 'I':
                return e['value']
            elif t == 'G':
                return e['gm'] * (node_v[e['nc1']] - node_v[e['nc2']])
            elif t == 'F':
                return e['gain'] * vsrc_i.get(e['vctrl'], 0.0)
        return None

    # ------------------ 导出 ------------------
    def export_netlist(self):
        try:
            elements, node_set, vsource_names, _ = self.build_circuit()
        except Exception as e:
            messagebox.showerror("导出失败", str(e))
            return

        fn = filedialog.asksaveasfilename(defaultextension=".txt",
                                          filetypes=[("网表文件", "*.txt")])
        if not fn:
            return

        lines = ["# 由电路绘制编辑器自动生成"]
        for e in elements:
            t = e['type']
            if t == 'R':
                lines.append(f"{e['name']} {e['n1']} {e['n2']} {e['value']}")
            elif t == 'V':
                lines.append(f"{e['name']} {e['n1']} {e['n2']} {e['value']}")
            elif t == 'I':
                lines.append(f"{e['name']} {e['n1']} {e['n2']} {e['value']}")
            elif t == 'E':
                lines.append(f"{e['name']} {e['n1']} {e['n2']} {e['nc1']} {e['nc2']} {e['gain']}")
            elif t == 'G':
                lines.append(f"{e['name']} {e['n1']} {e['n2']} {e['nc1']} {e['nc2']} {e['gm']}")
            elif t == 'H':
                lines.append(f"{e['name']} {e['n1']} {e['n2']} {e['vctrl']} {e['gain']}")
            elif t == 'F':
                lines.append(f"{e['name']} {e['n1']} {e['n2']} {e['vctrl']} {e['gain']}")

        with open(fn, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        self.status.config(text=f"已导出: {fn}")