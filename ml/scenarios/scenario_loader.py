"""Load and navigate VoxQuest-AI scenario JSON files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


class ScenarioLoader:
    """Load and query VoxQuest-AI scenario files.

    Scenarios are JSON documents with a ``nodes`` list and a
    ``benchmark_phrases`` list.  See
    ``ml/scenarios/multilingual_story.json`` for the canonical schema.
    """

    # Path to the bundled multilingual scenario relative to this file.
    _DEFAULT_SCENARIO = Path(__file__).with_name("multilingual_story.json")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, path: Optional[str] = None) -> dict:
        """Load and parse a scenario JSON file.

        Parameters
        ----------
        path:
            Filesystem path to a ``.json`` scenario file.  When ``None``,
            the bundled ``multilingual_story.json`` is loaded.

        Returns
        -------
        dict
            Parsed scenario dictionary.

        Raises
        ------
        FileNotFoundError
            When *path* does not exist.
        json.JSONDecodeError
            When the file is not valid JSON.
        """
        target = Path(path) if path else self._DEFAULT_SCENARIO
        if not target.is_file():
            raise FileNotFoundError(f"Scenario file not found: {target}")
        with target.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def get_node(self, scenario: dict, node_id: str) -> dict:
        """Return the node dict matching *node_id*.

        Parameters
        ----------
        scenario:
            A previously loaded scenario dict (from :meth:`load`).
        node_id:
            The ``node_id`` string to look up.

        Returns
        -------
        dict
            The matching node.

        Raises
        ------
        KeyError
            When no node with the given *node_id* exists.
        """
        for node in scenario.get("nodes", []):
            if node.get("node_id") == node_id:
                return node
        raise KeyError(
            f"Node '{node_id}' not found in scenario '{scenario.get('scenario_id')}'."
        )

    def get_benchmark_phrases(self, scenario: dict) -> list:
        """Return the list of benchmark phrase dicts from *scenario*.

        Each phrase dict contains at minimum ``text`` and ``language`` keys.

        Parameters
        ----------
        scenario:
            A previously loaded scenario dict (from :meth:`load`).

        Returns
        -------
        list[dict]
            Benchmark phrase objects; empty list when none are defined.
        """
        return scenario.get("benchmark_phrases", [])

    def list_nodes(self, scenario: dict) -> list:
        """Return a sorted list of all ``node_id`` strings in *scenario*."""
        return sorted(
            node.get("node_id", "") for node in scenario.get("nodes", [])
        )

    def get_choices(self, scenario: dict, node_id: str) -> list:
        """Return the choices list for the given node.

        Parameters
        ----------
        scenario:
            Loaded scenario dict.
        node_id:
            Target node identifier.

        Returns
        -------
        list[dict]
            Choice objects; empty list for terminal nodes.
        """
        node = self.get_node(scenario, node_id)
        return node.get("choices", [])
