# QR Code Updater

A cross-platform Python application to read QR codes from PDF files, modify the Purpose field, and generate updated QR codes.

## Features

- 📄 Load PDF files and automatically detect QR codes
- 🔍 Decode QR code content (supports UTF-8 and Cyrillic encoding)
- ✏️ Edit the "Purpose" field in payment QR codes
- 🔲 Generate new QR codes with updated information
- 💾 Save updated QR codes as PNG images
- 🎨 Modern dark-themed UI that works on Windows and macOS

## Installation

### 1. Create Virtual Environment (Recommended)

```bash
cd qr-code-updater
python3 -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install System Dependencies

#### macOS
```bash
brew install zbar
brew install poppler  # Only if using pdf2image backend
```

#### Windows
The pyzbar library should work out of the box on Windows.
If using pdf2image, install [Poppler for Windows](https://github.com/osber/poppler-for-windows).

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install libzbar0
sudo apt-get install poppler-utils  # Only if using pdf2image backend
```

## Usage

### Run the Application

```bash
python main.py
```

### Steps to Use

1. **Select PDF File**: Click "Browse PDF" to load a PDF containing a QR code
2. **View Decoded Content**: The app will automatically find and decode the QR code
3. **Edit Purpose**: Modify the "Purpose" field with your desired text
4. **Generate QR Code**: Click "Generate Updated QR Code" to create a new QR code
5. **Save**: Click "Save QR Code" to export the updated QR code as a PNG image

## QR Code Format

The application is designed to work with Russian payment QR codes in the following format:

```
ST00012|Name=...|PersonalAcc=...|BankName=...|BIC=...|CorrespAcc=...|Sum=...|Purpose=...|...
```

The `Purpose` field can be modified while keeping all other fields intact.

## Dependencies

| Package | Purpose |
|---------|---------|
| PyMuPDF | Reading PDF files (primary backend) |
| pdf2image | Alternative PDF reading backend |
| pyzbar | QR code detection and decoding |
| opencv-python | Image processing for QR detection |
| Pillow | Image manipulation |
| qrcode | QR code generation |

## Troubleshooting

### "No QR code found in PDF"
- Ensure the PDF contains a clear, scannable QR code
- Try a higher quality PDF scan
- The QR code should be clearly visible on the page

### "No PDF backend available"
- Install PyMuPDF: `pip install PyMuPDF`
- Or install pdf2image: `pip install pdf2image` (requires Poppler)

### "No QR decoder available"
- Install pyzbar: `pip install pyzbar`
- Install zbar system library (see Installation section)
- Install opencv-python: `pip install opencv-python`

### Import errors on macOS
If you see errors about zbar, make sure you've installed it:
```bash
brew install zbar
```

## License

MIT License - Feel free to use and modify as needed.
