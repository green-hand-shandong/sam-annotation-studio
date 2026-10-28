"""SQLite 持久化：用户/数据集/图片/任务/标注/审核/导出/日志。"""
import json
import os
import sqlite3
import time

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, pw_hash TEXT,
    role TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS datasets(
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT DEFAULT '',
    created_by TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS images(
    id INTEGER PRIMARY KEY AUTOINCREMENT, dataset_id INTEGER, filename TEXT,
    path TEXT, width INTEGER, height INTEGER);
CREATE TABLE IF NOT EXISTS tasks(
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, dataset_id INTEGER,
    categories TEXT DEFAULT '[]', status TEXT DEFAULT '进行中',
    assignee TEXT, created_by TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS annotations(
    id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER, image_id INTEGER,
    category_id INTEGER, bbox TEXT, mask_png TEXT, area INTEGER, score REAL,
    source TEXT DEFAULT 'manual', status TEXT DEFAULT '已完成',
    review_status TEXT DEFAULT '待审核', review_comment TEXT DEFAULT '',
    annotated_by TEXT, reviewed_by TEXT DEFAULT '', updated_at REAL);
CREATE TABLE IF NOT EXISTS logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, detail TEXT,
    created_at REAL);
CREATE TABLE IF NOT EXISTS exports(
    id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER, format TEXT,
    path TEXT, count INTEGER, created_by TEXT, created_at REAL);
"""


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init():
    con = connect()
    con.executescript(_SCHEMA)
    con.commit()
    cur = con.execute("SELECT COUNT(*) c FROM users")
    if cur.fetchone()["c"] == 0:
        from .auth import hash_password
        for u, p, r in [("admin", "admin123", "管理员"),
                        ("annotator", "123456", "标注员"),
                        ("reviewer", "123456", "审核员")]:
            con.execute("INSERT INTO users(username,pw_hash,role,created_at) VALUES(?,?,?,?)",
                        (u, hash_password(p), r, time.time()))
    con.commit()
    con.close()


def now() -> float:
    return time.time()


def log(user: str, action: str, detail: str = ""):
    con = connect()
    con.execute("INSERT INTO logs(user,action,detail,created_at) VALUES(?,?,?,?)",
                (user, action, detail, now()))
    con.commit()
    con.close()


def rowdict(row) -> dict:
    return {k: row[k] for k in row.keys()}


def rows(con, sql, args=()) -> list[dict]:
    return [rowdict(r) for r in con.execute(sql, args)]
