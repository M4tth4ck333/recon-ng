#!/usr/bin/env python3
"""
CRUCH - Enhanced Leet Speak Wordlist Generator
A wrapper and subroutine handler for advanced leetspeak wordlist generation
with crunch-like functionality and improved error handling.
m4tth4ck
Original leet.py by Tim Tomes (LaNMaSteR53)
Enhanced wrapper by: Enhanced Development Team
"""
import pygame
import math
import random
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Konstanten
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FPS = 60
BACKGROUND_COLOR = (5, 5, 20)


class NodeType(Enum):
    STAR = "star"
    PLANET = "planet"
    MOON = "moon"
    ASTEROID = "asteroid"


@dataclass
class Color:
    r: int
    g: int
    b: int

    def to_tuple(self) -> Tuple[int, int, int]:
        return (self.r, self.g, self.b)


class NetworkNode:
    """Repräsentiert einen Knoten im Netzwerk als Himmelskörper"""

    def __init__(self, node_id: str, node_type: NodeType, x: float, y: float,
                 radius: float = 10, color: Color = Color(255, 255, 255)):
        self.id = node_id
        self.type = node_type
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.connections: List['NetworkNode'] = []
        self.data: Dict = {}

        # Orbit-Parameter für Animation
        self.orbit_center_x = x
        self.orbit_center_y = y
        self.orbit_radius = 0
        self.orbit_angle = random.uniform(0, 2 * math.pi)
        self.orbit_speed = 0
        self.pulsation = 0

    def add_connection(self, other_node: 'NetworkNode'):
        """Fügt eine Verbindung zu einem anderen Knoten hinzu"""
        if other_node not in self.connections:
            self.connections.append(other_node)
            other_node.connections.append(self)

    def update_position(self, dt: float):
        """Aktualisiert Position basierend auf Orbit-Parametern"""
        if self.orbit_speed > 0:
            self.orbit_angle += self.orbit_speed * dt
            self.x = self.orbit_center_x + math.cos(self.orbit_angle) * self.orbit_radius
            self.y = self.orbit_center_y + math.sin(self.orbit_angle) * self.orbit_radius

        # Pulsation für "lebendige" Darstellung
        self.pulsation += dt * 2

    def get_display_radius(self) -> float:
        """Berechnet Radius mit Pulsationseffekt"""
        pulse_factor = 1 + 0.1 * math.sin(self.pulsation)
        return self.radius * pulse_factor


class NetworkSystem:
    """Verwaltet das gesamte Netzwerk-Planetensystem"""

    def __init__(self):
        self.nodes: Dict[str, NetworkNode] = {}
        self.star_systems: List[List[NetworkNode]] = []
        self.selected_node: Optional[NetworkNode] = None

    def add_node(self, node: NetworkNode):
        """Fügt einen Knoten zum System hinzu"""
        self.nodes[node.id] = node

    def create_star_system(self, center_node: NetworkNode, satellites: List[NetworkNode]):
        """Erstellt ein Stern-System mit Planeten/Monden"""
        system = [center_node]

        for i, satellite in enumerate(satellites):
            # Berechne Orbit-Parameter
            orbit_distance = 50 + i * 40
            satellite.orbit_center_x = center_node.x
            satellite.orbit_center_y = center_node.y
            satellite.orbit_radius = orbit_distance
            satellite.orbit_speed = 1.0 / (orbit_distance * 0.01)  # Kepler'sches Gesetz
            satellite.orbit_angle = random.uniform(0, 2 * math.pi)

            system.append(satellite)
            center_node.add_connection(satellite)

        self.star_systems.append(system)

    def update(self, dt: float):
        """Aktualisiert alle Knoten im System"""
        for node in self.nodes.values():
            node.update_position(dt)

    def get_node_at_position(self, x: float, y: float) -> Optional[NetworkNode]:
        """Findet Knoten an bestimmter Position"""
        for node in self.nodes.values():
            distance = math.sqrt((node.x - x) ** 2 + (node.y - y) ** 2)
            if distance <= node.radius:
                return node
        return None


class NetworkVisualizer:
    """Hauptklasse für die Visualisierung"""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Netzwerk Planetensystem")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.system = NetworkSystem()
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        self.dragging = False
        self.last_mouse_pos = (0, 0)

    def load_network_data(self, data: Dict):
        """Lädt Netzwerkdaten und konvertiert sie in Planetensystem"""
        # Beispielhafte Konvertierung von Netzwerkdaten
        nodes_data = data.get('nodes', [])
        connections_data = data.get('connections', [])

        # Erstelle Knoten
        for node_data in nodes_data:
            node_type = self._determine_node_type(node_data)
            color = self._determine_node_color(node_type, node_data)
            radius = self._determine_node_size(node_data)

            node = NetworkNode(
                node_id=node_data['id'],
                node_type=node_type,
                x=random.uniform(100, WINDOW_WIDTH - 100),
                y=random.uniform(100, WINDOW_HEIGHT - 100),
                radius=radius,
                color=color
            )
            node.data = node_data
            self.system.add_node(node)

        # Erstelle Verbindungen
        for conn in connections_data:
            node1 = self.system.nodes.get(conn['from'])
            node2 = self.system.nodes.get(conn['to'])
            if node1 and node2:
                node1.add_connection(node2)

    def _determine_node_type(self, node_data: Dict) -> NodeType:
        """Bestimmt Knotentyp basierend auf Eigenschaften"""
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

    def _determine_node_color(self, node_type: NodeType, node_data: Dict) -> Color:
        """Bestimmt Farbe basierend auf Knotentyp"""
        color_map = {
            NodeType.STAR: Color(255, 255, 100),  # Gelb
            NodeType.PLANET: Color(100, 150, 255),  # Blau
            NodeType.MOON: Color(200, 200, 200),  # Grau
            NodeType.ASTEROID: Color(150, 100, 50)  # Braun
        }
        return color_map.get(node_type, Color(255, 255, 255))

    def _determine_node_size(self, node_data: Dict) -> float:
        """Bestimmt Knotengröße basierend auf Eigenschaften"""
        base_size = 8
        importance = node_data.get('importance', 0.5)
        return base_size + importance * 20

    def handle_events(self):
        """Behandelt Eingabeereignisse"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Linke Maustaste
                    mouse_x, mouse_y = event.pos
                    world_x = (mouse_x - self.camera_x) / self.zoom
                    world_y = (mouse_y - self.camera_y) / self.zoom

                    clicked_node = self.system.get_node_at_position(world_x, world_y)
                    if clicked_node:
                        self.system.selected_node = clicked_node
                    else:
                        self.dragging = True
                        self.last_mouse_pos = event.pos

                elif event.button == 4:  # Mausrad hoch
                    self.zoom = min(self.zoom * 1.1, 3.0)
                elif event.button == 5:  # Mausrad runter
                    self.zoom = max(self.zoom * 0.9, 0.3)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    self.camera_x += dx
                    self.camera_y += dy
                    self.last_mouse_pos = event.pos

        return True

    def render(self):
        """Rendert das System"""
        self.screen.fill(BACKGROUND_COLOR)

        # Zeichne Verbindungen
        for node in self.system.nodes.values():
            for connected_node in node.connections:
                start_pos = self._world_to_screen(node.x, node.y)
                end_pos = self._world_to_screen(connected_node.x, connected_node.y)
                pygame.draw.line(self.screen, (50, 50, 100), start_pos, end_pos, 1)

        # Zeichne Orbits für ausgewählten Knoten
        if self.system.selected_node:
            selected = self.system.selected_node
            for connected in selected.connections:
                if connected.orbit_radius > 0:
                    center = self._world_to_screen(connected.orbit_center_x, connected.orbit_center_y)
                    radius = int(connected.orbit_radius * self.zoom)
                    pygame.draw.circle(self.screen, (30, 30, 60), center, radius, 1)

        # Zeichne Knoten
        for node in self.system.nodes.values():
            pos = self._world_to_screen(node.x, node.y)
            radius = int(node.get_display_radius() * self.zoom)

            # Highlight für ausgewählten Knoten
            if node == self.system.selected_node:
                pygame.draw.circle(self.screen, (255, 255, 255), pos, radius + 3, 2)

            pygame.draw.circle(self.screen, node.color.to_tuple(), pos, radius)

            # Zeichne Knotenlabel
            if self.zoom > 0.7:
                label = self.font.render(node.id, True, (255, 255, 255))
                label_pos = (pos[0] - label.get_width() // 2, pos[1] + radius + 5)
                self.screen.blit(label, label_pos)

        # Info-Panel
        if self.system.selected_node:
            self._render_info_panel(self.system.selected_node)

        pygame.display.flip()

    def _world_to_screen(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Konvertiert Weltkoordinaten zu Bildschirmkoordinaten"""
        screen_x = int(world_x * self.zoom + self.camera_x)
        screen_y = int(world_y * self.zoom + self.camera_y)
        return (screen_x, screen_y)

    def _render_info_panel(self, node: NetworkNode):
        """Rendert Informationspanel für ausgewählten Knoten"""
        panel_width = 200
        panel_height = 150
        panel_x = WINDOW_WIDTH - panel_width - 10
        panel_y = 10

        # Panel-Hintergrund
        pygame.draw.rect(self.screen, (30, 30, 30),
                         (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, (100, 100, 100),
                         (panel_x, panel_y, panel_width, panel_height), 2)

        # Knoteninfos
        y_offset = panel_y + 10
        texts = [
            f"ID: {node.id}",
            f"Typ: {node.type.value}",
            f"Verbindungen: {len(node.connections)}",
            f"Radius: {node.radius:.1f}",
        ]

        for text in texts:
            surface = self.font.render(text, True, (255, 255, 255))
            self.screen.blit(surface, (panel_x + 10, y_offset))
            y_offset += 25

    def run(self):
        """Hauptschleife der Anwendung"""
        running = True

        # Beispieldaten laden
        sample_data = {
            'nodes': [
                {'id': 'Server-1', 'importance': 0.9, 'connections_count': 15},
                {'id': 'Router-A', 'importance': 0.7, 'connections_count': 8},
                {'id': 'PC-001', 'importance': 0.3, 'connections_count': 2},
                {'id': 'PC-002', 'importance': 0.3, 'connections_count': 2},
                {'id': 'Switch-1', 'importance': 0.6, 'connections_count': 6},
                {'id': 'IoT-Device', 'importance': 0.2, 'connections_count': 1},
            ],
            'connections': [
                {'from': 'Server-1', 'to': 'Router-A'},
                {'from': 'Router-A', 'to': 'Switch-1'},
                {'from': 'Switch-1', 'to': 'PC-001'},
                {'from': 'Switch-1', 'to': 'PC-002'},
                {'from': 'Router-A', 'to': 'IoT-Device'},
            ]
        }

        self.load_network_data(sample_data)

        # Erstelle Sternsystem
        if 'Server-1' in self.system.nodes and 'Router-A' in self.system.nodes:
            center = self.system.nodes['Server-1']
            satellites = [self.system.nodes['Router-A']]
            self.system.create_star_system(center, satellites)

        while running:
            dt = self.clock.tick(FPS) / 1000.0

            running = self.handle_events()
            self.system.update(dt)
            self.render()

        pygame.quit()


# Verwendungsbeispiel
if __name__ == "__main__":
    app = NetworkVisualizer()
    app.run()