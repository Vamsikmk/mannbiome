#!/usr/bin/env python3
"""
Keystone Species Identifier
Identifies keystone species in the human microbiome based on research consensus
Loads species data from JSON configuration file
"""

import logging
import json
from pathlib import Path
from typing import Optional, List, Set, Dict

logger = logging.getLogger(__name__)


class KeystoneSpeciesIdentifier:
    """
    Identifies and categorizes keystone species in human microbiome
    
    Keystone species are microorganisms that exert a disproportionately large 
    functional or ecological impact relative to their abundance.
    """
    
    # Class-level cache for loaded data
    _data_cache: Optional[Dict] = None
    _species_map: Optional[Dict[str, Dict]] = None
    _genus_map: Optional[Dict[str, str]] = None
    
    @classmethod
    def _load_keystone_data(cls) -> Dict:
        """Load keystone species data from JSON file"""
        if cls._data_cache is not None:
            return cls._data_cache
        
        # Find the JSON file (look in multiple possible locations)
        possible_paths = [
            Path(__file__).parent.parent.parent / 'data' / 'keystone_species_mapping.json',
            Path(__file__).parent.parent / 'data' / 'keystone_species_mapping.json',
            Path(__file__).parent / 'keystone_species_mapping.json',
            Path('data/keystone_species_mapping.json'),
            Path('../data/keystone_species_mapping.json'),
        ]
        
        json_file = None
        for path in possible_paths:
            if path.exists():
                json_file = path
                break
        
        if json_file is None:
            logger.warning("Keystone species JSON file not found, using minimal fallback data")
            # Minimal fallback
            cls._data_cache = {
                "keystone_species": [],
                "genus_mappings": {},
                "domain_mapping": {}
            }
            return cls._data_cache
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                cls._data_cache = json.load(f)
            logger.info(f"Loaded keystone species data from {json_file}")
        except Exception as e:
            logger.error(f"Error loading keystone species JSON: {e}")
            cls._data_cache = {
                "keystone_species": [],
                "genus_mappings": {},
                "domain_mapping": {}
            }
        
        return cls._data_cache
    
    @classmethod
    def _build_species_map(cls) -> Dict[str, Dict]:
        """Build a lookup map of species names to their data"""
        if cls._species_map is not None:
            return cls._species_map
        
        data = cls._load_keystone_data()
        cls._species_map = {}
        
        for species in data.get('keystone_species', []):
            species_name = species.get('species_name', '').lower().strip()
            if species_name:
                cls._species_map[species_name] = species
        
        return cls._species_map
    
    @classmethod
    def _get_genus_mappings(cls) -> Dict[str, str]:
        """Get genus to category mappings"""
        if cls._genus_map is not None:
            return cls._genus_map
        
        data = cls._load_keystone_data()
        cls._genus_map = {k.lower(): v for k, v in data.get('genus_mappings', {}).items()}
        return cls._genus_map
    
    @classmethod
    def is_keystone_species(cls, bacteria_name: str) -> bool:
        """
        Check if a bacteria is a keystone species
        
        Args:
            bacteria_name: Full or partial bacteria name
            
        Returns:
            True if keystone species, False otherwise
        """
        if not bacteria_name:
            return False
        
        bacteria_lower = bacteria_name.lower().strip()
        species_map = cls._build_species_map()
        
        # Try exact match first
        if bacteria_lower in species_map:
            return True
        
        # Try partial match with full name
        for keystone_name in species_map.keys():
            if keystone_name in bacteria_lower or bacteria_lower in keystone_name:
                return True
        
        # Try genus-level match
        bacteria_parts = bacteria_lower.split()
        if bacteria_parts:
            genus = bacteria_parts[0]
            genus_mappings = cls._get_genus_mappings()
            if genus in genus_mappings:
                return True
        
        return False
    
    @classmethod
    def get_keystone_category(cls, bacteria_name: str) -> Optional[str]:
        """
        Get the keystone category for a bacteria
        
        Args:
            bacteria_name: Full or partial bacteria name
            
        Returns:
            Category string or None if not keystone
        """
        if not bacteria_name:
            return None
        
        bacteria_lower = bacteria_name.lower().strip()
        species_map = cls._build_species_map()
        
        # Try exact match first
        if bacteria_lower in species_map:
            return species_map[bacteria_lower].get('category')
        
        # Try partial match
        for keystone_name, data in species_map.items():
            if keystone_name in bacteria_lower or bacteria_lower in keystone_name:
                return data.get('category')
        
        # Try genus-level match
        bacteria_parts = bacteria_lower.split()
        if bacteria_parts:
            genus = bacteria_parts[0]
            genus_mappings = cls._get_genus_mappings()
            if genus in genus_mappings:
                return genus_mappings[genus]
        
        return None
    
    @classmethod
    def get_keystone_domains(cls, bacteria_name: str) -> List[str]:
        """
        Get the health domains associated with a keystone species
        
        Args:
            bacteria_name: Full or partial bacteria name
            
        Returns:
            List of domain names (e.g., ['gut', 'overall'])
        """
        if not bacteria_name:
            return []
        
        bacteria_lower = bacteria_name.lower().strip()
        species_map = cls._build_species_map()
        
        # Try exact match first
        if bacteria_lower in species_map:
            return species_map[bacteria_lower].get('domains', [])
        
        # Try partial match
        for keystone_name, data in species_map.items():
            if keystone_name in bacteria_lower or bacteria_lower in keystone_name:
                return data.get('domains', [])
        
        # For genus-level matches, return overall
        bacteria_parts = bacteria_lower.split()
        if bacteria_parts:
            genus = bacteria_parts[0]
            genus_mappings = cls._get_genus_mappings()
            if genus in genus_mappings:
                return ['overall']
        
        return []
    
    @classmethod
    def get_keystone_info(cls, bacteria_name: str) -> Optional[Dict]:
        """
        Get complete information about a keystone species
        
        Args:
            bacteria_name: Full or partial bacteria name
            
        Returns:
            Dictionary with species information or None
        """
        if not bacteria_name:
            return None
        
        bacteria_lower = bacteria_name.lower().strip()
        species_map = cls._build_species_map()
        
        # Try exact match first
        if bacteria_lower in species_map:
            return species_map[bacteria_lower]
        
        # Try partial match
        for keystone_name, data in species_map.items():
            if keystone_name in bacteria_lower or bacteria_lower in keystone_name:
                return data
        
        return None
    
    @classmethod
    def get_all_keystone_species(cls) -> List[str]:
        """Get list of all keystone species names"""
        species_map = cls._build_species_map()
        return list(species_map.keys())
    
    @classmethod
    def get_keystone_genera(cls) -> List[str]:
        """Get list of all keystone genera"""
        genus_mappings = cls._get_genus_mappings()
        return list(genus_mappings.keys())
    
    @classmethod
    def get_keystone_by_domain(cls, domain: str) -> List[Dict]:
        """
        Get all keystone species for a specific health domain
        
        Args:
            domain: Health domain name (e.g., 'gut', 'liver', 'cognitive')
            
        Returns:
            List of species dictionaries for that domain
        """
        data = cls._load_keystone_data()
        result = []
        
        for species in data.get('keystone_species', []):
            if domain.lower() in [d.lower() for d in species.get('domains', [])]:
                result.append(species)
        
        return result


# Convenience functions for easy import
def is_keystone_species(bacteria_name: str) -> bool:
    """Check if bacteria is a keystone species"""
    return KeystoneSpeciesIdentifier.is_keystone_species(bacteria_name)


def get_keystone_category(bacteria_name: str) -> Optional[str]:
    """Get keystone category for bacteria"""
    return KeystoneSpeciesIdentifier.get_keystone_category(bacteria_name)


if __name__ == "__main__":
    # Test the keystone identifier
    test_bacteria = [
        "Faecalibacterium prausnitzii",
        "Akkermansia muciniphila",
        "Bifidobacterium longum",
        "Lactobacillus acidophilus",
        "Escherichia coli",
        "Bacteroides fragilis",
        "Unknown bacteria"
    ]
    
    print("Keystone Species Identifier Test")
    print("=" * 60)
    for bacteria in test_bacteria:
        is_keystone = is_keystone_species(bacteria)
        category = get_keystone_category(bacteria)
        print(f"{bacteria:40} | Keystone: {is_keystone:5} | Category: {category}")
