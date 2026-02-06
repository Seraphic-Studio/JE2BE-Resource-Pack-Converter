"""
BE2JE Resource Pack Converter
Minecraft Bedrock Edition to Java Edition Resource Pack Converter
"""

import os
import json
import sys
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from utils.bedrock_pack_manager import BedrockPackManager
from converters.reverse_texture_converter import ReverseTextureConverter
from converters.java_structure_generator import JavaStructureGenerator

logger = logging.getLogger(__name__)

class BE2JEConverter:
    
    def __init__(self, mappings_dir: str = "mappings"):
        self.mappings_dir = mappings_dir
        self.pack_manager = BedrockPackManager()
        self.texture_converter = ReverseTextureConverter(mappings_dir)
        self.java_generator = JavaStructureGenerator()
        
        logger.info(f"Initialized reverse converter with mappings from {mappings_dir}")
    
    def convert_resource_pack(self, input_path: str, output_path: str, 
                            pack_name: str = None, pack_description: str = None,
                            validate_input: bool = True) -> bool:
        """
        Convert Bedrock Edition resource pack to Java Edition format
        
        Args:
            input_path: Path to input Bedrock pack (.mcpack or .zip)
            output_path: Path to output Java pack (.zip)
            pack_name: Optional custom pack name
            pack_description: Optional custom pack description
            validate_input: Whether to validate the input pack
        
        Returns:
            True if conversion successful, False otherwise
        """
        try:
            logger.info(f"Starting reverse conversion of {input_path}")
            
            if validate_input:
                logger.info("Validating input pack...")
                sys.stdout.flush()
                if not self._validate_input_pack(input_path):
                    return False
            
            logger.info("Preparing workspace...")
            sys.stdout.flush()
            temp_dir = self.pack_manager.create_temp_directory("be2je_conversion")
            bedrock_temp = temp_dir / "bedrock_extracted"
            java_temp = temp_dir / "java_build"
            
            bedrock_temp.mkdir(exist_ok=True)
            java_temp.mkdir(exist_ok=True)
            
            logger.info("Extracting Bedrock pack...")
            sys.stdout.flush()
            bedrock_root = self.pack_manager.extract_bedrock_pack(input_path, bedrock_temp)
            if not bedrock_root:
                return False
            
            # Read manifest to get pack info
            manifest = self.pack_manager.read_manifest(bedrock_root)
            if manifest:
                pack_info = self.java_generator.convert_manifest_to_mcmeta(manifest)
                if not pack_name:
                    pack_name = pack_info.get("name", "Converted Bedrock Pack")
                if not pack_description:
                    pack_description = pack_info.get("description", "Converted from Bedrock Edition")
            else:
                pack_info = self.pack_manager.get_pack_info(input_path)
                if not pack_name:
                    pack_name = pack_info.get("name", "Converted Bedrock Pack")
                if not pack_description:
                    pack_description = pack_info.get("description", "Converted from Bedrock Edition")
            
            logger.info(f"Converting pack: {pack_name}")
            logger.info(f"Original pack has {pack_info.get('texture_count', 0)} textures")
            
            logger.info("Creating Java Edition structure...")
            sys.stdout.flush()
            self.java_generator.create_java_structure(java_temp)
            if not self.java_generator.generate_pack_mcmeta(java_temp, pack_name, pack_description):
                logger.error("Failed to generate pack.mcmeta")
                return False
            
            logger.info("Converting textures...")
            sys.stdout.flush()
            bedrock_textures_dir = bedrock_root / "textures"
            java_textures_dir = java_temp / "assets" / "minecraft" / "textures"
            
            conversion_stats = self.texture_converter.convert_textures(bedrock_textures_dir, java_textures_dir)
            self._log_conversion_stats(conversion_stats)
            
            logger.info("Handling language files...")
            sys.stdout.flush()
            bedrock_texts_dir = bedrock_root / "texts"
            self.java_generator.generate_language_files(java_temp, bedrock_texts_dir)
            
            logger.info("Copying additional assets...")
            sys.stdout.flush()
            asset_stats = self._copy_other_assets(bedrock_root, java_temp)
            self._log_asset_stats(asset_stats)
            
            # Handle pack icon
            pack_icon = bedrock_root / "pack_icon.png"
            if pack_icon.exists():
                self.java_generator.generate_pack_png(java_temp, pack_icon)
            
            # Stubs for format differences
            logger.info("Processing format differences (stub)...")
            sys.stdout.flush()
            self.java_generator.stub_model_conversion(bedrock_root, java_temp)
            self.java_generator.stub_translation_handling(bedrock_root, java_temp)
            
            logger.info("Creating .zip file...")
            sys.stdout.flush()
            if not self.pack_manager.create_zip(java_temp, output_path):
                logger.error("Failed to create .zip file")
                return False
            
            self._generate_conversion_report(conversion_stats, asset_stats, output_path)
            
            logger.info(f"Reverse conversion completed successfully!")
            logger.info(f"Output saved to: {output_path}")
            
            return True
                
        except Exception as e:
            logger.error(f"❌ Conversion failed: {str(e)}")
            return False
        finally:
            self.pack_manager.cleanup_temp_directories()
    
    def _validate_input_pack(self, input_path: str) -> bool:
        """Validate the input Bedrock resource pack"""
        validation_result = self.pack_manager.validate_bedrock_pack(input_path)
        
        if not validation_result["valid"]:
            logger.error("Input pack validation failed:")
            for error in validation_result["errors"]:
                logger.error(f"  - {error}")
            return False
        
        logger.info("Input pack validation passed")
        logger.info(f"Pack has {len(validation_result['texture_categories'])} texture categories: {', '.join(validation_result['texture_categories'])}")
        
        return True
    
    def _log_conversion_stats(self, stats: Dict[str, int]):
        """Log texture conversion statistics"""
        total = sum(stats.values())
        logger.info(f"Texture conversion completed:")
        logger.info(f"  Total files processed: {total}")
        logger.info(f"  Successfully converted: {stats.get('converted', 0)}")
        logger.info(f"  Skipped (already exist): {stats.get('skipped', 0)}")
        logger.info(f"  Missing mappings: {stats.get('missing', 0)}")
        logger.info(f"  Errors: {stats.get('errors', 0)}")
        
        if stats.get('missing', 0) > 0:
            logger.warning("Some textures have missing reverse mappings - check missing_reverse_mappings.json for details")
    
    def _log_asset_stats(self, stats: Dict[str, int]):
        """Log asset copying statistics"""
        total = sum(stats.values())
        if total > 0:
            logger.info(f"Other assets copied:")
            for asset_type, count in stats.items():
                if count > 0:
                    logger.info(f"  {asset_type}: {count} files")
    
    def _copy_other_assets(self, bedrock_root: Path, java_temp: Path) -> Dict[str, int]:
        """Copy other assets like sounds, models, etc."""
        stats = {
            "sounds": 0,
            "models": 0,
            "other": 0
        }
        
        try:
            # Copy sounds
            bedrock_sounds = bedrock_root / "sounds"
            java_sounds = java_temp / "assets" / "minecraft" / "sounds"
            
            if bedrock_sounds.exists():
                stats["sounds"] = self._copy_directory_contents(bedrock_sounds, java_sounds)
                logger.info(f"Copied {stats['sounds']} sound files")
            
            # Copy models (though format may differ)
            bedrock_models = bedrock_root / "models"
            java_models = java_temp / "assets" / "minecraft" / "models"
            
            if bedrock_models.exists():
                stats["models"] = self._copy_directory_contents(bedrock_models, java_models)
                logger.info(f"Copied {stats['models']} model files (may need manual adjustment)")
            
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
    
    def _generate_conversion_report(self, conversion_stats: Dict[str, int], 
                                   asset_stats: Dict[str, int], output_path: str):
        """Generate a detailed conversion report"""
        try:
            report_path = Path(output_path).parent / "reverse_conversion_report.txt"
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("=== BE2JE Reverse Conversion Report ===\n\n")
                f.write(f"Output pack: {output_path}\n\n")
                
                f.write("Texture Conversion Statistics:\n")
                for stat_type, count in conversion_stats.items():
                    f.write(f"  {stat_type}: {count}\n")
                
                f.write("\nAsset Copy Statistics:\n")
                for asset_type, count in asset_stats.items():
                    if count > 0:
                        f.write(f"  {asset_type}: {count}\n")
                
                conversion_report = self.texture_converter.get_conversion_report()
                f.write(f"\nDetailed Conversion Info:\n")
                f.write(f"  Files with missing reverse mappings: {conversion_report['missing_mappings']}\n")
                
                if conversion_report['missing_files_list']:
                    f.write("\nTextures without reverse mappings (first 20):\n")
                    for missing_file in conversion_report['missing_files_list'][:20]:
                        f.write(f"  - {missing_file}\n")
            
            logger.info(f"Reverse conversion report saved to: {report_path}")
            
        except Exception as e:
            logger.warning(f"Failed to generate conversion report: {str(e)}")
