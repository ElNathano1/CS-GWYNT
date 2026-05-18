"""Round-trip tests for Effect/Trigger DB payload helpers."""

import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from database.models import Effect, Trigger


class TestEffectTriggerRoundTrip(unittest.TestCase):
    def test_trigger_condition_group_round_trip(self):
        trigger = Trigger(event="on_play")

        activate_conditions = [
            {"field_name": "board_count", "operator": "gt", "value": 5}
        ]
        trigger.set_condition_group("activate", "all", activate_conditions)

        result = trigger.get_condition_group("activate")
        self.assertIsNotNone(result)
        self.assertEqual(result["logic"], "all")  # type: ignore
        self.assertEqual(result["conditions"], activate_conditions)  # type: ignore

    def test_effect_target_and_value_round_trip(self):
        effect = Effect(description="Test", type="buff", trigger_id=1)

        target_payload = {"shape": "single", "selector": "self"}
        effect.set_target(target_payload)  # type: ignore

        value_payload = {
            "type": "power_table",
            "frontstage": 1,
            "offstage": 2,
            "backstage": 3,
        }
        effect.set_value_data(value_payload)

        self.assertEqual(effect.target_shape, "single")
        self.assertEqual(effect.get_target(), target_payload)
        self.assertEqual(effect.get_value_data(), value_payload)

    def test_effect_integer_value_round_trip(self):
        effect = Effect(description="Test int", type="set_power", trigger_id=1)

        effect.set_value_data(7)

        self.assertEqual(effect.value, 7)
        self.assertIsNone(effect.value_json)
        self.assertEqual(effect.get_value_data(), 7)


if __name__ == "__main__":
    unittest.main()
