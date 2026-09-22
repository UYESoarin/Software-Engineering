"""一箭又一箭：状态机 + 规则/表现分离。

规则层（rules.py）不 import pygame；表现层（view / anim / scenes）
只把规则层的结果画出来。关卡数据外置在 levels.json，改关不改判定。
"""
