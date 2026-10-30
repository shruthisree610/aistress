import os
import sys
import requests

sys.path.insert(0, os.path.join(os.getcwd(), "backend"))
from auth import make_token

BASE_URL = "http://127.0.0.1:8000"

def run_test():
    officer_id = "58d3d6b5-fc0a-49d5-9492-ecd22dd9d5eb"
    token = make_token(officer_id, "officer")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Test Unassessed Case (51535fe0-9269-4df8-a764-21dd092d03ac)
    unassessed_id = "51535fe0-9269-4df8-a764-21dd092d03ac"
    case_resp = requests.get(f"{BASE_URL}/api/cases/{unassessed_id}", headers=headers)
    print(f"Unassessed Case Detail [{case_resp.status_code}]:")
    assert case_resp.status_code == 200, f"Failed to get case {unassessed_id}"
    c_data = case_resp.json()
    case_obj = c_data.get("case", {})
    print(f"  Victim: {case_obj.get('victim_name')}")
    print(f"  Incident Location: {case_obj.get('incident_location')}")
    print(f"  GPS Latitude: {case_obj.get('latitude')}")
    print(f"  Assessment: {c_data.get('assessment')}")
    print(f"  Latest Analysis: {c_data.get('latest_analysis')}")
    assert c_data.get("latest_analysis") is None, "Expected latest_analysis to be None for unassessed case"
    assert c_data.get("assessment") is None, "Expected assessment to be None for unassessed case"
    assert case_obj.get("incident_location") == "kedfjopqjf", "Expected descriptive incident location"

    # Escalation forecast for unassessed case
    risk_resp = requests.get(f"{BASE_URL}/api/analytics/escalation-risk/{unassessed_id}", headers=headers)
    print(f"Unassessed Risk Forecast [{risk_resp.status_code}]:")
    assert risk_resp.status_code == 200
    r_data = risk_resp.json()
    print(f"  has_sufficient_data: {r_data.get('has_sufficient_data')}")
    print(f"  predicted_threat_level: {r_data.get('predicted_threat_level')}")
    print(f"  escalation_velocity: {r_data.get('escalation_velocity')}")
    assert r_data.get("has_sufficient_data") is False, "Expected has_sufficient_data to be False"
    assert r_data.get("predicted_threat_level") == "Insufficient Data"
    assert r_data.get("escalation_velocity") == "N/A"

    # 2. Test Assessed Case (59ec22d2-feac-4253-afab-2026f87504e3)
    assessed_id = "59ec22d2-feac-4253-afab-2026f87504e3"
    case_resp2 = requests.get(f"{BASE_URL}/api/cases/{assessed_id}", headers=headers)
    print(f"\nAssessed Case Detail [{case_resp2.status_code}]:")
    assert case_resp2.status_code == 200, f"Failed to get case {assessed_id}"
    c_data2 = case_resp2.json()
    latest2 = c_data2.get("latest_analysis")
    print(f"  Latest Analysis SVI: {latest2.get('svi_score') if latest2 else 'None'}")
    print(f"  Latest Analysis Risk: {latest2.get('risk_level') if latest2 else 'None'}")
    print(f"  Latest Analysis Timestamp: {latest2.get('timestamp') if latest2 else 'None'}")
    assert latest2 is not None, "Expected latest_analysis to exist for assessed case"
    assert "timestamp" in latest2, "Expected timestamp in latest_analysis"

    # Escalation forecast for assessed case
    risk_resp2 = requests.get(f"{BASE_URL}/api/analytics/escalation-risk/{assessed_id}", headers=headers)
    print(f"Assessed Risk Forecast [{risk_resp2.status_code}]:")
    assert risk_resp2.status_code == 200
    r_data2 = risk_resp2.json()
    print(f"  has_sufficient_data: {r_data2.get('has_sufficient_data')}")
    print(f"  predicted_threat_level: {r_data2.get('predicted_threat_level')}")
    print(f"  escalation_velocity: {r_data2.get('escalation_velocity')}")
    print(f"  danger_window_hours: {r_data2.get('danger_window_hours')}")
    print(f"  trajectory_pct: {r_data2.get('trajectory_pct')}")
    print(f"  risk_curve points: {r_data2.get('risk_curve', [])}")
    print(f"  risk_factors: {r_data2.get('risk_factors')}")
    assert r_data2.get("has_sufficient_data") is True, "Expected has_sufficient_data to be True"
    assert len(r_data2.get("risk_curve", [])) > 0, "Expected non-empty risk_curve"
    assert len(r_data2.get("risk_factors", [])) > 0, "Expected genuine risk factors"

    print("\n=======================================================")
    print(">>> ALL BACKEND API VERIFICATIONS PASSED SUCCESSFULLY! <<<")
    print("=======================================================")

if __name__ == "__main__":
    run_test()
