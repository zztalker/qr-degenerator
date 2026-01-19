#!/usr/bin/env python3
"""
QR Code Updater - A cross-platform application to read QR codes from PDFs,
modify the Purpose field, and generate updated QR codes.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import qrcode
import tempfile
import os
import re
from pathlib import Path

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
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

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
                       font=('Helvetica', 24, 'bold'))

        style.configure('Subtitle.TLabel',
                       background=self.COLORS['bg_dark'],
                       foreground=self.COLORS['text_dim'],
                       font=('Helvetica', 11))

        style.configure('Dark.TLabel',
                       background=self.COLORS['bg_dark'],
                       foreground=self.COLORS['text'],
                       font=('Helvetica', 11))

        style.configure('Card.TLabel',
                       background=self.COLORS['bg_medium'],
                       foreground=self.COLORS['text'],
                       font=('Helvetica', 11))

        style.configure('CardTitle.TLabel',
                       background=self.COLORS['bg_medium'],
                       foreground=self.COLORS['accent'],
                       font=('Helvetica', 13, 'bold'))

        # Button styles
        style.configure('Accent.TButton',
                       background=self.COLORS['accent'],
                       foreground='white',
                       font=('Helvetica', 11, 'bold'),
                       padding=(20, 10))

        style.map('Accent.TButton',
                 background=[('active', self.COLORS['accent_hover']),
                            ('pressed', self.COLORS['accent'])])

        style.configure('Secondary.TButton',
                       background=self.COLORS['bg_light'],
                       foreground=self.COLORS['text'],
                       font=('Helvetica', 10),
                       padding=(15, 8))

        style.map('Secondary.TButton',
                 background=[('active', self.COLORS['border']),
                            ('pressed', self.COLORS['bg_medium'])])

        # Entry style
        style.configure('Dark.TEntry',
                       fieldbackground=self.COLORS['bg_light'],
                       foreground=self.COLORS['text'],
                       insertcolor=self.COLORS['text'],
                       padding=10)

    def create_widgets(self):
        """Create all UI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Header
        self.create_header(main_frame)

        # Content area with two columns
        content_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
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
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = ttk.Label(header_frame, text="◈ QR Code Updater",
                               style='Title.TLabel')
        title_label.pack(anchor='w')

        subtitle_label = ttk.Label(header_frame,
                                  text="Extract QR codes from PDFs, modify Purpose field, and generate updated codes",
                                  style='Subtitle.TLabel')
        subtitle_label.pack(anchor='w', pady=(5, 0))

    def create_left_panel(self, parent):
        """Create left panel with controls."""
        left_frame = ttk.Frame(parent, style='Dark.TFrame')
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 15))
        left_frame.columnconfigure(0, weight=1)

        # File selection card
        file_card = self.create_card(left_frame, "1. Select PDF File")
        file_card.pack(fill=tk.X, pady=(0, 15))

        file_inner = ttk.Frame(file_card, style='Medium.TFrame')
        file_inner.pack(fill=tk.X, padx=15, pady=(0, 15))

        self.file_label = ttk.Label(file_inner, text="No file selected",
                                   style='Card.TLabel', wraplength=300)
        self.file_label.pack(fill=tk.X, pady=(0, 10))

        btn_frame = ttk.Frame(file_inner, style='Medium.TFrame')
        btn_frame.pack(fill=tk.X)

        browse_btn = ttk.Button(btn_frame, text="📁 Browse PDF",
                               style='Accent.TButton',
                               command=self.browse_pdf)
        browse_btn.pack(side=tk.LEFT)

        # Decoded text card
        decoded_card = self.create_card(left_frame, "2. Decoded QR Content")
        decoded_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        decoded_inner = ttk.Frame(decoded_card, style='Medium.TFrame')
        decoded_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # Text widget for decoded content with scrollbar
        text_frame = ttk.Frame(decoded_inner, style='Medium.TFrame')
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.decoded_text_widget = tk.Text(text_frame, height=8, wrap=tk.WORD,
                                          bg=self.COLORS['bg_light'],
                                          fg=self.COLORS['text'],
                                          insertbackground=self.COLORS['text'],
                                          font=('Consolas', 10),
                                          relief=tk.FLAT,
                                          padx=10, pady=10)
        self.decoded_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL,
                                 command=self.decoded_text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.decoded_text_widget.config(yscrollcommand=scrollbar.set)
        self.decoded_text_widget.config(state=tk.DISABLED)

        # Purpose update card
        purpose_card = self.create_card(left_frame, "3. Update Purpose Field")
        purpose_card.pack(fill=tk.X)

        purpose_inner = ttk.Frame(purpose_card, style='Medium.TFrame')
        purpose_inner.pack(fill=tk.X, padx=15, pady=(0, 15))

        # Current purpose display
        current_label = ttk.Label(purpose_inner, text="Current Purpose:",
                                 style='Card.TLabel')
        current_label.pack(anchor='w', pady=(0, 5))

        self.current_purpose_label = ttk.Label(purpose_inner, text="—",
                                              style='Card.TLabel',
                                              foreground=self.COLORS['text_dim'],
                                              wraplength=350)
        self.current_purpose_label.pack(anchor='w', pady=(0, 15))

        # New purpose input
        new_label = ttk.Label(purpose_inner, text="New Purpose:",
                             style='Card.TLabel')
        new_label.pack(anchor='w', pady=(0, 5))

        self.purpose_entry = tk.Entry(purpose_inner,
                                     bg=self.COLORS['bg_light'],
                                     fg=self.COLORS['text'],
                                     insertbackground=self.COLORS['text'],
                                     font=('Helvetica', 11),
                                     relief=tk.FLAT)
        self.purpose_entry.pack(fill=tk.X, pady=(0, 15), ipady=8)

        # Generate button
        generate_btn = ttk.Button(purpose_inner, text="⟳ Generate Updated QR Code",
                                 style='Accent.TButton',
                                 command=self.generate_updated_qr)
        generate_btn.pack(fill=tk.X)

    def create_right_panel(self, parent):
        """Create right panel with QR code display."""
        right_frame = ttk.Frame(parent, style='Dark.TFrame')
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(15, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

        # Original QR card
        original_card = self.create_card(right_frame, "Original QR Code")
        original_card.grid(row=0, column=0, sticky='nsew', pady=(0, 15))

        original_inner = ttk.Frame(original_card, style='Medium.TFrame')
        original_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        self.original_qr_label = ttk.Label(original_inner, text="No QR code loaded",
                                          style='Card.TLabel',
                                          anchor='center')
        self.original_qr_label.pack(fill=tk.BOTH, expand=True)

        # Updated QR card
        updated_card = self.create_card(right_frame, "Updated QR Code")
        updated_card.grid(row=1, column=0, sticky='nsew')

        updated_inner = ttk.Frame(updated_card, style='Medium.TFrame')
        updated_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        self.updated_qr_label = ttk.Label(updated_inner, text="Generate to see updated QR",
                                         style='Card.TLabel',
                                         anchor='center')
        self.updated_qr_label.pack(fill=tk.BOTH, expand=True)

        # Save button
        save_btn = ttk.Button(updated_inner, text="💾 Save QR Code",
                             style='Secondary.TButton',
                             command=self.save_qr_code)
        save_btn.pack(pady=(10, 0))

    def create_card(self, parent, title):
        """Create a card-style frame with title."""
        card = ttk.Frame(parent, style='Medium.TFrame')

        # Title
        title_label = ttk.Label(card, text=title, style='CardTitle.TLabel')
        title_label.pack(anchor='w', padx=15, pady=(15, 10))

        # Separator line
        separator = ttk.Frame(card, height=1)
        separator.pack(fill=tk.X, padx=15)
        separator.configure(style='Medium.TFrame')

        return card

    def create_status_bar(self, parent):
        """Create status bar at bottom."""
        status_frame = ttk.Frame(parent, style='Dark.TFrame')
        status_frame.pack(fill=tk.X, pady=(10, 0))

        self.status_label = ttk.Label(status_frame,
                                     text=f"Ready • PDF Backend: {PDF_BACKEND or 'Not available'} • QR Decoder: {QR_DECODER or 'Not available'}",
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
            for i, img in enumerate(images):
                qr_data, qr_image = self.find_qr_code(img)

                if qr_data:
                    self.decoded_text = qr_data
                    self.original_qr_image = qr_image

                    # Update UI
                    self.update_decoded_display(qr_data)
                    self.display_original_qr(qr_image)
                    self.set_status(f"✓ QR code found on page {i + 1}")
                    return

            self.set_status("No QR code found in PDF", is_error=True)

        except Exception as e:
            self.set_status(f"Error processing PDF: {str(e)}", is_error=True)
            messagebox.showerror("Error", f"Failed to process PDF:\n{str(e)}")

    def extract_images_from_pdf(self, pdf_path):
        """Extract images from PDF pages."""
        images = []

        if PDF_BACKEND == "pymupdf" and fitz:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Render at higher resolution for better QR detection
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
            doc.close()

        elif PDF_BACKEND == "pdf2image" and convert_from_path:
            images = convert_from_path(pdf_path, dpi=200)

        return images

    def find_qr_code(self, image):
        """Find and decode QR code in image."""
        if pyzbar_decode is None or cv2 is None:
            return None, None

        # Convert PIL Image to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Decode QR codes
        decoded_objects = pyzbar_decode(cv_image)

        for obj in decoded_objects:
            if obj.type == 'QRCODE':
                # Extract QR code region for display
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

                    qr_image = image.crop((x_min, y_min, x_max, y_max))
                else:
                    qr_image = image

                # Decode the data
                try:
                    qr_data = obj.data.decode('utf-8')
                except:
                    qr_data = obj.data.decode('cp1251')  # Try Russian encoding

                return qr_data, qr_image

        return None, None

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
            self.purpose_entry.insert(0, purpose)

    def extract_purpose(self, text):
        """Extract Purpose field from QR text."""
        match = re.search(r'Purpose=([^|]*)', text)
        return match.group(1) if match else None

    def display_original_qr(self, image):
        """Display the original QR code image."""
        if image:
            # Resize to fit display
            display_size = 180
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
        display_size = 180
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


def main():
    """Main entry point."""
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
