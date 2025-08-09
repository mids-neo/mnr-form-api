# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Medical form processing pipeline that extracts data from Patient MNR (Medical Necessity Review) forms and maps it to ASH Medical Necessity Review forms.

## Key Commands

### Run the Tool
```bash
# Mode A: Direct ASH JSON to PDF
python mnr_to_ash_single.py \
  --ash-pdf ash_medical_form.pdf \
  --output-pdf ash_filled.pdf \
  --ash-json ash_form_merged_from_mnr.json

# Mode B: Full MNR OCR -> ASH PDF pipeline
python mnr_to_ash_single.py \
  --ash-pdf ash_medical_form.pdf \
  --output-pdf ash_filled_mnr_only.pdf \
  --mnr-pdf "Patient C.S..pdf" \
  --mnr-template-json archive/patience_mnr_form_fields.json \
  --save-intermediate-json mnr_extracted.json \
  --save-ash-json ash_form_mnr_only.json
```

### Install Dependencies
```bash
# Required for PDF manipulation
pip install PyMuPDF PyPDF2 reportlab PyCryptodome

# Optional for OCR support (Mode B)
pip install pdf2image pytesseract
# Note: Also requires tesseract binary installed (e.g., sudo apt install tesseract-ocr)
```

## Architecture

The project uses a single unified script (`mnr_to_ash_single.py`) with two operational modes:

### Mode A: Direct ASH Form Filling
- Input: ASH-formatted JSON file
- Output: Filled ASH PDF
- Use case: When you already have data in ASH format

### Mode B: MNR to ASH Pipeline
1. **OCR Extraction**: Extracts text from MNR PDF using pytesseract
2. **Field Parsing**: Uses regex patterns to extract MNR field values
3. **Schema Mapping**: Transforms MNR nested structure to ASH flat structure
4. **PDF Generation**: Fills ASH PDF using only MNR-derived data

### PDF Filling Strategy
The tool attempts multiple methods in order:
1. **PyMuPDF** (`fitz`): For true fillable form fields
2. **PyPDF2**: Basic field updates when PyMuPDF fails
3. **ReportLab Overlay**: Creates text overlay when no fillable fields exist

## Key Files

- `mnr_to_ash_single.py` - Main unified implementation (802 lines)
- `ash_medical_form.pdf` - Blank ASH form template
- `Patient C.S..pdf` - Sample filled MNR form
- `ash_form_merged_from_mnr.json` - ASH form data with defaults
- `archive/patience_mnr_form_fields.json` - MNR template structure (unused in current workflow)

## Data Mapping Notes

### MNR to ASH Field Mappings
The tool maps MNR fields to ASH fields, using only data extracted from the MNR form:
- Patient demographics (name, DOB, gender) → ASH patient section
- Pain levels (0-10 scale) → ASH pain metrics
- Treatment history checkboxes → ASH therapy services
- Provider information → ASH clinic fields
- Symptom percentage buckets (e.g., "71-80%") → ASH frequency percentages

### Important Behavior
- No ASH defaults are preserved - only MNR-extracted values are used
- If OCR fails, the tool falls back to hardcoded sample data for demonstration
- Missing MNR fields result in empty ASH fields (not defaults)

## Debugging Tips

- Use `--save-intermediate-json` to inspect OCR extraction results
- Use `--save-ash-json` to verify the mapped ASH data before PDF filling
- Check console output for which PDF filling method succeeded
- If PDF appears empty, the form may not have fillable fields (overlay method will be used)