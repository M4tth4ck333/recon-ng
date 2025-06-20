#!/usr/bin/env python3
"""
Visualyzer - A Pygame-based wrapper and subroutine handler for advanced 
functional Visualyzer in python3 with modular sql-implemantion, search, cli/gui
integration, logging, and network object framework.
m4tth4ck
"""

# ===========================
# Imports
# ===========================
import pygame
import math
import random
import json
import logging
import os
import csv
import sqlite3
import psycopg2
import sqlalchemy
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Dict, List, Tuple, Optional
from enum import Enum
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from scapy.all import rdpcap
import xml.etree.ElementTree as ET
import argparse

# ===========================
# Framework Core Utilities
# ===========================
class CLIStatus:
    @staticmethod
    def print_status(message: str):
        print(f"[STATUS] {message}")

@dataclass
class Color:
    r: int
    g: int
    b: int

    def to_tuple(self) -> Tuple[int, int, int]:
        return (self.r, self.g, self.b)

# ===========================
# Logging Setup
# ===========================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===========================
# Config Loading
# ===========================
CONFIG_PATH = "config.json"
def load_config():
    default_config = {
        "window_width": 1200,
        "window_height": 800,
        "background_color": [5, 5, 20],
        "fps": 60,
        "naming_scheme": "celestial"
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                user_config = json.load(f)
            default_config.update(user_config)
        except Exception as e:
            logger.error(f"Fehler beim Laden der Konfiguration: {e}")
    return default_config

config = load_config()
WINDOW_WIDTH = config['window_width']
WINDOW_HEIGHT = config['window_height']
BACKGROUND_COLOR = tuple(config['background_color'])
FPS = config['fps']
NAMING_SCHEME = config['naming_scheme']

# ===========================
# Node Typisierung und Farbschema
# ===========================
class NodeType(Enum):
    PLANET = "planet"
    MOON = "moon"
    STAR = "star"
    ASTEROID = "asteroid"

class NodePropertiesDeterminer:
    @staticmethod
    def determine_node_type(node_data: Dict) -> NodeType:
        importance = node_data.get('importance', 0)
        connections_count = node_data.get('connections_count', 0)
        if importance > 0.8 or connections_count > 10:
            return NodeType.STAR
        elif importance > 0.5 or connections_count > 5:
            return NodeType.PLANET
        elif connections_count > 2:
            return NodeType.MOON
        else:
            return NodeType.ASTEROID

    @staticmethod
    def determine_node_color(node_type: NodeType) -> Color:
        color_map = {
            NodeType.STAR: Color(255, 255, 100),
            NodeType.PLANET: Color(100, 150, 255),
            NodeType.MOON: Color(200, 200, 200),
            NodeType.ASTEROID: Color(150, 100, 50)
        }
        return color_map.get(node_type, Color(255, 255, 255))

    @staticmethod
    def determine_node_size(node_data: Dict) -> float:
        base_size = 8
        importance = node_data.get('importance', 0.5)
        return base_size + importance * 20

# ===========================
# Dateilader
# ===========================
def load_json_file(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSON Ladefehler: {e}")
        return {}

def load_csv_file(filepath):
    try:
        with open(filepath, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            return [row for row in reader]
    except Exception as e:
        logger.error(f"CSV Ladefehler: {e}")
        return []

def load_sqlite_db(filepath, query):
    try:
        conn = sqlite3.connect(filepath)
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"SQLite Ladefehler: {e}")
        return []

def load_postgres_db(dsn, query):
    try:
        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"PostgreSQL Ladefehler: {e}")
        return []

def load_netxml(filepath):
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        return [{'id': node.get('id'), 'importance': random.random(), 'connections_count': random.randint(1, 10)} for node in root.findall(".//wireless-network")]
    except Exception as e:
        logger.error(f"NetXML Ladefehler: {e}")
        return []

def load_pcap(filepath):
    try:
        packets = rdpcap(filepath)
        return [{'id': str(i), 'importance': random.random(), 'connections_count': random.randint(1, 5)} for i, pkt in enumerate(packets[:10])]
    except Exception as e:
        logger.error(f"PCAP Ladefehler: {e}")
        return []

# ===========================
# Verzeichnisscan
# ===========================
def scan_home_for_data():
    home = os.path.expanduser("~")
    found_files = {"json": [], "csv": [], "sqlite": [], "netxml": [], "pcap": [], "postgres": []}
    for root, _, files in os.walk(home):
        for f in files:
            if f.endswith(".json"):
                found_files["json"].append(os.path.join(root, f))
            elif f.endswith(".csv"):
                found_files["csv"].append(os.path.join(root, f))
            elif f.endswith(".db") or f.endswith(".sqlite"):
                found_files["sqlite"].append(os.path.join(root, f))
            elif f.endswith(".netxml"):
                found_files["netxml"].append(os.path.join(root, f))
            elif f.endswith(".pcap") or f.endswith(".cap"):
                found_files["pcap"].append(os.path.join(root, f))
            elif f.endswith(".pgpass") or "postgres" in f.lower():
                found_files["postgres"].append(os.path.join(root, f))
    logger.info(f"Gefundene Dateien im Home-Verzeichnis: {found_files}")
    return found_files

# ===========================
# CLI Argumente
# ===========================
parser = argparse.ArgumentParser(description='Visualyzer - Netzwerkvisualisierung als Planetensystem')
parser.add_argument('--json', help='Netzwerkdaten aus JSON-Datei laden')
parser.add_argument('--csv', help='Netzwerkdaten aus CSV-Datei laden')
parser.add_argument('--sqlite', help='SQLite Datei')
parser.add_argument('--sqlquery', help='SQL Query')
parser.add_argument('--postgres', help='PostgreSQL DSN')
parser.add_argument('--pcap', help='PCAP Datei laden')
parser.add_argument('--netxml', help='NetXML Datei laden')
parser.add_argument('--scanhome', action='store_true', help='Home-Verzeichnis nach Datenquellen durchsuchen')
args = parser.parse_args()

# ===========================
# Tkinter Menüfenster
# ===========================
def open_tkinter_menu():
    def choose_file():
        filepath = filedialog.askopenfilename()
        messagebox.showinfo("Ausgewählt", f"Datei: {filepath}")

    root = tk.Tk()
    root.title("Visualyzer Menü")
    tk.Button(root, text="Datei öffnen", command=choose_file).pack()
    tk.Button(root, text="Beenden", command=root.destroy).pack()
    root.mainloop()

# ===========================
# Statusanzeige CLI
# ===========================
CLIStatus.print_status("Visualyzer gestartet")

if args.scanhome:
    scan_home_for_data()

# Der Visualisierungs- und GUI-Teil folgt modularisiert in visualyzer_gui.py, visualyzer_core.py etc.
