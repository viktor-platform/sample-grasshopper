"""Copyright (c) 2022 VIKTOR B.V.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

VIKTOR B.V. PROVIDES THIS SOFTWARE ON AN "AS IS" BASIS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from io import BytesIO
from io import TextIOWrapper
from pathlib import Path

from viktor import Color
from viktor.core import ViktorController
from viktor.external.generic import GenericAnalysis
from viktor.geometry import CircularExtrusion
from viktor.geometry import Extrusion
from viktor.geometry import Group
from viktor.geometry import Line
from viktor.geometry import Material
from viktor.geometry import Point
from viktor.geometry import RectangularExtrusion
from viktor.views import DataGroup
from viktor.views import DataItem
from viktor.views import GeometryAndDataResult
from viktor.views import GeometryAndDataView

from .parametrization import GrasshopperParametrization


class GrasshopperController(ViktorController):
    """Controller class which acts as interface for the Grasshopper entity type."""
    label = "Grasshopper"
    parametrization = GrasshopperParametrization
    viktor_convert_entity_field = True

    @GeometryAndDataView('3D model', duration_guess=10)
    def visualize(self, params, **kwargs):
        """Visualizes the 3d model of the grasshopper design and displays the data returned from it."""
        # Create all files needed to send to the worker
        with open(Path(__file__).parent / 'data' / 'sample_app.3dm', 'rb') as rhino_file:
            rhino_file_buffer = BytesIO(rhino_file.read())
        with open(Path(__file__).parent / 'data' / 'sample_app_gh.gh', 'rb') as grasshopper_file:
            grasshopper_file_buffer = BytesIO(grasshopper_file.read())
        input_str = f'{params.input.pitch_width}, {params.input.Offset}, {params.input.Shape}, {params.input.Depth}, ' \
                    f'{params.input.Asymmetry_length}, {params.input.Asymmetry_width}, {params.input.Height}'
        files = [
            ('input.txt', BytesIO(bytes(input_str, 'utf8'))),
            ('sample_app.3dm', rhino_file_buffer),
            ('sample_app_gh.gh', grasshopper_file_buffer)
        ]

        # Run the analysis and obtain the output file
        generic_analysis = GenericAnalysis(files=files, executable_key="run_grasshopper",
                                           output_filenames=["output.txt"])
        generic_analysis.execute(timeout=60)
        grass_hopper_data_bytes = generic_analysis.get_output_file("output.txt")
        wrapper = TextIOWrapper(grass_hopper_data_bytes, encoding='utf-8')
        grass_hopper_data = wrapper.read().splitlines()

        amount_of_seats = grass_hopper_data[0]
        field_width = float(grass_hopper_data[1]) * 2
        field_length = float(grass_hopper_data[2]) * 2
        triangle_strings = grass_hopper_data[3:]

        # Create results for view
        seats_amount = DataGroup(DataItem("Number of seats", amount_of_seats))
        geometry_group = self.generate_geometry_group_from_triangles(field_length, field_width, triangle_strings)
        return GeometryAndDataResult(geometry_group, seats_amount)

    def generate_geometry_group_from_triangles(self, field_length, field_width, triangle_strings):
        """Parses a line of 3 points to 3 circular beams to form a triangle"""
        geometry_group = Group([])
        for triangle_string in triangle_strings:
            point_a, point_b, point_c = self.parse_triangle_string(triangle_string)
            geometry_group.add(CircularExtrusion(0.5, Line(point_a, point_b)))
            geometry_group.add(CircularExtrusion(0.5, Line(point_a, point_c)))
            geometry_group.add(CircularExtrusion(0.5, Line(point_b, point_c)))

        field_obj = RectangularExtrusion(field_width, field_length, Line(Point(0, 0, 0), Point(0, 0, 0.1)))
        field_obj.material = Material('grass', color=Color.green())
        geometry_group.add(field_obj)

        mid_line = RectangularExtrusion(1, field_length, Line(Point(0, 0, 0), Point(0, 0, 0.4)))
        mid_line.material = Material('line', color=Color.white())
        geometry_group.add(mid_line)

        mid_circle_obj = CircularExtrusion(14, Line(Point(0, 0, 0), Point(0, 0, 0.2)))
        mid_circle_obj.material = Material('line', color=Color.white(), threejs_opacity=0.9)
        geometry_group.add(mid_circle_obj)

        mid_circle_inside_obj = CircularExtrusion(12, Line(Point(0, 0, 0), Point(0, 0, 0.3)))
        mid_circle_inside_obj.material = Material('grass', color=Color.green(), threejs_opacity=1)
        geometry_group.add(mid_circle_inside_obj)

        mid_point_obj = CircularExtrusion(1.5, Line(Point(0, 0, 0), Point(0, 0, 0.4)))
        mid_point_obj.material = Material('line', color=Color.white(), threejs_opacity=0.9)
        geometry_group.add(mid_point_obj)

        return geometry_group

    @staticmethod
    def parse_triangle_string(triangle_string):
        """Parses a string like "{0, 0, 0},{1, 1, 1},{2, 2, 2}" to 3 points."""
        points = []
        for point_str in triangle_string[1:-1].split("},{"):
            coordinates = [float(coordinate_str) for coordinate_str in point_str.split(',')]
            points.append(Point(coordinates[0], coordinates[1], coordinates[2]))
        return points[0], points[1], points[2]
