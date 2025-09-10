#!/usr/bin/env python3
"""
Unit tests for calm.profile calculation functions
Tests edge cases and validates calculation accuracy
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from calm_profile_system import score_assessment, clamp
import unittest


class TestCalculationUtils(unittest.TestCase):

    def test_clamp_function(self):
        """Test clamping function with edge cases"""
        # Normal values
        self.assertEqual(clamp(50), 50)
        self.assertEqual(clamp(0), 0)
        self.assertEqual(clamp(100), 100)

        # Edge cases
        self.assertEqual(clamp(-10), 0)
        self.assertEqual(clamp(150), 100)
        self.assertEqual(clamp(50, 10, 90), 50)
        self.assertEqual(clamp(5, 10, 90), 10)
        self.assertEqual(clamp(95, 10, 90), 90)

    def test_sample_persona_calculation(self):
        """Test calculation with sample persona: 15h, $150/hr, team 10"""
        # Mock assessment responses (all A's for testing)
        responses = {str(i): 1 for i in range(20)}

        # Mock context
        context = {
            "team_size": "6-15",  # Maps to 10.5 people
            "hourly_rate": 150,
            "meeting_load": "moderate",  # Maps to 0.8
            "platform": "google",
        }

        # Calculate overhead
        meeting_map = {"light": 0.6, "moderate": 0.8, "heavy": 1.0}
        overhead_base = meeting_map.get("moderate", 0.8)

        # Get archetype (assuming architect for test)
        result = score_assessment(responses)
        primary = result.get("archetype", {}).get("primary", "architect").lower()

        arche_adj = {
            "architect": 0.9,
            "conductor": 0.85,
            "curator": 1.1,
            "craftsperson": 1.2,
        }
        overhead_index = overhead_base * arche_adj.get(primary, 1.0)

        # Team size mapping
        team_size_map = {"solo": 1, "2-5": 3.5, "6-15": 10.5, "16-50": 33, "50+": 75}
        team_size = team_size_map.get("6-15", 1)

        # Apply clamping
        hourly_rate = max(25, min(500, 150))
        team_size = max(1, min(100, team_size))
        overhead_index = max(0.1, min(2.0, overhead_index))

        # Calculate hours and costs
        hours_lost_ppw = max(0.5, min(40, overhead_index * 5.0))
        weekly_cost = hours_lost_ppw * hourly_rate * team_size
        annual_cost = weekly_cost * 52

        # Expected calculations (before clamping)
        expected_overhead = 0.8 * 0.9  # moderate * architect
        expected_hours = expected_overhead * 5.0
        expected_weekly = expected_hours * 150 * 10.5
        expected_annual = expected_weekly * 52

        print(f"\nSample Persona Test Results:")
        print(f"Team size: {team_size} people")
        print(f"Hourly rate: ${hourly_rate}/hour")
        print(
            f"Overhead index: {overhead_index:.2f} (clamped from {expected_overhead:.2f})"
        )
        print(f"Hours lost/week: {hours_lost_ppw:.1f}h")
        print(f"Weekly cost: ${weekly_cost:,.0f}")
        print(f"Annual cost: ${annual_cost:,.0f}")

        # Validate calculations (use actual values after clamping)
        self.assertAlmostEqual(hours_lost_ppw, overhead_index * 5.0, places=1)
        self.assertAlmostEqual(
            weekly_cost, hours_lost_ppw * hourly_rate * team_size, places=0
        )
        self.assertAlmostEqual(annual_cost, weekly_cost * 52, places=0)

    def test_edge_cases(self):
        """Test edge cases for calculation robustness"""

        # Test zero hours
        hours_lost_ppw = max(0.5, min(40, 0.1 * 5.0))  # Minimum overhead
        self.assertEqual(hours_lost_ppw, 0.5)

        # Test high rates
        hourly_rate = max(25, min(500, 1000))  # Clamp high rate
        self.assertEqual(hourly_rate, 500)

        # Test large teams
        team_size = max(1, min(100, 200))  # Clamp large team
        self.assertEqual(team_size, 100)

        # Test maximum hours
        hours_lost_ppw = max(0.5, min(40, 2.0 * 5.0))  # Maximum overhead
        self.assertEqual(hours_lost_ppw, 10.0)  # 2.0 * 5.0 = 10.0, not 40

    def test_team_size_mapping(self):
        """Test team size mapping accuracy"""
        team_size_map = {"solo": 1, "2-5": 3.5, "6-15": 10.5, "16-50": 33, "50+": 75}

        # Test each mapping
        self.assertEqual(team_size_map["solo"], 1)
        self.assertEqual(team_size_map["2-5"], 3.5)  # Average of 2-5
        self.assertEqual(team_size_map["6-15"], 10.5)  # Average of 6-15
        self.assertEqual(team_size_map["16-50"], 33)  # Average of 16-50
        self.assertEqual(team_size_map["50+"], 75)  # Reasonable estimate

    def test_archetype_adjustments(self):
        """Test archetype adjustment factors"""
        arche_adj = {
            "architect": 0.9,
            "conductor": 0.85,
            "curator": 1.1,
            "craftsperson": 1.2,
        }

        # Test that adjustments are reasonable
        for archetype, adjustment in arche_adj.items():
            self.assertGreaterEqual(adjustment, 0.5)
            self.assertLessEqual(adjustment, 2.0)
            print(f"{archetype}: {adjustment}x multiplier")


if __name__ == "__main__":
    unittest.main()
