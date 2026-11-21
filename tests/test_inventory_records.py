"""Keep IDs/freshness in the upstream Phase 3 inventory file format."""

import json
import os
import tempfile
import unittest

from chonoi.inventory import read_inventory, write_inventory


class InventoryRecordsTest(unittest.TestCase):
    def test_item_records_roundtrip_without_losing_ids_or_freshness(self):
        items = [
            {"id": "I9", "kind": "ca_loc", "fresh": 75},
            {"id": "I2", "kind": "bong_sung", "fresh": 60},
            {"id": "I3", "kind": "ca_loc", "fresh": 80},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "inventory.json")
            write_inventory(path, items)
            with open(path, encoding="utf-8") as source:
                self.assertEqual(json.load(source), {"items": items})
            self.assertEqual(read_inventory(path), items)
            write_inventory(path, [])
            self.assertEqual(read_inventory(path), [])
        self.assertEqual(items[0], {"id": "I9", "kind": "ca_loc", "fresh": 75})
