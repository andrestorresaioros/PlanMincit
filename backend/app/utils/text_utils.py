"""Text normalization utilities"""
import unicodedata
import re


def normalize_text(text: str) -> str:
    """
    Normalize text for URL usage:
    - Remove accents/tildes
    - Convert to uppercase
    - Replace spaces and special chars with nothing
    - Remove punctuation
    
    Examples:
        "Visión de futuro" -> "VISIONDEFUTURO"
        "Alistamiento" -> "ALISTAMIENTO"
        "participación-social" -> "PARTICIPACIONSOCIAL"
    """
    if not text:
        return ""
    
    # Remove accents/tildes using NFD normalization
    nfd = unicodedata.normalize('NFD', text)
    text_without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    
    # Convert to uppercase
    text_upper = text_without_accents.upper()
    
    # Remove spaces, hyphens, and special characters
    text_clean = re.sub(r'[^A-Z0-9]', '', text_upper)
    
    return text_clean
