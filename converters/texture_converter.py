"""
Texture converter module for JE2BE converter
Handles the actual texture conversion and file management
"""

import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from utils.mapping_loader import MappingLoader

logger = logging.getLogger(__name__)

class TextureConverter:
    """Handles texture conversion from Java to Bedrock format"""
    
    def __init__(self, mappings_dir: str = "mappings"):
        self.mapping_loader = MappingLoader(mappings_dir)
        self.texture_mappings = self.mapping_loader.load_all_mappings()
        self.converted_files: Set[str] = set()
        self.missing_files: Set[str] = set()
        self.skipped_files: Set[str] = set()
        
    def convert_textures(self, java_textures_dir: Path, bedrock_textures_dir: Path) -> Dict[str, int]:
        """
        Convert all textures from Java to Bedrock format
        
        Returns:
            Dict with conversion statistics
        """
        stats = {
            "converted": 0,
            "skipped": 0,
            "missing": 0,
            "errors": 0
        }
        
        if not java_textures_dir.exists():
            logger.warning(f"Java textures directory not found: {java_textures_dir}")
            return stats
        
        java_blocks = java_textures_dir / "block"
        bedrock_blocks = bedrock_textures_dir / "blocks"
        if java_blocks.exists():
            block_stats = self._convert_texture_category(java_blocks, bedrock_blocks, "blocks")
            for key, value in block_stats.items():
                stats[key] += value
        
        java_items = java_textures_dir / "item"
        bedrock_items = bedrock_textures_dir / "items"
        if java_items.exists():
            item_stats = self._convert_texture_category(java_items, bedrock_items, "items")
            for key, value in item_stats.items():
                stats[key] += value
        
        java_entity = java_textures_dir / "entity"
        bedrock_entity = bedrock_textures_dir / "entity"
        if java_entity.exists():
            entity_stats = self._convert_texture_category(java_entity, bedrock_entity, "entity")
            for key, value in entity_stats.items():
                stats[key] += value
        
        java_env = java_textures_dir / "environment"
        bedrock_env = bedrock_textures_dir / "environment"
        if java_env.exists():
            env_stats = self._convert_texture_category(java_env, bedrock_env, "environment")
            for key, value in env_stats.items():
                stats[key] += value
        
        java_particle = java_textures_dir / "particle"
        bedrock_particle = bedrock_textures_dir / "particle"
        if java_particle.exists():
            particle_stats = self._convert_texture_category(java_particle, bedrock_particle, "particle")
            for key, value in particle_stats.items():
                stats[key] += value
        
        java_colormap = java_textures_dir / "colormap"
        bedrock_colormap = bedrock_textures_dir / "colormap"
        if java_colormap.exists():
            colormap_stats = self._convert_texture_category(java_colormap, bedrock_colormap, "colormap")
            for key, value in colormap_stats.items():
                stats[key] += value
        
        java_painting = java_textures_dir / "painting"
        bedrock_painting = bedrock_textures_dir / "painting"
        if java_painting.exists():
            painting_stats = self._convert_texture_category(java_painting, bedrock_painting, "painting")
            for key, value in painting_stats.items():
                stats[key] += value
        
        if self.missing_files:
            self.mapping_loader.save_missing_mappings(list(self.missing_files))
        
        return stats
    
    def _convert_texture_category(self, java_dir: Path, bedrock_dir: Path, category: str) -> Dict[str, int]:
        """Convert textures in a specific category"""
        stats = {
            "converted": 0,
            "skipped": 0,
            "missing": 0,
            "errors": 0
        }
        
        bedrock_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in java_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.png', '.tga', '.jpg', '.jpeg']:
                try:
                    result = self._convert_single_texture(file_path, java_dir, bedrock_dir, category)
                    stats[result] += 1
                except Exception as e:
                    logger.error(f"Error converting {file_path}: {str(e)}")
                    stats["errors"] += 1
        
        logger.info(f"Converted {category}: {stats['converted']} files, {stats['skipped']} skipped, {stats['missing']} missing mappings")
        return stats
    
    def _convert_single_texture(self, file_path: Path, java_dir: Path, bedrock_dir: Path, category: str) -> str:
        """Convert a single texture file"""
        relative_path = file_path.relative_to(java_dir)
        original_name = file_path.name
        
        if original_name.endswith('_n.png') or original_name.endswith('_s.png'):
            return "skipped"
        
        mapped_name = self.texture_mappings.get(original_name, None)
        
        if mapped_name is None:
            mapped_name = self._get_fallback_mapping(original_name, category)
            if mapped_name == original_name:
                self.missing_files.add(original_name)
                logger.debug(f"No mapping found for {original_name}, using original name")
        
        new_relative_path = relative_path.parent / mapped_name
        target_path = bedrock_dir / new_relative_path
        
        if target_path.exists():
            self.skipped_files.add(str(target_path))
            return "skipped"
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(file_path, target_path)
        self.converted_files.add(str(target_path))
        
        logger.debug(f"Converted {category}: {original_name} -> {mapped_name}")
        return "converted" if mapped_name != original_name else "missing"
    
    def _get_fallback_mapping(self, texture_name: str, category: str) -> str:
        """Get fallback mapping for unmapped textures"""
        if texture_name.startswith("minecraft_"):
            texture_name = texture_name[10:]
        
        fallback_patterns = {
            "oak_": "",
            "spruce_": "spruce_",
            "birch_": "birch_",
            "jungle_": "jungle_",
            "acacia_": "acacia_",
            "dark_oak_": "dark_oak_",
            
            "white_": "white_",
            "orange_": "orange_",
            "magenta_": "magenta_",
            "light_blue_": "light_blue_",
            "yellow_": "yellow_",
            "lime_": "lime_",
            "pink_": "pink_",
            "gray_": "gray_",
            "light_gray_": "silver_",
            "cyan_": "cyan_",
            "purple_": "purple_",
            "blue_": "blue_",
            "brown_": "brown_",
            "green_": "green_",
            "red_": "red_",
            "black_": "black_",
        }
        
        for pattern, replacement in fallback_patterns.items():
            if texture_name.startswith(pattern):
                return texture_name.replace(pattern, replacement, 1)
        
        return texture_name
    
    def get_conversion_report(self) -> Dict[str, any]:
        """Get detailed conversion report"""
        return {
            "converted_files": len(self.converted_files),
            "skipped_files": len(self.skipped_files),
            "missing_mappings": len(self.missing_files),
            "total_mappings_available": len(self.texture_mappings),
            "missing_files_list": sorted(list(self.missing_files)),
            "converted_files_sample": sorted(list(self.converted_files))[:10]  # First 10 as sample
        }
    
    def reload_mappings(self):
        """Reload mappings from files (useful for development)"""
        self.texture_mappings = self.mapping_loader.load_all_mappings()
        logger.info(f"Reloaded {len(self.texture_mappings)} texture mappings")
    
    def add_custom_mapping(self, java_name: str, bedrock_name: str):
        """Add a custom mapping at runtime"""
        self.texture_mappings[java_name] = bedrock_name
        logger.debug(f"Added custom mapping: {java_name} -> {bedrock_name}")
    
    def validate_converted_textures(self, bedrock_dir: Path) -> Dict[str, List[str]]:
        """Validate converted textures and check for issues"""
        issues = {
            "empty_files": [],
            "large_files": [],
            "wrong_extensions": [],
            "missing_expected": []
        }
        
        if not bedrock_dir.exists():
            return issues
        
        for texture_file in bedrock_dir.rglob("*"):
            if texture_file.is_file():
                file_size = texture_file.stat().st_size
                if file_size == 0:
                    issues["empty_files"].append(str(texture_file))
                elif file_size > 1024 * 1024:  # > 1MB
                    issues["large_files"].append(str(texture_file))
                
                if texture_file.suffix.lower() not in ['.png', '.tga', '.jpg', '.jpeg']:
                    issues["wrong_extensions"].append(str(texture_file))
        
        return issues
