import os
from PIL import Image


class ImageCompressor:
    """
    Handles the compression of images within a specified directory.
    Reduces file size by resizing large images and optimizing JPEG quality.
    """

    def __init__(self, input_folder: str, output_folder: str, max_dimension: int = 1920, quality: int = 80):
        """
        Initializes the ImageCompressor with input and output paths, and compression parameters.

        Args:
            input_folder (str): The path to the folder containing original images.
            output_folder (str): The path to the folder where compressed images will be saved.
            max_dimension (int): The maximum width or height for the compressed images.
            quality (int): The JPEG quality level (1-100).
        """
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.max_dimension = max_dimension
        self.quality = quality

        # Creates the destination folder if it does not already exist
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def compress_image(self, input_path: str, output_path: str) -> bool:
        """
        Opens an image, resizes it if it exceeds the maximum dimension, and saves it with JPEG optimization.

        Args:
            input_path (str): The file path of the source image.
            output_path (str): The file path for the destination image.

        Returns:
            bool: True if the operation succeeds, False otherwise.
        """
        try:
            with Image.open(input_path) as img:
                # Converts the image to standard color mode if it contains transparency
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Calculates new dimensions while maintaining the original aspect ratio
                width, height = img.size
                if width > self.max_dimension or height > self.max_dimension:
                    if width > height:
                        new_width = self.max_dimension
                        new_height = int((self.max_dimension / width) * height)
                    else:
                        new_height = self.max_dimension
                        new_width = int((self.max_dimension / height) * width)

                    # Applies the new dimensions using a high-quality resizing method
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Saves the final image with optimization and specified quality reduction
                img.save(output_path, 'JPEG', optimize=True, quality=self.quality)
                return True
        except Exception as e:
            print(f"Error processing {input_path}: {e}")
            return False

    def process_directory(self) -> None:
        """
        Iterates through all files in the input folder and applies the compression method to image files.
        """
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')

        # Loops through every item in the target directory
        for filename in os.listdir(self.input_folder):
            if filename.lower().endswith(valid_extensions):
                input_path = os.path.join(self.input_folder, filename)

                # Constructs a new filename to ensure the output is saved as a JPEG
                name_without_ext = os.path.splitext(filename)[0]
                output_filename = f"{name_without_ext}_compressed.jpg"
                output_path = os.path.join(self.output_folder, output_filename)

                # Executes the compression and reports the result
                success = self.compress_image(input_path, output_path)
                if success:
                    print(f"Successfully compressed: {filename}")
                else:
                    print(f"Failed to compress: {filename}")


if __name__ == "__main__":
    # Defines the default directories for reading and saving files
    source_dir = "input_images"
    dest_dir = "output_images"

    # Instantiates the class and begins the batch processing
    compressor = ImageCompressor(input_folder=source_dir, output_folder=dest_dir)
    compressor.process_directory()