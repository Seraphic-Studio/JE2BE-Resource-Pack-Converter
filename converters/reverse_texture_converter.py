"""
Reverse texture converter module for BE2JE converter
Handles texture conversion from Bedrock to Java Edition format
"""

import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

class ReverseTextureConverter:
    """Handles texture conversion from Bedrock to Java Edition format"""
    
    def __init__(self, mappings_dir: str = "mappings"):
        self.mappings_dir = Path(mappings_dir)
        self.reverse_mappings = self._create_reverse_mappings()
        self.converted_files: Set[str] = set()
        self.missing_mappings: Set[str] = set()
        self.skipped_files: Set[str] = set()
        
    def _create_reverse_mappings(self) -> Dict[str, str]:
        """Create reverse mappings from Bedrock to Java texture names"""
        # Load existing mappings and reverse them
        from utils.mapping_loader import MappingLoader
        
        mapping_loader = MappingLoader(str(self.mappings_dir))
        forward_mappings = mapping_loader.load_all_mappings()
        
        # Reverse the mappings (Bedrock -> Java)
        reverse_mappings = {}
        for java_name, bedrock_name in forward_mappings.items():
            # Some mappings might map multiple Java textures to same Bedrock texture
            # In reverse, we'll use the first mapping found
            if bedrock_name not in reverse_mappings:
                reverse_mappings[bedrock_name] = java_name
        
        logger.info(f"Created {len(reverse_mappings)} reverse texture mappings")
        return reverse_mappings
    
    def convert_textures(self, bedrock_textures_dir: Path, java_textures_dir: Path) -> Dict[str, int]:
        """
        Convert all textures from Bedrock to Java Edition format
        
        Returns:
            Dict with conversion statistics
        """
        stats = {
            "converted": 0,
            "skipped": 0,
            "missing": 0,
            "errors": 0
        }
        
        if not bedrock_textures_dir.exists():
            logger.warning(f"Bedrock textures directory not found: {bedrock_textures_dir}")
            return stats
        
        # Convert blocks: textures/blocks -> textures/block
        bedrock_blocks = bedrock_textures_dir / "blocks"
        java_blocks = java_textures_dir / "block"
        if bedrock_blocks.exists():
            block_stats = self._convert_texture_category(bedrock_blocks, java_blocks, "blocks")
            for key, value in block_stats.items():
                stats[key] += value
        
        # Convert items: textures/items -> textures/item
        bedrock_items = bedrock_textures_dir / "items"
        java_items = java_textures_dir / "item"
        if bedrock_items.exists():
            item_stats = self._convert_texture_category(bedrock_items, java_items, "items")
            for key, value in item_stats.items():
                stats[key] += value
        
        # Convert entity: textures/entity -> textures/entity (same)
        bedrock_entity = bedrock_textures_dir / "entity"
        java_entity = java_textures_dir / "entity"
        if bedrock_entity.exists():
            entity_stats = self._convert_texture_category(bedrock_entity, java_entity, "entity")
            for key, value in entity_stats.items():
                stats[key] += value
        
        # Convert environment: textures/environment -> textures/environment (same)
        bedrock_env = bedrock_textures_dir / "environment"
        java_env = java_textures_dir / "environment"
        if bedrock_env.exists():
            env_stats = self._convert_texture_category(bedrock_env, java_env, "environment")
            for key, value in env_stats.items():
                stats[key] += value
        
        # Convert particle: textures/particle -> textures/particle (same)
        bedrock_particle = bedrock_textures_dir / "particle"
        java_particle = java_textures_dir / "particle"
        if bedrock_particle.exists():
            particle_stats = self._convert_texture_category(bedrock_particle, java_particle, "particle")
            for key, value in particle_stats.items():
                stats[key] += value
        
        # Convert colormap: textures/colormap -> textures/colormap (same)
        bedrock_colormap = bedrock_textures_dir / "colormap"
        java_colormap = java_textures_dir / "colormap"
        if bedrock_colormap.exists():
            colormap_stats = self._convert_texture_category(bedrock_colormap, java_colormap, "colormap")
            for key, value in colormap_stats.items():
                stats[key] += value
        
        # Convert painting: textures/painting -> textures/painting (same)
        bedrock_painting = bedrock_textures_dir / "painting"
        java_painting = java_textures_dir / "painting"
        if bedrock_painting.exists():
            painting_stats = self._convert_texture_category(bedrock_painting, java_painting, "painting")
            for key, value in painting_stats.items():
                stats[key] += value
        
        if self.missing_mappings:
            self._save_missing_mappings(list(self.missing_mappings))
        
        return stats
    
    def _convert_texture_category(self, bedrock_dir: Path, java_dir: Path, category: str) -> Dict[str, int]:
        """Convert textures in a specific category"""
        stats = {
            "converted": 0,
            "skipped": 0,
            "missing": 0,
            "errors": 0
        }
        
        java_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Converting {category} textures from {bedrock_dir} to {java_dir}")
        
        for bedrock_file in bedrock_dir.rglob("*.png"):
            try:
                relative_path = bedrock_file.relative_to(bedrock_dir)
                bedrock_name = relative_path.stem
                
                # Look up the Java name
                java_name = self.reverse_mappings.get(bedrock_name, None)
                
                if java_name:
                    # Use mapped Java name
                    java_file = java_dir / f"{java_name}.png"
                    
                    if java_file.exists():
                        stats["skipped"] += 1
                        self.skipped_files.add(str(relative_path))
                        logger.debug(f"Skipped (already exists): {java_name}")
                    else:
                        java_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(bedrock_file, java_file)
                        stats["converted"] += 1
                        self.converted_files.add(str(relative_path))
                        logger.debug(f"Converted: {bedrock_name} -> {java_name}")
                else:
                    # No mapping found, copy with same name
                    java_file = java_dir / relative_path
                    
                    java_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(bedrock_file, java_file)
                    stats["missing"] += 1
                    self.missing_mappings.add(bedrock_name)
                    logger.debug(f"No mapping for: {bedrock_name}, copied as-is")
                    
            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Error converting {bedrock_file}: {str(e)}")
        
        logger.info(f"Converted {stats['converted']} {category} textures")
        return stats
    
    def _save_missing_mappings(self, missing: List[str]):
        """Save missing mappings to a JSON file"""
        try:
            import json
            missing_file = Path("missing_reverse_mappings.json")
            
            with open(missing_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(missing), f, indent=2)
            
            logger.info(f"Saved {len(missing)} missing reverse mappings to {missing_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save missing mappings: {str(e)}")
    
    def get_conversion_report(self) -> Dict[str, any]:
        """Get a detailed conversion report"""
        return {
            "converted_files": len(self.converted_files),
            "missing_mappings": len(self.missing_mappings),
            "skipped_files": len(self.skipped_files),
            "converted_files_list": sorted(list(self.converted_files)),
            "missing_files_list": sorted(list(self.missing_mappings)),
            "skipped_files_list": sorted(list(self.skipped_files))
        }
