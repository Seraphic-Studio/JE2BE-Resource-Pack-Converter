"""
Bedrock pack manager module for BE2JE converter
Handles .mcpack file operations and extraction
"""

import os
import json
import zipfile
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

class BedrockPackManager:
    """Manages Bedrock resource pack file operations"""
    
    def __init__(self):
        self.temp_dirs: List[Path] = []
    
    def extract_bedrock_pack(self, input_path: str, extract_dir: Path) -> Optional[Path]:
        """
        Extract Bedrock Edition resource pack (.mcpack)
        
        Returns:
            Path to the extracted pack root or None if extraction fails
        """
        try:
            input_path = Path(input_path)
            
            if not input_path.exists():
                logger.error(f"Input file does not exist: {input_path}")
                return None
            
            if input_path.suffix.lower() not in ['.mcpack', '.zip']:
                logger.error("Input file must be a .mcpack or .zip file")
                return None
            
            logger.info(f"Extracting Bedrock resource pack: {input_path.name}")
            
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Bedrock packs have manifest.json at the root
            if not (extract_dir / "manifest.json").exists():
                logger.error("Could not find manifest.json in the Bedrock resource pack")
                return None
            
            logger.info(f"Found Bedrock pack root: {extract_dir}")
            return extract_dir
            
        except zipfile.BadZipFile:
            logger.error(f"Invalid zip/mcpack file: {input_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to extract Bedrock resource pack: {str(e)}")
            return None
    
    def read_manifest(self, bedrock_root: Path) -> Optional[Dict[str, Any]]:
        """Read and parse the manifest.json file"""
        try:
            manifest_path = bedrock_root / "manifest.json"
            
            if not manifest_path.exists():
                logger.error("manifest.json not found")
                return None
            
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            logger.info("Successfully read manifest.json")
            return manifest
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in manifest.json: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to read manifest.json: {str(e)}")
            return None
    
    def validate_bedrock_pack(self, input_path: str) -> Dict[str, Any]:
        """Validate Bedrock Edition resource pack structure"""
        validation_result = {
            "valid": False,
            "has_manifest": False,
            "has_textures": False,
            "texture_categories": [],
            "errors": []
        }
        
        try:
            input_path = Path(input_path)
            
            if not input_path.exists():
                validation_result["errors"].append("File does not exist")
                return validation_result
            
            if input_path.suffix.lower() not in ['.mcpack', '.zip']:
                validation_result["errors"].append("File is not a .mcpack or .zip file")
                return validation_result
            
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                # Check for manifest.json
                if any('manifest.json' in f for f in file_list):
                    validation_result["has_manifest"] = True
                
                # Check for textures
                texture_paths = [f for f in file_list if 'textures/' in f and f.endswith('.png')]
                if texture_paths:
                    validation_result["has_textures"] = True
                
                # Get texture categories
                categories = set()
                for texture_path in texture_paths:
                    parts = texture_path.split('/')
                    if len(parts) >= 2 and parts[0] == 'textures':
                        categories.add(parts[1])  # blocks, items, entity, etc.
                
                validation_result["texture_categories"] = sorted(list(categories))
            
            validation_result["valid"] = (
                validation_result["has_manifest"] and 
                validation_result["has_textures"]
            )
            
            if not validation_result["valid"]:
                if not validation_result["has_manifest"]:
                    validation_result["errors"].append("No manifest.json found")
                if not validation_result["has_textures"]:
                    validation_result["errors"].append("No texture files found")
            
        except zipfile.BadZipFile:
            validation_result["errors"].append("Invalid or corrupted zip/mcpack file")
        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def get_pack_info(self, input_path: str) -> Dict[str, Any]:
        """Get information about a Bedrock Edition resource pack"""
        pack_info = {
            "name": "Unknown Pack",
            "description": "No description",
            "version": None,
            "file_size": 0,
            "texture_count": 0,
            "categories": []
        }
        
        try:
            input_path = Path(input_path)
            pack_info["file_size"] = input_path.stat().st_size
            
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                # Count textures
                texture_files = [f for f in file_list if f.endswith('.png')]
                pack_info["texture_count"] = len(texture_files)
                
                # Get categories
                categories = set()
                for texture_path in texture_files:
                    if 'textures/' in texture_path:
                        parts = texture_path.split('/')
                        texture_idx = next(i for i, part in enumerate(parts) if part == 'textures')
                        if texture_idx + 1 < len(parts):
                            categories.add(parts[texture_idx + 1])
                
                pack_info["categories"] = sorted(list(categories))
                
                # Read manifest
                manifest_files = [f for f in file_list if f.endswith('manifest.json')]
                if manifest_files:
                    try:
                        manifest_content = zip_ref.read(manifest_files[0])
                        manifest_data = json.loads(manifest_content.decode('utf-8'))
                        
                        header = manifest_data.get('header', {})
                        pack_info["name"] = header.get('name', pack_info["name"])
                        pack_info["description"] = header.get('description', pack_info["description"])
                        pack_info["version"] = header.get('version')
                        
                    except json.JSONDecodeError:
                        logger.warning("Could not parse manifest.json")
                else:
                    pack_info["name"] = input_path.stem
                    
        except Exception as e:
            logger.error(f"Failed to get pack info: {str(e)}")
        
        return pack_info
    
    def create_zip(self, java_temp: Path, output_path: str) -> bool:
        """Create the final Java Edition .zip file"""
        try:
            output_path = Path(output_path)
            
            if output_path.suffix.lower() != '.zip':
                output_path = output_path.with_suffix('.zip')
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Creating .zip file: {output_path}")
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                file_count = 0
                for file_path in java_temp.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(java_temp)
                        zipf.write(file_path, arcname)
                        file_count += 1
                        
                        if file_count % 100 == 0:
                            logger.debug(f"Added {file_count} files to .zip")
            
            file_size = output_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            logger.info(f"Created .zip file: {output_path}")
            logger.info(f"Pack size: {size_mb:.2f} MB ({file_count} files)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create .zip file: {str(e)}")
            return False
    
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
    
    def create_temp_directory(self, base_name: str = "be2je_temp") -> Path:
        """Create a temporary directory and track it for cleanup"""
        import tempfile
        
        temp_dir = Path(tempfile.mkdtemp(prefix=f"{base_name}_"))
        self.temp_dirs.append(temp_dir)
        logger.debug(f"Created temporary directory: {temp_dir}")
        
        return temp_dir
