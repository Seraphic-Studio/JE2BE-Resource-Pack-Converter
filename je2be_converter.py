"""
JE2BE Resource Pack Converter
Minecraft Java Edition to Bedrock Edition Resource Pack Converter
"""

import os
import json
import sys
import shutil
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

from utils.mapping_loader import MappingLoader
from utils.pack_manager import PackManager
from converters.texture_converter import TextureConverter
from converters.bedrock_generator import BedrockStructureGenerator
from converters.pbr_converter import PBRConverter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('je2be_converter.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

for handler in logging.getLogger().handlers:
    if hasattr(handler, 'stream'):
        handler.stream.reconfigure(line_buffering=True)

logger = logging.getLogger(__name__)

class JE2BEConverter:
    
    def __init__(self, mappings_dir: str = "mappings"):
        self.mappings_dir = mappings_dir
        self.mapping_loader = MappingLoader(mappings_dir)
        self.pack_manager = PackManager()
        self.texture_converter = TextureConverter(mappings_dir)
        self.bedrock_generator = BedrockStructureGenerator()
        self.pbr_converter = PBRConverter()
        
        self.texture_mappings = self.mapping_loader.load_all_mappings()
        logger.info(f"Initialized converter with {len(self.texture_mappings)} texture mappings")
    
    def convert_resource_pack(self, input_path: str, output_path: str, 
                            pack_name: str = None, pack_description: str = None,
                            validate_input: bool = True, enable_pbr: bool = True, 
                            essentials: bool = False, rtxfix: bool = False) -> bool:
        try:
            logger.info(f"Starting conversion of {input_path}")
            
            logger.info("Validating input pack...")
            sys.stdout.flush()
            if validate_input:
                if not self._validate_input_pack(input_path):
                    return False
            
            logger.info("Preparing workspace...")
            sys.stdout.flush()
            temp_dir = self.pack_manager.create_temp_directory("je2be_conversion")
            java_temp = temp_dir / "java_extracted"
            bedrock_temp = temp_dir / "bedrock_build"
            
            java_temp.mkdir(exist_ok=True)
            bedrock_temp.mkdir(exist_ok=True)
            
            logger.info("Extracting Java pack...")
            sys.stdout.flush()
            minecraft_dir = self.pack_manager.extract_java_pack(input_path, java_temp)
            if not minecraft_dir:
                return False
            
            pack_info = self.pack_manager.get_pack_info(input_path)
            if not pack_name:
                pack_name = pack_info.get("name", "Converted Java Resource Pack")
            if not pack_description:
                pack_description = pack_info.get("description", f"Converted from Java Edition")
            
            logger.info(f"Converting pack: {pack_name}")
            logger.info(f"Original pack has {pack_info['texture_count']} textures in categories: {', '.join(pack_info['categories'])}")
            
            logger.info("Creating Bedrock structure...")
            sys.stdout.flush()
            self.bedrock_generator.create_bedrock_structure(bedrock_temp)
            if not self.bedrock_generator.generate_manifest(bedrock_temp, pack_name, pack_description, enable_pbr=enable_pbr):
                logger.error("Failed to generate manifest.json")
                return False
            
            logger.info("Converting textures...")
            sys.stdout.flush()
            java_textures_dir = minecraft_dir / "textures"
            bedrock_textures_dir = bedrock_temp / "textures"
            
            conversion_stats = self.texture_converter.convert_textures(java_textures_dir, bedrock_textures_dir)
            self._log_conversion_stats(conversion_stats)
            
            if enable_pbr:
                logger.info("Processing PBR textures...")
            else:
                logger.info("Skipping PBR conversion...")
            sys.stdout.flush()
            pbr_stats = {}
            if enable_pbr:
                pbr_stats = self.pbr_converter.convert_pbr_textures(java_textures_dir, bedrock_textures_dir, self.texture_mappings)
                self._log_pbr_stats(pbr_stats)
            
            logger.info("Validating missing mappings...")
            sys.stdout.flush()
            self._validate_missing_mappings(java_textures_dir)
            
            logger.info("Copying required files...")
            sys.stdout.flush()
            
            self.bedrock_generator.generate_terrain_texture_json(bedrock_temp, "converted_pack")
            self.bedrock_generator.generate_item_texture_json(bedrock_temp, "converted_pack")
            self.bedrock_generator.generate_blocks_json(bedrock_temp)
            
            java_lang_dir = minecraft_dir / "lang"
            self.bedrock_generator.generate_language_files(bedrock_temp, java_lang_dir)
            
            asset_stats = self.pack_manager.copy_other_assets(minecraft_dir, bedrock_temp)
            self._log_asset_stats(asset_stats)
            
            if essentials:
                logger.info("Copying essentials files...")
                sys.stdout.flush()
                self._copy_essentials(bedrock_temp)
            if rtxfix:
                logger.info("Applying RTX fixes...")
                sys.stdout.flush()
                self._apply_rtxfix(bedrock_temp)
            
            logger.info("Creating .mcpack file...")
            sys.stdout.flush()
            if not self.pack_manager.create_mcpack(bedrock_temp, output_path):
                logger.error("Failed to create .mcpack file")
                return False
            
            self._generate_conversion_report(conversion_stats, asset_stats, pbr_stats, output_path, enable_pbr)
            
            logger.info(f"Conversion completed successfully!")
            logger.info(f"Output saved to: {output_path}")
            if enable_pbr:
                logger.info("PBR textures converted - pack supports RTX/ray tracing features")
            
            return True
                
        except Exception as e:
            logger.error(f"❌ Conversion failed: {str(e)}")
            return False
        finally:
            self.pack_manager.cleanup_temp_directories()
    
    def _validate_input_pack(self, input_path: str) -> bool:
        """Validate the input Java resource pack"""
        validation_result = self.pack_manager.validate_java_pack(input_path)
        
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
            logger.warning("Some textures have missing mappings - check missing_mappings.json for details")
    
    def _log_pbr_stats(self, stats: Dict[str, int]):
        """Log PBR conversion statistics"""
        if not stats:
            return
            
        logger.info(f"PBR conversion completed:")
        logger.info(f"  Specular maps converted: {stats.get('specular_converted', 0)}")
        logger.info(f"  Normal maps converted: {stats.get('normal_converted', 0)}")
        logger.info(f"  MER maps generated: {stats.get('mer_generated', 0)}")
        logger.info(f"  Texture set JSONs created: {stats.get('texture_sets_created', 0)}")
        logger.info(f"  PBR errors: {stats.get('errors', 0)}")
    
    def _log_asset_stats(self, stats: Dict[str, int]):
        """Log asset copying statistics"""
        total = sum(stats.values())
        if total > 0:
            logger.info(f"Other assets copied:")
            for asset_type, count in stats.items():
                if count > 0:
                    logger.info(f"  {asset_type}: {count} files")
    
    def _generate_conversion_report(self, conversion_stats: Dict[str, int], 
                                  asset_stats: Dict[str, int], pbr_stats: Dict[str, int],
                                  output_path: str, pbr_enabled: bool):
        """Generate a detailed conversion report"""
        try:
            report_path = Path(output_path).parent / "conversion_report.txt"
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("=== JE2BE Conversion Report ===\n\n")
                f.write(f"Output pack: {output_path}\n")
                f.write(f"PBR enabled: {pbr_enabled}\n")
                f.write(f"Total mappings available: {len(self.texture_mappings)}\n\n")
                
                f.write("Texture Conversion Statistics:\n")
                for stat_type, count in conversion_stats.items():
                    f.write(f"  {stat_type}: {count}\n")
                
                if pbr_enabled and pbr_stats:
                    f.write("\nPBR Conversion Statistics:\n")
                    for stat_type, count in pbr_stats.items():
                        f.write(f"  {stat_type}: {count}\n")
                
                f.write("\nAsset Copy Statistics:\n")
                for asset_type, count in asset_stats.items():
                    if count > 0:
                        f.write(f"  {asset_type}: {count}\n")
                
                conversion_report = self.texture_converter.get_conversion_report()
                f.write(f"\nDetailed Conversion Info:\n")
                f.write(f"  Files with missing mappings: {conversion_report['missing_mappings']}\n")
                
                if conversion_report['missing_files_list']:
                    f.write("\nTextures without mappings (first 20):\n")
                    for missing_file in conversion_report['missing_files_list'][:20]:
                        f.write(f"  - {missing_file}\n")
                
                f.write(f"\nMapping categories loaded:\n")
                for category in self.mapping_loader.get_categories():
                    category_mappings = self.mapping_loader.get_mapping_by_category(category)
                    f.write(f"  {category}: {len(category_mappings)} mappings\n")
                
                if pbr_enabled:
                    pbr_report = self.pbr_converter.get_conversion_report()
                    f.write(f"\nPBR Support Features:\n")
                    for feature, supported in pbr_report['supported_features'].items():
                        f.write(f"  {feature}: {'Yes' if supported else 'No'}\n")
            
            logger.info(f"Conversion report saved to: {report_path}")
            
        except Exception as e:
            logger.warning(f"Failed to generate conversion report: {str(e)}")
    
    def get_available_mappings_info(self) -> Dict[str, Any]:
        """Get information about available mappings"""
        categories = self.mapping_loader.get_categories()
        mapping_info = {
            "total_mappings": len(self.texture_mappings),
            "categories": {},
            "category_count": len(categories)
        }
        
        for category in categories:
            category_mappings = self.mapping_loader.get_mapping_by_category(category)
            mapping_info["categories"][category] = {
                "count": len(category_mappings),
                "sample_mappings": dict(list(category_mappings.items())[:3])  # First 3 as sample
            }
        
        return mapping_info
    
    def validate_mappings(self) -> Dict[str, Any]:
        """Validate all loaded mappings"""
        return self.mapping_loader.validate_mappings()
    
    def _validate_missing_mappings(self, java_textures_dir: Path) -> Dict[str, bool]:
        """
        Validate missing mappings against the input pack to detect code issues
        
        Args:
            java_textures_dir: Path to Java textures directory
            
        Returns:
            Dict mapping texture names to whether they're actually missing
        """
        try:
            missing_file = Path("missing_mappings.json")
            if not missing_file.exists():
                logger.info("No missing_mappings.json file found")
                return {}
            
            with open(missing_file, 'r') as f:
                missing_mappings = json.load(f)
            
            validation_results = {}
            actually_missing = []
            code_issues = []
            
            for texture_name in missing_mappings:
                possible_paths = [
                    java_textures_dir / f"{texture_name}.png",
                    java_textures_dir / "block" / f"{texture_name}.png",
                    java_textures_dir / "item" / f"{texture_name}.png",
                    java_textures_dir / "entity" / f"{texture_name}.png",
                    java_textures_dir / "models" / f"{texture_name}.png",
                    java_textures_dir / "gui" / f"{texture_name}.png",
                ]
                
                recursive_matches = list(java_textures_dir.rglob(f"{texture_name}.png"))
                
                texture_exists = any(path.exists() for path in possible_paths) or bool(recursive_matches)
                validation_results[texture_name] = texture_exists
                
                if texture_exists:
                    code_issues.append(texture_name)
                    if recursive_matches:
                        found_path = recursive_matches[0].relative_to(java_textures_dir)
                        logger.warning(f"⚠️  Texture '{texture_name}' found at '{found_path}' but not converted - possible mapping issue")
                    else:
                        logger.warning(f"⚠️  Texture '{texture_name}' exists in pack but marked as missing - possible mapping issue")
                else:
                    actually_missing.append(texture_name)
            
            if code_issues:
                logger.warning(f"Found {len(code_issues)} textures that exist but weren't converted:")
                for texture in code_issues[:5]:  # Show first 5
                    logger.warning(f"  - {texture}")
                if len(code_issues) > 5:
                    logger.warning(f"  ... and {len(code_issues) - 5} more")
                logger.warning("These may indicate mapping issues that need to be fixed")
            
            if actually_missing:
                logger.info(f"Confirmed {len(actually_missing)} textures are genuinely missing from the pack")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Failed to validate missing mappings: {e}")
            return {}

    def _copy_essentials(self, bedrock_temp: Path) -> None:
        """Copy files from essentials folder to bedrock blocks folder"""
        essentials_dir = Path("essentials")
        if not essentials_dir.exists():
            logger.warning("Essentials folder not found, skipping...")
            return
        
        blocks_dir = bedrock_temp / "textures" / "blocks"
        blocks_dir.mkdir(parents=True, exist_ok=True)
        
        copied_count = 0
        skipped_count = 0
        
        for file_path in essentials_dir.iterdir():
            if file_path.is_file():
                dest_path = blocks_dir / file_path.name
                
                if dest_path.exists():
                    logger.debug(f"Skipping {file_path.name} - already exists")
                    skipped_count += 1
                else:
                    try:
                        shutil.copy2(file_path, dest_path)
                        logger.debug(f"Copied essential file: {file_path.name}")
                        copied_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to copy {file_path.name}: {str(e)}")
        
        logger.info(f"Essentials: copied {copied_count} files, skipped {skipped_count} existing files")
    
    def _apply_rtxfix(self, bedrock_temp: Path) -> None:
        """Apply RTX fixes by copying/merging files from rtxfix folder"""
        rtxfix_dir = Path("rtxfix")
        if not rtxfix_dir.exists():
            logger.warning("RTXfix folder not found, skipping...")
            return
        
        copied_count = 0
        replaced_count = 0
        
        def copy_recursive(src_dir: Path, dest_dir: Path):
            nonlocal copied_count, replaced_count
            
            for item in src_dir.iterdir():
                dest_item = dest_dir / item.name
                
                if item.is_file():
                    try:
                        dest_item.parent.mkdir(parents=True, exist_ok=True)
                        
                        if dest_item.exists():
                            replaced_count += 1
                            logger.debug(f"Replacing file: {item.relative_to(rtxfix_dir)}")
                        else:
                            copied_count += 1
                            logger.debug(f"Adding file: {item.relative_to(rtxfix_dir)}")
                        
                        shutil.copy2(item, dest_item)
                        
                    except Exception as e:
                        logger.warning(f"Failed to copy {item.relative_to(rtxfix_dir)}: {str(e)}")
                
                elif item.is_dir():
                    copy_recursive(item, dest_item)
        
        copy_recursive(rtxfix_dir, bedrock_temp)
        logger.info(f"RTXfix: added {copied_count} files, replaced {replaced_count} files")

def main():
    parser = argparse.ArgumentParser(
        description="JE2BE Resource Pack Converter - Convert Java Edition resource packs to Bedrock Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s convert pack.zip converted.mcpack
  %(prog)s convert pack.zip converted.mcpack --pack-name "My Pack"
  %(prog)s convert pack.zip converted.mcpack --pack-name "My Pack" --essentials --rtxfix
  %(prog)s info
  %(prog)s validate
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    convert_parser = subparsers.add_parser('convert', help='Convert a resource pack')
    convert_parser.add_argument('input', help='Input Java Edition resource pack (.zip)')
    convert_parser.add_argument('output', help='Output Bedrock Edition pack (.mcpack)')
    convert_parser.add_argument('--pack-name', help='Custom pack name')
    convert_parser.add_argument('--pack-description', help='Custom pack description')
    convert_parser.add_argument('--no-validation', action='store_true', help='Skip input pack validation')
    convert_parser.add_argument('--disable-pbr', action='store_true', help='Disable PBR texture conversion')
    convert_parser.add_argument('--essentials', action='store_true', help='Copy files from essentials folder to blocks folder')
    convert_parser.add_argument('--rtxfix', action='store_true', help='Apply RTX fixes from rtxfix folder')
    
    info_parser = subparsers.add_parser('info', help='Show mapping information')
    
    validate_parser = subparsers.add_parser('validate', help='Validate mappings')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        converter = JE2BEConverter()
        
        if args.command == 'info':
            info = converter.get_available_mappings_info()
            print(f"\n=== JE2BE Converter Mapping Information ===")
            print(f"Total mappings: {info['total_mappings']}")
            print(f"Categories: {info['category_count']}")
            print("\nCategory details:")
            for category, details in info['categories'].items():
                print(f"  {category}: {details['count']} mappings")
                if details['sample_mappings']:
                    print(f"    Sample: {', '.join(list(details['sample_mappings'].keys())[:3])}")
            print()
            return 0
        
        elif args.command == 'validate':
            print("\n=== Validating Mappings ===")
            validation = converter.validate_mappings()
            print(f"Total mappings: {validation['total_mappings']}")
            print(f"Duplicate mappings: {validation['duplicate_count']}")
            if validation['duplicates']:
                print("Duplicates found:")
                for java_texture, bedrock_textures in list(validation['duplicates'].items())[:10]:
                    print(f"  {java_texture} -> {bedrock_textures}")
            print(f"Categories: {', '.join(validation['categories'])}")
            print()
            return 0
            
        elif args.command == 'convert':
            success = converter.convert_resource_pack(
                args.input,
                args.output,
                args.pack_name,
                args.pack_description,
                validate_input=not args.no_validation,
                enable_pbr=not args.disable_pbr,
                essentials=args.essentials,
                rtxfix=args.rtxfix
            )
            
            return 0 if success else 1
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
