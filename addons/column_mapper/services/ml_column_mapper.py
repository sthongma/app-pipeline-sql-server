"""
ML-Enhanced Column Mapping Service for PIPELINE_SQLSERVER

This service uses machine learning to automatically suggest column mappings
when file structures change or new file types are encountered.
"""

import json
import os
import re
import logging
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

import sys
from pathlib import Path
# Add app root to path (go up from services -> column_mapper -> addons -> app_root)
app_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(app_root))

from constants import PathConstants


class MLColumnMapper:
    """
    ML-Enhanced Column Mapping Service
    
    Features:
    1. Semantic similarity matching using sentence transformers
    2. String similarity using fuzzy matching
    3. Historical learning from previous mappings
    4. Confidence scoring for suggestions
    5. Auto-updating of column_settings.json
    """
    
    def __init__(self, log_callback: Optional[callable] = None):
        """Initialize the ML Column Mapper"""
        self.log_callback = log_callback if log_callback else print
        
        # Setup file logging
        self.setup_logging()
        
        # Load existing settings
        self.column_settings = self._load_column_settings()
        self.dtype_settings = self._load_dtype_settings()
        
        # Initialize ML models if available
        self.semantic_model = None
        self.vectorizer = None
        self.ml_ready = False
        
        if ML_AVAILABLE:
            try:
                self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.vectorizer = TfidfVectorizer()
                self.ml_ready = True
                self._log("ML models loaded successfully")
            except Exception as e:
                self._log(f"ML models not available: {str(e)}", 'warning')
                self._log("Will use fallback string similarity methods", 'warning')
        else:
            self._log("ML dependencies not installed", 'warning')
            self._log("Run: pip install sentence-transformers scikit-learn", 'info')
    
    def setup_logging(self):
        """Setup file logging for ML Column Mapper"""
        # Create logger
        self.file_logger = logging.getLogger('MLColumnMapper')
        self.file_logger.setLevel(logging.INFO)
        
        # Clear existing handlers to avoid duplication
        self.file_logger.handlers.clear()
        
        # File handler - use direct path calculation
        tool_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_file = os.path.join(tool_dir, "column_mapper.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        self.file_logger.addHandler(file_handler)
    
    def _log(self, message: str, level: str = 'info'):
        """Log to both callback and file"""
        # Log to callback (console)
        if self.log_callback:
            self.log_callback(message)
        
        # Log to file
        if hasattr(self, 'file_logger'):
            if level.lower() == 'error':
                self.file_logger.error(message)
            elif level.lower() == 'warning':
                self.file_logger.warning(message)
            elif level.lower() == 'debug':
                self.file_logger.debug(message)
            else:
                self.file_logger.info(message)
    
    def _load_column_settings(self) -> Dict[str, Dict[str, str]]:
        """Load column settings from JSON file"""
        try:
            with open(PathConstants.COLUMN_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _load_dtype_settings(self) -> Dict[str, Dict[str, str]]:
        """Load data type settings from JSON file"""
        try:
            with open(PathConstants.DTYPE_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_column_settings(self) -> bool:
        """Save updated column settings to JSON file"""
        try:
            os.makedirs(os.path.dirname(PathConstants.COLUMN_SETTINGS_FILE), exist_ok=True)
            with open(PathConstants.COLUMN_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.column_settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self._log(f"Error saving column settings: {str(e)}", 'error')
            return False
    
    def suggest_mappings_for_new_file(self, file_columns: List[str], file_type: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Suggest column mappings for a new file
        
        Args:
            file_columns: List of column names in the new file
            file_type: Optional file type hint
        
        Returns:
            Dict with suggestions for each column
        """
        suggestions = {}
        
        # Get all known target columns from existing mappings
        all_target_columns = set()
        for settings in self.column_settings.values():
            all_target_columns.update(settings.values())
        
        for column in file_columns:
            column_suggestions = self._find_similar_columns(column, all_target_columns, file_type)
            if column_suggestions:
                suggestions[column] = column_suggestions
        
        return suggestions
    
    def _find_similar_columns(self, source_column: str, target_columns: set, file_type: str = None) -> List[Dict[str, Any]]:
        """Find similar columns using ML and string matching"""
        similarities = []
        
        for target_column in target_columns:
            # Calculate different types of similarity
            semantic_score = self._calculate_semantic_similarity(source_column, target_column)
            string_score = self._calculate_string_similarity(source_column, target_column)
            context_score = self._calculate_context_similarity(source_column, target_column, file_type)
            
            # Weighted combined score
            combined_score = (
                semantic_score * 0.5 +
                string_score * 0.3 +
                context_score * 0.2
            )
            
            if combined_score > 0.3:  # Minimum threshold
                similarities.append({
                    'target_column': target_column,
                    'confidence': round(combined_score * 100, 1),
                    'semantic_score': round(semantic_score * 100, 1),
                    'string_score': round(string_score * 100, 1),
                    'context_score': round(context_score * 100, 1),
                    'reasoning': self._generate_reasoning(source_column, target_column, semantic_score, string_score)
                })
        
        # Sort by confidence score
        similarities.sort(key=lambda x: x['confidence'], reverse=True)
        return similarities[:5]  # Return top 5 suggestions
    
    def _calculate_semantic_similarity(self, col1: str, col2: str) -> float:
        """Calculate semantic similarity using sentence transformers"""
        if not self.ml_ready:
            return 0.0
        
        try:
            # Clean column names for better semantic understanding
            clean_col1 = self._clean_column_name(col1)
            clean_col2 = self._clean_column_name(col2)
            
            embeddings = self.semantic_model.encode([clean_col1, clean_col2])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return max(0, similarity)
        except Exception:
            return 0.0
    
    def _calculate_string_similarity(self, col1: str, col2: str) -> float:
        """Calculate string similarity using fuzzy matching"""
        # Normalize strings
        norm_col1 = self._normalize_string(col1)
        norm_col2 = self._normalize_string(col2)
        
        # SequenceMatcher for overall similarity
        seq_similarity = SequenceMatcher(None, norm_col1, norm_col2).ratio()
        
        # Check for common words/substrings
        words1 = set(re.findall(r'\b\w+\b', norm_col1.lower()))
        words2 = set(re.findall(r'\b\w+\b', norm_col2.lower()))
        
        if words1 and words2:
            word_similarity = len(words1 & words2) / len(words1 | words2)
        else:
            word_similarity = 0.0
        
        # Combined string similarity
        return (seq_similarity * 0.7 + word_similarity * 0.3)
    
    def _calculate_context_similarity(self, col1: str, col2: str, file_type: str = None) -> float:
        """Calculate context-based similarity"""
        context_score = 0.0
        
        # Domain-specific keywords
        order_keywords = ['order', 'คำสั่ง', 'ออเดอร์', 'สั่งซื้อ', 'หมายเลข']
        product_keywords = ['product', 'สินค้า', 'ผลิตภัณฑ์', 'ชื่อ', 'รหัส']
        price_keywords = ['price', 'ราคา', 'ยอด', 'เงิน', 'cost']
        date_keywords = ['date', 'time', 'วันที่', 'เวลา', 'created', 'updated']
        
        col1_lower = col1.lower()
        col2_lower = col2.lower()
        
        # Check if both columns belong to the same domain
        for keywords in [order_keywords, product_keywords, price_keywords, date_keywords]:
            if (any(k in col1_lower for k in keywords) and 
                any(k in col2_lower for k in keywords)):
                context_score += 0.5
                break
        
        # File type specific bonuses
        if file_type:
            if 'jst' in file_type.lower():
                # JST system specific mappings
                if ('หมายเลข' in col1_lower and 'หมายเลข' in col2_lower):
                    context_score += 0.3
            elif 'shopee' in file_type.lower():
                # Shopee specific mappings
                if ('shopee' in col1_lower or 'shopee' in col2_lower):
                    context_score += 0.2
        
        return min(context_score, 1.0)
    
    def _clean_column_name(self, column: str) -> str:
        """Clean column name for better semantic analysis"""
        # Remove special characters and normalize
        cleaned = re.sub(r'[^\w\s]', ' ', column)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Add context words for better understanding
        if any(word in column.lower() for word in ['id', 'รหัส', 'หมายเลข']):
            cleaned += ' identifier number'
        if any(word in column.lower() for word in ['name', 'ชื่อ']):
            cleaned += ' name title'
        if any(word in column.lower() for word in ['date', 'time', 'วันที่', 'เวลา']):
            cleaned += ' date time'
        if any(word in column.lower() for word in ['price', 'ราคา', 'ยอด']):
            cleaned += ' price amount money'
        
        return cleaned
    
    def _normalize_string(self, text: str) -> str:
        """Normalize string for comparison"""
        # Remove special characters, convert to lowercase
        normalized = re.sub(r'[^\w\s]', '', text.lower())
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def _generate_reasoning(self, source: str, target: str, semantic_score: float, string_score: float) -> str:
        """Generate human-readable reasoning for the suggestion"""
        reasons = []
        
        if semantic_score > 0.7:
            reasons.append("ความหมายคล้ายกันมาก")
        elif semantic_score > 0.4:
            reasons.append("ความหมายคล้ายกัน")
        
        if string_score > 0.7:
            reasons.append("ชื่อคล้ายกันมาก")
        elif string_score > 0.4:
            reasons.append("ชื่อคล้ายกัน")
        
        # Check for specific patterns
        if any(word in source.lower() for word in ['หมายเลข', 'number', 'id']) and \
           any(word in target.lower() for word in ['หมายเลข', 'number', 'id']):
            reasons.append("ทั้งคู่เป็นหมายเลขอ้างอิง")
        
        if any(word in source.lower() for word in ['ชื่อ', 'name']) and \
           any(word in target.lower() for word in ['ชื่อ', 'name']):
            reasons.append("ทั้งคู่เป็นชื่อ")
        
        return " | ".join(reasons) if reasons else "คล้ายกันในลักษณะอื่น"
    
    def auto_map_file_columns(self, file_columns: List[str], file_type: str, confidence_threshold: float = 70.0) -> Dict[str, str]:
        """
        Automatically map file columns to target columns
        
        Args:
            file_columns: Columns in the new file
            file_type: Type identifier for the file
            confidence_threshold: Minimum confidence score for auto-mapping
        
        Returns:
            Dictionary of {source_column: target_column} mappings
        """
        auto_mappings = {}
        suggestions = self.suggest_mappings_for_new_file(file_columns, file_type)
        
        for source_column, column_suggestions in suggestions.items():
            if column_suggestions:
                best_suggestion = column_suggestions[0]  # Highest confidence
                if best_suggestion['confidence'] >= confidence_threshold:
                    auto_mappings[source_column] = best_suggestion['target_column']
                    self._log(
                        f"Auto-mapped '{source_column}' -> '{best_suggestion['target_column']}' "
                        f"(confidence: {best_suggestion['confidence']}%)"
                    )
        
        return auto_mappings
    
    def create_new_file_type_mapping(self, file_type: str, column_mappings: Dict[str, str]) -> bool:
        """
        Create a new file type mapping configuration
        
        Args:
            file_type: New file type identifier
            column_mappings: Dictionary of {source_column: target_column}
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add to column settings
            self.column_settings[file_type] = column_mappings
            
            # Save updated settings
            if self._save_column_settings():
                self._log(f"Created new mapping for file type: {file_type}")
                self._log(f"Mapped {len(column_mappings)} columns")
                return True
            else:
                return False
                
        except Exception as e:
            self._log(f"Error creating new file type mapping: {str(e)}", 'error')
            return False
    
    def suggest_file_type_from_columns(self, columns: List[str]) -> List[Dict[str, Any]]:
        """
        Suggest possible file types based on column names
        
        Args:
            columns: List of column names
            
        Returns:
            List of suggested file types with confidence scores
        """
        suggestions = []
        
        for file_type, mappings in self.column_settings.items():
            source_columns = set(mappings.keys())
            target_columns = set(mappings.values())
            
            # Calculate how many columns match
            direct_matches = len(set(columns) & source_columns)
            semantic_matches = 0
            
            # Calculate semantic matches
            for col in columns:
                if col not in source_columns:
                    for source_col in source_columns:
                        similarity = self._calculate_string_similarity(col, source_col)
                        if similarity > 0.6:
                            semantic_matches += 1
                            break
            
            total_matches = direct_matches + semantic_matches
            confidence = (total_matches / max(len(source_columns), len(columns))) * 100
            
            if confidence > 20:  # Minimum threshold
                suggestions.append({
                    'file_type': file_type,
                    'confidence': round(confidence, 1),
                    'direct_matches': direct_matches,
                    'semantic_matches': semantic_matches,
                    'total_columns': len(source_columns)
                })
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:3]  # Top 3 suggestions
    
    def learn_from_user_mapping(self, file_type: str, user_mappings: Dict[str, str]) -> None:
        """
        Learn from user's manual column mappings to improve future suggestions
        
        Args:
            file_type: The file type being mapped
            user_mappings: User's column mappings
        """
        # Store the learning data (could be expanded to use ML training)
        learning_file = os.path.join(PathConstants.CONFIG_DIR, "mapping_history.json")
        
        try:
            # Load existing learning data
            if os.path.exists(learning_file):
                with open(learning_file, 'r', encoding='utf-8') as f:
                    learning_data = json.load(f)
            else:
                learning_data = {}
            
            # Add new learning data
            if file_type not in learning_data:
                learning_data[file_type] = []
            
            learning_data[file_type].append({
                'mappings': user_mappings,
                'timestamp': pd.Timestamp.now().isoformat()
            })
            
            # Save learning data
            os.makedirs(os.path.dirname(learning_file), exist_ok=True)
            with open(learning_file, 'w', encoding='utf-8') as f:
                json.dump(learning_data, f, ensure_ascii=False, indent=2)
            
            self._log(f"Learned from {len(user_mappings)} user mappings for {file_type}")
            
        except Exception as e:
            self._log(f"Could not save learning data: {str(e)}", 'error')
    
    def generate_mapping_report(self, suggestions: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Generate a human-readable report of mapping suggestions
        
        Args:
            suggestions: Mapping suggestions from suggest_mappings_for_new_file
            
        Returns:
            Formatted report string
        """
        report = ["=" * 60]
        report.append("ML Column Mapping Suggestions")
        report.append("=" * 60)
        report.append("")
        
        if not suggestions:
            report.append("No mapping suggestions found.")
            report.append("This might be a completely new file format.")
            return "\n".join(report)
        
        total_columns = len(suggestions)
        high_confidence = sum(1 for sug_list in suggestions.values() 
                            for sug in sug_list if sug['confidence'] > 70)
        
        report.append(f"Summary:")
        report.append(f"   • Columns analyzed: {total_columns}")
        report.append(f"   • High confidence suggestions: {high_confidence}")
        report.append("")
        
        for source_col, sug_list in suggestions.items():
            report.append(f"Column '{source_col}':")
            
            if not sug_list:
                report.append("   No suggestions found")
            else:
                for i, sug in enumerate(sug_list[:3], 1):  # Top 3
                    confidence_emoji = "HIGH" if sug['confidence'] > 70 else "MED" if sug['confidence'] > 50 else "LOW"
                    report.append(f"   {confidence_emoji} {i}. {sug['target_column']} ({sug['confidence']}%)")
                    report.append(f"      Reason: {sug['reasoning']}")
            
            report.append("")
        
        report.append("=" * 60)
        report.append("Tips:")
        report.append("   • >70% confidence: Safe for auto-mapping")
        report.append("   • 50-70%: Review before applying")
        report.append("   • <50%: Manual review recommended")
        
        return "\n".join(report)