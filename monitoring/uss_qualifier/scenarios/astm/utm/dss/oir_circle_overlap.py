"""API regression for circular OIR overlap at the S2 covering boundary."""

from datetime import UTC, datetime, timedelta

from uas_standards.astm.f3548.v21.api import (
    OperationalIntentState,
    PutOperationalIntentReferenceParameters,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geo import Circle
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.ids import register_resource_type
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DSSInstanceResource,
)
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.fragments.oir import (
    crud as oir_fragments,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class OIRCircleOverlap(TestScenario):
    """Check that a small circle overlapping the edge of a larger OIR is searchable."""

    OIR_TYPE = register_resource_type(
        407, "Circle overlap operational intent reference"
    )

    # Fixed Kentland fixture: changing coordinates may hide the S2 boundary bug.
    # All circles are inside the default test area; the OIR covers ~3.8 km².
    _OIR_CIRCLE = Circle.from_meters(37.2010000000, -80.5760000000, 1100)
    _BOUNDARY_QUERY = Circle.from_meters(37.2001131858, -80.5883072609, 1)
    _DISTANT_QUERY = Circle.from_meters(37.201, -80.546, 1)
    _INNER_QUERY = Circle.from_meters(37.201, -80.576, 200)

    _dss: DSSInstance

    def __init__(self, dss: DSSInstanceResource, id_generator: IDGeneratorResource):
        super().__init__()
        self._dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "create and query operational intent references"
            }
        )
        self._pid = [self._dss.participant_id]
        self._oir_id = id_generator.id_factory.make_id(self.OIR_TYPE)
        self._created_oir = None

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Setup")
        self._cleanup_known_oir("Clear previous test OIR")
        self.end_test_case()

        self.begin_test_case("Discover an OIR through an overlapping circle")
        start = datetime.now(UTC) + timedelta(minutes=5)
        end = start + timedelta(minutes=60)
        self.begin_test_step("Create large circular OIR")
        params = PutOperationalIntentReferenceParameters(
            extents=[
                Volume4D.from_values(
                    t0=start, t1=end, alt0=30, alt1=120, circle=self._OIR_CIRCLE
                ).to_f3548v21()
            ],
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=make_fake_url(),
            subscription_id=None,
        )
        self._created_oir, _, _ = oir_fragments.create_oir_query(
            scenario=self, dss=self._dss, oir_id=self._oir_id, oir_params=params
        )
        self.end_test_step()

        # Each case changes one query dimension while keeping the OIR unchanged.
        cases = [
            # A: Catch the original false negative near the circle boundary.
            (
                "Boundary overlap is discoverable",
                self._BOUNDARY_QUERY,
                start,
                end,
                30,
                120,
                True,
            ),
            # B: Reject an OIR outside the horizontal search area.
            (
                "Distant circle does not match",
                self._DISTANT_QUERY,
                start,
                end,
                30,
                120,
                False,
            ),
            # C: Reject a match outside the requested altitude range.
            (
                "Disjoint altitude does not match",
                self._BOUNDARY_QUERY,
                start,
                end,
                250,
                350,
                False,
            ),
            # D: Reject an OIR outside the requested time window.
            (
                "Disjoint time does not match",
                self._BOUNDARY_QUERY,
                end + timedelta(minutes=10),
                end + timedelta(minutes=40),
                30,
                120,
                False,
            ),
            # E: Keep a normal positive control, away from the boundary.
            (
                "Ordinary contained circle is discoverable",
                self._INNER_QUERY,
                start,
                end,
                30,
                120,
                True,
            ),
        ]
        for title, circle, t0, t1, alt0, alt1, expected in cases:
            self.begin_test_step(title)
            query = Volume4D.from_values(
                t0=t0, t1=t1, alt0=alt0, alt1=alt1, circle=circle
            ).to_f3548v21()
            with self.check(title, self._pid) as check:
                try:
                    found, response = self._dss.find_op_intent(query)
                    self.record_query(response)
                    ids = {oir.id for oir in found}
                    # Check the specific OIR, not just whether HTTP returned 200.
                    actual = self._oir_id in ids
                    if actual != expected:
                        check.record_failed(
                            summary=(
                                "Overlapping OIR was missing"
                                if expected
                                else "OIR was returned for a disjoint 4D query"
                            ),
                            details=(
                                f"Case: {title}; expected_found={expected}; "
                                f"actual_found={actual}; expected_id={self._oir_id}; "
                                f"returned_ids={sorted(ids)}; "
                                f"query_time=[{t0.isoformat()}, {t1.isoformat()}]; "
                                f"query_altitude_m=[{alt0}, {alt1}]"
                            ),
                            query_timestamps=[response.request.timestamp],
                        )
                except QueryError as e:
                    self.record_queries(e.queries)
                    check.record_failed(
                        summary=f"Search failed: {title}",
                        details=f"HTTP {e.cause_status_code}: {e.msg}",
                        query_timestamps=e.query_timestamps,
                    )
            self.end_test_step()

        self.begin_test_step("Delete large circular OIR")
        oir_fragments.delete_oir_query(
            scenario=self,
            dss=self._dss,
            oir_id=self._oir_id,
            ovn=self._created_oir.ovn,
        )
        self._created_oir = None
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _cleanup_known_oir(self, name: str):
        self.begin_test_step(name)
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        self.end_cleanup()
