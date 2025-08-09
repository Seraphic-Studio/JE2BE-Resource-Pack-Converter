"""
PBR (Physically Based Rendering) Converter Module
Converts Java LabPBR format to Bedrock MER format

Java LabPBR Standard:
- Specular map (_s.png): RGBA
  - Red: Smoothness (perceptual)
  - Green: F0/Reflectance (0-229) or Metal ID (230-255)
  - Blue: Porosity (0-64) or SSS (65-255) on dielectrics
  - Alpha: Emission (0-254)
- Normal map (_n.png): RGBA
  - Red/Green: Normal XY
  - Blue: Ambient Occlusion
  - Alpha: Height map

Bedrock PBR Standard:
- MER map (_mer.png): RGB
  - Red: Metalness (0-255)
  - Green: Emissive (0-255)
  - Blue: Roughness (0-255)
- Normal map (_normal.png): RGB
  - RGB: Normal XYZ (no AO or height)
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageOps
import numpy as np

logger = logging.getLogger(__name__)

class PBRConverter:
    """Converts Java LabPBR textures to Bedrock MER format"""
    
    def __init__(self):
        """Initialize the PBR converter"""
        self.conversion_stats = {
            "specular_converted": 0,
            "normal_converted": 0,
            "mer_generated": 0,
            "texture_sets_created": 0,
            "errors": 0
        }
        
        self.metal_definitions = {
            230: {"name": "iron", "f0": [0.56, 0.57, 0.58]},
            231: {"name": "gold", "f0": [1.00, 0.78, 0.34]},
            232: {"name": "aluminum", "f0": [0.91, 0.92, 0.92]},
            233: {"name": "chrome", "f0": [0.55, 0.56, 0.56]},
            234: {"name": "copper", "f0": [0.95, 0.64, 0.54]},
            235: {"name": "lead", "f0": [0.63, 0.63, 0.66]},
            236: {"name": "platinum", "f0": [0.67, 0.69, 0.66]},
            237: {"name": "silver", "f0": [0.95, 0.93, 0.88]}
        }
    
    def detect_pbr_textures(self, texture_dir: Path) -> Dict[str, Dict[str, Path]]:
        """
        Detect PBR texture sets in a directory
        
        Args:
            texture_dir: Directory containing textures
            
        Returns:
            Dict mapping base texture names to their PBR components
        """
        pbr_sets = {}
        
        texture_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.tga']:
            texture_files.extend(texture_dir.glob(f"**/{ext}"))
        
        for texture_file in texture_files:
            name = texture_file.stem
            
            if name.endswith('_s'):
                base_name = name[:-2]
                if base_name not in pbr_sets:
                    pbr_sets[base_name] = {}
                pbr_sets[base_name]['specular'] = texture_file
            
            elif name.endswith('_n'):
                base_name = name[:-2]
                if base_name not in pbr_sets:
                    pbr_sets[base_name] = {}
                pbr_sets[base_name]['normal'] = texture_file
            
            elif not any(name.endswith(suffix) for suffix in ['_s', '_n', '_e', '_r', '_m', '_mer', '_normal']):
                if name not in pbr_sets:
                    pbr_sets[name] = {}
                pbr_sets[name]['diffuse'] = texture_file
        
        pbr_sets = {k: v for k, v in pbr_sets.items() 
                   if 'specular' in v or 'normal' in v}
        
        logger.info(f"Detected {len(pbr_sets)} PBR texture sets")
        for set_name, components in pbr_sets.items():
            logger.debug(f"  {set_name}: {list(components.keys())}")
        
        return pbr_sets
    
    def convert_specular_to_mer(self, specular_path: Path, mer_path: Path) -> bool:
        """
        Convert Java specular map to Bedrock MER format
        
        Args:
            specular_path: Path to Java specular map
            mer_path: Output path for MER map
            
        Returns:
            bool: True if conversion successful
        """
        try:
            with Image.open(specular_path) as specular_img:
                if specular_img.mode != 'RGBA':
                    specular_img = specular_img.convert('RGBA')
                
                spec_array = np.array(specular_img)
                
                smoothness = spec_array[:, :, 0]  # Red channel
                f0_metal = spec_array[:, :, 1]    # Green channel
                porosity_sss = spec_array[:, :, 2]  # Blue channel
                emission = spec_array[:, :, 3]    # Alpha channel
                
                mer_array = np.zeros((spec_array.shape[0], spec_array.shape[1], 3), dtype=np.uint8)
                
                smoothness_normalized = smoothness / 255.0
                roughness_linear = (1.0 - smoothness_normalized) ** 2
                roughness_bedrock = (roughness_linear * 255).astype(np.uint8)
                mer_array[:, :, 2] = roughness_bedrock  # Blue = Roughness
                
                metalness = np.zeros_like(f0_metal, dtype=np.uint8)
                
                metal_mask = f0_metal >= 230
                metalness[metal_mask] = 255  # Full metalness for predefined metals
                
                f0_mask = f0_metal < 230
                metallic_threshold = 10
                metalness[f0_mask & (f0_metal > metallic_threshold)] = f0_metal[f0_mask & (f0_metal > metallic_threshold)]
                
                mer_array[:, :, 0] = metalness  # Red = Metalness
                
                emission_mask = emission < 255
                emission_bedrock = np.zeros_like(emission, dtype=np.uint8)
                emission_bedrock[emission_mask] = emission[emission_mask]
                mer_array[:, :, 1] = emission_bedrock  # Green = Emissive
                
                mer_img = Image.fromarray(mer_array, 'RGB')
                mer_path.parent.mkdir(parents=True, exist_ok=True)
                mer_img.save(mer_path)
                
                self.conversion_stats["specular_converted"] += 1
                self.conversion_stats["mer_generated"] += 1
                
                logger.debug(f"Converted specular to MER: {specular_path.name} -> {mer_path.name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to convert specular map {specular_path}: {str(e)}")
            self.conversion_stats["errors"] += 1
            return False
    
    def convert_normal_map(self, normal_path: Path, output_path: Path) -> bool:
        """
        Convert Java normal map to Bedrock format
        
        Args:
            normal_path: Path to Java normal map
            output_path: Output path for Bedrock normal map
            
        Returns:
            bool: True if conversion successful
        """
        try:
            with Image.open(normal_path) as normal_img:
                if normal_img.mode != 'RGBA':
                    normal_img = normal_img.convert('RGBA')
                
                normal_array = np.array(normal_img)
                
                normal_x = normal_array[:, :, 0]  # Red
                normal_y = normal_array[:, :, 1]  # Green
                nx_normalized = (normal_x / 255.0) * 2.0 - 1.0
                ny_normalized = (normal_y / 255.0) * 2.0 - 1.0
                
                nz_squared = 1.0 - (nx_normalized**2 + ny_normalized**2)
                nz_squared = np.maximum(0.0, nz_squared)  # Clamp to prevent negative values
                nz_normalized = np.sqrt(nz_squared)
                
                normal_z = ((nz_normalized + 1.0) / 2.0 * 255).astype(np.uint8)
                
                bedrock_normal = np.zeros((normal_array.shape[0], normal_array.shape[1], 3), dtype=np.uint8)
                bedrock_normal[:, :, 0] = normal_x  # Red = X
                bedrock_normal[:, :, 1] = normal_y  # Green = Y
                bedrock_normal[:, :, 2] = normal_z  # Blue = Z (reconstructed)
                
                normal_img_out = Image.fromarray(bedrock_normal, 'RGB')
                output_path.parent.mkdir(parents=True, exist_ok=True)
                normal_img_out.save(output_path)
                
                self.conversion_stats["normal_converted"] += 1
                
                logger.debug(f"Converted normal map: {normal_path.name} -> {output_path.name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to convert normal map {normal_path}: {str(e)}")
            self.conversion_stats["errors"] += 1
            return False
    
    def create_texture_set_json(self, texture_name: str, output_dir: Path, 
                               has_mer: bool = False, has_normal: bool = False) -> bool:
        """
        Create a texture set JSON file for Bedrock PBR
        
        Args:
            texture_name: Base name of the texture
            output_dir: Output directory for the JSON file (should be blocks folder)
            has_mer: Whether MER map exists
            has_normal: Whether normal map exists
            
        Returns:
            bool: True if creation successful
        """
        try:
            texture_set = {
                "format_version": "1.16.100",
                "minecraft:texture_set": {
                    "color": texture_name
                }
            }
            
            if has_mer:
                texture_set["minecraft:texture_set"]["metalness_emissive_roughness"] = f"{texture_name}_mer"
            
            if has_normal:
                texture_set["minecraft:texture_set"]["normal"] = f"{texture_name}_normal"
            
            if not output_dir.name == "blocks":
                blocks_dir = output_dir.parent.parent / "blocks"  # Go up to textures then down to blocks
                blocks_dir.mkdir(parents=True, exist_ok=True)
                json_path = blocks_dir / f"{texture_name}.texture_set.json"
            else:
                json_path = output_dir / f"{texture_name}.texture_set.json"
            
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(texture_set, f, indent=2)
            
            self.conversion_stats["texture_sets_created"] += 1
            
            logger.debug(f"Created texture set JSON: {json_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create texture set JSON for {texture_name}: {str(e)}")
            self.conversion_stats["errors"] += 1
            return False
    
    def convert_pbr_textures(self, java_textures_dir: Path, bedrock_textures_dir: Path, 
                           texture_mappings: Optional[Dict[str, str]] = None) -> Dict[str, int]:
        """
        Convert all PBR textures from Java to Bedrock format
        Only creates files for textures that exist and have mappings
        
        Args:
            java_textures_dir: Java textures directory
            bedrock_textures_dir: Bedrock textures output directory
            texture_mappings: Optional dict of Java->Bedrock texture mappings
            
        Returns:
            Dict with conversion statistics
        """
        logger.info("Starting PBR texture conversion...")
        
        pbr_sets = self.detect_pbr_textures(java_textures_dir)
        
        if not pbr_sets:
            logger.info("No PBR textures detected")
            return self.conversion_stats
        
        logger.info(f"Converting {len(pbr_sets)} PBR texture sets...")
        
        for set_name, components in pbr_sets.items():
            logger.debug(f"Processing PBR set: {set_name}")
            
            diffuse_name = f"{set_name}.png"
            if texture_mappings and diffuse_name in texture_mappings:
                bedrock_diffuse_name = texture_mappings[diffuse_name]
                bedrock_base_name = bedrock_diffuse_name.replace('.png', '').replace('.tga', '')
            else:
                bedrock_base_name = set_name
            
            has_mer = False
            has_normal = False
            
            if 'specular' in components:
                specular_path = components['specular']
                
                mer_filename = f"{bedrock_base_name}_mer.png"
                mer_path = bedrock_textures_dir / "blocks" / mer_filename
                
                if self.convert_specular_to_mer(specular_path, mer_path):
                    has_mer = True
            
            if 'normal' in components:
                normal_path = components['normal']
                
                normal_filename = f"{bedrock_base_name}_normal.png"
                normal_out_path = bedrock_textures_dir / "blocks" / normal_filename
                
                if self.convert_normal_map(normal_path, normal_out_path):
                    has_normal = True
            
            if has_mer or has_normal:
                blocks_dir = bedrock_textures_dir / "blocks"
                self.create_texture_set_json(bedrock_base_name, blocks_dir, has_mer, has_normal)
        
        logger.info(f"PBR conversion completed:")
        logger.info(f"  Specular maps converted: {self.conversion_stats['specular_converted']}")
        logger.info(f"  Normal maps converted: {self.conversion_stats['normal_converted']}")
        logger.info(f"  MER maps generated: {self.conversion_stats['mer_generated']}")
        logger.info(f"  Texture set JSONs created: {self.conversion_stats['texture_sets_created']}")
        logger.info(f"  Errors: {self.conversion_stats['errors']}")
        
        return self.conversion_stats
    
    def generate_mer_from_individual_maps(self, metallic_path: Optional[Path] = None,
                                        emissive_path: Optional[Path] = None,
                                        roughness_path: Optional[Path] = None,
                                        output_path: Path = None) -> bool:
        """
        Generate MER map from individual M, E, R maps (if available)
        
        Args:
            metallic_path: Path to metallic map
            emissive_path: Path to emissive map  
            roughness_path: Path to roughness map
            output_path: Output path for MER map
            
        Returns:
            bool: True if generation successful
        """
        try:
            reference_img = None
            for path in [metallic_path, emissive_path, roughness_path]:
                if path and path.exists():
                    reference_img = Image.open(path)
                    break
            
            if not reference_img:
                logger.warning("No reference maps found for MER generation")
                return False
            
            width, height = reference_img.size
            mer_array = np.zeros((height, width, 3), dtype=np.uint8)
            
            if metallic_path and metallic_path.exists():
                with Image.open(metallic_path) as metallic_img:
                    if metallic_img.mode != 'L':
                        metallic_img = ImageOps.grayscale(metallic_img)
                    metallic_array = np.array(metallic_img)
                    mer_array[:, :, 0] = metallic_array
            
            if emissive_path and emissive_path.exists():
                with Image.open(emissive_path) as emissive_img:
                    if emissive_img.mode != 'L':
                        emissive_img = ImageOps.grayscale(emissive_img)
                    emissive_array = np.array(emissive_img)
                    mer_array[:, :, 1] = emissive_array
            
            if roughness_path and roughness_path.exists():
                with Image.open(roughness_path) as roughness_img:
                    if roughness_img.mode != 'L':
                        roughness_img = ImageOps.grayscale(roughness_img)
                    roughness_array = np.array(roughness_img)
                    mer_array[:, :, 2] = roughness_array
            
            mer_img = Image.fromarray(mer_array, 'RGB')
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mer_img.save(output_path)
            
            logger.debug(f"Generated MER map: {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate MER map: {str(e)}")
            return False
    
    def get_conversion_report(self) -> Dict[str, any]:
        """Get detailed conversion report"""
        return {
            "pbr_conversion_stats": self.conversion_stats,
            "metal_definitions_available": len(self.metal_definitions),
            "supported_features": {
                "labpbr_specular_conversion": True,
                "labpbr_normal_conversion": True,
                "mer_generation": True,
                "texture_set_json_creation": True,
                "metal_id_support": True,
                "emission_conversion": True,
                "roughness_conversion": True
            }
        }
    
    def reset_stats(self):
        """Reset conversion statistics"""
        self.conversion_stats = {
            "specular_converted": 0,
            "normal_converted": 0,
            "mer_generated": 0,
            "texture_sets_created": 0,
            "errors": 0
        }
