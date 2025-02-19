import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from PIL import Image
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Global variable to track the process
script_process = None
stop_event = multiprocessing.Event()  # Event flag to stop the process
processed_count = multiprocessing.Value('i', 0)  # Shared variable for processed count
total_images = multiprocessing.Value('i', 0)  # Shared variable for total images

# Function to select a folder and update the entry field
def select_folder(entry):
    folder = filedialog.askdirectory()  # Open the folder selection dialog

    # If a folder is selected, update the entry field
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)
    check_paths()

# Function to check if all folder paths have been selected
def check_paths():
    if entry1.get() and entry2.get() and entry3.get():
        run_button.pack(pady=10)  # Show the "Run" button if all paths are selected

# Function to create an RGBA image
def create_rgba_image(image_path, mask_path, output_path, output_format):
    try:
        with Image.open(image_path) as image:
            image = image.convert('RGB')
            rgba = Image.new('RGBA', image.size)
            rgba.paste(image)

            if os.path.exists(mask_path):
                with Image.open(mask_path) as mask:
                    mask = mask.convert('L')
                    rgba.putalpha(mask)
            else:
                alpha = Image.new('L', image.size, 255)
                rgba.putalpha(alpha)

            if output_format.lower() == 'tiff':
                rgba.save(output_path, format='TIFF', compression='tiff_lzw')
            else:  # Default to PNG
                rgba.save(output_path, format='PNG')
    except Exception as e:
        logging.error(f"Error processing image {image_path}: {e}")
        raise

# Function to process each image and report progress
def process_image(image_file, input_folder, mask_folder, output_folder, output_format, processed_count):
    try:
        base_name = os.path.splitext(image_file)[0]
        mask_file = base_name + '.png'
        image_path = os.path.join(input_folder, image_file)
        mask_path = os.path.join(mask_folder, mask_file)
        output_extension = '.tiff' if output_format.lower() == 'tiff' else '.png'
        output_path = os.path.join(output_folder, base_name + output_extension)

        create_rgba_image(image_path, mask_path, output_path, output_format)

        # Increment the processed count
        processed_count.value += 1
    except Exception as e:
        logging.error(f"Failed to process {image_file}: {e}")

# Function to process all images and calculate progress
def process_all_images(input_folder, mask_folder, output_folder, output_format, processed_count):
    try:
        os.makedirs(output_folder, exist_ok=True)
        image_files = [f for f in os.listdir(input_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff'))]

        if len(image_files) == 0:
            raise ValueError("No images found in the selected input folder.")

        total_images.value = len(image_files)  # Set the global variable total_images

        with ProcessPoolExecutor() as executor:
            process_func = partial(process_image, input_folder=input_folder, mask_folder=mask_folder, 
                                   output_folder=output_folder, output_format=output_format, 
                                   processed_count=processed_count)
            executor.map(process_func, image_files)

        logging.info(f"Processing complete. Total images processed: {len(image_files)}")
        messagebox.showinfo("Completed", f"Processing complete!\nTotal images: {len(image_files)}")

    except Exception as e:
        logging.error(f"Error occurred during processing: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

# Function to run the script in a separate process
def run_script():
    global script_process, stop_event, total_images, processed_count

    stop_event.clear()  # Reset the stop event before starting the script
    processed_count.value = 0  # Reset processed count before starting the script

    input_folder = entry1.get()
    mask_folder = entry2.get()
    output_folder = entry3.get()

    # Default output format to 'png' if not specified
    output_format = format_entry.get().strip().lower() if format_entry.get().strip() else 'png'

    # Validate folders
    if not os.path.isdir(input_folder):
        messagebox.showerror("Error", "Invalid input folder path!")
        return
    if not os.path.isdir(mask_folder):
        messagebox.showerror("Error", "Invalid mask folder path!")
        return
    if not os.path.isdir(output_folder):
        messagebox.showerror("Error", "Invalid output folder path!")
        return

    logging.info(f"Running with:\nInput folder: {input_folder}\nMask folder: {mask_folder}\nOutput folder: {output_folder}\nOutput format: {output_format}")

    # Total number of images to be processed (from input folder)
    total_images.value = len([f for f in os.listdir(input_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff'))])

    # Check if there are images to process
    if total_images.value == 0:
        messagebox.showerror("Error", "No images found in the input folder!")
        return

    # Start the script in a new process to avoid blocking the GUI
    script_process = multiprocessing.Process(target=process_all_images, args=(input_folder, mask_folder, output_folder, output_format, processed_count))
    script_process.start()

    # Start a separate thread to monitor progress updates
    update_progress()

# Function to update the progress label
def update_progress():
    global processed_count, total_images

    # Update the progress every 100ms
    app.after(100, check_progress)

def check_progress():
    global processed_count, total_images

    processed_value = processed_count.value
    total_value = total_images.value
    if total_value > 0:
        progress_percentage = (processed_value / total_value) * 100
        progress_label.config(text=f"Progress: {processed_value}/{total_value} ({int(progress_percentage)}%)")
        progress_bar["value"] = progress_percentage

    if processed_value < total_value:
        update_progress()  # Keep updating progress until complete
    else:
        if processed_value == total_value:
            messagebox.showinfo("Completed", "Processing complete!")

# Function to handle window close event
def on_close():
    global script_process, stop_event
    if script_process is not None and script_process.is_alive():
        # If the script is still running, stop it gracefully
        if messagebox.askokcancel("Quit", "The script is still running. Do you want to quit?"):
            stop_event.set()  # Set the stop event flag
            script_process.terminate()  # Terminate the running process
            script_process.join()  # Wait for the process to finish or be stopped
            app.quit()  # Close the application
    else:
        app.quit()

# Function to create and run the GUI
def create_gui():
    global entry1, entry2, entry3, format_entry, run_button, app, progress_label, progress_bar, processed_count, total_images

    # Create a Manager to handle shared values for processed count and total images
    manager = multiprocessing.Manager()
    processed_count = manager.Value('i', 0)  # Shared variable for processed count
    total_images = manager.Value('i', 0)  # Shared variable for total images

    # Create the main application window
    app = tk.Tk()
    app.title("Image Processing Script")
    app.geometry("500x400")

    # Handle the close event
    app.protocol("WM_DELETE_WINDOW", on_close)

    # Title label
    title_label = tk.Label(app, text="Select Folders and Run Script", font=("Arial", 16))
    title_label.pack(pady=10)

    # Folder 1 selection
    frame1 = tk.Frame(app)
    frame1.pack(pady=5)
    tk.Label(frame1, text="Input Folder:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
    entry1 = tk.Entry(frame1, width=40)
    entry1.pack(side=tk.LEFT, padx=5)
    tk.Button(frame1, text="Browse", command=lambda: select_folder(entry1)).pack(side=tk.LEFT, padx=5)

    # Folder 2 selection
    frame2 = tk.Frame(app)
    frame2.pack(pady=5)
    tk.Label(frame2, text="Mask Folder:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
    entry2 = tk.Entry(frame2, width=40)
    entry2.pack(side=tk.LEFT, padx=5)
    tk.Button(frame2, text="Browse", command=lambda: select_folder(entry2)).pack(side=tk.LEFT, padx=5)

    # Folder 3 selection
    frame3 = tk.Frame(app)
    frame3.pack(pady=5)
    tk.Label(frame3, text="Output Folder:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
    entry3 = tk.Entry(frame3, width=40)
    entry3.pack(side=tk.LEFT, padx=5)
    tk.Button(frame3, text="Browse", command=lambda: select_folder(entry3)).pack(side=tk.LEFT, padx=5)

    # Output format entry (optional) with default value set to 'png'
    frame4 = tk.Frame(app)
    frame4.pack(pady=5)
    tk.Label(frame4, text="Output Format (png/tiff):", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
    format_entry = tk.Entry(frame4, width=10)
    format_entry.pack(side=tk.LEFT, padx=5)
    format_entry.insert(0, 'png')  # Set the default value to 'png'

    # "Run" button (initially hidden)
    run_button = tk.Button(app, text="Run Script", command=run_script)

    # Progress Label
    progress_label = tk.Label(app, text="Progress: 0/0 (0%)", font=("Arial", 12))
    progress_label.pack(pady=10)

    # Progress Bar (Optional)
    progress_bar = ttk.Progressbar(app, length=400, mode='determinate')
    progress_bar.pack(pady=10)

    # Start the main application loop
    app.mainloop()

# Run the GUI only once when the script is executed
if __name__ == "__main__":
    create_gui()
