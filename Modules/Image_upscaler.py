import argparse
import os
import sys
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

class ImageUpscaler:
    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
    def enhance_image(self, image, **kwargs):
        """Apply various enhancements to the image"""
        enhanced = image.copy()
        
        # Apply sharpening
        if kwargs.get('m_sharpen', 0) > 0:
            sharpen_amount = kwargs['m_sharpen']
            radius = kwargs.get('m_sharpen_radius', 1.0)
            
            # Create unsharp mask filter
            blurred = enhanced.filter(ImageFilter.GaussianBlur(radius=radius))
            enhanced = Image.blend(enhanced, blurred, -sharpen_amount)
        
        # Apply denoising (using blur as approximation)
        if kwargs.get('m_denoise', 0) > 0:
            denoise_amount = kwargs['m_denoise']
            enhanced = enhanced.filter(ImageFilter.GaussianBlur(radius=denoise_amount * 0.5))
        
        # Apply contrast adjustment
        if kwargs.get('m_contrast', 1.0) != 1.0:
            contrast_enhancer = ImageEnhance.Contrast(enhanced)
            enhanced = contrast_enhancer.enhance(kwargs['m_contrast'])
        
        # Apply saturation adjustment
        if kwargs.get('m_saturation', 1.0) != 1.0:
            color_enhancer = ImageEnhance.Color(enhanced)
            enhanced = color_enhancer.enhance(kwargs['m_saturation'])
        
        # Apply detail enhancement
        if kwargs.get('m_use_detail', False):
            detail_amount = kwargs.get('m_detail', 1.0)
            detail_filter = ImageFilter.DETAIL
            detail_enhanced = enhanced.filter(detail_filter)
            enhanced = Image.blend(enhanced, detail_enhanced, detail_amount)
        
        # Auto white balance (simplified)
        if kwargs.get('m_use_awb', False):
            enhanced = self.auto_white_balance(enhanced)
        
        return enhanced
    
    def auto_white_balance(self, image):
        """Simplified auto white balance"""
        if image.mode != 'RGB':
            return image
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Calculate average for each channel
        avg_r = np.mean(img_array[:, :, 0])
        avg_g = np.mean(img_array[:, :, 1])
        avg_b = np.mean(img_array[:, :, 2])
        
        # Calculate scaling factors
        gray_avg = (avg_r + avg_g + avg_b) / 3
        scale_r = gray_avg / avg_r if avg_r > 0 else 1
        scale_g = gray_avg / avg_g if avg_g > 0 else 1
        scale_b = gray_avg / avg_b if avg_b > 0 else 1
        
        # Apply scaling
        img_array[:, :, 0] = np.clip(img_array[:, :, 0] * scale_r, 0, 255)
        img_array[:, :, 1] = np.clip(img_array[:, :, 1] * scale_g, 0, 255)
        img_array[:, :, 2] = np.clip(img_array[:, :, 2] * scale_b, 0, 255)
        
        return Image.fromarray(img_array.astype(np.uint8))
    
    def upscale_image(self, input_path, output_path, **kwargs):
        """Upscale and enhance a single image"""
        try:
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                original_size = img.size
                
                # Determine new size
                if kwargs.get('width') and kwargs.get('height'):
                    new_size = (kwargs['width'], kwargs['height'])
                elif kwargs.get('width'):
                    ratio = kwargs['width'] / original_size[0]
                    new_size = (kwargs['width'], int(original_size[1] * ratio))
                elif kwargs.get('height'):
                    ratio = kwargs['height'] / original_size[1]
                    new_size = (int(original_size[0] * ratio), kwargs['height'])
                else:
                    scale = kwargs.get('scale', 2.0)
                    new_size = (int(original_size[0] * scale), int(original_size[1] * scale))
                
                # Choose resampling method based on adaptive setting
                if kwargs.get('no_adaptive', False):
                    resampling = Image.LANCZOS
                else:
                    # Use different algorithms based on scale factor
                    scale_factor = max(new_size[0] / original_size[0], new_size[1] / original_size[1])
                    if scale_factor > 2:
                        resampling = Image.LANCZOS
                    else:
                        resampling = Image.BICUBIC
                
                # Resize image
                upscaled = img.resize(new_size, resampling)
                
                # Apply enhancements
                enhanced = self.enhance_image(upscaled, **kwargs)
                
                # Save the result
                enhanced.save(output_path, quality=95, optimize=True)
                
                return True, f"Successfully processed: {input_path}"
                
        except Exception as e:
            return False, f"Error processing {input_path}: {str(e)}"
    
    def process_directory(self, input_dir, output_dir, **kwargs):
        """Process all images in a directory"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        if not input_path.exists():
            return False, "Input directory does not exist"
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Find all image files
        image_files = []
        for ext in self.supported_formats:
            image_files.extend(input_path.glob(f"*{ext}"))
            image_files.extend(input_path.glob(f"*{ext.upper()}"))
        
        if not image_files:
            return False, "No supported image files found in input directory"
        
        # Process images with threading
        workers = kwargs.get('workers', 4)
        results = []
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            
            for img_file in image_files:
                output_file = output_path / img_file.name
                future = executor.submit(self.upscale_image, str(img_file), str(output_file), **kwargs)
                futures.append(future)
            
            for future in as_completed(futures):
                success, message = future.result()
                results.append((success, message))
                print(message)
        
        successful = sum(1 for success, _ in results if success)
        total = len(results)
        
        return True, f"Processed {successful}/{total} images successfully"

class ImageUpscalerGUI:
    def __init__(self):
        self.upscaler = ImageUpscaler()
        self.root = tk.Tk()
        self.root.title("Advanced Image Upscaler - Classical Interface")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Apply classical Windows styling
        style = ttk.Style()
        style.theme_use('clam')  # More classical look
        
        self.setup_gui()
    
    def setup_gui(self):
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create tabs
        self.create_io_tab()
        self.create_scaling_tab()
        self.create_enhancement_tab()
        self.create_advanced_tab()
        self.create_processing_tab()
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Process button
        self.process_btn = ttk.Button(control_frame, text="Process Images", 
                                     command=self.process_images, style='Accent.TButton')
        self.process_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Reset button
        ttk.Button(control_frame, text="Reset All", command=self.reset_all).pack(side=tk.LEFT, padx=(0, 10))
        
        # Exit button
        ttk.Button(control_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT)
        
        # Progress and status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        status_frame.columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Status label
        self.status = tk.StringVar(value="Ready - Select input and output files/directories")
        ttk.Label(status_frame, textvariable=self.status, relief='sunken', 
                 anchor='w', padding="5").grid(row=1, column=0, sticky=(tk.W, tk.E))
    
    def create_io_tab(self):
        """Create Input/Output tab"""
        io_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(io_frame, text="Input/Output")
        
        # Input section
        input_group = ttk.LabelFrame(io_frame, text="Input Source", padding="10")
        input_group.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        input_group.columnconfigure(1, weight=1)
        
        self.input_type = tk.StringVar(value="file")
        ttk.Radiobutton(input_group, text="Single Image File", 
                       variable=self.input_type, value="file",
                       command=self.on_input_type_change).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(input_group, text="Directory of Images", 
                       variable=self.input_type, value="dir",
                       command=self.on_input_type_change).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(input_group, text="Path:").grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        
        path_frame = ttk.Frame(input_group)
        path_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        path_frame.columnconfigure(0, weight=1)
        
        self.input_path = tk.StringVar()
        self.input_entry = ttk.Entry(path_frame, textvariable=self.input_path, font=('TkDefaultFont', 9))
        self.input_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.browse_input_btn = ttk.Button(path_frame, text="Browse...", command=self.browse_input)
        self.browse_input_btn.grid(row=0, column=1)
        
        # Output section
        output_group = ttk.LabelFrame(io_frame, text="Output Destination", padding="10")
        output_group.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        output_group.columnconfigure(0, weight=1)
        
        ttk.Label(output_group, text="Path:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        output_path_frame = ttk.Frame(output_group)
        output_path_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        output_path_frame.columnconfigure(0, weight=1)
        
        self.output_path = tk.StringVar()
        self.output_entry = ttk.Entry(output_path_frame, textvariable=self.output_path, font=('TkDefaultFont', 9))
        self.output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.browse_output_btn = ttk.Button(output_path_frame, text="Browse...", command=self.browse_output)
        self.browse_output_btn.grid(row=0, column=1)
        
        # Supported formats info
        info_frame = ttk.LabelFrame(io_frame, text="Supported Formats", padding="10")
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        formats_text = "Supported image formats: JPG, JPEG, PNG, BMP, TIFF, WEBP"
        ttk.Label(info_frame, text=formats_text, foreground='gray50').grid(row=0, column=0, sticky=tk.W)
    
    def create_scaling_tab(self):
        """Create Scaling Options tab"""
        scale_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(scale_frame, text="Scaling")
        
        # Scale method group
        method_group = ttk.LabelFrame(scale_frame, text="Scaling Method", padding="10")
        method_group.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        method_group.columnconfigure(1, weight=1)
        
        self.scale_method = tk.StringVar(value="factor")
        ttk.Radiobutton(method_group, text="Scale by Factor", 
                       variable=self.scale_method, value="factor",
                       command=self.on_scale_method_change).grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(method_group, text="Specific Dimensions", 
                       variable=self.scale_method, value="dimensions",
                       command=self.on_scale_method_change).grid(row=0, column=1, sticky=tk.W)
        
        # Scale factor group
        self.factor_group = ttk.LabelFrame(scale_frame, text="Scale Factor", padding="10")
        self.factor_group.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.factor_group.columnconfigure(1, weight=1)
        
        ttk.Label(self.factor_group, text="Factor:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.scale = tk.DoubleVar(value=2.0)
        scale_scale = ttk.Scale(self.factor_group, from_=0.5, to=8.0, variable=self.scale, 
                               orient=tk.HORIZONTAL, length=300)
        scale_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        self.scale_label = ttk.Label(self.factor_group, text="2.0x")
        self.scale_label.grid(row=0, column=2, padx=(5, 0))
        
        # Update label when scale changes
        def update_scale_label(*args):
            self.scale_label.config(text=f"{self.scale.get():.1f}x")
        self.scale.trace('w', update_scale_label)
        
        # Dimensions group
        self.dimensions_group = ttk.LabelFrame(scale_frame, text="Target Dimensions", padding="10")
        self.dimensions_group.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(self.dimensions_group, text="Width:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.width = tk.IntVar()
        width_entry = ttk.Entry(self.dimensions_group, textvariable=self.width, width=10)
        width_entry.grid(row=0, column=1, padx=(0, 20))
        
        ttk.Label(self.dimensions_group, text="Height:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.height = tk.IntVar()
        height_entry = ttk.Entry(self.dimensions_group, textvariable=self.height, width=10)
        height_entry.grid(row=0, column=3)
        
        ttk.Label(self.dimensions_group, text="(Leave empty to maintain aspect ratio)", 
                 foreground='gray50').grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(5, 0))
        
        # Initially disable dimensions
        self.on_scale_method_change()
        
        # Resampling options
        resample_group = ttk.LabelFrame(scale_frame, text="Resampling Options", padding="10")
        resample_group.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.no_adaptive = tk.BooleanVar()
        ttk.Checkbutton(resample_group, text="Force Lanczos Resampling (disable adaptive)", 
                       variable=self.no_adaptive).grid(row=0, column=0, sticky=tk.W)
        
        ttk.Label(resample_group, text="Adaptive resampling automatically selects the best algorithm", 
                 foreground='gray50').grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
    
    def create_enhancement_tab(self):
        """Create Enhancement Options tab"""
        enhance_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(enhance_frame, text="Enhancement")
        
        # Sharpening group
        sharpen_group = ttk.LabelFrame(enhance_frame, text="Sharpening", padding="10")
        sharpen_group.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        sharpen_group.columnconfigure(1, weight=1)
        sharpen_group.columnconfigure(3, weight=1)
        
        ttk.Label(sharpen_group, text="Amount:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.sharpen = tk.DoubleVar(value=0.0)
        ttk.Scale(sharpen_group, from_=0.0, to=2.0, variable=self.sharpen, 
                 orient=tk.HORIZONTAL).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Label(sharpen_group, text="Radius:").grid(row=0, column=2, sticky=tk.W, padx=(20, 10))
        self.sharpen_radius = tk.DoubleVar(value=1.0)
        ttk.Scale(sharpen_group, from_=0.1, to=3.0, variable=self.sharpen_radius, 
                 orient=tk.HORIZONTAL).grid(row=0, column=3, sticky=(tk.W, tk.E), padx=5)
        
        # Color adjustments group
        color_group = ttk.LabelFrame(enhance_frame, text="Color Adjustments", padding="10")
        color_group.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        color_group.columnconfigure(1, weight=1)
        color_group.columnconfigure(3, weight=1)
        
        ttk.Label(color_group, text="Contrast:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.contrast = tk.DoubleVar(value=1.0)
        ttk.Scale(color_group, from_=0.1, to=3.0, variable=self.contrast, 
                 orient=tk.HORIZONTAL).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Label(color_group, text="Saturation:").grid(row=0, column=2, sticky=tk.W, padx=(20, 10))
        self.saturation = tk.DoubleVar(value=1.0)
        ttk.Scale(color_group, from_=0.0, to=3.0, variable=self.saturation, 
                 orient=tk.HORIZONTAL).grid(row=0, column=3, sticky=(tk.W, tk.E), padx=5)
        
        # Noise reduction group
        denoise_group = ttk.LabelFrame(enhance_frame, text="Noise Reduction", padding="10")
        denoise_group.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        denoise_group.columnconfigure(1, weight=1)
        
        ttk.Label(denoise_group, text="Denoise Amount:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.denoise = tk.DoubleVar(value=0.0)
        ttk.Scale(denoise_group, from_=0.0, to=2.0, variable=self.denoise, 
                 orient=tk.HORIZONTAL).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # Detail enhancement group
        detail_group = ttk.LabelFrame(enhance_frame, text="Detail Enhancement", padding="10")
        detail_group.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        detail_group.columnconfigure(1, weight=1)
        
        self.use_detail = tk.BooleanVar()
        ttk.Checkbutton(detail_group, text="Enable Detail Enhancement", 
                       variable=self.use_detail).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(detail_group, text="Detail Amount:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.detail = tk.DoubleVar(value=0.5)
        ttk.Scale(detail_group, from_=0.0, to=1.0, variable=self.detail, 
                 orient=tk.HORIZONTAL).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # Auto white balance
        awb_group = ttk.LabelFrame(enhance_frame, text="White Balance", padding="10")
        awb_group.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.use_awb = tk.BooleanVar()
        ttk.Checkbutton(awb_group, text="Auto White Balance", 
                       variable=self.use_awb).grid(row=0, column=0, sticky=tk.W)
        
        ttk.Label(awb_group, text="Automatically adjusts color temperature", 
                 foreground='gray50').grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
    
    def create_advanced_tab(self):
        """Create Advanced Options tab"""
        advanced_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(advanced_frame, text="Advanced")
        
        # Performance group
        performance_group = ttk.LabelFrame(advanced_frame, text="Performance Settings", padding="10")
        performance_group.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(performance_group, text="Worker Threads:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.workers = tk.IntVar(value=4)
        workers_spin = ttk.Spinbox(performance_group, from_=1, to=16, textvariable=self.workers, width=5)
        workers_spin.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(performance_group, text="(Higher values may improve batch processing speed)", 
                 foreground='gray50').grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Quality settings group
        quality_group = ttk.LabelFrame(advanced_frame, text="Quality Settings", padding="10")
        quality_group.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(quality_group, text="Output Quality: 95% (High Quality)", 
                 foreground='gray50').grid(row=0, column=0, sticky=tk.W)
        ttk.Label(quality_group, text="Optimization: Enabled", 
                 foreground='gray50').grid(row=1, column=0, sticky=tk.W)
        
        # Debug options group
        debug_group = ttk.LabelFrame(advanced_frame, text="Debug Options", padding="10")
        debug_group.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        self.verbose_output = tk.BooleanVar()
        ttk.Checkbutton(debug_group, text="Verbose Console Output", 
                       variable=self.verbose_output).grid(row=0, column=0, sticky=tk.W)
        
        self.preserve_metadata = tk.BooleanVar(value=True)
        ttk.Checkbutton(debug_group, text="Preserve Image Metadata", 
                       variable=self.preserve_metadata).grid(row=1, column=0, sticky=tk.W)
    
    def create_processing_tab(self):
        """Create Processing Status tab"""
        process_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(process_frame, text="Processing")
        
        # Current operation group
        current_group = ttk.LabelFrame(process_frame, text="Current Operation", padding="10")
        current_group.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        current_group.columnconfigure(0, weight=1)
        
        self.current_operation = tk.StringVar(value="No operation in progress")
        ttk.Label(current_group, textvariable=self.current_operation, 
                 font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=0, sticky=tk.W)
        
        # Progress details
        progress_group = ttk.LabelFrame(process_frame, text="Progress Details", padding="10")
        progress_group.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        progress_group.columnconfigure(0, weight=1)
        progress_group.rowconfigure(0, weight=1)
        
        # Text widget for progress details
        text_frame = ttk.Frame(progress_group)
        text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.progress_text = tk.Text(text_frame, height=15, wrap=tk.WORD, 
                                   font=('Consolas', 9), state='disabled')
        self.progress_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for text widget
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.progress_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.progress_text.configure(yscrollcommand=scrollbar.set)
        
        # Control buttons
        control_frame = ttk.Frame(process_frame)
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(control_frame, text="Clear Log", 
                  command=self.clear_progress_log).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="Save Log", 
                  command=self.save_progress_log).pack(side=tk.LEFT)
    
    def on_input_type_change(self):
        """Handle input type change"""
        self.input_path.set("")
        self.output_path.set("")
        self.update_status("Input type changed - please select new paths")
    
    def on_scale_method_change(self):
        """Handle scale method change"""
        if self.scale_method.get() == "factor":
            # Enable factor controls, disable dimension controls
            for widget in self.factor_group.winfo_children():
                widget.configure(state='normal')
            for widget in self.dimensions_group.winfo_children():
                if isinstance(widget, (ttk.Entry, ttk.Scale)):
                    widget.configure(state='disabled')
        else:
            # Enable dimension controls, disable factor controls
            for widget in self.factor_group.winfo_children():
                if isinstance(widget, (ttk.Scale,)):
                    widget.configure(state='disabled')
            for widget in self.dimensions_group.winfo_children():
                if isinstance(widget, (ttk.Entry, ttk.Scale)):
                    widget.configure(state='normal')
    
    def browse_input(self):
        """Browse for input file or directory"""
        if self.input_type.get() == "file":
            filename = filedialog.askopenfilename(
                title="Select Image File",
                filetypes=[
                    ("All Images", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp"),
                    ("JPEG files", "*.jpg *.jpeg"),
                    ("PNG files", "*.png"),
                    ("BMP files", "*.bmp"),
                    ("TIFF files", "*.tiff"),
                    ("WebP files", "*.webp"),
                    ("All files", "*.*")
                ]
            )
            if filename:
                self.input_path.set(filename)
                self.update_status(f"Selected input file: {os.path.basename(filename)}")
        else:
            dirname = filedialog.askdirectory(title="Select Input Directory")
            if dirname:
                self.input_path.set(dirname)
                self.update_status(f"Selected input directory: {os.path.basename(dirname)}")
    
    def browse_output(self):
        """Browse for output file or directory"""
        if self.input_type.get() == "file":
            filename = filedialog.asksaveasfilename(
                title="Save Image As",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg"),
                    ("BMP files", "*.bmp"),
                    ("TIFF files", "*.tiff"),
                    ("WebP files", "*.webp"),
                    ("All files", "*.*")
                ],
                defaultextension=".png"
            )
            if filename:
                self.output_path.set(filename)
                self.update_status(f"Output file: {os.path.basename(filename)}")
        else:
            dirname = filedialog.askdirectory(title="Select Output Directory")
            if dirname:
                self.output_path.set(dirname)
                self.update_status(f"Output directory: {os.path.basename(dirname)}")
    
    def reset_all(self):
        """Reset all settings to defaults"""
        # Input/Output
        self.input_type.set("file")
        self.input_path.set("")
        self.output_path.set("")
        
        # Scaling
        self.scale_method.set("factor")
        self.scale.set(2.0)
        self.width.set(0)
        self.height.set(0)
        self.no_adaptive.set(False)
        
        # Enhancement
        self.sharpen.set(0.0)
        self.sharpen_radius.set(1.0)
        self.denoise.set(0.0)
        self.contrast.set(1.0)
        self.saturation.set(1.0)
        self.use_detail.set(False)
        self.detail.set(0.5)
        self.use_awb.set(False)
        
        # Advanced
        self.workers.set(4)
        self.verbose_output.set(False)
        self.preserve_metadata.set(True)
        
        # Update UI state
        self.on_scale_method_change()
        self.clear_progress_log()
        self.update_status("All settings reset to defaults")
    
    def update_status(self, message):
        """Update status message"""
        self.status.set(message)
        self.log_message(f"Status: {message}")
    
    def log_message(self, message):
        """Add message to progress log"""
        self.progress_text.configure(state='normal')
        self.progress_text.insert(tk.END, f"{message}\n")
        self.progress_text.see(tk.END)
        self.progress_text.configure(state='disabled')
        self.root.update_idletasks()
    
    def clear_progress_log(self):
        """Clear progress log"""
        self.progress_text.configure(state='normal')
        self.progress_text.delete(1.0, tk.END)
        self.progress_text.configure(state='disabled')
    
    def save_progress_log(self):
        """Save progress log to file"""
        filename = filedialog.asksaveasfilename(
            title="Save Progress Log",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            defaultextension=".txt"
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.progress_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Log saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log: {str(e)}")
    
    def validate_inputs(self):
        """Validate user inputs"""
        if not self.input_path.get():
            messagebox.showerror("Error", "Please select an input file or directory")
            self.notebook.select(0)  # Switch to I/O tab
            return False
        
        if not self.output_path.get():
            messagebox.showerror("Error", "Please select an output file or directory")
            self.notebook.select(0)  # Switch to I/O tab
            return False
        
        if not os.path.exists(self.input_path.get()):
            messagebox.showerror("Error", "Input path does not exist")
            return False
        
        # Validate scaling options
        if self.scale_method.get() == "dimensions":
            if self.width.get() <= 0 and self.height.get() <= 0:
                messagebox.showerror("Error", "Please specify at least width or height")
                self.notebook.select(1)  # Switch to Scaling tab
                return False
        
        return True
    
    def get_processing_params(self):
        """Get processing parameters"""
        params = {
            'no_adaptive': self.no_adaptive.get(),
            'm_sharpen': self.sharpen.get(),
            'm_sharpen_radius': self.sharpen_radius.get(),
            'm_denoise': self.denoise.get(),
            'm_contrast': self.contrast.get(),
            'm_saturation': self.saturation.get(),
            'm_use_detail': self.use_detail.get(),
            'm_detail': self.detail.get(),
            'm_use_awb': self.use_awb.get(),
            'workers': self.workers.get()
        }
        
        # Add scaling parameters
        if self.scale_method.get() == "factor":
            params['scale'] = self.scale.get()
        else:
            if self.width.get() > 0:
                params['width'] = self.width.get()
            if self.height.get() > 0:
                params['height'] = self.height.get()
        
        return params
    
    def process_images(self):
        """Process images with current settings"""
        if not self.validate_inputs():
            return
        
        # Switch to processing tab
        self.notebook.select(4)
        
        # Get parameters
        params = self.get_processing_params()
        
        # Start processing
        self.progress.start()
        self.process_btn.configure(state='disabled')
        self.current_operation.set("Initializing...")
        
        def process_thread():
            try:
                if self.input_type.get() == "file":
                    self.current_operation.set("Processing single image...")
                    self.log_message("=" * 50)
                    self.log_message("SINGLE IMAGE PROCESSING")
                    self.log_message("=" * 50)
                    self.log_message(f"Input: {self.input_path.get()}")
                    self.log_message(f"Output: {self.output_path.get()}")
                    self.log_message(f"Parameters: {params}")
                    self.log_message("")
                    
                    success, message = self.upscaler.upscale_image(
                        self.input_path.get(), 
                        self.output_path.get(), 
                        **params
                    )
                else:
                    self.current_operation.set("Processing directory...")
                    self.log_message("=" * 50)
                    self.log_message("BATCH PROCESSING")
                    self.log_message("=" * 50)
                    self.log_message(f"Input Directory: {self.input_path.get()}")
                    self.log_message(f"Output Directory: {self.output_path.get()}")
                    self.log_message(f"Parameters: {params}")
                    self.log_message("")
                    
                    success, message = self.upscaler.process_directory(
                        self.input_path.get(), 
                        self.output_path.get(), 
                        **params
                    )
                
                self.root.after(0, self.process_complete, success, message)
            except Exception as e:
                self.root.after(0, self.process_complete, False, str(e))
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def process_complete(self, success, message):
        """Handle process completion"""
        self.progress.stop()
        self.process_btn.configure(state='normal')
        self.current_operation.set("Process completed")
        
        self.log_message("")
        self.log_message("=" * 50)
        self.log_message("PROCESS COMPLETED")
        self.log_message("=" * 50)
        self.log_message(f"Result: {'SUCCESS' if success else 'FAILED'}")
        self.log_message(f"Message: {message}")
        self.log_message("")
        
        if success:
            self.update_status(f"✓ {message}")
            messagebox.showinfo("Success", message)
        else:
            self.update_status(f"✗ {message}")
            messagebox.showerror("Error", message)
    
    def run(self):
        """Run the application"""
        # Center window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f'+{x}+{y}')
        
        self.root.mainloop()

def main():
    if len(sys.argv) == 1:
        # Launch GUI if no arguments
        app = ImageUpscalerGUI()
        app.run()
    else:
        # CLI mode
        parser = argparse.ArgumentParser(description="Advanced Image Upscaler")
        
        # Input/Output
        input_group = parser.add_mutually_exclusive_group(required=True)
        input_group.add_argument('-i', '--input', help='Input image file')
        input_group.add_argument('-id', '--input-dir', help='Input directory')
        
        output_group = parser.add_mutually_exclusive_group(required=True)
        output_group.add_argument('-o', '--output', help='Output image file')
        output_group.add_argument('-od', '--output-dir', help='Output directory')
        
        # Scaling options
        parser.add_argument('--scale', type=float, default=2.0, help='Scale factor (default: 2.0)')
        parser.add_argument('--width', type=int, help='Target width')
        parser.add_argument('--height', type=int, help='Target height')
        parser.add_argument('--no-adaptive', action='store_true', help='Disable adaptive resampling')
        
        # Enhancement options
        parser.add_argument('--m-sharpen', type=float, default=0.0, help='Sharpening amount (0.0-2.0)')
        parser.add_argument('--m-sharpen-radius', type=float, default=1.0, help='Sharpening radius (0.1-3.0)')
        parser.add_argument('--m-denoise', type=float, default=0.0, help='Denoising amount (0.0-2.0)')
        parser.add_argument('--m-contrast', type=float, default=1.0, help='Contrast adjustment (0.1-3.0)')
        parser.add_argument('--m-saturation', type=float, default=1.0, help='Saturation adjustment (0.0-3.0)')
        parser.add_argument('--m-use-detail', action='store_true', help='Enable detail enhancement')
        parser.add_argument('--m-detail', type=float, default=0.5, help='Detail enhancement amount (0.0-1.0)')
        parser.add_argument('--m-use-awb', action='store_true', help='Enable auto white balance')
        
        # Processing options
        parser.add_argument('--workers', type=int, default=4, help='Number of worker threads (default: 4)')
        
        args = parser.parse_args()
        
        # Validate arguments
        if args.input and args.output_dir:
            parser.error("Cannot use single input file with output directory")
        if args.input_dir and args.output:
            parser.error("Cannot use input directory with single output file")
        
        # Create upscaler
        upscaler = ImageUpscaler()
        
        # Prepare kwargs
        kwargs = {
            'scale': args.scale,
            'width': args.width,
            'height': args.height,
            'no_adaptive': args.no_adaptive,
            'm_sharpen': args.m_sharpen,
            'm_sharpen_radius': args.m_sharpen_radius,
            'm_denoise': args.m_denoise,
            'm_contrast': args.m_contrast,
            'm_saturation': args.m_saturation,
            'm_use_detail': args.m_use_detail,
            'm_detail': args.m_detail,
            'm_use_awb': args.m_use_awb,
            'workers': args.workers
        }
        
        # Process images
        if args.input:
            success, message = upscaler.upscale_image(args.input, args.output, **kwargs)
        else:
            success, message = upscaler.process_directory(args.input_dir, args.output_dir, **kwargs)
        
        print(message)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()