from django.test import TestCase

# Create your tests here.

from shapely.geometry import LineString, Point
from shapely.ops import nearest_points
import matplotlib.pyplot as plt

l1 = LineString([(0,0), (-5,0), (-5,-3)])
l2 = LineString([(-2,-3), (-2,1), (3,1)])
# l2 = LineString([(-3,-3), (-3,0), (-6,0)])

x,y = l1.xy
plt.plot(x,y)

# x,y = l2.xy
# plt.plot(x,y)

# if l1.intersects(l2):
#     intersection = l1.intersection(l2)
#     if intersection.geom_type == 'Point':
#         x,y = intersection.x, intersection.y
#         plt.plot(x,y, marker='o', markersize=10)
#         plt.show()
#     elif intersection.geom_type == 'LineString':
#         x,y = intersection.xy
#         plt.plot(x,y, marker='o', markersize=10)
#         plt.show()

# point = Point((-1.5,-0.2))
# x,y = point.x, point.y
# plt.plot(x,y, marker='o', markersize=10)

# near_point, near_line = nearest_points(point, l1)
# x,y = near_line.x, near_line.y
# plt.plot(x,y, marker='x', markersize=10)

# plt.show()