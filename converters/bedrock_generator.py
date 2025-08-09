"""
Bedrock structure generator for JE2BE converter
Creates Bedrock Edition specific files and directory structure
"""

import json
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class BedrockStructureGenerator:
    """Generates Bedrock Edition specific files and directory structure"""
    
    def __init__(self):
        self.required_directories = [
            "textures/blocks",
            "textures/items", 
            "textures/entity",
            "textures/environment",
            "textures/particle",
            "textures/ui",
            "textures/colormap",
            "textures/painting",
            "models",
            "sounds",
            "texts",
            "animations",
            "entity",
            "fogs",
            "render_controllers",
            "materials"
        ]
    
    def create_bedrock_structure(self, bedrock_temp: Path):
        """Create the basic Bedrock Edition directory structure"""
        logger.info("Creating Bedrock Edition directory structure...")
        
        for dir_path in self.required_directories:
            full_path = bedrock_temp / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {dir_path}")
    
    def generate_manifest(self, bedrock_temp: Path, pack_name: str = None, 
                          pack_description: str = None, version: List[int] = None,
                          enable_pbr: bool = False) -> bool:
        """Generate the manifest.json file for Bedrock Edition"""
        try:
            if not pack_name:
                pack_name = "Converted Java Resource Pack"
            if not pack_description:
                pack_description = f"Converted from Java Edition on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            if not version:
                version = [1, 0, 0]
                
            manifest = {
                "format_version": 2,
                "header": {
                    "description": pack_description,
                    "name": pack_name,
                    "uuid": str(uuid.uuid4()),
                    "version": version,
                    "min_engine_version": [1, 21, 0]
                },
                "modules": [
                    {
                        "description": pack_description,
                        "type": "resources",
                        "uuid": str(uuid.uuid4()),
                        "version": version
                    }
                ]
            }
            
            if enable_pbr:
                manifest["capabilities"] = ["pbr", "raytraced"]
                logger.info("Enabled PBR and raytraced capabilities in manifest")
            
            manifest_path = bedrock_temp / "manifest.json"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            
            logger.info(f"Generated manifest.json: {pack_name} v{'.'.join(map(str, version))}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate manifest.json: {str(e)}")
            return False
    
    def generate_terrain_texture_json(self, bedrock_temp: Path, pack_name: str = "converted_pack") -> bool:
        """Copy terrain_texture.json from required folder"""
        try:
            required_file = Path("required") / "terrain_texture.json"
            if not required_file.exists():
                logger.error("Required terrain_texture.json not found in required folder")
                return False
            
            dest_path = bedrock_temp / "textures" / "terrain_texture.json"
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            import shutil
            shutil.copy2(required_file, dest_path)
            
            logger.info("Copied terrain_texture.json from required folder")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy terrain_texture.json: {str(e)}")
            return False
    
    def generate_item_texture_json(self, bedrock_temp: Path, pack_name: str = "converted_pack") -> bool:
        """Copy item_texture.json from required folder"""
        try:
            required_file = Path("required") / "item_texture.json"
            if not required_file.exists():
                logger.error("Required item_texture.json not found in required folder")
                return False
            
            dest_path = bedrock_temp / "textures" / "item_texture.json"
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            import shutil
            shutil.copy2(required_file, dest_path)
            
            logger.info("Copied item_texture.json from required folder")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy item_texture.json: {str(e)}")
            return False
    
    def generate_blocks_json(self, bedrock_temp: Path) -> bool:
        """Copy blocks.json from required folder"""
        try:
            required_file = Path("required") / "blocks.json"
            if not required_file.exists():
                logger.error("Required blocks.json not found in required folder")
                return False
            
            dest_path = bedrock_temp / "blocks.json"
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            import shutil
            shutil.copy2(required_file, dest_path)
            
            logger.info("Copied blocks.json from required folder")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy blocks.json: {str(e)}")
            return False
    
    def _get_basic_blocks_data(self) -> Dict[str, Any]:
        """Get basic block definitions that are commonly needed"""
        return {
            "grass": {
                "textures": {
                    "up": "grass_top",
                    "down": "dirt",
                    "side": "grass_side"
                },
                "sound": "grass"
            },
            "dirt": {
                "textures": "dirt",
                "sound": "gravel"
            },
            "stone": {
                "textures": "stone",
                "sound": "stone"
            },
            "cobblestone": {
                "textures": "cobblestone",
                "sound": "stone"
            },
            
            "log_oak": {
                "textures": {
                    "up": "log_oak_top",
                    "down": "log_oak_top",
                    "side": "log_oak"
                },
                "sound": "wood"
            },
            "planks_oak": {
                "textures": "planks_oak",
                "sound": "wood"
            },
            "leaves_oak": {
                "textures": "leaves_oak",
                "sound": "grass"
            },
            
            "coal_ore": {
                "textures": "coal_ore",
                "sound": "stone"
            },
            "iron_ore": {
                "textures": "iron_ore",
                "sound": "stone"
            },
            "gold_ore": {
                "textures": "gold_ore",
                "sound": "stone"
            },
            "diamond_ore": {
                "textures": "diamond_ore",
                "sound": "stone"
            },
            
            "glass": {
                "textures": "glass",
                "sound": "glass"
            },
            
            "sand": {
                "textures": "sand",
                "sound": "sand"
            },
            "sandstone": {
                "textures": {
                    "up": "sandstone_top",
                    "down": "sandstone_bottom",
                    "side": "sandstone_normal"
                },
                "sound": "stone"
            }
        }
    
    def _get_block_sound(self, texture_name: str) -> str:
        """Determine appropriate sound for a block based on its texture name"""
        sound_mappings = {
            "wood": ["wood", "plank", "log", "door", "trapdoor", "fence"],
            "grass": ["grass", "leaves", "flower", "plant", "vine"],
            "stone": ["stone", "ore", "brick", "cobble", "concrete"],
            "sand": ["sand"],
            "gravel": ["gravel", "dirt"],
            "glass": ["glass"],
            "metal": ["iron", "gold", "copper", "metal", "anvil"],
            "cloth": ["wool", "carpet"],
            "snow": ["snow", "ice"]
        }
        
        texture_lower = texture_name.lower()
        
        for sound, keywords in sound_mappings.items():
            if any(keyword in texture_lower for keyword in keywords):
                return sound
        
        return "stone"  # Default sound
    
    def generate_pack_icon(self, bedrock_temp: Path, icon_path: Optional[Path] = None) -> bool:
        """Generate or copy pack icon"""
        try:
            pack_icon_path = bedrock_temp / "pack_icon.png"
            
            if icon_path and icon_path.exists():
                import shutil
                shutil.copy2(icon_path, pack_icon_path)
                logger.info(f"Copied custom pack icon from {icon_path}")
            else:
                logger.info("No custom icon provided, pack will use default Bedrock icon")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle pack icon: {str(e)}")
            return False
    
    def generate_language_files(self, bedrock_temp: Path, java_lang_dir: Optional[Path] = None) -> bool:
        """Generate language files for Bedrock Edition"""
        try:
            texts_dir = bedrock_temp / "texts"
            texts_dir.mkdir(parents=True, exist_ok=True)
            
            if java_lang_dir and java_lang_dir.exists():
                for lang_file in java_lang_dir.glob("*.json"):
                    self._convert_lang_file(lang_file, texts_dir)
            else:
                en_us_path = texts_dir / "en_US.lang"
                with open(en_us_path, 'w', encoding='utf-8') as f:
                    f.write("## Converted Java Resource Pack\n")
                    f.write("## Language file converted from Java Edition\n")
                
                logger.info("Created basic en_US.lang file")
            
            languages_data = {
                "language": [
                    ["en_US", "English (US)", "English (US)", 100]
                ]
            }
            
            languages_path = texts_dir / "languages.json"
            with open(languages_path, 'w', encoding='utf-8') as f:
                json.dump(languages_data, f, indent=2)
            
            logger.info("Generated language files")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate language files: {str(e)}")
            return False
    
    def _convert_lang_file(self, java_lang_file: Path, texts_dir: Path):
        """Convert Java .json lang file to Bedrock .lang format"""
        try:
            with open(java_lang_file, 'r', encoding='utf-8') as f:
                java_lang = json.load(f)
            
            locale = java_lang_file.stem
            bedrock_locale = self._convert_locale_code(locale)
            
            bedrock_lang_file = texts_dir / f"{bedrock_locale}.lang"
            
            with open(bedrock_lang_file, 'w', encoding='utf-8') as f:
                f.write(f"## Converted from Java Edition {locale}.json\n")
                f.write(f"## Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for key, value in java_lang.items():
                    bedrock_key = self._convert_lang_key(key)
                    f.write(f"{bedrock_key}={value}\n")
            
            logger.debug(f"Converted language file: {java_lang_file.name} -> {bedrock_lang_file.name}")
            
        except Exception as e:
            logger.warning(f"Failed to convert language file {java_lang_file}: {str(e)}")
    
    def _convert_locale_code(self, java_locale: str) -> str:
        """Convert Java locale code to Bedrock format"""
        locale_mappings = {
            "en_us": "en_US",
            "en_gb": "en_GB", 
            "de_de": "de_DE",
            "es_es": "es_ES",
            "es_mx": "es_MX",
            "fr_fr": "fr_FR",
            "fr_ca": "fr_CA",
            "it_it": "it_IT",
            "ja_jp": "ja_JP",
            "ko_kr": "ko_KR",
            "pt_br": "pt_BR",
            "pt_pt": "pt_PT",
            "ru_ru": "ru_RU",
            "zh_cn": "zh_CN",
            "zh_tw": "zh_TW"
        }
        
        return locale_mappings.get(java_locale.lower(), "en_US")
    
    def _convert_lang_key(self, java_key: str) -> str:
        """Convert Java language key to Bedrock equivalent"""
        key_mappings = {
            "block.minecraft.": "tile.",
            "item.minecraft.": "item.",
            "entity.minecraft.": "entity.",
            "enchantment.minecraft.": "enchantment.",
            "effect.minecraft.": "effect.",
            "biome.minecraft.": "biome."
        }
        
        for java_prefix, bedrock_prefix in key_mappings.items():
            if java_key.startswith(java_prefix):
                return java_key.replace(java_prefix, bedrock_prefix, 1)
        
        return java_key
    
    def validate_bedrock_structure(self, bedrock_temp: Path) -> Dict[str, List[str]]:
        """Validate the generated Bedrock structure"""
        issues = {
            "missing_required_files": [],
            "missing_directories": [],
            "invalid_json_files": []
        }
        
        required_files = [
            "manifest.json",
            "textures/terrain_texture.json",
            "textures/item_texture.json"
        ]
        
        for required_file in required_files:
            file_path = bedrock_temp / required_file
            if not file_path.exists():
                issues["missing_required_files"].append(required_file)
        
        for required_dir in self.required_directories:
            dir_path = bedrock_temp / required_dir
            if not dir_path.exists():
                issues["missing_directories"].append(required_dir)
        
        for json_file in bedrock_temp.rglob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError:
                relative_path = json_file.relative_to(bedrock_temp)
                issues["invalid_json_files"].append(str(relative_path))
        
        return issues
