import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from PIL import Image, ImageTk
import threading

class ClassicFileConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("Classic File Converter v1.0")
        self.root.geometry("650x500")
        self.root.configure(bg='#c0c0c0')
        self.root.resizable(True, True)
        
        # Variables
        self.input_files = []
        self.output_folder = ""
        self.current_format = tk.StringVar(value="png")
        self.conversion_mode = tk.StringVar(value="single")
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame with classic border
        main_frame = tk.Frame(self.root, bg='#c0c0c0', relief='raised', bd=2)
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Title section
        title_frame = tk.Frame(main_frame, bg='#000080', height=25)
        title_frame.pack(fill='x', pady=(0,10))
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, text="IMAGE CONVERTER", 
                              bg='#000080', fg='white', font=('MS Sans Serif', 9, 'bold'))
        title_label.pack(pady=3)
        
        # Mode selection
        mode_frame = tk.LabelFrame(main_frame, text="Conversion Mode", 
                                  bg='#c0c0c0', font=('MS Sans Serif', 8, 'bold'))
        mode_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Radiobutton(mode_frame, text="Single File", variable=self.conversion_mode, 
                      value="single", bg='#c0c0c0', font=('MS Sans Serif', 8),
                      command=self.mode_changed).pack(side='left', padx=10, pady=5)
        
        tk.Radiobutton(mode_frame, text="Bulk Conversion", variable=self.conversion_mode, 
                      value="bulk", bg='#c0c0c0', font=('MS Sans Serif', 8),
                      command=self.mode_changed).pack(side='left', padx=10, pady=5)
        
        # Input section
        input_frame = tk.LabelFrame(main_frame, text="Input Files", 
                                   bg='#c0c0c0', font=('MS Sans Serif', 8, 'bold'))
        input_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Input buttons frame
        input_btn_frame = tk.Frame(input_frame, bg='#c0c0c0')
        input_btn_frame.pack(fill='x', padx=5, pady=5)
        
        self.select_files_btn = tk.Button(input_btn_frame, text="Select File(s)", 
                                         command=self.select_files, bg='#e0e0e0',
                                         relief='raised', bd=2, font=('MS Sans Serif', 8))
        self.select_files_btn.pack(side='left', padx=5)
        
        self.select_folder_btn = tk.Button(input_btn_frame, text="Select Folder", 
                                          command=self.select_folder, bg='#e0e0e0',
                                          relief='raised', bd=2, font=('MS Sans Serif', 8))
        self.select_folder_btn.pack(side='left', padx=5)
        
        tk.Button(input_btn_frame, text="Clear", command=self.clear_files, 
                 bg='#e0e0e0', relief='raised', bd=2, font=('MS Sans Serif', 8)).pack(side='right', padx=5)
        
        # File list
        list_frame = tk.Frame(input_frame, bg='#c0c0c0')
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.file_listbox = tk.Listbox(list_frame, bg='white', font=('MS Sans Serif', 8),
                                      relief='sunken', bd=2)
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.file_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Output section
        output_frame = tk.LabelFrame(main_frame, text="Output Settings", 
                                    bg='#c0c0c0', font=('MS Sans Serif', 8, 'bold'))
        output_frame.pack(fill='x', padx=10, pady=5)
        
        # Output folder
        folder_frame = tk.Frame(output_frame, bg='#c0c0c0')
        folder_frame.pack(fill='x', padx=5, pady=5)
        
        tk.Label(folder_frame, text="Output Folder:", bg='#c0c0c0', 
                font=('MS Sans Serif', 8)).pack(side='left')
        
        self.output_label = tk.Label(folder_frame, text="Same as input", bg='white',
                                    relief='sunken', bd=1, font=('MS Sans Serif', 8))
        self.output_label.pack(side='left', fill='x', expand=True, padx=5)
        
        tk.Button(folder_frame, text="Browse", command=self.select_output_folder,
                 bg='#e0e0e0', relief='raised', bd=2, font=('MS Sans Serif', 8)).pack(side='right')
        
        # Format selection
        format_frame = tk.Frame(output_frame, bg='#c0c0c0')
        format_frame.pack(fill='x', padx=5, pady=5)
        
        tk.Label(format_frame, text="Convert to:", bg='#c0c0c0', 
                font=('MS Sans Serif', 8)).pack(side='left')
        
        formats = ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff', 'webp']
        format_combo = ttk.Combobox(format_frame, textvariable=self.current_format,
                                   values=formats, state='readonly', width=10)
        format_combo.pack(side='left', padx=10)
        
        # Progress section
        progress_frame = tk.Frame(main_frame, bg='#c0c0c0')
        progress_frame.pack(fill='x', padx=10, pady=5)
        
        self.progress_label = tk.Label(progress_frame, text="Ready", bg='#c0c0c0',
                                      font=('MS Sans Serif', 8))
        self.progress_label.pack(side='left')
        
        self.progress_bar = ttk.Progressbar(progress_frame, length=200, mode='determinate')
        self.progress_bar.pack(side='right', padx=5)
        
        # Control buttons
        button_frame = tk.Frame(main_frame, bg='#c0c0c0')
        button_frame.pack(fill='x', padx=10, pady=10)
        
        self.convert_btn = tk.Button(button_frame, text="CONVERT", command=self.start_conversion,
                                    bg='#90EE90', relief='raised', bd=3, font=('MS Sans Serif', 9, 'bold'),
                                    height=2)
        self.convert_btn.pack(side='left', padx=5)
        
        tk.Button(button_frame, text="EXIT", command=self.root.quit,
                 bg='#FFB6C1', relief='raised', bd=3, font=('MS Sans Serif', 9, 'bold'),
                 height=2).pack(side='right', padx=5)
        
        # Status bar
        status_frame = tk.Frame(main_frame, bg='#c0c0c0', relief='sunken', bd=1)
        status_frame.pack(fill='x', side='bottom')
        
        self.status_label = tk.Label(status_frame, text="Ready to convert files", 
                                    bg='#c0c0c0', font=('MS Sans Serif', 8))
        self.status_label.pack(side='left', padx=5, pady=2)
        
        # Initialize mode
        self.mode_changed()
    
    def mode_changed(self):
        """Handle mode change between single and bulk"""
        if self.conversion_mode.get() == "single":
            self.select_folder_btn.configure(state='disabled')
        else:
            self.select_folder_btn.configure(state='normal')
    
    def select_files(self):
        """Select individual files"""
        filetypes = [
            ('Image files', '*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp'),
            ('All files', '*.*')
        ]
        
        if self.conversion_mode.get() == "single":
            file = filedialog.askopenfilename(title="Select Image File", filetypes=filetypes)
            if file:
                self.input_files = [file]
                self.update_file_list()
        else:
            files = filedialog.askopenfilenames(title="Select Image Files", filetypes=filetypes)
            if files:
                self.input_files.extend(files)
                self.update_file_list()
    
    def select_folder(self):
        """Select folder for bulk conversion"""
        folder = filedialog.askdirectory(title="Select Folder with Images")
        if folder:
            # Find all image files in folder
            image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']
            files = []
            for file in os.listdir(folder):
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    files.append(os.path.join(folder, file))
            
            if files:
                self.input_files.extend(files)
                self.update_file_list()
                self.status_label.configure(text=f"Found {len(files)} image files in folder")
            else:
                messagebox.showwarning("No Images", "No image files found in selected folder")
    
    def clear_files(self):
        """Clear all selected files"""
        self.input_files = []
        self.update_file_list()
        self.status_label.configure(text="File list cleared")
    
    def update_file_list(self):
        """Update the file listbox"""
        self.file_listbox.delete(0, tk.END)
        for file in self.input_files:
            self.file_listbox.insert(tk.END, os.path.basename(file))
        
        self.status_label.configure(text=f"{len(self.input_files)} files selected")
    
    def select_output_folder(self):
        """Select output folder"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_label.configure(text=folder)
    
    def start_conversion(self):
        """Start the conversion process in a separate thread"""
        if not self.input_files:
            messagebox.showwarning("No Files", "Please select files to convert")
            return
        
        # Disable convert button during conversion
        self.convert_btn.configure(state='disabled', text="Converting...")
        
        # Start conversion in thread to prevent GUI freezing
        thread = threading.Thread(target=self.convert_files)
        thread.daemon = True
        thread.start()
    
    def convert_files(self):
        """Convert all selected files"""
        total_files = len(self.input_files)
        converted = 0
        errors = []
        
        for i, input_file in enumerate(self.input_files):
            try:
                # Update progress
                progress = (i / total_files) * 100
                self.progress_bar.configure(value=progress)
                self.progress_label.configure(text=f"Converting {i+1}/{total_files}")
                self.root.update_idletasks()
                
                # Determine output path
                if self.output_folder:
                    output_dir = self.output_folder
                else:
                    output_dir = os.path.dirname(input_file)
                
                # Create output filename
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                output_file = os.path.join(output_dir, f"{base_name}.{self.current_format.get()}")
                
                # Convert image
                with Image.open(input_file) as img:
                    # Handle different formats
                    if self.current_format.get().lower() == 'jpg' or self.current_format.get().lower() == 'jpeg':
                        # Convert RGBA to RGB for JPEG
                        if img.mode in ('RGBA', 'LA', 'P'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                            img = background
                        img.save(output_file, 'JPEG', quality=95)
                    else:
                        img.save(output_file)
                
                converted += 1
                
            except Exception as e:
                errors.append(f"{os.path.basename(input_file)}: {str(e)}")
        
        # Update final progress
        self.progress_bar.configure(value=100)
        self.progress_label.configure(text="Complete")
        
        # Show results
        if errors:
            error_msg = f"Converted {converted}/{total_files} files.\n\nErrors:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n... and {len(errors)-5} more errors"
            messagebox.showwarning("Conversion Complete with Errors", error_msg)
        else:
            messagebox.showinfo("Success", f"Successfully converted {converted} files!")
        
        # Reset UI
        self.convert_btn.configure(state='normal', text="CONVERT")
        self.progress_bar.configure(value=0)
        self.progress_label.configure(text="Ready")
        self.status_label.configure(text=f"Conversion complete: {converted} files")

def main():
    root = tk.Tk()
    app = ClassicFileConverter(root)
    root.mainloop()

if __name__ == "__main__":
    main()