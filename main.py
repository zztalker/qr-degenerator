#!/usr/bin/env python3
"""
QR Code Updater - A cross-platform application to read QR codes from PDFs,
modify the Purpose field, and generate updated QR codes.

Usage:
    python main.py           # Normal mode
    python main.py --debug   # Debug mode (saves images, verbose output)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import qrcode
import re
import argparse
from pathlib import Path
from datetime import datetime

# Debug mode - controlled by --debug argument
DEBUG_MODE = False
DEBUG_OUTPUT_DIR = Path(__file__).parent / "debug_output"


def debug_print(*args, **kwargs):
    """Print only if debug mode is enabled."""
    if DEBUG_MODE:
        print(*args, **kwargs)

# PDF and QR detection imports
try:
    import fitz  # PyMuPDF
    PDF_BACKEND = "pymupdf"
except ImportError:
    fitz = None
    PDF_BACKEND = None

try:
    from pdf2image import convert_from_path
    if PDF_BACKEND is None:
        PDF_BACKEND = "pdf2image"
except ImportError:
    convert_from_path = None

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    import cv2
    import numpy as np
    QR_DECODER = "pyzbar"
except ImportError:
    pyzbar_decode = None
    cv2 = None
    np = None
    QR_DECODER = None


def save_debug_image(image, name, subfolder=""):
    """Save image to debug folder if debug mode is enabled."""
    if not DEBUG_MODE:
        return

    try:
        # Create debug directory
        output_dir = DEBUG_OUTPUT_DIR
        if subfolder:
            output_dir = output_dir / subfolder
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{timestamp}_{name}.png"
        filepath = output_dir / filename

        # Save image
        if hasattr(image, 'save'):
            image.save(filepath)
        elif cv2 is not None:
            # OpenCV image (numpy array)
            cv2.imwrite(str(filepath), image)

        debug_print(f"[DEBUG] Saved: {filepath}")
    except Exception as e:
        debug_print(f"[DEBUG] Failed to save image: {e}")


class QRCodeUpdater:
    """Main application class for QR Code Updater."""

    # Color scheme - Modern dark theme
    COLORS = {
        'bg_dark': '#1a1a2e',
        'bg_medium': '#16213e',
        'bg_light': '#0f3460',
        'accent': '#e94560',
        'accent_hover': '#ff6b6b',
        'text': '#eaeaea',
        'text_dim': '#a0a0a0',
        'success': '#4ecca3',
        'border': '#2a2a4a',
    }

    def __init__(self, root):
        self.root = root
        self.root.title("QR Code Updater")
        self.root.geometry("950x650")
        self.root.minsize(900, 600)

        # Configure root background
        self.root.configure(bg=self.COLORS['bg_dark'])

        # State variables
        self.pdf_path = None
        self.decoded_text = None
        self.updated_text = None
        self.qr_image = None
        self.original_qr_image = None

        # Configure styles
        self.setup_styles()

        # Build UI
        self.create_widgets()

    def setup_styles(self):
        """Configure ttk styles for modern look."""
        style = ttk.Style()
        style.theme_use('clam')

        # Frame styles
        style.configure('Dark.TFrame', background=self.COLORS['bg_dark'])
        style.configure('Medium.TFrame', background=self.COLORS['bg_medium'])
        style.configure('Card.TFrame', background=self.COLORS['bg_medium'])

        # Label styles
        style.configure('Title.TLabel',
                       background=self.COLORS['bg_dark'],
                       foreground=self.COLORS['accent'],
                       font=('Helvetica', 20, 'bold'))

        style.configure('Subtitle.TLabel',
                       background=self.COLORS['bg_dark'],
                       foreground=self.COLORS['text_dim'],
                       font=('Helvetica', 10))

        style.configure('Dark.TLabel',
                       background=self.COLORS['bg_dark'],
                       foreground=self.COLORS['text'],
                       font=('Helvetica', 10))

        style.configure('Card.TLabel',
                       background=self.COLORS['bg_medium'],
                       foreground=self.COLORS['text'],
                       font=('Helvetica', 10))

        style.configure('CardTitle.TLabel',
                       background=self.COLORS['bg_medium'],
                       foreground=self.COLORS['accent'],
                       font=('Helvetica', 11, 'bold'))

        # Button styles
        style.configure('Accent.TButton',
                       background=self.COLORS['accent'],
                       foreground='white',
                       font=('Helvetica', 10, 'bold'),
                       padding=(15, 8))

        style.map('Accent.TButton',
                 background=[('active', self.COLORS['accent_hover']),
                            ('pressed', self.COLORS['accent'])])

        style.configure('Secondary.TButton',
                       background=self.COLORS['bg_light'],
                       foreground=self.COLORS['text'],
                       font=('Helvetica', 9),
                       padding=(12, 6))

        style.map('Secondary.TButton',
                 background=[('active', self.COLORS['border']),
                            ('pressed', self.COLORS['bg_medium'])])

    def create_widgets(self):
        """Create all UI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Header (compact)
        self.create_header(main_frame)

        # Content area with two columns
        content_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=2)
        content_frame.rowconfigure(0, weight=1)

        # Left column - Input/Controls
        self.create_left_panel(content_frame)

        # Right column - QR Display
        self.create_right_panel(content_frame)

        # Status bar
        self.create_status_bar(main_frame)

    def create_header(self, parent):
        """Create application header."""
        header_frame = ttk.Frame(parent, style='Dark.TFrame')
        header_frame.pack(fill=tk.X)

        title_label = ttk.Label(header_frame, text="◈ QR Code Updater",
                               style='Title.TLabel')
        title_label.pack(side=tk.LEFT)

        subtitle_label = ttk.Label(header_frame,
                                  text="  •  Extract QR from PDF, modify Purpose, generate updated code",
                                  style='Subtitle.TLabel')
        subtitle_label.pack(side=tk.LEFT, pady=(5, 0))

    def create_left_panel(self, parent):
        """Create left panel with controls."""
        left_frame = ttk.Frame(parent, style='Dark.TFrame')
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)  # Decoded text expands

        # File selection card (row 0, fixed height)
        file_card = self.create_card(left_frame, "1. Select PDF File")
        file_card.grid(row=0, column=0, sticky='ew', pady=(0, 10))

        file_inner = ttk.Frame(file_card, style='Medium.TFrame')
        file_inner.pack(fill=tk.X, padx=12, pady=(0, 12))

        file_row = ttk.Frame(file_inner, style='Medium.TFrame')
        file_row.pack(fill=tk.X)

        self.file_label = ttk.Label(file_row, text="No file selected",
                                   style='Card.TLabel', wraplength=250)
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        browse_btn = ttk.Button(file_row, text="📁 Browse",
                               style='Accent.TButton',
                               command=self.browse_pdf)
        browse_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # Decoded text card (row 1, expands)
        decoded_card = self.create_card(left_frame, "2. Decoded QR Content")
        decoded_card.grid(row=1, column=0, sticky='nsew', pady=(0, 10))

        decoded_inner = ttk.Frame(decoded_card, style='Medium.TFrame')
        decoded_inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        # Text widget for decoded content with scrollbar
        text_frame = ttk.Frame(decoded_inner, style='Medium.TFrame')
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.decoded_text_widget = tk.Text(text_frame, height=6, wrap=tk.WORD,
                                          bg=self.COLORS['bg_light'],
                                          fg=self.COLORS['text'],
                                          insertbackground=self.COLORS['text'],
                                          font=('Consolas', 9),
                                          relief=tk.FLAT,
                                          padx=8, pady=8)
        self.decoded_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL,
                                 command=self.decoded_text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.decoded_text_widget.config(yscrollcommand=scrollbar.set)
        self.decoded_text_widget.config(state=tk.DISABLED)

        # Purpose update card (row 2, fixed height)
        purpose_card = self.create_card(left_frame, "3. Update Purpose Field")
        purpose_card.grid(row=2, column=0, sticky='ew')

        purpose_inner = ttk.Frame(purpose_card, style='Medium.TFrame')
        purpose_inner.pack(fill=tk.X, padx=12, pady=(0, 12))

        # Current purpose display (compact, single row)
        current_row = ttk.Frame(purpose_inner, style='Medium.TFrame')
        current_row.pack(fill=tk.X, pady=(0, 8))

        current_label = ttk.Label(current_row, text="Current:",
                                 style='Card.TLabel')
        current_label.pack(side=tk.LEFT)

        self.current_purpose_label = ttk.Label(current_row, text="—",
                                              style='Card.TLabel',
                                              foreground=self.COLORS['text_dim'],
                                              wraplength=400)
        self.current_purpose_label.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)

        # New purpose input row
        new_row = ttk.Frame(purpose_inner, style='Medium.TFrame')
        new_row.pack(fill=tk.X)

        new_label = ttk.Label(new_row, text="New:",
                             style='Card.TLabel')
        new_label.pack(side=tk.LEFT)

        self.purpose_entry = tk.Entry(new_row,
                                     bg=self.COLORS['bg_light'],
                                     fg=self.COLORS['text'],
                                     insertbackground=self.COLORS['text'],
                                     font=('Helvetica', 10),
                                     relief=tk.FLAT)
        self.purpose_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10), ipady=6)

        # Generate button - always visible
        generate_btn = ttk.Button(new_row, text="⟳ Generate QR",
                                 style='Accent.TButton',
                                 command=self.generate_updated_qr)
        generate_btn.pack(side=tk.RIGHT)

    def create_right_panel(self, parent):
        """Create right panel with QR code display."""
        right_frame = ttk.Frame(parent, style='Dark.TFrame')
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

        # Original QR card
        original_card = self.create_card(right_frame, "Original QR Code")
        original_card.grid(row=0, column=0, sticky='nsew', pady=(0, 10))

        original_inner = ttk.Frame(original_card, style='Medium.TFrame')
        original_inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.original_qr_label = ttk.Label(original_inner, text="No QR code loaded",
                                          style='Card.TLabel',
                                          anchor='center')
        self.original_qr_label.pack(fill=tk.BOTH, expand=True)

        # Updated QR card
        updated_card = self.create_card(right_frame, "Updated QR Code")
        updated_card.grid(row=1, column=0, sticky='nsew')

        updated_inner = ttk.Frame(updated_card, style='Medium.TFrame')
        updated_inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.updated_qr_label = ttk.Label(updated_inner, text="Generate to see updated QR",
                                         style='Card.TLabel',
                                         anchor='center')
        self.updated_qr_label.pack(fill=tk.BOTH, expand=True)

        # Save button
        save_btn = ttk.Button(updated_inner, text="💾 Save QR Code",
                             style='Secondary.TButton',
                             command=self.save_qr_code)
        save_btn.pack(pady=(5, 0))

    def create_card(self, parent, title):
        """Create a card-style frame with title."""
        card = ttk.Frame(parent, style='Medium.TFrame')

        # Title
        title_label = ttk.Label(card, text=title, style='CardTitle.TLabel')
        title_label.pack(anchor='w', padx=12, pady=(10, 8))

        return card

    def create_status_bar(self, parent):
        """Create status bar at bottom."""
        status_frame = ttk.Frame(parent, style='Dark.TFrame')
        status_frame.pack(fill=tk.X, pady=(8, 0))

        self.status_label = ttk.Label(status_frame,
                                     text=f"Ready • PDF: {PDF_BACKEND or 'N/A'} • QR: {QR_DECODER or 'N/A'}",
                                     style='Subtitle.TLabel')
        self.status_label.pack(anchor='w')

    def set_status(self, message, is_error=False):
        """Update status bar message."""
        color = self.COLORS['accent'] if is_error else self.COLORS['success']
        self.status_label.configure(text=message, foreground=color)

    def browse_pdf(self):
        """Open file dialog to select PDF."""
        file_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )

        if file_path:
            self.pdf_path = file_path
            self.file_label.configure(text=Path(file_path).name)
            self.set_status("Loading PDF and searching for QR codes...")
            self.root.update()
            self.process_pdf(file_path)

    def process_pdf(self, pdf_path):
        """Process PDF to find and decode QR codes."""
        if PDF_BACKEND is None:
            messagebox.showerror("Error", "No PDF backend available. Please install PyMuPDF or pdf2image.")
            return

        if QR_DECODER is None:
            messagebox.showerror("Error", "No QR decoder available. Please install pyzbar and opencv-python.")
            return

        try:
            # Extract images from PDF
            images = self.extract_images_from_pdf(pdf_path)

            if not images:
                self.set_status("No pages found in PDF", is_error=True)
                return

            # Search for QR codes in each image
            debug_print(f"[DEBUG] Found {len(images)} images in PDF")
            for i, img in enumerate(images):
                debug_print(f"[DEBUG] Processing image {i+1} of {len(images)}")
                qr_data, qr_image = self.find_utf8_qr_code(img)
                debug_print(f"[DEBUG] QR data: {qr_data}")
                if qr_data:
                    self.decoded_text = qr_data
                    self.original_qr_image = qr_image

                    # Update UI
                    self.update_decoded_display(qr_data)
                    self.display_original_qr(qr_image)
                    self.set_status(f"✓ UTF-8 QR code found on page {i + 1}")
                    return

            self.set_status("No UTF-8 QR code found in PDF", is_error=True)

        except Exception as e:
            self.set_status(f"Error processing PDF: {str(e)}", is_error=True)
            messagebox.showerror("Error", f"Failed to process PDF:\n{str(e)}")

    def extract_images_from_pdf(self, pdf_path):
        """Extract images from PDF pages."""
        images = []

        # Clear debug folder for new extraction
        if DEBUG_MODE:
            import shutil
            if DEBUG_OUTPUT_DIR.exists():
                shutil.rmtree(DEBUG_OUTPUT_DIR)
            DEBUG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            debug_print(f"[DEBUG] Debug images will be saved to: {DEBUG_OUTPUT_DIR}")

        if PDF_BACKEND == "pymupdf" and fitz:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Render at higher resolution for better QR detection
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)

                # Save debug image
                save_debug_image(img, f"page_{page_num + 1}_extracted")
            doc.close()

        elif PDF_BACKEND == "pdf2image" and convert_from_path:
            images = convert_from_path(pdf_path, dpi=200)
            for i, img in enumerate(images):
                save_debug_image(img, f"page_{i + 1}_extracted")

        return images

    def find_utf8_qr_code(self, image):
        """
        Find and decode QR code in image.
        Prefers UTF-8 encoded QR codes (starting with ST00012).
        Ignores Windows-1251 encoded QR codes.
        Uses multiple detection methods and image preprocessing for better coverage.
        """
        if cv2 is None:
            return None, None

        # Convert PIL Image to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        # Create multiple image variants for better detection
        image_variants = self._create_image_variants(gray_image)

        utf8_candidates = []
        qr_detector = cv2.QRCodeDetector()

        # Method 1: Try OpenCV's QRCodeDetector on all image variants
        debug_print("[DEBUG] Trying OpenCV QRCodeDetector on multiple image variants...")
        for variant_name, variant_img in image_variants.items():
            save_debug_image(variant_img, f"variant_{variant_name}")

            retval, decoded_info, points, straight_qrcode = qr_detector.detectAndDecodeMulti(variant_img)

            if retval and decoded_info:
                debug_print(f"[DEBUG] OpenCV ({variant_name}): found {len(decoded_info)} QR codes")
                for i, data in enumerate(decoded_info):
                    if data:  # Non-empty string
                        debug_print(f"[DEBUG] OpenCV ({variant_name}) QR #{i+1}: length={len(data)}, starts='{data[:30]}...'")

                        # Extract region if points available
                        qr_image = image
                        if points is not None and len(points) > i:
                            pts = points[i]
                            x_coords = [p[0] for p in pts]
                            y_coords = [p[1] for p in pts]
                            x_min, x_max = int(min(x_coords)), int(max(x_coords))
                            y_min, y_max = int(min(y_coords)), int(max(y_coords))
                            padding = 20
                            x_min = max(0, x_min - padding)
                            y_min = max(0, y_min - padding)
                            x_max = min(image.width, x_max + padding)
                            y_max = min(image.height, y_max + padding)
                            qr_image = image.crop((x_min, y_min, x_max, y_max))

                        qr_type = "ST00012" if 'ST00012' in data[:20] else "other"
                        save_debug_image(qr_image, f"opencv_{variant_name}_qr_{i+1}_{qr_type}")

                        if 'ST00012' in data[:20]:
                            debug_print(f"[DEBUG] OpenCV ({variant_name}) QR #{i+1}: ✓ Found ST00012!")
                            utf8_candidates.append((data, qr_image))

        if utf8_candidates:
            return utf8_candidates[0]

        # Method 2: pyzbar on multiple image variants
        if pyzbar_decode is not None:
            debug_print("[DEBUG] Trying pyzbar on multiple image variants...")

            all_detected_regions = []  # Track regions to re-scan

            for variant_name, variant_img in image_variants.items():
                # Convert grayscale back to BGR for pyzbar
                if len(variant_img.shape) == 2:
                    variant_bgr = cv2.cvtColor(variant_img, cv2.COLOR_GRAY2BGR)
                else:
                    variant_bgr = variant_img

                decoded_objects = pyzbar_decode(variant_bgr)
                debug_print(f"[DEBUG] pyzbar ({variant_name}): found {len(decoded_objects)} codes")

                for i, obj in enumerate(decoded_objects):
                    debug_print(f"[DEBUG] pyzbar ({variant_name}) #{i+1}: type = {obj.type}")

                    qr_region = self._extract_qr_region(image, obj)
                    save_debug_image(qr_region, f"pyzbar_{variant_name}_{i+1}_{obj.type}")

                    # For QRCODE type, try to decode
                    if obj.type == 'QRCODE':
                        raw_data = obj.data
                        debug_print(f"[DEBUG] pyzbar ({variant_name}) #{i+1}: bytes={len(raw_data)}, first 20={raw_data[:20]}")

                        try:
                            qr_data = raw_data.decode('utf-8')
                            debug_print(f"[DEBUG] pyzbar ({variant_name}) #{i+1}: starts='{qr_data[:30]}...'")

                            if 'ST00012' in qr_data[:20]:
                                debug_print(f"[DEBUG] pyzbar ({variant_name}) #{i+1}: ✓ Found ST00012!")
                                utf8_candidates.append((qr_data, qr_region))
                        except UnicodeDecodeError:
                            pass

                    # For CODE128 or other types, save region for re-scanning
                    elif obj.type in ['CODE128', 'CODE39', 'EAN13']:
                        all_detected_regions.append((obj, qr_region, variant_name))

            if utf8_candidates:
                return utf8_candidates[0]

            # Method 3: Re-scan CODE128 regions as they might be misidentified QR codes
            debug_print("[DEBUG] Re-scanning misidentified regions with OpenCV...")
            for obj, region_pil, variant_name in all_detected_regions:
                # Convert region to OpenCV and try QR detection
                region_cv = cv2.cvtColor(np.array(region_pil), cv2.COLOR_RGB2GRAY)

                # Try with different preprocessing on the region
                for thresh_name, thresh_img in self._create_image_variants(region_cv).items():
                    retval, data, points, _ = qr_detector.detectAndDecode(thresh_img)
                    if retval and data:
                        debug_print(f"[DEBUG] Re-scan ({variant_name}/{thresh_name}): decoded='{data[:30]}...'")
                        save_debug_image(region_pil, f"rescan_{variant_name}_{thresh_name}_SUCCESS")

                        if 'ST00012' in data[:20]:
                            debug_print(f"[DEBUG] Re-scan: ✓ Found ST00012!")
                            utf8_candidates.append((data, region_pil))
                            break

                if utf8_candidates:
                    break

            if utf8_candidates:
                return utf8_candidates[0]

        debug_print("[DEBUG] No ST00012 UTF-8 payment QR code found")
        return None, None

    def _create_image_variants(self, gray_image):
        """Create multiple preprocessed versions of the image for better detection."""
        variants = {
            'original': gray_image,
        }

        # Adaptive threshold
        variants['adaptive_thresh'] = cv2.adaptiveThreshold(
            gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # OTSU threshold
        _, variants['otsu'] = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # High contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        variants['clahe'] = clahe.apply(gray_image)

        # Inverted (some QR codes are inverted)
        variants['inverted'] = cv2.bitwise_not(gray_image)

        # Sharpened
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        variants['sharpened'] = cv2.filter2D(gray_image, -1, kernel)

        return variants

    def _extract_qr_region(self, image, obj):
        """Extract the QR code region from the image."""
        points = obj.polygon
        if points:
            # Get bounding box
            x_coords = [p.x for p in points]
            y_coords = [p.y for p in points]
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)

            # Add some padding
            padding = 20
            x_min = max(0, x_min - padding)
            y_min = max(0, y_min - padding)
            x_max = min(image.width, x_max + padding)
            y_max = min(image.height, y_max + padding)

            return image.crop((x_min, y_min, x_max, y_max))
        return image

    def update_decoded_display(self, text):
        """Update the decoded text display."""
        # Enable editing temporarily
        self.decoded_text_widget.config(state=tk.NORMAL)
        self.decoded_text_widget.delete(1.0, tk.END)

        # Format for readability - split by pipe
        formatted = text.replace('|', '\n')
        self.decoded_text_widget.insert(1.0, formatted)
        self.decoded_text_widget.config(state=tk.DISABLED)

        # Extract and display current Purpose
        purpose = self.extract_purpose(text)
        self.current_purpose_label.configure(text=purpose or "Not found")

        # Pre-fill the entry with current purpose
        self.purpose_entry.delete(0, tk.END)
        if purpose:
            debug_print(f"[DEBUG] Current purpose: {purpose}")
            add_text = Path("append.txt").read_text()
            self.purpose_entry.insert(0, purpose + add_text)
            debug_print(f"[DEBUG] Updated purpose: {purpose + add_text}")

    def extract_purpose(self, text):
        """Extract Purpose field from QR text."""
        match = re.search(r'Purpose=([^|]*)', text)
        return match.group(1) if match else None

    def display_original_qr(self, image):
        """Display the original QR code image."""
        if image:
            # Resize to fit display
            display_size = 150
            image = image.copy()
            image.thumbnail((display_size, display_size), Image.Resampling.LANCZOS)

            photo = ImageTk.PhotoImage(image)
            self.original_qr_label.configure(image=photo, text="")
            self.original_qr_label.image = photo  # Keep reference

    def generate_updated_qr(self):
        """Generate new QR code with updated Purpose."""
        if not self.decoded_text:
            messagebox.showwarning("Warning", "Please load a PDF with a QR code first.")
            return

        new_purpose = self.purpose_entry.get().strip()
        if not new_purpose:
            messagebox.showwarning("Warning", "Please enter a new Purpose value.")
            return

        # Update the Purpose field in the text
        self.updated_text = re.sub(
            r'Purpose=[^|]*',
            f'Purpose={new_purpose}',
            self.decoded_text
        )

        # Generate new QR code
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(self.updated_text)
        qr.make(fit=True)

        self.qr_image = qr.make_image(fill_color="black", back_color="white")

        # Display the new QR code
        display_image = self.qr_image.copy()
        display_size = 300
        display_image.thumbnail((display_size, display_size), Image.Resampling.LANCZOS)

        photo = ImageTk.PhotoImage(display_image)
        self.updated_qr_label.configure(image=photo, text="")
        self.updated_qr_label.image = photo  # Keep reference

        self.set_status("✓ Updated QR code generated successfully")

    def save_qr_code(self):
        """Save the generated QR code to file."""
        if not self.qr_image:
            messagebox.showwarning("Warning", "Please generate an updated QR code first.")
            return

        # Suggest filename based on original PDF
        default_name = "updated_qr_code.png"
        if self.pdf_path:
            pdf_name = Path(self.pdf_path).stem
            default_name = f"{pdf_name}_updated_qr.png"

        file_path = filedialog.asksaveasfilename(
            title="Save QR Code",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )

        if file_path:
            self.qr_image.save(file_path)
            self.set_status(f"✓ QR code saved to {Path(file_path).name}")
            messagebox.showinfo("Success", f"QR code saved to:\n{file_path}")


def check_dependencies():
    """Check and report on missing dependencies."""
    issues = []

    if PDF_BACKEND is None:
        issues.append("• PDF reading: Install PyMuPDF (pip install PyMuPDF) or pdf2image")

    if QR_DECODER is None:
        issues.append("• QR decoding: Install pyzbar and opencv-python")
        issues.append("  On macOS: brew install zbar")
        issues.append("  On Windows: pyzbar should work directly")
        issues.append("  On Linux: sudo apt-get install libzbar0")

    return issues


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="QR Code Updater - Extract QR codes from PDFs, modify Purpose field, generate updated codes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py           # Normal mode
    python main.py --debug   # Debug mode (saves images to debug_output/, verbose output)
        """
    )
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug mode: save extracted images and print verbose output'
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    global DEBUG_MODE

    # Parse command line arguments
    args = parse_arguments()
    DEBUG_MODE = args.debug

    if DEBUG_MODE:
        print("=" * 50)
        print("DEBUG MODE ENABLED")
        print(f"Debug images will be saved to: {DEBUG_OUTPUT_DIR}")
        print("=" * 50)

    root = tk.Tk()

    # Check dependencies
    issues = check_dependencies()
    if issues:
        msg = "Some dependencies are missing:\n\n" + "\n".join(issues)
        msg += "\n\nThe application will start but some features may not work."
        messagebox.showwarning("Missing Dependencies", msg)

    app = QRCodeUpdater(root)
    root.mainloop()


if __name__ == "__main__":
    main()
