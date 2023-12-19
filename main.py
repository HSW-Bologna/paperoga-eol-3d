#!/usr/bin/env python

from __future__ import annotations
from itertools import takewhile

from solid import *
from solid.utils import *
from dataclasses import dataclass, asdict

from typing import List, Tuple


class ConstantOpenSCADObject(OpenSCADObject):
    def __init__(self, code):
        super().__init__("not reander able", {})
        self.code = code

    def _render(self, render_holes=42):
        return self.code


def scad_inline(code):
    return ConstantOpenSCADObject(code)


ORIGIN_X_SHIFT = 3.1
ORIGIN_Y_SHIFT = 3.5
MIN = .0001


@dataclass
class Measures:
    pcb_width = 110.6
    pcb_depth = 100.6

    needle_diameter = 1.65
    needle_root_height = 8
    needle_spring_play = 10
    thickness = 2

    display_width = 62  # 67.5
    display_depth = 85

    prog_1_position = (87.189, 71.78)
    exp_trh_1_position = (9.529, 91.94)
    rs232_1_position = (1.089, 70.9)
    tastiera_1_position = (16.689, 66.88)
    coin_1_position = (101.569, 92.94)
    ptc_1_position = (103.589, 74.4)
    ch_0_10v_1_position = (103.589, 65.2)
    alm_10v_1_position = (14.689, 2)
    alm_24v_1_position = (94.769, 1.6)
    out1_1_position = (78.489, 1.6)
    out2_1_position = (50.369, 1.6)
    input_1_position = (101.789, 38.94)

    columns_positions = [(0, 0), (.1, 48.8),
                         (103.5, 0), (103.4, 48.9),]
    column_diameter = 8.2
    column_root_height = 2.5
    column_screw_diameter = 4.1

    jaw_byte = 12
    jaw_height = 20

    pier_depth = 10
    pier_width = 5
    pier_height = 8
    pier_furrow_width = 1
    pier_furrow_height = 5

    hinge_depth = 10
    hinge_internal_depth = 5.8
    hinge_diameter = 6
    hinge_hole_diameter = 2

    margin = .1

    def lower_left_column_y(self):
        return self.columns_positions[0][1] + \
            ORIGIN_Y_SHIFT - self.pcb_depth/2

    def upper_left_column_y(self):
        return self.lower_left_column_y() + self.columns_positions[1][1]

    def center_left_column_y(self):
        return (self.lower_left_column_y() + self.upper_left_column_y())/2

    def left_column_distance_y(self):
        return abs(self.lower_left_column_y() - self.upper_left_column_y())

    def lower_right_column_y(self):
        return self.columns_positions[2][1] + ORIGIN_Y_SHIFT - self.pcb_depth/2

    def upper_right_column_y(self):
        return self.lower_right_column_y() + self.columns_positions[3][1]

    def center_right_column_y(self):
        return (self.lower_right_column_y() + self.upper_right_column_y())/2

    def right_column_distance_y(self):
        return abs(self.lower_right_column_y() - self.upper_right_column_y())



def hex_column(diameter, height):
    return union()(scad_inline("$fn=6;"), cylinder(d=diameter, h=height, center=True))


def needles(array: List[Tuple[float, float]], height, diameter):
    result = union()()
    for (x, y) in array:
        result += translate((x, y, 0))(cylinder(d=diameter, h=height))
    return result


def needle_array(rows, columns, diameter, height, distance=2.54, rotation=0):
    array = []
    for row in range(rows):
        for column in range(columns):
            array.append((row*(distance), column*(distance)))

    x_centering = -rows*distance/4
    if (rows % 2) != 0:
        x_centering = -(rows-1)*distance/2

    y_centering = -columns*distance*3/8
    if (columns % 2) != 0:
        y_centering = -(columns-1)*distance/2

    return rotate((0, 0, rotation))(needles(array, height, diameter))
    # return translate((x_centering,y_centering,0))(needles(array, height, diameter))


def build_pier(m: Measures):
    pier_body = cube((m.pier_width, m.pier_depth, m.pier_height), center=True)

    furrow = cube((m.pier_furrow_width, m.pier_depth,
                  m.pier_furrow_height), center=True)
    pier_body -= translate((+(m.pier_width - m.pier_furrow_width)/2,
                           0, -(m.pier_height-m.pier_furrow_height)/2))(furrow)

    wall = cube((m.thickness, m.pier_depth, m.needle_spring_play), center=True)
    pier_body += translate((-(m.pier_width - m.thickness)/2,
                           0, -(m.pier_height-m.needle_spring_play)/2))(wall)

    return pier_body


def build_hinge(diameter, hole_diameter, width):
    body = cylinder(d=diameter, h=width, center=True)
    body += translate((diameter/4, 0, 0)
                      )(cube((diameter/2, diameter, width), center=True))
    body -= cylinder(d=hole_diameter, h=width, center=True)
    return body


def build_jaw(m: Measures, distance):
    def half_cylinder(diameter, height):
        return intersection()(cylinder(d=diameter, h=height, center=True), translate((diameter/4, 0, 0))(cube((diameter/2, diameter, height), center=True)))

    hinge = build_hinge(m.hinge_diameter, m.hinge_hole_diameter, m.hinge_depth)

    extra_height = m.needle_root_height - m.hinge_diameter
    assert (extra_height > 0)

    trunk = rotate((0, -90, 0))(rotate((90, 0, 0))(hinge))
    trunk += translate((0, 0, (m.hinge_diameter+extra_height)/2)
                       )(cube((m.hinge_diameter, m.hinge_depth, extra_height), center=True))
    trunk -= translate((0, 0, extra_height/4))(cube((m.hinge_diameter,
                                                     m.hinge_diameter, m.hinge_diameter+extra_height/2), center=True))
    trunk += translate((0, 0, (m.hinge_diameter+m.needle_spring_play)/2+extra_height))(
        cube((m.hinge_diameter, m.hinge_depth, m.needle_spring_play), center=True))

    scaling = (m.jaw_height/m.hinge_depth)*2

    center_trunk = trunk
    center_trunk -= translate((-m.hinge_diameter/4, 0, (m.hinge_diameter+m.pier_furrow_height)/2+extra_height)
                              )(cube((m.hinge_diameter/2, m.hinge_depth, m.pier_furrow_height), center=True))
    center_trunk += translate(((m.hinge_diameter+m.thickness)/2-m.hinge_diameter, 0, m.hinge_diameter/2 + extra_height + m.needle_spring_play))(rotate((0, -90, 0))(scale((scaling, 1, 1))(half_cylinder(m.hinge_depth, m.thickness))))

    center_trunk += translate((0, 0, (m.needle_spring_play+m.hinge_diameter+m.pier_furrow_height) /
                              2+extra_height))(cube((m.hinge_diameter, distance, m.needle_spring_play-m.pier_furrow_height), center=True))

    jaw_trunk = trunk
    jaw_trunk += translate((m.jaw_byte/2, 0, m.hinge_diameter/2 + extra_height + m.needle_spring_play))(hull()(
        cube((m.jaw_byte+m.hinge_diameter, m.hinge_depth, MIN), center=True),
        translate((-(m.jaw_byte+m.hinge_diameter-MIN)/2, 0, 0)
                  )(rotate((0, -90, 0))(scale((scaling, 1, 1))(half_cylinder(m.hinge_depth, MIN))))
    ) - translate(((m.hinge_diameter)/2,0,0))(cube((m.jaw_byte,m.column_screw_diameter,m.jaw_height), center=True)))

    return center_trunk + translate((0, -distance/2, 0))(jaw_trunk) + translate((0, distance/2, 0))(jaw_trunk)


def build_cradle(m: Measures):
    def x_shift(x):
        return x + ORIGIN_X_SHIFT - m.pcb_width/2

    def y_shift(y):
        return y + ORIGIN_Y_SHIFT - m.pcb_depth/2

    total_body_height = m.needle_root_height + m.needle_spring_play
    body = cube((m.pcb_width+m.thickness*2, m.pcb_depth +
                 m.thickness*2, total_body_height), center=True)

    pcb_recess = cube(
        (m.pcb_width, m.pcb_depth, m.needle_spring_play), center=True)
    body -= translate((0, 0, m.needle_root_height/2))(pcb_recess)

    display_hole = cube((m.display_width, m.display_depth,
                         m.needle_root_height), center=True)
    body -= translate((0, (m.pcb_depth+m.thickness*2 -
                      m.display_depth)/2-m.thickness, -m.needle_spring_play/2))(display_hole)

    body -= translate((-m.pcb_width/4, -m.pcb_depth/6-m.thickness, (total_body_height -
                      m.needle_spring_play)/2))(cube((m.pcb_width/2+m.thickness*2, m.pcb_depth*2/3, m.needle_spring_play), center=True))
    body -= translate((+m.pcb_width/3+m.thickness, -m.pcb_depth/6-m.thickness, (total_body_height -
                      m.needle_spring_play)/2))(cube((m.pcb_width/3, m.pcb_depth*2/3, m.needle_spring_play), center=True))

    body += translate((-(m.pcb_width+m.thickness*2-m.pier_width)/2, m.center_left_column_y(),
                      (total_body_height+m.pier_height)/2 - m.needle_spring_play))(build_pier(m))

    hinge = rotate((90, 0, 0))(build_hinge(m.hinge_diameter,
                                           m.hinge_hole_diameter, m.hinge_internal_depth - m.margin*2))
    body += translate((-(m.pcb_width+m.thickness*2+m.hinge_diameter)/2,
                      m.lower_left_column_y(), -(total_body_height-m.hinge_diameter)/2))(hinge)
    body += translate((-(m.pcb_width+m.thickness*2+m.hinge_diameter)/2,
                      m.upper_left_column_y(), -(total_body_height-m.hinge_diameter)/2))(hinge)
    body += translate((-(m.pcb_width+m.thickness*2+m.hinge_diameter)/2,
                      m.center_left_column_y(), -(total_body_height-m.hinge_diameter)/2))(hinge)

    body += translate((+(m.pcb_width+m.thickness*2-m.pier_width)/2, m.center_right_column_y(),
                      (total_body_height+m.pier_height)/2 - m.needle_spring_play))(mirror((1, 0, 0))(build_pier(m)))

    hinge = mirror((1, 0, 0))(rotate((90, 0, 0))(build_hinge(
        m.hinge_diameter, m.hinge_hole_diameter, m.hinge_internal_depth - m.margin*2)))
    body += translate((+(m.pcb_width+m.thickness*2+m.hinge_diameter)/2,
                      m.lower_right_column_y(), -(total_body_height-m.hinge_diameter)/2))(hinge)
    body += translate((+(m.pcb_width+m.thickness*2+m.hinge_diameter)/2,
                      m.upper_right_column_y(), -(total_body_height-m.hinge_diameter)/2))(hinge)
    body += translate((+(m.pcb_width+m.thickness*2+m.hinge_diameter)/2,
                      m.center_right_column_y(), -(total_body_height-m.hinge_diameter)/2))(hinge)

    for (x, y) in m.columns_positions:
        x = x_shift(x)
        y = y_shift(y)

        body -= translate((x, y, (total_body_height-m.column_root_height-m.needle_spring_play)/2)
                          )(hex_column(diameter=m.column_diameter, height=m.column_root_height+m.needle_spring_play))
        body -= translate((x, y, (m.needle_root_height-m.needle_spring_play-m.needle_root_height)/2)
                          )(cylinder(d=m.column_screw_diameter, h=m.needle_root_height, center=True))

    body -= translate((x_shift(m.prog_1_position[0]), y_shift(m.prog_1_position[1]), -(total_body_height)/2))(
        needle_array(1, 5, m.needle_diameter, m.needle_root_height),
    )

    body -= translate((x_shift(m.exp_trh_1_position[0]), y_shift(m.exp_trh_1_position[1]), -(total_body_height)/2))(
        needle_array(3, 2, m.needle_diameter,
                     m.needle_root_height, rotation=180),
    )

    body -= translate((x_shift(m.rs232_1_position[0]), y_shift(m.rs232_1_position[1]), -(total_body_height)/2))(
        needle_array(1, 4, m.needle_diameter, m.needle_root_height),
    )

    body -= translate((x_shift(m.tastiera_1_position[0]), y_shift(m.tastiera_1_position[1]), -(total_body_height)/2))(
        needle_array(1, 7, m.needle_diameter, m.needle_root_height),
    )

    body -= translate((x_shift(m.coin_1_position[0]), y_shift(m.coin_1_position[1]), -(total_body_height)/2))(
        needle_array(5, 2, m.needle_diameter,
                     m.needle_root_height, rotation=180),
    )

    body -= translate((x_shift(m.ptc_1_position[0]), y_shift(m.ptc_1_position[1]), -(total_body_height)/2))(
        needle_array(1, 2, m.needle_diameter,
                     m.needle_root_height, rotation=-180),
    )

    body -= translate((x_shift(m.ch_0_10v_1_position[0]), y_shift(m.ch_0_10v_1_position[1]), -(total_body_height)/2))(
        needle_array(1, 4, m.needle_diameter,
                     m.needle_root_height, rotation=-180),
    )

    body -= translate((x_shift(m.alm_10v_1_position[0]), y_shift(m.alm_10v_1_position[1]), -(total_body_height)/2))(
        needle_array(2, 1, m.needle_diameter, m.needle_root_height,
                     distance=3.96, rotation=-180),
    )

    body -= translate((x_shift(m.alm_24v_1_position[0]), y_shift(m.alm_24v_1_position[1]), -(total_body_height)/2))(
        needle_array(2, 1, m.needle_diameter, m.needle_root_height,
                     distance=3.96, rotation=-180),
    )

    body -= translate((x_shift(m.out1_1_position[0]), y_shift(m.out1_1_position[1]), -(total_body_height)/2))(
        needle_array(6, 1, m.needle_diameter, m.needle_root_height,
                     distance=3.96, rotation=-180),
    )

    body -= translate((x_shift(m.out2_1_position[0]), y_shift(m.out2_1_position[1]), -(total_body_height)/2))(
        needle_array(6, 1, m.needle_diameter, m.needle_root_height,
                     distance=3.96, rotation=-180),
    )

    body -= translate((x_shift(m.input_1_position[0]), y_shift(m.input_1_position[1]), -(total_body_height)/2))(
        needle_array(1, 6, m.needle_diameter, m.needle_root_height,
                     distance=3.96, rotation=-180),
    )

    return body


def main():
    m = Measures()
    piece = build_cradle(m)
    #piece += translate((-(m.pcb_width-m.thickness)/2-m.hinge_diameter, m.center_left_column_y(), -(
    #    m.needle_root_height+m.needle_spring_play-m.hinge_diameter)/2))(color("red")(build_jaw(m, m.left_column_distance_y())))
    piece = translate((+(m.pcb_width-m.thickness)/2+m.hinge_diameter, m.center_right_column_y(), -(
        m.needle_root_height+m.needle_spring_play-m.hinge_diameter)/2))(color("red")(mirror((1,0,0))(build_jaw(m, m.right_column_distance_y()))))

    scad_render_to_file(scad_inline("\n$fn=64;\n") +
                        piece, "paperoga.scad")


if __name__ == "__main__":
    main()
