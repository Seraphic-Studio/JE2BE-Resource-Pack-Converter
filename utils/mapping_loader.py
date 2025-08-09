"""
Mapping loader utility for JE2BE converter
Loads and manages texture mappings from JSON files
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class MappingLoader:
    """Utility class to load and manage texture mappings"""
    
    def __init__(self, mappings_dir: str = "mappings"):
        self.mappings_dir = Path(mappings_dir)
        self.loaded_mappings = {}
        
    def load_all_mappings(self) -> Dict[str, str]:
        """Load all mapping files and combine them into a single dictionary"""
        combined_mappings = {}
        
        if not self.mappings_dir.exists():
            logger.warning(f"Mappings directory not found: {self.mappings_dir}")
            return combined_mappings
        
        mapping_files = list(self.mappings_dir.glob("*.json"))
        
        if not mapping_files:
            logger.warning(f"No mapping files found in {self.mappings_dir}")
            return combined_mappings
        
        logger.info(f"Loading {len(mapping_files)} mapping files...")
        
        for mapping_file in mapping_files:
            try:
                category_mappings = self.load_mapping_file(mapping_file)
                if category_mappings:
                    mappings = category_mappings.get("mappings", {})
                    combined_mappings.update(mappings)
                    
                    category = category_mappings.get("category", mapping_file.stem)
                    logger.debug(f"Loaded {len(mappings)} mappings from {category}")
                    
            except Exception as e:
                logger.error(f"Failed to load mapping file {mapping_file}: {str(e)}")
        
        logger.info(f"Total mappings loaded: {len(combined_mappings)}")
        return combined_mappings
    
    def load_mapping_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a single mapping file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            category = data.get("category", file_path.stem)
            self.loaded_mappings[category] = data
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in mapping file {file_path}: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Error loading mapping file {file_path}: {str(e)}")
            return {}
    
    def get_mapping_by_category(self, category: str) -> Dict[str, str]:
        """Get mappings for a specific category"""
        if category not in self.loaded_mappings:
            category_file = self.mappings_dir / f"{category}.json"
            if category_file.exists():
                self.load_mapping_file(category_file)
        
        if category in self.loaded_mappings:
            return self.loaded_mappings[category].get("mappings", {})
        
        return {}
    
    def get_categories(self) -> List[str]:
        """Get list of available mapping categories"""
        return list(self.loaded_mappings.keys())
    
    def find_mapping(self, java_texture: str) -> str:
        """Find a bedrock mapping for a java texture name"""
        all_mappings = self.load_all_mappings()
        return all_mappings.get(java_texture, java_texture)
    
    def has_mapping(self, java_texture: str) -> bool:
        """Check if a mapping exists for the given java texture"""
        all_mappings = self.load_all_mappings()
        return java_texture in all_mappings
    
    def get_unmapped_textures(self, java_textures: List[str]) -> List[str]:
        """Get list of textures that don't have mappings"""
        all_mappings = self.load_all_mappings()
        return [texture for texture in java_textures if texture not in all_mappings]
    
    def save_missing_mappings(self, missing_textures: List[str], output_file: str = "missing_mappings.json"):
        """Save missing mappings to a file for manual review"""
        missing_data = {
            "description": "Missing texture mappings that need manual review",
            "category": "missing",
            "count": len(missing_textures),
            "mappings": {texture: texture for texture in missing_textures}
        }
        
        output_path = Path(output_file)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(missing_data, f, indent=2)
            
            logger.info(f"Saved {len(missing_textures)} missing mappings to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save missing mappings: {str(e)}")
    
    def validate_mappings(self) -> Dict[str, List[str]]:
        """Validate all mappings and return any issues found"""
        issues = {
            "duplicate_java": [],
            "duplicate_bedrock": [],
            "invalid_format": []
        }
        
        all_mappings = self.load_all_mappings()
        bedrock_mappings = {}
        
        for java_texture, bedrock_texture in all_mappings.items():
            if bedrock_texture in bedrock_mappings:
                issues["duplicate_bedrock"].append(f"{java_texture} and {bedrock_mappings[bedrock_texture]} both map to {bedrock_texture}")
            else:
                bedrock_mappings[bedrock_texture] = java_texture
            
            if not java_texture.endswith('.png') or not bedrock_texture.endswith('.png'):
                issues["invalid_format"].append(f"{java_texture} -> {bedrock_texture}")
        
        return issues
    
    def create_reverse_mapping(self) -> Dict[str, str]:
        """Create a reverse mapping (bedrock -> java) for validation"""
        all_mappings = self.load_all_mappings()
        return {bedrock: java for java, bedrock in all_mappings.items()}

if __name__ == "__main__":
    loader = MappingLoader()
    mappings = loader.load_all_mappings()
    print(f"Loaded {len(mappings)} total mappings")
    
    categories = loader.get_categories()
    print(f"Categories: {categories}")
    
    issues = loader.validate_mappings()
    for issue_type, issue_list in issues.items():
        if issue_list:
            print(f"{issue_type}: {len(issue_list)} issues found")
            for issue in issue_list[:5]:  # Show first 5
                print(f"  - {issue}")
