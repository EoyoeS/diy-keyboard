import tkinter as tk
from tkinter import ttk, filedialog
import json
from threading import Thread
import ctypes
import os

import keyboard

SETTING_FILE = 'setting.json'
ICON_FILE = 'keyboard_icon.ico'
TITLE = 'DIY-KeyBoard'

LAYOUT = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['a', '0', 'b'],
]

SCAN_CODE = {
    '1': 0x4F,
    '2': 0x50,
    '3': 0x51,
    '4': 0x4B,
    '5': 0x4C,
    '6': 0x4D,
    '7': 0x47,
    '8': 0x48,
    '9': 0x49,
    '0': 0x52,
}

DEFAULT_MAP = {'launch': False, 'map': {}}
DEFAULT_INFO = '点击按钮编辑快捷键。\n左键点击：键位映射；右键点击：打开文件；滚轮点击：重置。'


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        # 告诉操作系统使用程序自身的dpi适配
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        # 获取屏幕的缩放因子
        ScaleFactor = ctypes.windll.shcore.GetScaleFactorForDevice(0)
        # 设置程序缩放
        self.tk.call('tk', 'scaling', ScaleFactor / 96)
        self.iconbitmap(ICON_FILE)  # 设置图标
        self.title(TITLE)
        self.geometry('800x700')
        self.resizable(False, False)
        self.setting = self.init_setting()
        self.key_map = self.setting['map']
        self.info = self.init_info()
        self.buttons = self.init_buttons()
        self.changing = False
        self.reset = self.init_reset()

    def init_setting(self):
        """初始化快捷键映射"""
        self.setting_file = SETTING_FILE
        try:
            with open(self.setting_file, 'r') as f:
                setting = json.load(f)
        except FileNotFoundError:
            setting = DEFAULT_MAP
            with open(self.setting_file, 'w') as f:
                json.dump(setting, f, indent=4)
        self.launch_var = tk.BooleanVar(value=setting['launch'])
        self.set = ttk.Checkbutton(
            self,
            text='已开启' if self.launch_var.get() else '未开启',
            variable=self.launch_var,
            onvalue=True,
            offvalue=False,
            command=self.change_launch,
            padding=20,
        )
        self.set.pack()
        return setting

    def init_info(self):
        info = tk.StringVar()
        info.set(DEFAULT_INFO)
        label = ttk.Label(
            self,
            textvariable=info,
            justify=tk.CENTER,
        )
        label.pack()
        return info

    def change_launch(self):
        """修改开关"""
        self.setting['launch'] = self.launch_var.get()
        with open(self.setting_file, 'w') as f:
            json.dump(self.setting, f, indent=4)
        if not self.launch_var.get():
            self.set.config(text='未开启')
            for k, map_ in self.key_map.items():
                keyboard.unhook(SCAN_CODE.get(k, k))
        else:
            self.set.config(text='已开启')
            for k, map_ in self.key_map.items():
                if map_['type'] == 'hotkey':
                    keyboard.remap_key(SCAN_CODE.get(k, k), map_['value'])
                elif map_['type'] == 'open':
                    keyboard.on_press_key(
                        SCAN_CODE.get(k, k), self.open_file, suppress=True
                    )

    def init_buttons(self):
        """初始化按钮"""
        self.button_frame = ttk.Frame(self, borderwidth=30)
        self.button_frame.pack()
        buttons = []
        for r in range(4):
            line = []
            for c in range(3):
                map_ = self.key_map.get(LAYOUT[r][c])
                if map_ is None:
                    text = LAYOUT[r][c]
                else:
                    if map_['type'] == 'hotkey':
                        text = map_['value']
                        keyboard.remap_key(
                            SCAN_CODE.get(LAYOUT[r][c], LAYOUT[r][c]), map_['value']
                        )
                    elif map_['type'] == 'open':
                        text = '打开文件'
                        keyboard.on_press_key(
                            SCAN_CODE.get(LAYOUT[r][c], LAYOUT[r][c]),
                            self.open_file,
                            suppress=True,
                        )
                button = ttk.Button(
                    self.button_frame,
                    text=text,
                    name='bt' + LAYOUT[r][c],
                    padding=25,
                )
                button.bind('<ButtonRelease-1>', self.change_hotkey)
                button.bind('<Button-3>', self.button_pressed)
                button.bind('<ButtonRelease-3>', self.change_open)
                # 右键弹起时
                button.bind('<Button-2>', self.button_pressed)
                button.bind('<ButtonRelease-2>', self.clear_key_map)
                button.bind('<Enter>', self.button_enter)
                button.bind('<Leave>', self.button_leave)
                button.grid(row=r, column=c, padx=10, pady=10, sticky=tk.NSEW)
                line.append(button)
            buttons.append(line)
        return buttons

    def change_hotkey(self, event: tk.Event):
        """修改快捷键"""
        if not self.check_launch() or self.changing:
            return
        t = Thread(target=self.change_hotkey_button, args=(event.widget,))
        t.start()

    def change_hotkey_button(self, button: ttk.Button):
        """记录快捷键"""
        self.changing = True
        self.set.state(['disabled'])  # 先禁用开关
        self.reset.state(['disabled'])  # 禁用重置按钮
        # 先取消映射
        self.clear_button_key_map(button)
        button['text'] = '按下快捷键'  # 提示按下快捷键
        new_hotkey = keyboard.read_hotkey(suppress=False).lower()
        button['text'] = new_hotkey
        new_hotkey = new_hotkey.replace(',', 'comma')  # 防止逗号在解析时被当做分隔符
        # 如果新的快捷键不是原按键，就映射
        physical_key = button.winfo_name()[2:]
        if new_hotkey != physical_key:
            keyboard.remap_key(SCAN_CODE.get(physical_key, physical_key), new_hotkey)
            self.key_map[physical_key] = {'type': 'hotkey', 'value': new_hotkey}
            with open(self.setting_file, 'w') as f:
                json.dump(self.setting, f, indent=4)
        self.info_button(physical_key)
        self.changing = False
        self.reset.state(['!disabled'])  # 恢复重置按钮
        self.set.state(['!disabled'])  # 恢复开关

    def change_open(self, event: tk.Event):
        """修改打开文件"""
        # 按钮弹起动画
        button = event.widget
        button.state(['!pressed'])
        if not self.check_launch() or self.changing:
            return
        self.changing = True
        filename = filedialog.askopenfilename()
        if filename:
            button['text'] = '打开文件'
            physical_key = button.winfo_name()[2:]
            keyboard.on_press_key(
                SCAN_CODE.get(physical_key, physical_key), self.open_file, suppress=True
            )
            self.key_map[physical_key] = {'type': 'open', 'value': filename}
            with open(self.setting_file, 'w') as f:
                json.dump(self.setting, f, indent=4)
            self.info_button(physical_key)
        self.changing = False

    def open_file(self, event: keyboard.KeyboardEvent):
        filename = self.key_map[event.name]['value']
        os.startfile(filename)

    def button_pressed(self, event: tk.Event):
        """按下按钮的动画"""
        button = event.widget
        button.state(['pressed'])

    def clear_key_map(self, event: tk.Event):
        """弹起右键时清除快捷键"""
        # 按钮弹起动画
        button = event.widget
        button.state(['!pressed'])
        if not self.check_launch() or self.changing:
            return
        self.clear_button_key_map(button)

    def check_launch(self):
        """检查是否开启"""
        if not self.launch_var.get():
            # 如果没有开，闪烁提示
            self.set.state(['pressed'])
            self.after(100, lambda: self.set.state(['!pressed']))
            return False
        return True

    def init_reset(self):
        """初始化重置按钮"""
        reset = ttk.Button(
            self,
            text='重置',
            command=self.clear_all_hotkey,
            padding=20,
        )
        reset.pack()
        return reset

    def clear_all_hotkey(self):
        """清除所有快捷键"""
        if not self.check_launch() or self.changing:
            return
        for r in self.buttons:
            for button in r:
                self.clear_button_key_map(button, write=False)
        with open(self.setting_file, 'w') as f:
            json.dump(self.setting, f, indent=4)
        self.info.set(DEFAULT_INFO)

    def clear_button_key_map(self, button: ttk.Button, write=True):
        """清除按钮的快捷键"""
        physical_key = button.winfo_name()[2:]
        button['text'] = physical_key
        # 如果有映射，取消映射
        map_ = self.key_map.pop(physical_key, None)
        if map_ is not None:
            keyboard.unhook(SCAN_CODE.get(physical_key, physical_key))
            if write:
                with open(self.setting_file, 'w') as f:
                    json.dump(self.setting, f, indent=4)

    def info_button(self, key: str):
        """鼠标进入按钮"""
        map_ = self.key_map.get(key)
        if map_ is None:
            self.info.set(DEFAULT_INFO)
            return
        if map_['type'] == 'hotkey':
            self.info.set(f'"{key}" 键位映射：\n' + map_['value'])
        elif map_['type'] == 'open':
            self.info.set(f'"{key}" 打开文件：\n' + map_['value'])

    def button_enter(self, event: tk.Event):
        """鼠标进入按钮"""
        self.info_button(event.widget.winfo_name()[2:])

    def button_leave(self, _: tk.Event):
        """鼠标离开按钮"""
        self.info.set(DEFAULT_INFO)


if __name__ == '__main__':
    app = App()
    app.mainloop()
