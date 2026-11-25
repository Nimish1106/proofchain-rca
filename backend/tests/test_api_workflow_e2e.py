"""Comprehensive API integration tests for RCA, Review, CAPA, Ingestion, and Copilot."""

from uuid import uuid4

from app.agents import capa_graph
from app.services import copilot_service, rca_service


def _create_investigation(client):
    resp = client.post(
        "/api/v1/investigations",
        json={
            "title": "Reactor Jacket Temperature Excursion",
            "product_name": "Atorvastatin Calcium API",
            "batch_number": "BATCH-INITIAL",
            "manufacturing_site": "Plant B",
            "process_stage": "Crystallization",
            "incident_description": "Temperature spiked during cooling.",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_full_rca_review_capa_workflow_via_api(client, monkeypatch):
    inv = _create_investigation(client)
    inv_id = inv["id"]

    # 1. Ingest text & email documents and verify content + download endpoints
    txt_resp = client.post(
        f"/api/v1/investigations/{inv_id}/ingest-text",
        json={
            "title": "Operator Shift Log",
            "content": "Cooling valve V-104 stuck at 20% open; reactor hit 84 C.",
        },
    )
    assert txt_resp.status_code == 201
    doc_id = txt_resp.json()["document"]["id"]

    content_resp = client.get(
        f"/api/v1/investigations/{inv_id}/documents/{doc_id}/content"
    )
    assert content_resp.status_code == 200
    assert "V-104" in content_resp.json()["pages"][0]["content"]

    dl_resp = client.get(
        f"/api/v1/investigations/{inv_id}/documents/{doc_id}/download"
    )
    assert dl_resp.status_code == 200
    assert "V-104" in dl_resp.text

    email_resp = client.post(
        f"/api/v1/investigations/{inv_id}/ingest-email",
        json={
            "subject": "Maintenance Alert V-104",
            "sender": "maint@pharma.example",
            "date": "2026-11-20",
            "body": "Actuator seal wear noted on V-104 last Tuesday.",
        },
    )
    assert email_resp.status_code == 201

    # Grab evidence IDs
    ev_resp = client.get(f"/api/v1/investigations/{inv_id}/evidence")
    assert ev_resp.status_code == 200
    evidence_items = ev_resp.json()["items"]
    assert len(evidence_items) == 2
    ev1_id = evidence_items[0]["id"]

    # 2. Mock RCA graph and run POST /rca
    class MockRCAGraph:
        def invoke(self, state):
            return {
                "hypotheses": [
                    {
                        "hypothesis_key": "H1",
                        "title": "Cooling control valve V-104 actuator sticking",
                        "description": "Valve V-104 failed to open past 20% due to seal wear.",
                        "causal_mechanism": "Reduced glycol flow caused insufficient heat removal.",
                        "evidence_links": [
                            {
                                "evidence_item_id": ev1_id,
                                "relationship_type": "supports",
                                "rationale": "Shift log records V-104 stuck at 20%.",
                            }
                        ],
                    }
                ],
                "analysis_details": {
                    "summary": "Evidence points to valve V-104 flow restriction.",
                    "analyses": [
                        {
                            "hypothesis_key": "H1",
                            "why_steps": [
                                {
                                    "step_number": 1,
                                    "question": "Why did reactor temperature reach 84 C?",
                                    "answer": "Cooling valve V-104 stuck at 20% open.",
                                    "answer_basis": "source_supported",
                                    "evidence_item_id": ev1_id,
                                },
                                {
                                    "step_number": 2,
                                    "question": "Why did valve V-104 stick at 20%?",
                                    "answer": "Suspected actuator seal wear.",
                                    "answer_basis": "hypothesis",
                                    "evidence_item_id": None,
                                },
                            ],
                            "evidence_gaps": [
                                {
                                    "gap_type": "missing_record",
                                    "description": "Valve calibration and PM history missing.",
                                    "recommended_question": "When was V-104 last serviced?",
                                    "priority": "high",
                                }
                            ],
                        }
                    ],
                    "global_gaps": [
                        {
                            "gap_type": "insufficient_detail",
                            "description": "Ambient glycol header pressure log absent.",
                            "recommended_question": "Was header pressure nominal?",
                            "priority": "medium",
                        }
                    ],
                    "warnings": ["Hypotheses remain proposed pending QA review."],
                },
                "hypothesis_generation": {"warnings": []},
            }

    monkeypatch.setattr(rca_service, "get_configured_model", lambda: "test-groq-model")
    monkeypatch.setattr(rca_service, "build_rca_graph", lambda: MockRCAGraph())

    rca_post = client.post(f"/api/v1/investigations/{inv_id}/rca")
    assert rca_post.status_code == 201
    run_data = rca_post.json()
    assert run_data["status"] == "completed"
    assert len(run_data["hypotheses"]) == 1
    hyp = run_data["hypotheses"][0]
    assert hyp["status"] == "proposed"
    assert len(hyp["why_steps"]) == 2
    assert len(hyp["evidence_gaps"]) == 1
    assert len(run_data["global_gaps"]) == 1

    # Verify list & get endpoints
    runs_list = client.get(f"/api/v1/investigations/{inv_id}/rca")
    assert runs_list.status_code == 200
    assert runs_list.json()["total"] == 1

    run_get = client.get(
        f"/api/v1/investigations/{inv_id}/rca/{run_data['id']}"
    )
    assert run_get.status_code == 200
    assert run_get.json()["id"] == run_data["id"]

    # 3. Human review: confirm hypothesis, edit why step, resolve & reopen gap
    hyp_patch = client.patch(
        f"/api/v1/investigations/{inv_id}/hypotheses/{hyp['id']}",
        json={
            "status": "confirmed_by_investigator",
            "review_note": "Confirmed via maintenance teardown.",
        },
    )
    assert hyp_patch.status_code == 200
    assert hyp_patch.json()["status"] == "confirmed_by_investigator"
    assert hyp_patch.json()["reviewed_at"] is not None

    step2 = hyp["why_steps"][1]
    step_patch = client.patch(
        f"/api/v1/investigations/{inv_id}/why-steps/{step2['id']}",
        json={"answer": "Confirmed actuator O-ring degradation during teardown."},
    )
    assert step_patch.status_code == 200
    assert "O-ring" in step_patch.json()["answer"]

    # Empty answer on source_supported step should fail validation (422)
    step1 = hyp["why_steps"][0]
    bad_step_patch = client.patch(
        f"/api/v1/investigations/{inv_id}/why-steps/{step1['id']}",
        json={"answer": "   "},
    )
    assert bad_step_patch.status_code == 422

    gap = hyp["evidence_gaps"][0]
    gap_patch = client.patch(
        f"/api/v1/investigations/{inv_id}/evidence-gaps/{gap['id']}",
        json={"status": "addressed", "resolution_note": "PM log attached."},
    )
    assert gap_patch.status_code == 200
    assert gap_patch.json()["status"] == "addressed"
    assert gap_patch.json()["resolved_at"] is not None

    reopen_patch = client.patch(
        f"/api/v1/investigations/{inv_id}/evidence-gaps/{gap['id']}",
        json={"status": "open"},
    )
    assert reopen_patch.status_code == 200
    assert reopen_patch.json()["resolved_at"] is None

    # 4. CAPA generation (two-stage LangGraph: generation + stress test) & review
    calls = []

    def fake_capa_groq(*, messages, schema_name, json_schema):
        calls.append(schema_name)
        if schema_name == "capa_generation":
            return {
                "recommendations": [
                    {
                        "hypothesis_key": "H1",
                        "capa_type": "corrective",
                        "title": "Replace V-104 actuator seals",
                        "description": "Install PTFE-lined actuator seals on V-104.",
                        "expected_outcome": "Restore full 0-100% valve travel.",
                        "verification_method": "Stroke test across full range.",
                        "effectiveness_criteria": "Zero sticking over 10 consecutive cycles.",
                        "priority": "high",
                        "residual_risk": "Future elastomer wear if PM interval too long.",
                    }
                ],
                "summary": "Draft CAPAs addressing V-104.",
                "warnings": [],
            }
        return {
            "recommendations": [
                {
                    "hypothesis_key": "H1",
                    "capa_type": "corrective",
                    "title": "Replace V-104 actuator seals and bench-calibrate",
                    "description": "Install PTFE-lined actuator seals on V-104 and update torque spec.",
                    "expected_outcome": "Restore full 0-100% valve travel under load.",
                    "verification_method": "3-cycle hot/cold stroke test at operating pressure.",
                    "effectiveness_criteria": "100% stroke accuracy within +/-1% across 30 days.",
                    "priority": "high",
                    "residual_risk": "Residual risk: adjacent valves V-105/V-106 share same seal batch.",
                },
                {
                    "hypothesis_key": "H1",
                    "capa_type": "preventive",
                    "title": "Add quarterly PM inspection for all cooling actuators",
                    "description": "Inspect and log actuator stroke response quarterly across Plant B.",
                    "expected_outcome": "Early wear detection prior to batch deviation.",
                    "verification_method": "Audit CMMS schedule completion.",
                    "effectiveness_criteria": "Zero valve-related temperature excursions over 12 months.",
                    "priority": "medium",
                    "residual_risk": "PM compliance depends on maintenance scheduling.",
                },
            ],
            "summary": "Stress-tested CAPAs with objective verification criteria.",
            "warnings": ["Check sibling valves V-105 and V-106."],
        }

    monkeypatch.setattr(capa_graph, "generate_structured_response", fake_capa_groq)

    capa_post = client.post(f"/api/v1/investigations/{inv_id}/capa")
    assert capa_post.status_code == 201
    assert calls == ["capa_generation", "capa_stress_test"]
    capas = capa_post.json()["items"]
    assert len(capas) == 2
    assert capas[0]["status"] == "proposed"

    capa_patch = client.patch(
        f"/api/v1/investigations/{inv_id}/capa/{capas[0]['id']}",
        json={"status": "approved", "review_note": "Approved by QA Lead."},
    )
    assert capa_patch.status_code == 200
    assert capa_patch.json()["status"] == "approved"


def test_copilot_targeted_edit_preserves_unrelated_fields(client, monkeypatch):
    inv = _create_investigation(client)
    inv_id = inv["id"]

    def fake_copilot_groq(*, messages, schema_name, json_schema):
        return {
            "message": "I suggest updating batch_number to BATCH-2026-09.",
            "suggested_edits": [
                {
                    "field_name": "batch_number",
                    "current_value": "BATCH-INITIAL",
                    "suggested_value": "BATCH-2026-09",
                    "rationale": "Matches deviation report header.",
                }
            ],
            "warnings": [],
        }

    monkeypatch.setattr(
        copilot_service, "generate_structured_response", fake_copilot_groq
    )

    ask_resp = client.post(
        f"/api/v1/investigations/{inv_id}/copilot",
        json={"message": "Update batch number to BATCH-2026-09"},
    )
    assert ask_resp.status_code == 200
    data = ask_resp.json()
    assert len(data["suggested_edits"]) == 1
    assert data["suggested_edits"][0]["field_name"] == "batch_number"

    apply_resp = client.post(
        f"/api/v1/investigations/{inv_id}/copilot/apply",
        json={"edits": data["suggested_edits"]},
    )
    assert apply_resp.status_code == 200
    updated = apply_resp.json()
    assert updated["batch_number"] == "BATCH-2026-09"
    # Unrelated fields remain intact
    assert updated["product_name"] == "Atorvastatin Calcium API"
    assert updated["manufacturing_site"] == "Plant B"
    assert updated["process_stage"] == "Crystallization"
    assert updated["title"] == "Reactor Jacket Temperature Excursion"


def test_list_rca_and_capa_for_missing_investigation_returns_404(client):
    fake_id = str(uuid4())
    assert client.get(f"/api/v1/investigations/{fake_id}/rca").status_code == 404
    assert client.get(f"/api/v1/investigations/{fake_id}/capa").status_code == 404


def test_accept_and_apply_human_readable_date_on_existing_evidence(client, monkeypatch):
    """Ensure human-readable dates like '20 November 2026' apply as ISO YYYY-MM-DD."""
    inv = _create_investigation(client)
    inv_id = inv["id"]

    # Update directly via PATCH using human-readable date
    patch_resp = client.patch(
        f"/api/v1/investigations/{inv_id}",
        json={"incident_date": "20 November 2026"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["incident_date"] == "2026-11-20"

    # Also via Copilot targeted edit
    apply_resp = client.post(
        f"/api/v1/investigations/{inv_id}/copilot/apply",
        json={
            "edits": [
                {
                    "field_name": "incident_date",
                    "current_value": "2026-11-20",
                    "suggested_value": "21st November 2026",
                    "rationale": "Corrected from batch log.",
                }
            ]
        },
    )
    assert apply_resp.status_code == 200
    assert apply_resp.json()["incident_date"] == "2026-11-21"
