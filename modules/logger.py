import logging
import os
from datetime import datetime

# Log klasörünü belirle
LOG_DIR = "./log"
os.makedirs(LOG_DIR, exist_ok=True)  # Klasör yoksa oluştur

# Log dosya adı (tarih bazlı)
log_filename = datetime.now().strftime("%Y-%m-%d") + ".log"
log_filepath = os.path.join(LOG_DIR, log_filename)

# Logger oluştur
logger = logging.getLogger("my_logger")
logger.setLevel(logging.DEBUG)  # Tüm log seviyelerini al

# Log formatı belirle
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# Dosya log handler
file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Konsol log handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Konsolda sadece INFO ve üstünü göster
console_handler.setFormatter(formatter)

# Handlers'ları log objesine ekle
logger.addHandler(file_handler)
logger.addHandler(console_handler)