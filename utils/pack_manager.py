"""
Pack manager module for JE2BE converter
Handles zip file operations and .mcpack creation
"""

import os
import json
import zipfile
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

class PackManager:
    """Manages resource pack file operations"""
    
    def __init__(self):
        self.temp_dirs: List[Path] = []
    
    def extract_java_pack(self, input_path: str, extract_dir: Path) -> Optional[Path]:
        """
        Extract Java Edition resource pack and find the minecraft assets directory
        
        Returns:
            Path to the minecraft directory or None if not found
        """
        try:
            input_path = Path(input_path)
            
            if not input_path.exists():
                logger.error(f"Input file does not exist: {input_path}")
                return None
            
            if input_path.suffix.lower() != '.zip':
                logger.error("Input file must be a .zip file")
                return None
            
            logger.info(f"Extracting Java resource pack: {input_path.name}")
            
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            assets_dir = self._find_assets_directory(extract_dir)
            if not assets_dir:
                logger.error("Could not find assets/minecraft directory in the Java resource pack")
                return None
            
            minecraft_dir = assets_dir / 'minecraft'
            if not minecraft_dir.exists():
                logger.error("Could not find minecraft directory in assets")
                return None
            
            logger.info(f"Found minecraft directory: {minecraft_dir}")
            return minecraft_dir
            
        except zipfile.BadZipFile:
            logger.error(f"Invalid zip file: {input_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to extract Java resource pack: {str(e)}")
            return None
    
    def _find_assets_directory(self, extract_dir: Path) -> Optional[Path]:
        """Find the assets directory in the extracted files"""
        for root, dirs, files in os.walk(extract_dir):
            if 'assets' in dirs:
                assets_path = Path(root) / 'assets'
                if (assets_path / 'minecraft').exists():
                    return assets_path
        
        if (extract_dir / 'minecraft').exists():
            assets_mock = extract_dir / 'assets_mock'
            assets_mock.mkdir(exist_ok=True)
            
            minecraft_src = extract_dir / 'minecraft'
            minecraft_dst = assets_mock / 'minecraft'
            
            if not minecraft_dst.exists():
                shutil.move(str(minecraft_src), str(minecraft_dst))
            
            return assets_mock
        
        return None
    
    def create_mcpack(self, bedrock_temp: Path, output_path: str) -> bool:
        """Create the final .mcpack file"""
        try:
            output_path = Path(output_path)
            
            if output_path.suffix.lower() != '.mcpack':
                output_path = output_path.with_suffix('.mcpack')
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Creating .mcpack file: {output_path}")
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                file_count = 0
                for file_path in bedrock_temp.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(bedrock_temp)
                        zipf.write(file_path, arcname)
                        file_count += 1
                        
                        if file_count % 100 == 0:
                            logger.debug(f"Added {file_count} files to .mcpack")
            
            file_size = output_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            logger.info(f"Created .mcpack file: {output_path}")
            logger.info(f"Pack size: {size_mb:.2f} MB ({file_count} files)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create .mcpack file: {str(e)}")
            return False
    
    def validate_java_pack(self, input_path: str) -> Dict[str, Any]:
        """Validate Java Edition resource pack structure"""
        validation_result = {
            "valid": False,
            "has_pack_mcmeta": False,
            "has_assets": False,
            "has_textures": False,
            "texture_categories": [],
            "errors": []
        }
        
        try:
            input_path = Path(input_path)
            
            if not input_path.exists():
                validation_result["errors"].append("File does not exist")
                return validation_result
            
            if input_path.suffix.lower() != '.zip':
                validation_result["errors"].append("File is not a .zip file")
                return validation_result
            
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                if any('pack.mcmeta' in f for f in file_list):
                    validation_result["has_pack_mcmeta"] = True
                
                if any('assets/' in f for f in file_list):
                    validation_result["has_assets"] = True
                
                texture_paths = [f for f in file_list if 'textures/' in f and f.endswith('.png')]
                if texture_paths:
                    validation_result["has_textures"] = True
                
                categories = set()
                for texture_path in texture_paths:
                    parts = texture_path.split('/')
                    if len(parts) >= 3 and parts[-3] == 'textures':
                        categories.add(parts[-2])  # block, item, entity, etc.
                
                validation_result["texture_categories"] = sorted(list(categories))
            
            validation_result["valid"] = (
                validation_result["has_assets"] and 
                validation_result["has_textures"]
            )
            
            if not validation_result["valid"]:
                if not validation_result["has_assets"]:
                    validation_result["errors"].append("No assets directory found")
                if not validation_result["has_textures"]:
                    validation_result["errors"].append("No texture files found")
            
        except zipfile.BadZipFile:
            validation_result["errors"].append("Invalid or corrupted zip file")
        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def get_pack_info(self, input_path: str) -> Dict[str, Any]:
        """Get information about a Java Edition resource pack"""
        pack_info = {
            "name": "Unknown Pack",
            "description": "No description",
            "pack_format": None,
            "file_size": 0,
            "texture_count": 0,
            "categories": []
        }
        
        try:
            input_path = Path(input_path)
            pack_info["file_size"] = input_path.stat().st_size
            
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                texture_files = [f for f in file_list if f.endswith('.png')]
                pack_info["texture_count"] = len(texture_files)
                
                categories = set()
                for texture_path in texture_files:
                    if 'textures/' in texture_path:
                        parts = texture_path.split('/')
                        texture_idx = next(i for i, part in enumerate(parts) if part == 'textures')
                        if texture_idx + 1 < len(parts):
                            categories.add(parts[texture_idx + 1])
                
                pack_info["categories"] = sorted(list(categories))
                
                mcmeta_files = [f for f in file_list if f.endswith('pack.mcmeta')]
                if mcmeta_files:
                    try:
                        mcmeta_content = zip_ref.read(mcmeta_files[0])
                        mcmeta_data = json.loads(mcmeta_content.decode('utf-8'))
                        
                        pack_data = mcmeta_data.get('pack', {})
                        pack_info["description"] = pack_data.get('description', pack_info["description"])
                        pack_info["pack_format"] = pack_data.get('pack_format')
                        
                        if pack_info["description"] != "No description":
                            pack_info["name"] = pack_info["description"][:50]  # First 50 chars
                        else:
                            pack_info["name"] = input_path.stem
                            
                    except json.JSONDecodeError:
                        logger.warning("Could not parse pack.mcmeta")
                else:
                    pack_info["name"] = input_path.stem
                    
        except Exception as e:
            logger.error(f"Failed to get pack info: {str(e)}")
        
        return pack_info
    
    def cleanup_temp_directories(self):
        """Clean up temporary directories"""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up {temp_dir}: {str(e)}")
        
        self.temp_dirs.clear()
    
    def create_temp_directory(self, base_name: str = "je2be_temp") -> Path:
        """Create a temporary directory and track it for cleanup"""
        import tempfile
        
        temp_dir = Path(tempfile.mkdtemp(prefix=f"{base_name}_"))
        self.temp_dirs.append(temp_dir)
        logger.debug(f"Created temporary directory: {temp_dir}")
        
        return temp_dir
    
    def copy_other_assets(self, minecraft_dir: Path, bedrock_temp: Path) -> Dict[str, int]:
        """Copy other assets like sounds, models, etc."""
        stats = {
            "sounds": 0,
            "models": 0,
            "lang_files": 0,
            "pack_icon": 0,
            "other": 0
        }
        
        try:
            pack_png_locations = [
                minecraft_dir.parent.parent / "pack.png",  # pack root
                minecraft_dir.parent / "pack.png",        # assets folder
                minecraft_dir / "pack.png"                # minecraft folder
            ]
            
            for pack_png in pack_png_locations:
                if pack_png.exists():
                    pack_icon_dest = bedrock_temp / "pack_icon.png"
                    shutil.copy2(pack_png, pack_icon_dest)
                    stats["pack_icon"] = 1
                    logger.info(f"Copied pack.png as pack_icon.png from {pack_png}")
                    break
            
            java_sounds = minecraft_dir / "sounds"
            bedrock_sounds = bedrock_temp / "sounds"
            
            if java_sounds.exists():
                stats["sounds"] = self._copy_directory_contents(java_sounds, bedrock_sounds)
                logger.info(f"Copied {stats['sounds']} sound files")
            
            java_models = minecraft_dir / "models"
            bedrock_models = bedrock_temp / "models"
            
            if java_models.exists():
                stats["models"] = self._copy_directory_contents(java_models, bedrock_models)
                logger.info(f"Copied {stats['models']} model files")
            
            java_lang = minecraft_dir / "lang"
            if java_lang.exists():
                stats["lang_files"] = len(list(java_lang.glob("*.json")))
                logger.info(f"Found {stats['lang_files']} language files")
            
            other_dirs = ["fonts", "gpu_warnlist.json", "regional_compliancies.json"]
            for other_item in other_dirs:
                java_path = minecraft_dir / other_item
                if java_path.exists():
                    bedrock_path = bedrock_temp / other_item
                    if java_path.is_file():
                        bedrock_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(java_path, bedrock_path)
                        stats["other"] += 1
                    elif java_path.is_dir():
                        stats["other"] += self._copy_directory_contents(java_path, bedrock_path)
            
        except Exception as e:
            logger.warning(f"Failed to copy some assets: {str(e)}")
        
        return stats
    
    def _copy_directory_contents(self, src_dir: Path, dst_dir: Path) -> int:
        """Copy contents of a directory and return file count"""
        file_count = 0
        
        try:
            dst_dir.mkdir(parents=True, exist_ok=True)
            
            for item in src_dir.rglob("*"):
                if item.is_file():
                    relative_path = item.relative_to(src_dir)
                    dst_path = dst_dir / relative_path
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dst_path)
                    file_count += 1
                    
        except Exception as e:
            logger.warning(f"Error copying {src_dir} to {dst_dir}: {str(e)}")
        
        return file_count
