import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.join(root_dir, "backend"))

# Helper to generate JWT token using existing backend.auth
from backend import auth

BASE_URL = "http://127.0.0.1:8000/api"

def get_token_for(user_id: str, role: str) -> str:
    return auth.make_token(user_id=user_id, role=role)

def request(method: str, path: str, token: str = None, data: dict = None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            return resp.status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except Exception:
            return e.code, {"error": err_body}

def run_tests():
    print("=" * 60)
    print("NIVARA COMPLETE WORKFLOW INTEGRATION E2E VERIFICATION")
    print("=" * 60)

    # 1. Setup Identities
    # Officer: Officer Sharma / duty officer in DB
    officer_id = "58d3d6b5-fc0a-49d5-9492-ecd22dd9d5eb"
    officer_email = "officer.sharma@police.gov.in"
    officer_token = get_token_for(officer_id, "officer")

    # Victim: Shruthi (existing user)
    victim_id = "74cbe76b-2c5b-4908-aac1-97406f83f8da"
    victim_email = "shruthi@gmail.com"
    victim_token = get_token_for(victim_id, "victim")

    print(f"\n[1] Officer Token generated for: {officer_email} ({officer_id})")
    print(f"[1] Victim Token generated for: {victim_email} ({victim_id})")

    # 2. Test Complaint Creation (Victim Side)
    print("\n--- Part 1: Victim File Complaint Flow ---")
    complaint_payload = {
        "title": "Verifiable Harassment & Stalking Complaint",
        "description": "Perpetrator followed me from metro station to residence and issued verbal threats.",
        "category": "stalking",
        "incident_location": "OMR Main Road near Karapakkam Junction",
        "incident_date": "2026-10-30",
        "priority": "high",
        "evidence_notes": "CCTV footage requested from nearby shop"
    }
    status, res = request("POST", "/complaints", token=victim_token, data=complaint_payload)
    print(f"POST /complaints -> HTTP {status}")
    assert status == 200, f"Complaint creation failed: {res}"
    assert res.get("ok") is True, "Expected ok=True"
    case_id = res["case_id"]
    ref_num = res.get("reference_number")
    ack_status = res.get("acknowledgment_status")
    print(f"Created Case ID: {case_id}")
    print(f"Reference Number: {ref_num}")
    print(f"Acknowledgment Status: {ack_status}")
    print(f"SVI Score: {res.get('svi_score')} ({res.get('risk_level')})")
    assert ref_num.startswith("CMP-"), f"Reference number should start with CMP-, got {ref_num}"
    assert ack_status == "unassigned", f"Expected unassigned, got {ack_status}"
    assert res.get("svi_score") == 60, f"Expected SVI 60 for high priority, got {res.get('svi_score')}"

    # 3. Officer Unassigned/Triage Queue Verification
    print("\n--- Part 1 & 2: Officer Dashboard Queue & Triage ---")
    status, cases = request("GET", "/cases/mine", token=officer_token)
    print(f"GET /cases/mine -> HTTP {status}, Total cases: {len(cases)}")
    assert status == 200, f"Failed to fetch officer cases: {cases}"

    # Find the created case in officer queue
    created_case = next((c for c in cases if c["id"] == case_id), None)
    assert created_case is not None, f"Created case {case_id} not found in officer queue!"
    print(f"Found created case in Officer Queue:")
    print(f"  ID: {created_case['id']}")
    print(f"  Reference Number: {created_case.get('reference_number')}")
    print(f"  Category: {created_case.get('category')}")
    print(f"  Priority: {created_case.get('priority')}")
    print(f"  Ack Status: {created_case.get('acknowledgment_status')}")
    print(f"  Officer ID: {created_case.get('officer_id')} (Awaiting duty officer claim)")
    assert created_case.get("acknowledgment_status") == "unassigned"

    # 4. Check Reference Case Data Integrity (CMP-85C4FF03)
    ref_case_id = "85c4ff03-dbb6-40e7-a562-42b5b281ac50"
    print(f"\n--- Part 3-8: Case Detail & Data Integrity for Reference Case ({ref_case_id}) ---")
    status, ref_detail = request("GET", f"/cases/{ref_case_id}", token=officer_token)
    print(f"GET /cases/{ref_case_id} -> HTTP {status}")
    assert status == 200, f"Failed to get reference case: {ref_detail}"

    rc = ref_detail["case"]
    print(f"Reference Case Core Fields:")
    print(f"  Reference Number: {rc.get('reference_number')}")
    print(f"  Victim Name: {rc.get('victim_name')}")
    print(f"  Victim Phone: {rc.get('victim_phone')}")
    print(f"  Victim Blood Group: {rc.get('victim_blood_group')}")
    print(f"  Reported Address: {rc.get('incident_location')}")
    print(f"  Live GPS: ({rc.get('latitude')}, {rc.get('longitude')})")
    print(f"  SVI Score: {rc.get('svi_score')} ({rc.get('risk_level')})")
    print(f"  Priority: {rc.get('priority')}")

    assert rc.get("reference_number") == "CMP-85C4FF03", f"Expected CMP-85C4FF03, got {rc.get('reference_number')}"
    assert rc.get("svi_score") == 85, f"Expected SVI 85, got {rc.get('svi_score')}"
    assert rc.get("risk_level") == "Critical", f"Expected Critical, got {rc.get('risk_level')}"
    assert rc.get("incident_location") == "Undisclosed Location"
    assert abs(rc.get("latitude") - 12.835269) < 0.001
    assert abs(rc.get("longitude") - 80.218959) < 0.001
    assert rc.get("victim_name") == "shruthi"
    assert rc.get("victim_phone") == "6380630473"
    assert rc.get("victim_blood_group") == "B+"

    # Verify honest sub-scores
    print(f"\nSub-scores honesty check:")
    print(f"  latest_analysis: {ref_detail.get('latest_analysis')}")
    print(f"  assessment: {ref_detail.get('assessment')}")
    print(f"  voice_analysis: {ref_detail.get('voice_analysis')}")
    assert ref_detail.get("latest_analysis") is None, "Should be None (Not Assessed) for emergency intake without NLP run"
    assert ref_detail.get("assessment") is None, "Should be None (Not Assessed)"

    # Verify recommendations engine
    recs = ref_detail.get("recommendations", [])
    print(f"\nRecommendations generated for SVI 85 Critical case: count={len(recs)}")
    for r in recs:
        rtype = r.get("type") or r.get("action") or ""
        rdesc = r.get("description") or r.get("rationale") or ""
        print(f"  - [{r.get('priority', '').upper()}] {rtype}: {rdesc}")
    assert len(recs) >= 3, "Expected at least 3 critical recommendations"
    assert any("Dispatch" in (r.get("type") or "") or "Police" in (r.get("type") or "") or "Immediate" in (r.get("type") or "") for r in recs)

    # Escalation risk forecast check
    status, fcast = request("GET", f"/analytics/escalation-risk/{ref_case_id}", token=officer_token)
    print(f"\nGET /analytics/escalation-risk/{ref_case_id} -> HTTP {status}")
    assert status == 200
    print(f"  Current SVI: {fcast.get('current_svi')}")
    print(f"  Velocity: {fcast.get('escalation_velocity')}")
    print(f"  Danger Window: {fcast.get('danger_window_hours')}")
    print(f"  Trajectory Pct: {fcast.get('trajectory_pct')}")
    print(f"  Risk Factors: {fcast.get('risk_factors')}")
    print(f"  Recommended Action: {fcast.get('recommended_action')}")
    print(f"  Risk Curve: {fcast.get('risk_curve')}")

    assert fcast.get("current_svi") == 85
    assert fcast.get("predicted_threat_level") == "CRITICAL THREAT"
    assert "Immediate" in fcast.get("danger_window_hours", "")
    assert "active patrol check-in" in fcast.get("recommended_action", "").lower()
    assert any(rf.get("factor") == "Reported Incident Narrative Severity" for rf in fcast.get("risk_factors", []))
    assert len(fcast.get("risk_curve", [])) >= 3
    # Verify trajectory curve values: baseline 85, +12h: 92, +24h: 100
    curve_scores = [pt["score"] for pt in fcast.get("risk_curve", [])]
    assert curve_scores == [85, 92, 100], f"Expected curve [85, 92, 100], got {curve_scores}"

    # 5. Test All 7 Officer Actions on the Newly Created Case
    print(f"\n--- Part 9: Test All 7 Officer Actions on Case {case_id} ---")

    # Action A: Acknowledge & Claim
    print("\n[Action A] Acknowledge & Claim Case")
    status, ack_res = request("POST", "/officer/action", token=officer_token, data={
        "case_id": case_id,
        "action": "acknowledged",
        "notes": "Acknowledged by Duty Officer Sharma. Initiating triage."
    })
    print(f"POST /officer/action (acknowledged) -> HTTP {status}: {ack_res}")
    assert status == 200
    assert ack_res.get("ok") is True

    # Test Duplicate Acknowledgment
    status, dup_ack_res = request("POST", "/officer/action", token=officer_token, data={
        "case_id": case_id,
        "action": "acknowledged"
    })
    print(f"Duplicate acknowledgment -> HTTP {status}: {dup_ack_res.get('message')}")
    assert dup_ack_res.get("already_acknowledged") is True

    # Action B: Dedicated Save Note
    print("\n[Action B] Dedicated Save Note")
    status, note_res = request("POST", "/officer/action", token=officer_token, data={
        "case_id": case_id,
        "action": "note",
        "notes": "Patrol vehicle alerted to OMR Karapakkam corridor."
    })
    print(f"POST /officer/action (note) -> HTTP {status}: {note_res}")
    assert status == 200

    # Action C: Contact Victim
    print("\n[Action C] Contact Victim Record")
    status, contact_res = request("POST", "/officer/action", token=officer_token, data={
        "case_id": case_id,
        "action": "contacted_victim",
        "outcome": "Successfully contacted",
        "notes": "Spoke directly with victim. Confirmed safe in residential society."
    })
    print(f"POST /officer/action (contacted_victim) -> HTTP {status}: {contact_res}")
    assert status == 200

    # Action D: Internal Unit Dispatch
    print("\n[Action D] Internal Dispatch")
    status, disp_res = request("POST", "/officer/action", token=officer_token, data={
        "case_id": case_id,
        "action": "dispatched_unit",
        "unit": "Patrol Unit OMR-3",
        "dispatch_status": "dispatched",
        "notes": "Mobile patrol dispatched for active area presence."
    })
    print(f"POST /officer/action (dispatched_unit) -> HTTP {status}: {disp_res}")
    assert status == 200

    # Test Duplicate Dispatch Prevention
    status, dup_disp = request("POST", "/officer/action", token=officer_token, data={
        "case_id": case_id,
        "action": "dispatched_unit",
        "unit": "Patrol Unit OMR-3",
        "dispatch_status": "dispatched"
    })
    print(f"Duplicate dispatch -> HTTP {status}: {dup_disp.get('message')}")
    assert dup_disp.get("already_dispatched") is True

    # Action E: Generate Case Summary
    print("\n[Action E] Structured Case Summary")
    status, sum_res = request("POST", f"/cases/summary/{case_id}", token=officer_token)
    print(f"POST /cases/summary/{case_id} -> HTTP {status}")
    print(f"Summary generated (source: {sum_res.get('source')}):")
    print(f"{sum_res.get('summary')}")
    assert status == 200
    assert len(sum_res.get("summary", "")) > 20

    # Action F: Case Logs & Audit Trail
    print("\n[Action F] Case Logs & Activity History")
    status, logs_resp = request("GET", f"/cases/{case_id}/logs", token=officer_token)
    entries = logs_resp.get("logs", []) if isinstance(logs_resp, dict) else logs_resp
    print(f"GET /cases/{case_id}/logs -> HTTP {status}, Total entries: {len(entries)}")
    assert status == 200
    assert len(entries) >= 4, f"Expected at least 4 log entries (ack, note, contact, dispatch), got {len(entries)}"
    for l in entries:
        print(f"  - [{l.get('source')}] {l.get('action')} by {l.get('actor_name')}: {l.get('details')}")

    # Action G: Counsellor Assignment
    print("\n[Action G] Approved Counsellor Retrieval and Assignment")
    status, counsellors = request("GET", "/users/counsellors?data_filter=approved", token=officer_token)
    print(f"GET /users/counsellors?data_filter=approved -> HTTP {status}, Count: {len(counsellors)}")
    assert status == 200
    c_names = [c["name"] for c in counsellors]
    print(f"Available counsellors: {c_names}")
    # Verify only intended counsellors Dr. Priya and shru
    assert all(name in ["Dr. Priya", "shru"] for name in c_names), f"Unexpected counsellors found: {c_names}"

    target_c = counsellors[0]
    status, assign_res = request("POST", "/officer/assign", token=officer_token, data={
        "case_id": case_id,
        "counsellor_id": target_c["id"]
    })
    print(f"POST /officer/assign -> HTTP {status}: {assign_res}")
    assert status == 200
    assert assign_res.get("ok") is True

    # 6. Verify Updated Case Detail contains all modifications
    print(f"\n--- Verify Updated Case Detail for Case {case_id} ---")
    status, updated_detail = request("GET", f"/cases/{case_id}", token=officer_token)
    assert status == 200
    uc = updated_detail["case"]
    print(f"  Status: {uc.get('status')}")
    print(f"  Ack Status: {uc.get('acknowledgment_status')} by {uc.get('acknowledged_by')}")
    print(f"  Dispatch: {uc.get('dispatch_unit')} [{uc.get('dispatch_status')}]")
    print(f"  Counsellor: {uc.get('counsellor_name')} (assigned {uc.get('assigned_at')})")
    print(f"  Contact History Count: {len(uc.get('contact_history', []))}")
    print(f"  Actions Count: {len(updated_detail.get('actions', []))}")

    assert uc.get("status") == "in_progress"
    assert uc.get("acknowledgment_status") == "acknowledged"
    assert uc.get("dispatch_status") == "dispatched"
    assert uc.get("counsellor_id") == target_c["id"]
    assert len(uc.get("contact_history", [])) == 1
    assert len(updated_detail.get("actions", [])) >= 3

    # 7. Verify Data Isolation: Reference Case was untouched
    print(f"\n--- Verify Data Isolation (Reference Case {ref_case_id}) ---")
    status, ref_check = request("GET", f"/cases/{ref_case_id}", token=officer_token)
    assert status == 200
    assert ref_check["case"]["id"] == ref_case_id
    assert ref_check["case"]["reference_number"] == "CMP-85C4FF03"
    assert ref_check["case"]["svi_score"] == 85
    print("Reference case data is completely isolated and unaltered.")

    print("\n" + "=" * 60)
    print("ALL 12 PARTS OF WORKFLOW VERIFIED SUCCESSFULLY WITH ZERO ERRORS!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(2)
