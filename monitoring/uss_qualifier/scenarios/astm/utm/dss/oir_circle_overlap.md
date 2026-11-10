# ASTM SCD DSS: OIR circle overlap test scenario

## Overview

Tests the DSS operational intent reference search API when a small query circle
overlaps a larger registered circle close to its boundary. This is an HTTP-level
regression for the false negative fixed in interuss/dss#1914.

The coordinates are an intentionally fixed, previously verified regression
fixture. Both circles are within the default Kentland planning-area rectangle; the
1.1 km reference circle is below the maximum allowed area. Run against a test DSS that accepts this
geographical area. Both request volumes share time and altitude bounds.

## Resources

### dss

A DSS instance with ASTM F3548-21 Strategic Coordination permission, used to
create, search, and delete operational intent references.

### id_generator

An `IDGeneratorResource` supplying a dedicated test OIR ID.

## Setup test case

### Clear previous test OIR test step

Remove an OIR left by a previous run, if it exists.

#### 🛑 Operational intent references can be queried by ID check

Retrieving an OIR by ID must succeed or return 404 when absent;
otherwise **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)** is violated.

#### 🛑 Operational intent reference removed check

A test-owned OIR must be removable by ID and correct OVN under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Discover an OIR through an overlapping circle test case

### Create large circular OIR test step

Create an accepted OIR with a 1,100 m circular footprint and matching
time and altitude bounds.

#### 🛑 Create operational intent reference query succeeds check

Valid OIR creation must succeed under **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Search with small overlapping circle test step

Query with a 1 m circle near the large circle's boundary. The two regions
geographically intersect, so the created OIR must be discoverable.

#### 🛑 Overlapping circle query finds the OIR check

A query that overlaps an OIR's 4D extent must return its reference.
A missing reference or failed query violates **[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Delete large circular OIR test step

Remove the created OIR after the search.

#### 🛑 Delete operational intent reference query succeeds check

Deleting a test-owned OIR with the correct OVN must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### Clean up test OIR test step

Remove the known OIR ID on failure or early termination.

#### ⚠️ Operational intent references can be queried by ID check

The DSS should return the reference or 404 for an absent reference
under **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Operational intent reference removed check

A test-owned OIR must be removable using the correct OVN under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.
