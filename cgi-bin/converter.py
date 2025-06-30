#!/usr/bin/env python3
import cgi
import cgitb
import os
from datetime import datetime
import subprocess
import sys
from pathlib import Path
from typing import Tuple, Optional

cgitb.enable()

BASE_DIR = Path("/var/www/webapp")
HTML_DIR = BASE_DIR / "html"
ORIGINAL_DIR = BASE_DIR / "original"
CONVERTED_DIR = BASE_DIR / "converted"
RESULT_TEMPLATE = BASE_DIR / "html" / "result.html"
ERROR_TEMPLATE = BASE_DIR / "html" / "error.html"

for directory in [HTML_DIR, ORIGINAL_DIR, CONVERTED_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

class ImageProcessor:
    """
    Класс для обработки загрузки и конвертации изображений.
    """

    def __init__(self):
        self.form = cgi.FieldStorage()

    def validate_upload(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Проверяет загруженный файл.
        Возвращает (content_type, filename) или (None, error_message).
        """
        if 'image' not in self.form:
            return None, "No file uploaded"

        file_item = self.form['image']
        if not file_item.filename:
            return None, "No filename provided"

        content_type = file_item.type
        if content_type not in ['image/jpeg', 'image/png']:
            return None, "Invalid file type. Only JPEG and PNG are allowed."

        return content_type, None

    def save_uploaded_file(self, content_type: str) -> Tuple[Optional[Path], Optional[str]]:
        """
        Сохраняет загруженное изображение.
        Возвращает (saved_path, None) при успехе или (None, error_message) при ошибке.
        """
        file_item = self.form['image']
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        ext = ".jpg" if content_type == 'image/jpeg' else ".png"
        unique_name = f"{timestamp}_{os.getpid()}{ext}"
        save_path = ORIGINAL_DIR / unique_name

        try:
            with open(save_path, 'wb') as f:
                while True:
                    chunk = file_item.file.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            return save_path, None
        except Exception as e:
            return None, f"Failed to save file: {str(e)}"

    def convert_to_grayscale(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует изображение в градации серого используя ImageMagick.
        """
        try:
            result = subprocess.run(
                ['convert', str(input_path), '-colorspace', 'Gray', str(output_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            sys.stderr.write(f"Conversion failed: {e.stderr.decode()}\n")
            return False
        except Exception as e:
            sys.stderr.write(f"Unexpected conversion error: {str(e)}\n")
            return False

    def render_template(self, template_path: Path, **context) -> str:
        """
        Рендерит HTML-шаблон с подстановкой переменных.
        """
        try:
            with open(template_path, 'r') as f:
                content = f.read()
            
            for key, value in context.items():
                content = content.replace(f"{{{{{key}}}}}", str(value))
            
            return content
        except Exception as e:
            sys.stderr.write(f"Template rendering error: {str(e)}\n")
            return "<h1>Internal Server Error</h1>"

def main():
    print("Content-Type: text/html\n")

    try:
        processor = ImageProcessor()
        
        content_type, error = processor.validate_upload()
        if error:
            print(processor.render_template(ERROR_TEMPLATE, message=error))
            return

        original_path, error = processor.save_uploaded_file(content_type)
        if error:
            print(processor.render_template(ERROR_TEMPLATE, message=error))
            return

        unique_name = original_path.name
        converted_path = CONVERTED_DIR / unique_name
        
        if not processor.convert_to_grayscale(original_path, converted_path):
            print(processor.render_template(ERROR_TEMPLATE, message="Image conversion failed"))
            return

        result_html = processor.render_template(
            RESULT_TEMPLATE,
            original_filename=unique_name,
            converted_filename=unique_name
        )
        print(result_html)

    except Exception as e:
        sys.stderr.write(f"Unexpected error: {str(e)}\n")
        print(processor.render_template(ERROR_TEMPLATE, message="Internal server error"))

if __name__ == '__main__':
    main()