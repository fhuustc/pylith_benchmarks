#!/usr/bin/env python
# ----------------------------------------------------------------------
#
# Brad T. Aagaard, U.S. Geological Survey
#
# ----------------------------------------------------------------------
#
# Plot slip profiles over cycles.
#
# PREREQUISITES: matplotlib, numpy, tables

style = "lightbg"
fileSuffix = "pdf"
plotSize = "paper"
fontsize = 8

from pyre.units.time import year
from pyre.units.length import km,m
tcycle = 200.0*year
elastThick = 40.0*km
eqslip = 4.0*m

# ======================================================================
import matplotlib.pyplot as pyplot
import matplotlib.lines as lines
import numpy
import sys
import os

sys.path.append("../../../figures")
import matplotlibext

# import pdb
# pdb.set_trace()

header = 0.45

cells = ["Hex8",
         "Tet4",
         ]
#symdict = {'Hex8': 's',
#           'Tet4': '^',
#           }
lineStyle = [("red", (2.0, 1.0)),
             ("blue", (4.0, 1.0)),
             ("purple", (6.0, 1.0)),
             ("green", (3.0, 1.0, 1.5, 1.0)),
             ("orange", (6.0, 1.0, 1.5, 1.0)),
             ("black", (None, None)),
             ]

# ----------------------------------------------------------------------
class AnalyticSoln(object):

  def __init__(self, filename):
    from pyre.units import parser
    uparser = parser()

    fin = open(filename, "r")
    line = fin.readline()
    dt = uparser.parse(line.split("=")[1])
    line = fin.readline()
    dx = uparser.parse(line.split("=")[1])
    line = fin.readline()
    ncycles = int(line.split("=")[1])
    line = fin.readline()
    nsteps = int(line.split("=")[1])
    line = fin.readline()
    npoints = int(line.split("=")[1])

    data = numpy.loadtxt(fin).reshape( (ncycles, nsteps, npoints) )
    data /= eqslip.value # Normalize by earthquake slip

    from pyre.units.time import year

    self.dist = numpy.linspace(0.0, dx.value*(npoints-1), npoints)
    self.dist /= elastThick.value # Normalize by elastic thickness
    self.data = data
    self.time = numpy.linspace(0.0, dt.value/year.value*(nsteps-1), nsteps)
    return


  def getProfile(self, cycle, t):
    dt = self.time[1] - self.time[0]
    itime = numpy.where(numpy.fabs(self.time-t) < 0.5*dt)[0][0]
    disp = self.data[cycle,itime,:]
    return (self.dist, disp.squeeze())


# ----------------------------------------------------------------------
class PyLithOutput(object):

  def __init__(self, cell):
    filename = "output/%s-groundsurf.h5" % cell.lower()
    import tables
    h5 = tables.openFile(filename, "r")
    time = h5.root.time[:]
    vertices = h5.root.geometry.vertices[:]
    disp = h5.root.vertex_fields.displacement[:]
    h5.close()
    indices = numpy.bitwise_and(numpy.fabs(vertices[:,1]) < 1.0,
                                vertices[:,0] >= 0.0)
    dist = vertices[indices,0].squeeze()
    disp = disp[:,indices,1].squeeze()
    
    # Remove value on negative side of fault and sort distances.
    numSteps = disp.shape[0]
    dispTest = disp[numSteps -1,:]
    negInd = numpy.nonzero(dispTest < 0.0)[0][0]
    distPos = numpy.delete(dist, negInd)
    indices = numpy.argsort(distPos)
    
    self.dist = dist[indices] / elastThick.value # Normalize by elastic thickness
    self.disp = disp[:,indices] / eqslip.value # Normalize by eqslip
    self.time = time

    return


  def getProfile(self, cycle, t):
    dt = self.time[1] - self.time[0]
    tProf = tcycle.value*cycles[icycle]+t*year.value
    iProf = numpy.where(numpy.fabs(self.time-tProf) < 0.5*dt)[0][0]
    t0 = tcycle.value*cycles[icycle]
    i0 = numpy.where(numpy.fabs(self.time-t0) < 0.5*dt)[0][0]
    disp = self.disp[iProf,:] - self.disp[i0,:]
    return (self.dist, disp.squeeze())


# ----------------------------------------------------------------------
figure = matplotlibext.Figure(color=style,fontsize=fontsize)
figure.open(3.0, 4.0, margins=[[0.45, 0, 0.2], [0.4, 0.3, 0.12]], dpi=150)


ax = figure.axes(2.0+header, 1, 1.0+header, 1)

analytic = AnalyticSoln("output/analytic_disp.txt")
sims = {}
for c in cells:
  sims[c] = PyLithOutput(c)

cycles = [2,9]
snaptime = numpy.array([0.05, 0.25, 0.50, 0.75, 0.95])*tcycle.value/year.value

nrows = 2
ncols = 1
icol = 0

for irow in xrange(nrows):
  icycle = irow
  ax = figure.axes(nrows+header, ncols, irow+1+header, icol+1)

  for t in snaptime:
    coord, soln = analytic.getProfile(cycles[icycle], t)
    coord, soln0 = analytic.getProfile(cycles[icycle], 0)
    ax.plot(coord, soln-soln0, color='fg')
    ax.hold(True)

    isim = 0
    for c in cells:
      coord, soln = sims[c].getProfile(cycles[icycle], t)
      ax.plot(coord, soln, 
              color=lineStyle[isim][0],
              dashes=lineStyle[isim][1])
      isim += 1

  pyplot.text(9.9, 0.03, "t=0.05", horizontalalignment="right")
  pyplot.text(9.9, 0.13, "t=0.25", horizontalalignment="right")
  pyplot.text(9.9, 0.255, "t=0.50", horizontalalignment="right")
  pyplot.text(9.9, 0.37, "t=0.75", horizontalalignment="right")
  pyplot.text(9.9, 0.46, "t=0.95", horizontalalignment="right")

  ax.set_xlim(0, 10)
  ax.set_ylim(0, 0.5)
  ax.set_title("Earthquake Cycle %d" % (cycles[icycle]+1,))
  if irow == nrows-1:
    ax.set_xlabel("Dist. from Fault / Elastic thickness")
  else:
    ax.set_xticklabels([])
  ax.set_ylabel("Disp. / Coseismic Disp. ")


  if irow == 0 and icol == ncols-1:
    proxies = []
    proxies.append(lines.Line2D((0,0),(1,1), color='fg'))
    isim = 0
    for c in cells:
      proxies.append(lines.Line2D((0,0),(1,1), 
                                  color=lineStyle[isim][0],
                                  dashes=lineStyle[isim][1]))
      isim += 1

    ax.legend(proxies, ["Analytic"] + cells,
              loc="lower right",
              bbox_to_anchor=(1,1.2), 
              borderaxespad=0)


pyplot.show()
pyplot.savefig("savageprescott_profiles")


# End of file