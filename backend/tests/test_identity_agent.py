"""
Unit tests for IdentityResolutionAgent graph anomaly detection.
"""

import networkx as nx
import pytest
from app.agents.identity import IdentityResolutionAgent
from app.models.vessel import Vessel


def test_detect_anomalies_circular_ownership():
    agent = IdentityResolutionAgent(db=None)
    vessel = Vessel(imo=9123456, name="Test Vessel", year_built=2020)
    
    G = nx.DiGraph()
    G.add_node("vessel_9123456", label="Test Vessel")
    G.add_node("entity_1", label="Company A")
    G.add_node("entity_2", label="Company B")
    
    # Create a cycle: entity_1 -> entity_2 -> entity_1
    G.add_edge("entity_1", "entity_2")
    G.add_edge("entity_2", "entity_1")
    G.add_edge("entity_1", "vessel_9123456")
    
    anomalies = agent._detect_anomalies(G, vessel)
    types = [a["type"] for a in anomalies]
    assert "circular_ownership" in types


def test_detect_anomalies_deep_ownership():
    agent = IdentityResolutionAgent(db=None)
    vessel = Vessel(imo=9123456, name="Test Vessel", year_built=2020)
    
    G = nx.DiGraph()
    G.add_node("vessel_9123456", label="Test Vessel")
    
    # Create a 7-layer chain: e1 -> e2 -> e3 -> e4 -> e5 -> e6 -> e7 -> vessel
    nodes = [f"entity_{i}" for i in range(1, 8)]
    for n in nodes:
        G.add_node(n, label=f"Layer {n}")
    
    for i in range(len(nodes) - 1):
        G.add_edge(nodes[i], nodes[i + 1])
    G.add_edge(nodes[-1], "vessel_9123456")
    
    anomalies = agent._detect_anomalies(G, vessel)
    types = [a["type"] for a in anomalies]
    assert "deep_ownership" in types
