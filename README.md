# MNR Form Processing API

FastAPI backend for processing Medical Necessity Review (MNR) forms and converting them to ASH Medical forms.

## Features

- **PDF Upload & OCR**: Upload MNR PDF forms and extract data using OCR
- **Data Extraction**: Parse medical form fields from scanned documents
- **Form Mapping**: Convert MNR format to ASH Medical format
- **PDF Generation**: Fill ASH Medical PDF forms with extracted data
- **REST API**: Full REST API for form processing pipeline

## Installation

### Backend Setup

1. Install Python dependencies:
```bash
cd mnr_form_api
pip install -r requirements.txt
```

2. For OCR support (optional):
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

3. Start the API server:
```bash
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd mnr-form-ai
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env` file:
```bash
echo "VITE_API_URL=http://localhost:8000" > .env
```

4. Start the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:5173 (or the port shown in terminal)

## API Endpoints

### Core Endpoints

- `POST /api/upload-mnr` - Upload an MNR PDF file
- `POST /api/extract-mnr` - Extract data from uploaded MNR PDF
- `POST /api/map-to-ash` - Map MNR data to ASH format
- `POST /api/generate-ash-pdf` - Generate filled ASH PDF
- `POST /api/process-complete` - Complete pipeline (upload → extract → map → generate)
- `GET /api/download/{filename}` - Download generated PDF
- `GET /api/forms` - List available forms

### Example Usage

#### Complete Pipeline
```bash
curl -X POST "http://localhost:8000/api/process-complete" \
  -H "accept: application/json" \
  -F "file=@Patient C.S..pdf"
```

#### Step-by-step Processing
```bash
# 1. Upload MNR PDF
curl -X POST "http://localhost:8000/api/upload-mnr" \
  -F "file=@Patient C.S..pdf"

# 2. Extract data
curl -X POST "http://localhost:8000/api/extract-mnr" \
  -H "Content-Type: application/json" \
  -d '{"mnr_pdf_name": "Patient C.S..pdf"}'

# 3. Map to ASH format
curl -X POST "http://localhost:8000/api/map-to-ash" \
  -H "Content-Type: application/json" \
  -d '{"Height": {"feet": 5, "inches": 8}, ...}'

# 4. Generate ASH PDF
curl -X POST "http://localhost:8000/api/generate-ash-pdf" \
  -H "Content-Type: application/json" \
  -d '{"height": "5 ft 8 in", ...}'
```

## Frontend Features

The React frontend provides:

- **PDF Upload**: Drag-and-drop or click to upload MNR PDFs
- **Manual Entry**: Enter patient notes manually if no PDF available
- **Live Preview**: See extracted/entered data in real-time
- **ASH PDF Download**: Download the generated ASH Medical form
- **Form Reset**: Clear all data and start fresh

## Data Flow

1. **Input**: MNR PDF form or manual patient notes
2. **OCR Processing**: Extract text from PDF (if uploaded)
3. **Field Parsing**: Extract structured data using regex patterns
4. **Schema Mapping**: Transform MNR nested structure to ASH flat structure
5. **PDF Generation**: Fill ASH template with mapped data
6. **Output**: Downloadable filled ASH Medical PDF

## File Structure

```
mnr_form_api/
├── main.py                 # FastAPI application
├── mnr_to_ash_single.py    # Core processing logic
├── requirements.txt        # Python dependencies
├── ash_medical_form.pdf    # ASH template
├── Patient C.S..pdf        # Sample MNR form
├── uploads/               # Uploaded files (created on first run)
└── outputs/               # Generated PDFs (created on first run)

mnr-form-ai/
├── src/
│   ├── services/
│   │   └── api.ts        # API client
│   ├── pages/
│   │   └── Index.tsx     # Main page with upload
│   └── components/       # React components
├── .env                  # Environment variables
└── package.json         # Node dependencies
```

## Technologies Used

### Backend
- **FastAPI**: Modern Python web framework
- **PyMuPDF**: PDF form field manipulation
- **PyPDF2**: PDF reading and writing
- **ReportLab**: PDF overlay generation
- **Pytesseract**: OCR text extraction
- **pdf2image**: PDF to image conversion

### Frontend
- **React**: UI framework
- **TypeScript**: Type-safe JavaScript
- **Vite**: Build tool
- **TailwindCSS**: Styling
- **shadcn/ui**: Component library

## Development

### Running Tests
```bash
# Backend tests
cd mnr_form_api
python -m pytest

# Frontend tests
cd mnr-form-ai
npm test
```

### API Documentation

When the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### OCR Not Working
- Ensure tesseract is installed: `tesseract --version`
- Check PDF quality - low resolution scans may fail
- API falls back to sample data if OCR fails

### PDF Generation Issues
- Verify ash_medical_form.pdf exists in mnr_form_api/
- Check console for specific error messages
- Try different PDF filling methods in code

### CORS Errors
- Ensure backend is running on port 8000
- Check .env file has correct VITE_API_URL
- Verify CORS middleware configuration in main.py

## License

MIT