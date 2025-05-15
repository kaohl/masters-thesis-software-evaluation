#!/bin/env python3

import math_helpers as mh

import math
import unittest

class TestMathHelpers(unittest.TestCase):

    def assert_sae(self, n, p, expected):
        # Test n and -n
        self.assertEqual(expected, mh.significand_and_exponent(n, p))
        self.assertEqual((-expected[0], expected[1]), mh.significand_and_exponent(-n, p))

    def test_abs_lt_1(self):
        self.assert_sae(0.5, 3, (5, -1))

    def test_abs_1(self):
        self.assert_sae(1, 3, (1, 0))

    def test_abs_lt_10(self):
        self.assert_sae(9, 3, (9, 0))

    def test_abs_100(self):
        self.assert_sae(100, 3, (1, 2))

    def test_precision(self):
        self.assert_sae(0.567, 1, (5.7, -1))
        self.assert_sae(0.567, 2, (5.67, -1))
        self.assert_sae(0.0567, 1, (5.7, -2))
        self.assert_sae(1.12345, 1, (1.1, 0))
        self.assert_sae(1.12345, 4, (1.1235, 0))

        self.assert_sae(9.99, 2, (9.99, 0)) # No rounding.
        self.assert_sae(9.99, 1, (1, 1))    # Rounds to 10.

if __name__ == '__main__':
    unittest.main()

