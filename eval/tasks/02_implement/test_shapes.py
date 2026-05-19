"""Tests for shapes.py. All fail until the agent implements the stubs."""

import math

import pytest

from shapes import area_circle, hypotenuse, perimeter_rectangle, volume_cylinder


def test_area_circle_unit():
    assert area_circle(1) == pytest.approx(math.pi)


def test_area_circle_zero():
    assert area_circle(0) == 0


def test_area_circle_larger():
    assert area_circle(3) == pytest.approx(9 * math.pi)


def test_perimeter_rectangle_square():
    assert perimeter_rectangle(2, 2) == 8


def test_perimeter_rectangle_long():
    assert perimeter_rectangle(5, 3) == 16


def test_volume_cylinder_unit():
    assert volume_cylinder(1, 1) == pytest.approx(math.pi)


def test_volume_cylinder_larger():
    assert volume_cylinder(2, 5) == pytest.approx(20 * math.pi)


def test_hypotenuse_3_4_5():
    assert hypotenuse(3, 4) == 5


def test_hypotenuse_zero_legs():
    assert hypotenuse(0, 0) == 0


def test_hypotenuse_5_12_13():
    assert hypotenuse(5, 12) == 13
