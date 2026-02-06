"""
Java structure generator for BE2JE converter
Creates Java Edition specific files and directory structure
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class JavaStructureGenerator:
    """Generates Java Edition specific files and directory structure"""
    
    def __init__(self):
        self.required_directories = [
            "assets/minecraft/textures/block",
            "assets/minecraft/textures/item",
            "assets/minecraft/textures/entity",
            "assets/minecraft/textures/environment",
            "assets/minecraft/textures/particle",
            "assets/minecraft/textures/gui",
            "assets/minecraft/textures/colormap",
            "assets/minecraft/textures/painting",
            "assets/minecraft/models/block",
            "assets/minecraft/models/item",
            "assets/minecraft/sounds",
            "assets/minecraft/lang"
        ]
    
    def create_java_structure(self, java_temp: Path):
        """Create the basic Java Edition directory structure"""
        logger.info("Creating Java Edition directory structure...")
        
        for dir_path in self.required_directories:
            full_path = java_temp / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {dir_path}")
    
    def generate_pack_mcmeta(self, java_temp: Path, pack_name: str = None, 
                            pack_description: str = None, pack_format: int = 15) -> bool:
        """Generate the pack.mcmeta file for Java Edition"""
        try:
            if not pack_description:
                from datetime import datetime
                pack_description = f"Converted from Bedrock Edition on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            mcmeta = {
                "pack": {
                    "pack_format": pack_format,
                    "description": pack_description
                }
            }
            
            mcmeta_path = java_temp / "pack.mcmeta"
            with open(mcmeta_path, 'w', encoding='utf-8') as f:
                json.dump(mcmeta, f, indent=2)
            
            logger.info(f"Generated pack.mcmeta with format {pack_format}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate pack.mcmeta: {str(e)}")
            return False
    
    def convert_manifest_to_mcmeta(self, manifest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Bedrock manifest.json to Java pack.mcmeta structure"""
        try:
            header = manifest_data.get("header", {})
            pack_name = header.get("name", "Converted Bedrock Pack")
            description = header.get("description", "Converted from Bedrock Edition")
            
            # Map Bedrock version to Java pack format (simplified)
            # Bedrock 1.21+ maps to Java 15 (1.20.x)
            pack_format = 15
            
            return {
                "name": pack_name,
                "description": description,
                "pack_format": pack_format
            }
        except Exception as e:
            logger.warning(f"Failed to parse manifest: {str(e)}")
            return {
                "name": "Converted Pack",
                "description": "Converted from Bedrock Edition",
                "pack_format": 15
            }
    
    def generate_language_files(self, java_temp: Path, bedrock_texts_dir: Optional[Path] = None) -> bool:
        """Generate language files for Java Edition"""
        try:
            lang_dir = java_temp / "assets" / "minecraft" / "lang"
            lang_dir.mkdir(parents=True, exist_ok=True)
            
            if bedrock_texts_dir and bedrock_texts_dir.exists():
                for lang_file in bedrock_texts_dir.glob("*.lang"):
                    self._convert_lang_file(lang_file, lang_dir)
            else:
                # Create basic en_us.json file
                en_us_path = lang_dir / "en_us.json"
                with open(en_us_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "_comment": "Converted from Bedrock Edition"
                    }, f, indent=2)
                
                logger.info("Created basic en_us.json file")
            
            logger.info("Generated language files")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate language files: {str(e)}")
            return False
    
    def _convert_lang_file(self, bedrock_lang_file: Path, lang_dir: Path):
        """Convert Bedrock .lang file to Java .json format"""
        try:
            java_lang = {}
            
            with open(bedrock_lang_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            java_key = self._convert_lang_key_to_java(key.strip())
                            java_lang[java_key] = value.strip()
            
            # Convert locale code
            locale = bedrock_lang_file.stem
            java_locale = self._convert_locale_code_to_java(locale)
            
            java_lang_file = lang_dir / f"{java_locale}.json"
            
            with open(java_lang_file, 'w', encoding='utf-8') as f:
                json.dump(java_lang, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Converted language file: {bedrock_lang_file.name} -> {java_lang_file.name}")
            
        except Exception as e:
            logger.warning(f"Failed to convert language file {bedrock_lang_file}: {str(e)}")
    
    def _convert_locale_code_to_java(self, bedrock_locale: str) -> str:
        """Convert Bedrock locale code to Java format"""
        # Java uses lowercase with underscore (e.g., en_us)
        return bedrock_locale.lower()
    
    def _convert_lang_key_to_java(self, bedrock_key: str) -> str:
        """Convert Bedrock language key to Java equivalent"""
        key_mappings = {
            "tile.": "block.minecraft.",
            "item.": "item.minecraft.",
            "entity.": "entity.minecraft.",
            "enchantment.": "enchantment.minecraft.",
            "effect.": "effect.minecraft.",
            "biome.": "biome.minecraft."
        }
        
        for bedrock_prefix, java_prefix in key_mappings.items():
            if bedrock_key.startswith(bedrock_prefix):
                return bedrock_key.replace(bedrock_prefix, java_prefix, 1)
        
        return bedrock_key
    
    def generate_pack_png(self, java_temp: Path, icon_path: Optional[Path] = None) -> bool:
        """Generate or copy pack.png"""
        try:
            pack_png_path = java_temp / "pack.png"
            
            if icon_path and icon_path.exists():
                import shutil
                shutil.copy2(icon_path, pack_png_path)
                logger.info(f"Copied pack icon from {icon_path}")
            else:
                logger.info("No icon provided, skipping pack.png")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle pack.png: {str(e)}")
            return False
    
    def stub_model_conversion(self, bedrock_temp: Path, java_temp: Path) -> Dict[str, int]:
        """Stub for handling model differences between Bedrock and Java"""
        logger.info("Model conversion stub - to be implemented for full conversion")
        # TODO: Implement actual model conversion
        return {"models_processed": 0}
    
    def stub_translation_handling(self, bedrock_temp: Path, java_temp: Path) -> Dict[str, int]:
        """Stub for handling translation differences"""
        logger.info("Translation handling stub - to be implemented for full conversion")
        # TODO: Implement detailed translation mapping
        return {"translations_processed": 0}
