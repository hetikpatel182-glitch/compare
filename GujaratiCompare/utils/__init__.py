# ====================================================
# Gujarati Paragraph Compare Pro
# utils/__init__.py — Package Initializer
# ====================================================

from utils.parser import TextParser
from utils.similarity import SimilarityCalculator
from utils.compare import ComparisonEngine

__all__ = ['TextParser', 'SimilarityCalculator', 'ComparisonEngine']
