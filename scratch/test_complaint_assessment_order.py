import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api"

def run_tests():
    print("=== STEP 1: Authenticate as Victim and Officer ===")
    
    # Login as victim (default test or demo victim)
    victim_login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "victim@example.com",
        "password": "password123"
    })
    if victim_login_res.status_code != 200:
        # Try registering or using test victim
        reg_res = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "Ananya Sharma",
            "email": "ananya.sharma@test.org",
            "password": "TestPassword123!",
            "role": "victim",
            "phone": "+91 98765 43210"
        })
        if reg_res.status_code in [200, 201]:
            victim_token = reg_res.json().get("access_token")
            victim_user = reg_res.json().get("user")
        else:
            login_res = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "ananya.sharma@test.org",
                "password": "TestPassword123!"
            })
            victim_token = login_res.json()["access_token"]
            victim_user = login_res.json()["user"]
    else:
        victim_token = victim_login_res.json()["access_token"]
        victim_user = victim_login_res.json()["user"]

    print(f"Victim authenticated: {victim_user.get('name')} ({victim_user.get('email')})")
    victim_headers = {"Authorization": f"Bearer {victim_token}"}

    # Login as officer
    officer_login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "officer@example.com",
        "password": "password123"
    })
    if officer_login_res.status_code != 200:
        reg_off = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "Inspector Rajesh Kumar",
            "email": "rajesh.officer@test.org",
            "password": "TestPassword123!",
            "role": "officer",
            "badge_number": "POL-9921"
        })
        if reg_off.status_code in [200, 201]:
            officer_token = reg_off.json()["access_token"]
            officer_user = reg_off.json()["user"]
        else:
            log_off = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "rajesh.officer@test.org",
                "password": "TestPassword123!"
            })
            officer_token = log_off.json()["access_token"]
            officer_user = log_off.json()["user"]
    else:
        officer_token = officer_login_res.json()["access_token"]
        officer_user = officer_login_res.json()["user"]

    print(f"Officer authenticated: {officer_user.get('name')}")
    officer_headers = {"Authorization": f"Bearer {officer_token}"}

    print("\n=== STEP 2: Submit Complaint 1 (With GPS coordinates) ===")
    complaint_payload = {
        "title": "Severe Stalking and Harassment near College Gate",
        "description": "An unidentified individual on a black motorbike has been following me repeatedly from the university library to the metro station over the past three days. Today he approached and verbally threatened me when I reached the bus stop.",
        "category": "stalking",
        "incident_date": "2026-10-29",
        "incident_location": "Gate 3, North University Campus, Metro Road",
        "priority": "high",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "suspect_details": "Male, black jacket, helmet with red visor, black Pulsar bike"
    }

    c1_res = requests.post(f"{BASE_URL}/complaints", json=complaint_payload, headers=victim_headers)
    assert c1_res.status_code == 200, f"Failed to submit complaint: {c1_res.text}"
    c1_data = c1_res.json()
    case_id_1 = c1_data["case_id"]
    ref_num_1 = c1_data["reference_number"]
    print(f"Complaint 1 Lodged successfully: Case ID = {case_id_1}, Ref = {ref_num_1}")
    print(f"Priority = {c1_data.get('priority')}, SVI = {c1_data.get('svi_score')}, Risk Level = {c1_data.get('risk_level')}")

    print("\n=== STEP 3: Verify Complaint 1 Appears in Officer Cases Queue ===")
    cases_res = requests.get(f"{BASE_URL}/cases", headers=officer_headers)
    assert cases_res.status_code == 200, f"Officer cannot list cases: {cases_res.text}"
    all_cases = cases_res.json()
    matching_case = next((c for c in all_cases if c["id"] == case_id_1), None)
    assert matching_case is not None, f"Complaint {case_id_1} not visible in officer cases list!"
    print(f"Complaint successfully visible in Officer queue! Status: {matching_case.get('status')}, Acknowledgment: {matching_case.get('acknowledgment_status')}")

    print("\n=== STEP 4: Retrieve Complete Case Detail as Officer ===")
    detail_res = requests.get(f"{BASE_URL}/cases/{case_id_1}", headers=officer_headers)
    assert detail_res.status_code == 200, f"Cannot fetch case detail: {detail_res.text}"
    detail = detail_res.json()

    print("\n=== STEP 5: Verify Order of 5 Sections in Case Data ===")
    
    # 1. VICTIM COMPLAINT DETAILS
    c_info = detail["case"]
    print("--- 1. VICTIM COMPLAINT DETAILS ---")
    print(f"Victim Name: {c_info.get('victim_name')}")
    print(f"Complaint ID: {c_info.get('reference_number')}")
    print(f"Category: {c_info.get('category')}")
    print(f"Description / Narrative: {c_info.get('description')}")
    print(f"Incident Date: {c_info.get('incident_date')}")
    print(f"Submission Timestamp: {c_info.get('created_at')}")

    assert c_info.get("victim_name") is not None, "Missing victim name"
    assert c_info.get("reference_number") == ref_num_1, "Reference number mismatch"
    assert c_info.get("category") == "stalking", "Category mismatch"
    assert c_info.get("description") == complaint_payload["description"], "Description mismatch"
    assert c_info.get("incident_date") == "2026-10-29", "Incident date mismatch"
    assert c_info.get("created_at") is not None, "Missing created_at timestamp"
    print("-> Section 1 VALIDATED.")

    # 2. TEXT RISK SCORE
    print("\n--- 2. TEXT RISK SCORE ---")
    analysis = detail.get("latest_analysis")
    assessment = detail.get("assessment")
    assert analysis is not None or assessment is not None, "Missing text risk score analysis"
    text_score = assessment.get("text_score") if assessment else analysis.get("text_score")
    risk_level = assessment.get("risk_level") if assessment else analysis.get("risk_level")
    print(f"Text Risk Score: {text_score} / 100")
    print(f"Risk Category: {risk_level}")
    print(f"Associated Case ID: {c_info.get('reference_number')}")
    assert text_score is not None and text_score > 0, "Text risk score must be > 0"
    assert risk_level in ["Low", "Moderate", "High", "Critical"], "Valid risk category required"
    print("-> Section 2 VALIDATED.")

    # 3. VOICE STRESS SCORE
    print("\n--- 3. VOICE STRESS SCORE ---")
    voice_analysis = detail.get("voice_analysis")
    voice_score = assessment.get("voice_score") if assessment else None
    print(f"Voice Analysis: {voice_analysis}")
    print(f"Voice Stress Score: {voice_score} (Expected: None / 'Not Assessed')")
    assert voice_score is None, f"Voice score should be None for text-only complaint, got: {voice_score}"
    assert voice_analysis is None, "Voice analysis should be None when no audio submitted"
    print("-> Section 3 (Correctly Identified as 'Not Assessed') VALIDATED.")

    # 4. SAFETY SEVERITY SCORE
    print("\n--- 4. SAFETY SEVERITY SCORE ---")
    safety_score = assessment.get("safety_score") if assessment else None
    print(f"Safety Severity Score: {safety_score} / 100")
    print(f"Severity Category: {assessment.get('risk_level')}")
    print(f"Associated Victim: {c_info.get('victim_name')}")
    print(f"Associated Case ID: {c_info.get('reference_number')}")
    assert safety_score is not None, "Safety severity score must be present"
    print("-> Section 4 VALIDATED.")

    # 5. INCIDENT LOCATION
    print("\n--- 5. INCIDENT LOCATION ---")
    print(f"Reported Address / Landmark: {c_info.get('incident_location')}")
    print(f"Latitude: {c_info.get('latitude')}")
    print(f"Longitude: {c_info.get('longitude')}")
    assert c_info.get("incident_location") == complaint_payload["incident_location"], "Incident address mismatch"
    assert c_info.get("latitude") == 13.0827, "Latitude mismatch"
    assert c_info.get("longitude") == 80.2707, "Longitude mismatch"
    print("-> Section 5 VALIDATED.")

    print("\n=== STEP 6: Submit Complaint 2 (WITHOUT GPS Coordinates - No Fake GPS) ===")
    complaint_no_gps = {
        "title": "Domestic Intimidation and Withheld Documentation",
        "description": "My former partner refuses to return my original educational certificates and passport, and sends threatening messages whenever I ask for them back.",
        "category": "domestic_abuse",
        "incident_date": "2026-10-28",
        "incident_location": "Apartment 4B, Green Meadows Residency, Velachery",
        "priority": "standard",
        "latitude": None,
        "longitude": None
    }
    c2_res = requests.post(f"{BASE_URL}/complaints", json=complaint_no_gps, headers=victim_headers)
    assert c2_res.status_code == 200, f"Failed to submit complaint 2: {c2_res.text}"
    case_id_2 = c2_res.json()["case_id"]
    ref_num_2 = c2_res.json()["reference_number"]
    print(f"Complaint 2 Lodged: Case ID = {case_id_2}, Ref = {ref_num_2}")

    detail_res_2 = requests.get(f"{BASE_URL}/cases/{case_id_2}", headers=officer_headers)
    assert detail_res_2.status_code == 200
    d2 = detail_res_2.json()
    c2_info = d2["case"]

    print("\n--- Verifying Complaint 2 Location Without Fake Coordinates ---")
    print(f"Reported Address: {c2_info.get('incident_location')}")
    print(f"Latitude: {c2_info.get('latitude')}")
    print(f"Longitude: {c2_info.get('longitude')}")
    assert c2_info.get("latitude") is None, "Fake latitude was generated!"
    assert c2_info.get("longitude") is None, "Fake longitude was generated!"
    assert c2_info.get("incident_location") == "Apartment 4B, Green Meadows Residency, Velachery"
    print("-> Verified: Zero fake coordinates generated. Text address preserved accurately.")

    print("\n--- Verifying Complaint 2 Assessment Scores ---")
    d2_assessment = d2.get("assessment")
    print(f"Text Risk Score: {d2_assessment.get('text_score')}")
    print(f"Voice Stress Score: {d2_assessment.get('voice_score')} ('Not Assessed')")
    print(f"Safety Severity Score: {d2_assessment.get('safety_score')}")
    assert d2_assessment.get("text_score") is not None
    assert d2_assessment.get("voice_score") is None
    assert d2_assessment.get("safety_score") is not None
    print("-> Verified: Complaint 2 has real text risk score, voice stress is None (Not Assessed), and safety severity score is present.")

    print("\n========================================================")
    print("ALL VERIFICATIONS PASSED SUCCESSFULLY!")
    print("========================================================")

if __name__ == "__main__":
    run_tests()
