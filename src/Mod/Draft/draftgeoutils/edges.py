# ***************************************************************************
# *   Copyright (c) 2009, 2010 Yorik van Havre <yorik@uncreated.net>        *
# *   Copyright (c) 2009, 2010 Ken Cline <cline@frii.com>                   *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with FreeCAD; if not, write to the Free Software        *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************
"""Provides various functions for using edges."""
## @package edges
# \ingroup DRAFTGEOUTILS
# \brief Provides various functions for using edges.

import lazy_loader.lazy_loader as lz

import FreeCAD
import DraftVecUtils

from draftgeoutils.general import geomType

# Delay import of module until first use because it is heavy
Part = lz.LazyLoader("Part", globals(), "Part")


def findEdge(anEdge, aList):
    """Return True if edge is found in list of edges."""
    for e in range(len(aList)):
        if str(anEdge.Curve) == str(aList[e].Curve):
            if DraftVecUtils.equals(anEdge.Vertexes[0].Point,
                                    aList[e].Vertexes[0].Point):
                if DraftVecUtils.equals(anEdge.Vertexes[-1].Point,
                                        aList[e].Vertexes[-1].Point):
                    return e
    return None


def orientEdge(edge, normal=None, make_arc=False):
    """Re-orient the edge such that it is in the XY plane.

    Re-orients `edge` such that it is in the XY plane.
    If `normal` is passed, this is used as the basis for the rotation,
    otherwise the placement of `edge` is used.
    """
    # This 'normalizes' the placement to the xy plane
    edge = edge.copy()
    xyDir = FreeCAD.Vector(0, 0, 1)
    base = FreeCAD.Vector(0, 0, 0)

    if normal:
        angle = DraftVecUtils.angle(normal, xyDir) * FreeCAD.Units.Radian
        axis = normal.cross(xyDir)
    else:
        axis = edge.Placement.Rotation.Axis
        angle = -1*edge.Placement.Rotation.Angle*FreeCAD.Units.Radian
    if axis == FreeCAD.Vector(0.0, 0.0, 0.0):
        axis = FreeCAD.Vector(0.0, 0.0, 1.0)
    if angle:
        edge.rotate(base, axis, angle)
    if isinstance(edge.Curve, Part.Line):
        return Part.LineSegment(edge.Curve,
                                edge.FirstParameter,
                                edge.LastParameter)
    elif make_arc and isinstance(edge.Curve, Part.Circle) and not edge.Closed:
        return Part.ArcOfCircle(edge.Curve,
                                edge.FirstParameter,
                                edge.LastParameter,
                                edge.Curve.Axis.z > 0)
    elif make_arc and isinstance(edge.Curve, Part.Ellipse) and not edge.Closed:
        return Part.ArcOfEllipse(edge.Curve,
                                 edge.FirstParameter,
                                 edge.LastParameter,
                                 edge.Curve.Axis.z > 0)
    return edge.Curve


def isSameLine(e1, e2):
    """Return True if the 2 edges are lines and have the same points."""
    if not isinstance(e1.Curve, Part.LineSegment):
        return False
    if not isinstance(e2.Curve, Part.LineSegment):
        return False

    if (DraftVecUtils.equals(e1.Vertexes[0].Point,
                             e2.Vertexes[0].Point)
        and DraftVecUtils.equals(e1.Vertexes[-1].Point,
                                 e2.Vertexes[-1].Point)):
        return True
    elif (DraftVecUtils.equals(e1.Vertexes[-1].Point,
                               e2.Vertexes[0].Point)
          and DraftVecUtils.equals(e1.Vertexes[0].Point,
                                   e2.Vertexes[-1].Point)):
        return True
    return False


def isLine(bspline):
    """Return True if the given BSpline curve is a straight line."""
    step = bspline.LastParameter/10
    b = bspline.tangent(0)

    for i in range(10):
        if bspline.tangent(i * step) != b:
            return False
    return True


def invert(shape):
    """Return an inverted copy of the edge or wire contained in the shape."""
    if shape.ShapeType == "Wire":
        edges = [invert(edge) for edge in shape.OrderedEdges]
        edges.reverse()
        return Part.Wire(edges)
    elif shape.ShapeType == "Edge":
        if len(shape.Vertexes) == 1:
            return shape
        if geomType(shape) == "Line":
            return Part.LineSegment(shape.Vertexes[-1].Point,
                                    shape.Vertexes[0].Point).toShape()
        elif geomType(shape) == "Circle":
            mp = findMidpoint(shape)
            return Part.Arc(shape.Vertexes[-1].Point,
                            mp,
                            shape.Vertexes[0].Point).toShape()
        elif geomType(shape) in ["BSplineCurve", "BezierCurve"]:
            if isLine(shape.Curve):
                return Part.LineSegment(shape.Vertexes[-1].Point,
                                        shape.Vertexes[0].Point).toShape()

        print("DraftGeomUtils.invert: unable to invert", shape.Curve)
        return shape
    else:
        print("DraftGeomUtils.invert: unable to handle", shape.ShapeType)
        return shape


def findMidpoint(edge):
    """Return the midpoint of a straight line or circular edge."""
    first = edge.Vertexes[0].Point
    last = edge.Vertexes[-1].Point

    if geomType(edge) == "Circle":
        center = edge.Curve.Center
        radius = edge.Curve.Radius
        if len(edge.Vertexes) == 1:
            # Circle
            dv = first.sub(center)
            dv = dv.negative()
            return center.add(dv)

        axis = edge.Curve.Axis
        chord = last.sub(first)
        perp = chord.cross(axis)
        perp.normalize()
        ray = first.sub(center)
        apothem = ray.dot(perp)
        sagitta = radius - apothem
        startpoint = FreeCAD.Vector.add(first, chord.multiply(0.5))
        endpoint = DraftVecUtils.scaleTo(perp, sagitta)
        return FreeCAD.Vector.add(startpoint, endpoint)

    elif geomType(edge) == "Line":
        halfedge = (last.sub(first)).multiply(0.5)
        return FreeCAD.Vector.add(first, halfedge)

    else:
        return None
