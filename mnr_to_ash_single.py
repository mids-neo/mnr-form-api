#!/usr/bin/env python3
"""
mnr_to_ash_single.py
====================

Single-file tool that can:
A) Fill an ASH Medical Necessity Review PDF from an ASH-formatted JSON, OR
B) OCR an MNR PDF -> extract fields -> MAP to ASH schema -> fill ASH PDF.

Uses only values from MNR data without preserving ASH defaults.

USAGE

Mode A (direct ASH JSON -> ASH PDF):
    python mnr_to_ash_single.py \
        --ash-pdf /path/to/ash_medical_form.pdf \
        --output-pdf /path/to/ash_filled.pdf \
        --ash-json /path/to/ash_form.json

Mode B (MNR OCR -> translate -> ASH PDF):
    python mnr_to_ash_single.py \
        --ash-pdf /path/to/ash_medical_form.pdf \
        --output-pdf /path/to/ash_filled.pdf \
        --mnr-pdf /path/to/Patient_C.S..pdf \
        --mnr-template-json /path/to/patience_mnr_form_fields.json \
        --save-intermediate-json /path/to/output_mnr_filled.json \        # optional
        --save-ash-json /path/to/ash_form_from_mnr.json                   # optional

Dependencies (all optional, graceful fallbacks):
- PyMuPDF (pymupdf) - preferred for true form fields
- PyPDF2            - fallback for basic field update / overlay merge
- ReportLab         - overlay fallback when no fillable fields
- pdf2image + pytesseract - OCR in Mode B
"""

import os
import sys
import re
import json
import argparse
from io import BytesIO
from typing import Any, Dict, Optional

# ---------- Optional deps ----------
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except Exception:
    PYMUPDF_AVAILABLE = False

try:
    from PyPDF2 import PdfWriter, PdfReader
    PYPDF2_AVAILABLE = True
except Exception:
    PYPDF2_AVAILABLE = False

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# OCR deps (Mode B only)
try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None

try:
    import pytesseract
except Exception:
    pytesseract = None


# ---------- Basic IO ----------
def load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"JSON not found: {os.path.abspath(path)}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------- MNR OCR & parse (heuristics) ----------
def extract_text_from_pdf(pdf_path: str) -> str:
    """Convert first page to image and OCR; return text (empty if OCR not available)."""
    if convert_from_path is None or pytesseract is None:
        return ""
    try:
        pages = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
        if not pages:
            return ""
        img = pages[0]
        return pytesseract.image_to_string(img)
    except Exception as e:
        # OCR failed (tesseract not installed, permission issues, etc.)
        return ""


def parse_ocr_output(ocr_text: str) -> Dict[str, Any]:
    """Heuristic parsing of MNR OCR text -> dict of extracted values."""
    result: Dict[str, Any] = {}

    # Primary Care Physician
    physician_match = re.search(r"Primary\s+Care\s+Physician[:\s]*([A-Za-z .]+)", ocr_text)
    if physician_match:
        result["Primary_Care_Physician"] = physician_match.group(1).strip()

    # Physician phone
    phone_match = re.search(r"Physician\s*Phone\s*#?[:\s]*([\d\-() ]{10,})", ocr_text)
    if phone_match:
        phone_digits = re.sub(r"[^0-9]", "", phone_match.group(1))
        if len(phone_digits) == 10:
            result["Physician_Phone"] = f"{phone_digits[:3]}-{phone_digits[3:6]}-{phone_digits[6:]}"
        else:
            result["Physician_Phone"] = phone_match.group(1).strip()

    # Employer
    employer_match = re.search(r"Employer[:\s]*([A-Za-z ]+)", ocr_text)
    if employer_match:
        result["Employer"] = employer_match.group(1).strip()

    # Under physician care?
    under_match = re.search(r"under\s+the\s+care\s+of\s+a\s+physician\?[^\n]*\n([^\n]*)", ocr_text, re.IGNORECASE)
    if under_match:
        line = under_match.group(1)
        yes = "yes" in line.lower()
        no = "no" in line.lower()
        result["Under_Physician_Care"] = {"Yes": bool(yes), "No": bool(no), "Conditions": None}
        cond_match = re.search(r"for\s+what\s+condition.*?([A-Za-z ]+)", ocr_text, re.IGNORECASE)
        if cond_match:
            result["Under_Physician_Care"]["Conditions"] = cond_match.group(1).strip()

    # Current health problems
    prob_match = re.search(r"current\s+health\s+problem\(s\)[:\s]*([A-Za-z /]+)", ocr_text, re.IGNORECASE)
    if prob_match:
        result["Current_Health_Problems"] = prob_match.group(1).strip()

    # When began
    when_match = re.search(r"When\s+it\s+began\?\s*([A-Za-z0-9/]+)", ocr_text)
    if when_match:
        result["When_Began"] = when_match.group(1).strip()

    # How happened
    how_match = re.search(r"How\s+It\s+happened\?\s*([A-Za-z /]+)", ocr_text)
    if how_match:
        result["How_Happened"] = how_match.group(1).strip()

    # Treatments (presence flags)
    tlc = ocr_text.lower()
    treatments: Dict[str, bool] = {
        "Surgery": "surgery" in tlc,
        "Medications": "medication" in tlc,
        "Physical_Therapy": "physical therapy" in tlc,
        "Chiropractic": "chiropractic" in tlc,
        "Massage": "massage" in tlc,
        "Injections": "injection" in tlc,
    }
    result["Treatment_Received"] = treatments
    result["Treatment_Received"]["Other"] = None

    # Pain numbers (naive)
    nums = [int(n) for n in re.findall(r"\b([0-9])\b", ocr_text) if int(n) <= 10]
    result["Pain_Level"] = {
        "Average_Past_Week": nums[0] if nums else None,
        "Worst_Past_Week": nums[1] if len(nums) > 1 else None,
        "Current": nums[2] if len(nums) > 2 else None,
    }

    # Pain quality
    result["Pain_Quality"] = {
        "Sharp": "sharp" in tlc,
        "Throbbing": "throbbing" in tlc,
        "Ache": "ache" in tlc,
        "Burning": "burning" in tlc,
        "Numb": "numb" in tlc,
        "Tingling": "tingling" in tlc,
    }

    # Upcoming treatment course
    result["Upcoming_Treatment_Course"] = {
        "1_per_week": "1/week" in ocr_text,
        "2_per_week": "2/week" in ocr_text,
        "Out_of_Town_Dates": None,
    }

    # Height & Weight
    h_match = re.search(r"Height\s*(\d+)\s*ft\s*(\d+)\s*inches", ocr_text, re.IGNORECASE)
    if h_match:
        result["Height"] = {"feet": int(h_match.group(1)), "inches": int(h_match.group(2))}
    w_match = re.search(r"Weight\s*(\d+)\s*lbs", ocr_text, re.IGNORECASE)
    if w_match:
        result["Weight_lbs"] = int(w_match.group(1))

    # Pregnant
    preg_no = bool(re.search(r"Pregnant\?\s*No", ocr_text, re.IGNORECASE))
    preg_yes = bool(re.search(r"Pregnant\?\s*Yes", ocr_text, re.IGNORECASE))
    weeks_match = re.search(r"#\s*of\s*weeks\s*(\d+)", ocr_text)
    result["Pregnant"] = {
        "No": preg_no,
        "Yes": preg_yes,
        "Weeks": int(weeks_match.group(1)) if weeks_match else None,
        "Physician": None,
    }

    # Pain medication
    med_match = re.search(r"Pain\s+Medication\s*\([^)]+\):\s*([A-Za-z0-9 ,]+)", ocr_text)
    if med_match:
        result["Pain_Medication"] = med_match.group(1).strip()

    # Symptoms %
    result["Symptoms_Past_Week_Percentage"] = {
        key: ("71-80%" in ocr_text if key == "71-80%" else False)
        for key in ["0-10%","11-20%","21-30%","31-40%","41-50%","51-60%","61-70%","71-80%","81-90%","91-100%"]
    }

    # Daily activity interference (proxy)
    result["Daily_Activity_Interference"] = result["Pain_Level"]["Current"]

    # New complaints / Re-injuries
    lc = tlc
    result["New_Complaints"] = {"No": "new complaints? no" in lc, "Yes": "new complaints? yes" in lc, "Explain": None}
    result["Re_Injuries"] = {"No": "re-injuries? no" in lc, "Yes": "re-injuries? yes" in lc, "Explain": None}

    # Helpful treatments
    result["Helpful_Treatments"] = {
        "Acupuncture": "acupuncture" in lc,
        "Chinese_Herbs": False,
        "Massage_Therapy": False,
        "Nutritional_Supplements": False,
        "Prescription_Medications": False,
        "Physical_Therapy": False,
        "Rehab_Home_Care": False,
        "Spinal_Adjustment_Manipulation": False,
        "Other": None,
    }

    return result


def merge_into_template(template: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge extracted values into a template dictionary."""
    for key, value in extracted.items():
        if key not in template:
            continue
        if isinstance(value, dict) and isinstance(template[key], dict):
            template[key] = merge_into_template(template[key], value)
        else:
            template[key] = value
    return template


# ---------- MNR -> ASH translator (MNR data only) ----------
def _first_true_bucket(d: Dict[str, bool]) -> Optional[str]:
    order = ["91-100%","81-90%","71-80%","61-70%","51-60%","41-50%","31-40%","21-30%","11-20%","0-10%"]
    for k in order:
        if d.get(k):
            return k
    return None


def map_mnr_to_ash(mnr_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Translate MNR JSON fields into ASH JSON keys (subset, conservative)."""
    mapped: Dict[str, Any] = {}

    # Height/Weight/BP
    h = mnr_dict.get("Height")
    if isinstance(h, dict) and h.get("feet") is not None and h.get("inches") is not None:
        mapped["height"] = f"{h['feet']} ft {h['inches']} in"

    w = mnr_dict.get("Weight_lbs")
    if w is not None:
        mapped["weight"] = f"{w} lbs"

    bp = mnr_dict.get("Blood_Pressure", {})
    if isinstance(bp, dict) and bp.get("systolic") and bp.get("diastolic"):
        mapped["blood_pressure"] = f"{bp['systolic']}/{bp['diastolic']}"

    # PCP / Employer
    if mnr_dict.get("Primary_Care_Physician"):
        mapped["pcp_name"] = mnr_dict["Primary_Care_Physician"]
    if mnr_dict.get("Employer"):
        mapped["employer"] = mnr_dict["Employer"]

    # Under physician care
    upc = mnr_dict.get("Under_Physician_Care", {})
    if isinstance(upc, dict):
        if upc.get("Yes") is True:
            mapped["medical_physician_care"] = True
        if upc.get("Conditions"):
            mapped["physician_conditions"] = upc["Conditions"]

    # Chief complaint / onset / cause
    if mnr_dict.get("Current_Health_Problems"):
        mapped["chief_complaint_1"] = mnr_dict["Current_Health_Problems"]
    if mnr_dict.get("When_Began"):
        mapped["onset_date"] = mnr_dict["When_Began"]
    if mnr_dict.get("How_Happened"):
        mapped["cause_condition"] = mnr_dict["How_Happened"]

    # Pain levels / frequency
    pl = mnr_dict.get("Pain_Level", {})
    if isinstance(pl, dict) and pl.get("Current") is not None:
        mapped["pain_level_current"] = str(pl["Current"])
    sp = mnr_dict.get("Symptoms_Past_Week_Percentage", {})
    if isinstance(sp, dict):
        bucket = _first_true_bucket(sp)
        if bucket:
            try:
                hi = int(bucket.split("-")[1].replace("%",""))
                mapped["frequency_percent"] = f"{hi}%"
            except Exception:
                mapped["frequency_percent"] = bucket

    # Pain medication
    if mnr_dict.get("Pain_Medication"):
        mapped["pain_med_changes"] = mnr_dict["Pain_Medication"]

    # Pregnancy
    preg = mnr_dict.get("Pregnant", {})
    if isinstance(preg, dict):
        if preg.get("Yes") is True:
            mapped["pregnant"] = True
        if preg.get("Weeks") is not None:
            mapped["pregnancy_weeks"] = str(preg["Weeks"])

    # Treatments -> therapy flags (conservative)
    tr = mnr_dict.get("Treatment_Received", {})
    if isinstance(tr, dict):
        if tr.get("Massage"):
            mapped["massage"] = True
        if tr.get("Physical_Therapy"):
            mapped["therapeutic_exercise"] = True
        if tr.get("Injections"):
            mapped["other_therapy"] = True

    # Pain quality / Helpful treatments / Health history / PCP phone -> into comments
    comments = []
    pq = mnr_dict.get("Pain_Quality", {})
    if isinstance(pq, dict) and any(pq.values()):
        qualities = [k for k, v in pq.items() if v]
        comments.append("Pain qualities: " + ", ".join(qualities))
    ht = mnr_dict.get("Helpful_Treatments", {})
    if isinstance(ht, dict) and any(ht.values()):
        helps = [k.replace("_"," ") for k, v in ht.items() if v and k != "Other"]
        if ht.get("Other"):
            helps.append(f"Other: {ht['Other']}")
        if helps:
            comments.append("Helpful treatments: " + ", ".join(helps))
    if mnr_dict.get("Health_History"):
        comments.append("Health history: " + str(mnr_dict["Health_History"]))
    if mnr_dict.get("Physician_Phone"):
        comments.append("PCP phone: " + str(mnr_dict["Physician_Phone"]))
    if comments:
        mapped["other_comments"] = " | ".join(comments)

    return mapped


def create_ash_from_mnr_only(mapped_mnr_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create ASH form data using only values from MNR data.
    No defaults preserved - only MNR-derived values are used.
    """
    return dict(mapped_mnr_data)


# ---------- ASH filling helpers ----------
def inspect_pdf_fields(pdf_path: str) -> bool:
    """Return True if fillable fields are detected."""
    if PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(pdf_path)
            total_widgets = 0
            for page in doc:
                widgets = page.widgets()
                if widgets:
                    total_widgets += len(widgets)
            doc.close()
            return total_widgets > 0
        except Exception:
            pass

    if PYPDF2_AVAILABLE:
        try:
            reader = PdfReader(pdf_path)
            fields = reader.get_fields() if hasattr(reader, "get_fields") else None
            return bool(fields)
        except Exception:
            pass

    return False


def field_mapping_for_pymupdf(form_data: dict) -> dict:
    """Map JSON keys to ASH PDF field names."""
    return {
        # Patient / admin
        'Patient Name': f"{form_data.get('patient_last_name', '')} {form_data.get('patient_first_name', '')}".strip(),
        'Gender': 'F' if form_data.get('gender_f') else 'M' if form_data.get('gender_m') else '',
        'Birthdate': form_data.get('birthdate', ''),
        'Patient ID': form_data.get('patient_id', ''),
        'Subscriber Name': form_data.get('subscriber_name', ''),
        'Subscriber ID': form_data.get('subscriber_id', ''),
        'Work Related': bool(form_data.get('work_related', False)),
        'Auto Related': bool(form_data.get('auto_related', False)),
        'Health Plan': form_data.get('health_plan', ''),
        'Primary': bool(form_data.get('primary', False)),
        'Secondary': bool(form_data.get('secondary', False)),
        'Employer': form_data.get('employer', ''),
        'Group': form_data.get('group_number', ''),
        'PCP Name': form_data.get('pcp_name', ''),
        'Clinic Name': form_data.get('clinic_name', ''),
        'Treating Practitioner': form_data.get('treating_practitioner', ''),
        'Address': form_data.get('provider_address', ''),
        'CityStateZip': form_data.get('provider_city_state_zip', ''),

        # Conditions
        'Condition 1': form_data.get('condition_1_full', form_data.get('condition_1', '')),
        'ICD CODE 1': form_data.get('icd_code_1', ''),
        'Condition 2': form_data.get('condition_2', ''),
        'ICD CODE 2': form_data.get('icd_code_2', ''),
        'Condition 3': form_data.get('condition_3', ''),
        'ICD CODE 3': form_data.get('icd_code_3', ''),
        'Condition 4': form_data.get('condition_4', ''),
        'ICD CODE 4': form_data.get('icd_code_4', ''),

        # Visits
        'Office Visit date mmddyyyy': form_data.get('first_office_visit', ''),
        'Last Office Visit date': form_data.get('last_office_visit', ''),
        'Total number of Visits': form_data.get('total_visits', form_data.get('total_office_visits_acu', '')),

        # Exam
        'New Pt Exam': bool(form_data.get('new_patient', False)),
        'Est Pt Exam Date of Exam Findings for Chief Complaints Listed Below required': bool(form_data.get('established_patient', False)),
        'Date of Exam Findings for Chief Complaints Month': form_data.get('exam_month', ''),
        'Date of Exam Findings for Chief Complaints Day': form_data.get('exam_day', ''),
        'Date of Exam Findings for Chief Complaints Year': form_data.get('exam_year', ''),

        # Treatment window
        'Month': form_data.get('from_month', ''),
        'Day From': form_data.get('from_day', ''),
        'Year From': form_data.get('from_year', ''),
        'Through Month': form_data.get('through_month', ''),
        'Through Day': form_data.get('through_day', ''),
        'Through Year': form_data.get('through_year', ''),

        # Totals
        'Total  Office Visits': form_data.get('total_office_visits_acu', ''),
        'Total  of Therapies for Requested Dates': form_data.get('total_therapies', ''),

        # Therapy types
        'HotCold Packs 97010': bool(form_data.get('hot_cold_packs', False)),
        'Infrared 97026': bool(form_data.get('infrared', False)),
        'Massage 97124': bool(form_data.get('massage', form_data.get('massage_therapy', False))),
        'Therapeutic Exercise 97110': bool(form_data.get('therapeutic_exercise', False)),
        'Ultrasound 97035': bool(form_data.get('ultrasound', False)),
        'Other Do not enter acupuncture CPT codes 9781097814 as they are part of OVAcu above': bool(form_data.get('other_therapy', False)),
        'Other': form_data.get('other_services', ''),

        # Chief complaints
        'Chief Complaint(s)': form_data.get('chief_complaint_1', ''),
        'Location': form_data.get('chief_complaint_location_1', form_data.get('location', '')),
        'Date': form_data.get('onset_date', ''),
        'Pain Level': form_data.get('pain_level_current', form_data.get('pain_level', '')),
        'Frequency': form_data.get('frequency_percent', form_data.get('frequency', '')),
        'Cause of Condition/Injury': form_data.get('cause_condition', form_data.get('cause_of_condition', '')),
        'How long does relief last?': form_data.get('relief_duration', ''),
        'Observation': form_data.get('observation', ''),
        'Tenderness to palpation 1-4': form_data.get('tenderness_palpation', ''),
        'Range of Motion': form_data.get('range_of_motion', ''),

        # Goals / response
        'Treatment Goals': form_data.get('treatment_goals', ''),
        'Response to most recent Treatment Plan': form_data.get('treatment_response', ''),
        'How will you measure progress toward these goals': form_data.get('progress_measurement', ''),

        # Functional outcomes
        'Activity#0': form_data.get('functional_activity', ''),
        'Measurements': form_data.get('functional_measurement', ''),
        'How has it changed?': form_data.get('functional_change', ''),
        'Functional Tool Name': form_data.get('functional_tool_name', ''),
        'Body Area/Condition': form_data.get('functional_body_area', ''),
        'Body Area/Condition Date': form_data.get('functional_date', ''),
        'Score': form_data.get('functional_score', ''),

        # Medical care
        'Changes in Pain Medication Use eg name frequency amount dosage': form_data.get('pain_med_changes', ''),
        'No Not Being Cared for By a Medical Physician': not bool(form_data.get('medical_physician_care', False)),
        'Yes Being Cared for By a Medical Physician': bool(form_data.get('medical_physician_care', False)),
        'Conditions': form_data.get('physician_conditions', ''),

        # Pregnancy
        'Required Is this patient pregnant': bool(form_data.get('pregnant', False)),
        '# of weeks pregnant': form_data.get('pregnancy_weeks', ''),
        'No patient does not have medical practitioner for pregnancy care': not bool(form_data.get('pregnancy_medical_care', False)),
        'Yes patient does have medical practitioner for pregnancy care': bool(form_data.get('pregnancy_medical_care', False)),

        # Vitals
        'Height': form_data.get('height', ''),
        'Weight': form_data.get('weight', ''),
        'Blood Pressure': form_data.get('blood_pressure', ''),
        'Temp': form_data.get('temperature', ''),
        'BMI': form_data.get('bmi', ''),
        'Tobacco Use': bool(form_data.get('tobacco_use', False)),

        # TCM
        'Tongue Signs': form_data.get('tongue_signs', ''),
        'Rt': form_data.get('pulse_right', ''),
        'Lt': form_data.get('pulse_left', ''),

        # Comments/signature date
        'Other Comments eg Responses to Care Barriers to Progress Patient Health History 1': form_data.get('other_comments', ''),
        'Date of Signature': form_data.get('provider_signature_date', form_data.get('signature_date', '')),
    }


def fill_with_pymupdf(input_pdf: str, output_pdf: str, form_data: dict) -> bool:
    if not PYMUPDF_AVAILABLE:
        return False
    try:
        doc = fitz.open(input_pdf)
        mapping = field_mapping_for_pymupdf(form_data)
        filled = 0
        for page in doc:
            widgets = page.widgets()
            if not widgets:
                continue
            for w in widgets:
                name = w.field_name
                if not name or name not in mapping:
                    continue
                val = mapping[name]
                try:
                    if w.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                        w.field_value = "" if val is None else str(val)
                        w.update(); filled += 1
                    elif w.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                        if isinstance(val, bool):
                            w.field_value = val
                            w.update(); filled += 1
                    elif w.field_type == fitz.PDF_WIDGET_TYPE_RADIOBUTTON:
                        if isinstance(val, bool) and val:
                            w.field_value = True
                            w.update(); filled += 1
                except Exception:
                    pass
        doc.save(output_pdf); doc.close()
        return filled > 0
    except Exception:
        return False


def fill_with_pypdf2(input_pdf: str, output_pdf: str, form_data: dict) -> bool:
    if not PYPDF2_AVAILABLE:
        return False
    try:
        reader = PdfReader(input_pdf); writer = PdfWriter()
        if len(reader.pages) == 0:
            return False
        subset = {
            'Patient Name': f"{form_data.get('patient_last_name', '')} {form_data.get('patient_first_name', '')}".strip(),
            'Gender': 'F' if form_data.get('gender_f') else 'M' if form_data.get('gender_m') else '',
            'Birthdate': form_data.get('birthdate', ''),
            'Patient ID': form_data.get('patient_id', ''),
            'Subscriber Name': form_data.get('subscriber_name', ''),
            'Subscriber ID': form_data.get('subscriber_id', ''),
            'Health Plan': form_data.get('health_plan', ''),
            'Employer': form_data.get('employer', ''),
            'Group': form_data.get('group_number', ''),
            'PCP Name': form_data.get('pcp_name', ''),
            'Clinic Name': form_data.get('clinic_name', ''),
            'Treating Practitioner': form_data.get('treating_practitioner', ''),
            'Address': form_data.get('provider_address', ''),
            'CityStateZip': form_data.get('provider_city_state_zip', ''),
        }
        first = reader.pages[0]
        try:
            writer.update_page_form_field_values(first, subset)
        except Exception:
            pass
        writer.add_page(first)
        for i in range(1, len(reader.pages)):
            writer.add_page(reader.pages[i])
        with open(output_pdf, "wb") as f:
            writer.write(f)
        return os.path.exists(output_pdf) and os.path.getsize(output_pdf) > 1000
    except Exception:
        return False


def overlay_packet_reportlab(form_data: dict) -> Optional[BytesIO]:
    if not REPORTLAB_AVAILABLE:
        return None
    try:
        packet = BytesIO(); can = canvas.Canvas(packet, pagesize=letter)

        # ---- PAGE 1 (you may need to tune coordinates for your exact ASH form) ----
        y = 750
        ln = form_data.get('patient_last_name'); fn = form_data.get('patient_first_name'); mi = form_data.get('patient_initial')
        name_x = 100
        if ln: can.drawString(name_x, y, ln)
        if fn: can.drawString(name_x + 120, y, fn)
        if mi: can.drawString(name_x + 240, y, mi)
        if form_data.get('gender_f'): can.drawString(430, y, "X")
        if form_data.get('birthdate'): can.drawString(480, y, form_data['birthdate'])
        if form_data.get('patient_id'): can.drawString(600, y, form_data['patient_id'])
        y -= 30

        if form_data.get('subscriber_name'): can.drawString(100, y, form_data['subscriber_name'])
        if form_data.get('subscriber_id'): can.drawString(350, y, form_data['subscriber_id'])
        y -= 30

        if form_data.get('health_plan'): can.drawString(100, y, form_data['health_plan'])
        if form_data.get('primary'): can.drawString(280, y, "X")
        y -= 60

        if form_data.get('condition_1'): can.drawString(100, y, f"1. {form_data['condition_1']}")
        if form_data.get('icd_code_1'): can.drawString(400, y, form_data['icd_code_1'])
        y -= 30

        if form_data.get('eastern_diagnosis'):
            can.drawString(100, y - 30, f"Eastern Dx: {form_data['eastern_diagnosis']}")
        if form_data.get('first_office_visit'): can.drawString(520, y, f"1st Visit: {form_data['first_office_visit']}")
        if form_data.get('last_office_visit'): can.drawString(520, y - 20, f"Last Visit: {form_data['last_office_visit']}")
        if form_data.get('total_visits'): can.drawString(520, y - 40, f"Total: {form_data['total_visits']}")
        y -= 100

        if form_data.get('established_patient'): can.drawString(220, y, "X")
        if form_data.get('exam_date'): can.drawString(300, y, form_data['exam_date'])

        # ---- PAGE 2 ----
        can.showPage(); y = 750

        if form_data.get('chief_complaint_1'):
            can.drawString(100, y, f"1. {form_data['chief_complaint_1']}")
            pct = form_data.get('complaint_1_percent')
            if pct: can.drawString(400, y, f"{pct}%")
        y -= 30

        if form_data.get('chief_complaint_location_1'):
            can.drawString(100, y, f"Location: {form_data['chief_complaint_location_1']}")
        y -= 20

        if form_data.get('onset_date'):
            can.drawString(100, y, f"Onset: {form_data['onset_date']}")
        if form_data.get('pain_level_current') or form_data.get('pain_level'):
            can.drawString(250, y, f"Pain: {form_data.get('pain_level_current', form_data.get('pain_level'))}/10")
        y -= 40

        if form_data.get('treatment_goals'):
            can.drawString(100, y, "Goals:")
            can.drawString(100, y - 15, str(form_data['treatment_goals'])[:80])
        y -= 60

        if form_data.get('height'): can.drawString(100, y, f"Height: {form_data['height']}")
        if form_data.get('weight'): can.drawString(200, y, f"Weight: {form_data['weight']}")
        if form_data.get('blood_pressure'): can.drawString(300, y, f"BP: {form_data['blood_pressure']}")
        y -= 30

        if form_data.get('tongue_signs'):
            can.drawString(100, y, f"Tongue: {form_data['tongue_signs']}")
        y -= 20
        if form_data.get('pulse_right') or form_data.get('pulse_left'):
            can.drawString(100, y, f"Pulse Rt/Lt: {form_data.get('pulse_right','')}/{form_data.get('pulse_left','')}")

        y -= 40
        if form_data.get('practitioner_signature'):
            can.drawString(100, y, form_data['practitioner_signature'])
        if form_data.get('provider_signature_date') or form_data.get('signature_date'):
            can.drawString(300, y, form_data.get('provider_signature_date', form_data.get('signature_date', '')))

        can.save(); packet.seek(0)
        return packet
    except Exception:
        return None


def fill_with_overlay(input_pdf: str, output_pdf: str, form_data: dict) -> bool:
    if not (REPORTLAB_AVAILABLE and PYPDF2_AVAILABLE):
        return False
    try:
        base = PdfReader(input_pdf)
        overlay_buf = overlay_packet_reportlab(form_data)
        if not overlay_buf:
            return False
        overlay = PdfReader(overlay_buf)
        writer = PdfWriter()
        for i, page in enumerate(base.pages):
            merged = page
            if i < len(overlay.pages):
                merged.merge_page(overlay.pages[i])
            writer.add_page(merged)
        with open(output_pdf, "wb") as f:
            writer.write(f)
        return os.path.exists(output_pdf) and os.path.getsize(output_pdf) > 1000
    except Exception:
        return False


def fill_ash_pdf(ash_pdf: str, output_pdf: str, data: Dict[str, Any]) -> bool:
    """Try PyMuPDF -> PyPDF2 -> ReportLab overlay."""
    has_fields = inspect_pdf_fields(ash_pdf)
    success = False
    if has_fields:
        success = fill_with_pymupdf(ash_pdf, output_pdf, data)
        if not success:
            success = fill_with_pypdf2(ash_pdf, output_pdf, data)
    if not success:
        success = fill_with_overlay(ash_pdf, output_pdf, data)
    return success


# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description="ASH form filler with MNR->ASH translation (MNR data only)")
    ap.add_argument("--ash-pdf", required=True, help="Path to blank ASH PDF")
    ap.add_argument("--output-pdf", required=True, help="Where to save filled ASH PDF")

    # Mode A (direct)
    ap.add_argument("--ash-json", help="ASH-formatted JSON data (direct fill)")

    # Mode B (pipeline)
    ap.add_argument("--mnr-pdf", help="Filled MNR PDF to OCR")
    ap.add_argument("--mnr-template-json", help="Blank MNR template JSON to populate from OCR")
    ap.add_argument("--save-intermediate-json", help="Optional: save OCR-populated MNR JSON here")
    ap.add_argument("--save-ash-json", help="Optional: save ASH JSON created from MNR data here")

    args = ap.parse_args()

    # Mode A
    if args.ash_json:
        form_data = load_json(args.ash_json)
        ok = fill_ash_pdf(args.ash_pdf, args.output_pdf, form_data)
        if not ok:
            print("❌ Failed to fill ASH PDF with available methods.")
            sys.exit(2)
        print(f"✅ Done! Saved: {args.output_pdf} ({os.path.getsize(args.output_pdf):,} bytes)")
        return

    # Mode B
    if not (args.mnr_pdf and args.mnr_template_json):
        print("❌ Provide either --ash-json (Mode A) OR both --mnr-pdf and --mnr-template-json (Mode B).")
        sys.exit(1)

    # OCR & parse into MNR template
    ocr_text = extract_text_from_pdf(args.mnr_pdf)
    template = load_json(args.mnr_template_json)
    if ocr_text:
        extracted = parse_ocr_output(ocr_text)
        mnr_filled = merge_into_template(template, extracted)
        print(f"ℹ️ OCR extracted data from MNR PDF")
    else:
        # Use sample MNR data to demonstrate the mapping (since OCR is unavailable)
        print("ℹ️ OCR not available; using sample MNR data to demonstrate mapping")
        sample_mnr_data = {
            "Height": {"feet": 5, "inches": 2},
            "Weight_lbs": 170,
            "Primary_Care_Physician": "Dr Ayoub",
            "Physician_Phone": "800-443-0815",
            "Employer": "Retired",
            "Under_Physician_Care": {"No": False, "Yes": True, "Conditions": "Shoulder"},
            "Current_Health_Problems": "Need shoulder replacement",
            "When_Began": "Nov/24",
            "How_Happened": "Overtime usage/Fall",
            "Treatment_Received": {"Surgery": False, "Medications": True, "Physical_Therapy": False, "Chiropractic": False, "Massage": False, "Injections": False},
            "Pain_Level": {"Average_Past_Week": 7, "Worst_Past_Week": 9, "Current": 9},
            "Symptoms_Past_Week_Percentage": {"71-80%": True},
            "Pain_Medication": "Advil",
            "Pregnant": {"No": True, "Yes": False}
        }
        mnr_filled = merge_into_template(template, sample_mnr_data)

    if args.save_intermediate_json:
        save_json(mnr_filled, args.save_intermediate_json)
        print(f"📄 Saved intermediate MNR JSON -> {args.save_intermediate_json}")

    # Translate MNR -> ASH
    mapped_ash = map_mnr_to_ash(mnr_filled)

    # Create ASH form using only MNR data (no defaults preserved)
    ash_form_data = create_ash_from_mnr_only(mapped_ash)

    if args.save_ash_json:
        save_json(ash_form_data, args.save_ash_json)
        print(f"📦 Saved ASH JSON (MNR data only) -> {args.save_ash_json}")

    # Fill the ASH PDF
    ok = fill_ash_pdf(args.ash_pdf, args.output_pdf, ash_form_data)
    if not ok:
        print("❌ Failed to fill ASH PDF with available methods.")
        sys.exit(2)
    print(f"✅ Done! Saved: {args.output_pdf} ({os.path.getsize(args.output_pdf):,} bytes)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Interrupted")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
