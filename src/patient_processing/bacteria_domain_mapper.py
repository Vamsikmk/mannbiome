#!/usr/bin/env python3
"""
Bacteria-Domain Mapper
Extracts bacteria-health domain associations from scientific claims database
Creates mapping table for downstream scoring and classification
"""

import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
import logging
import re
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BacteriaDomainMapper:
    """
    Maps bacteria species to health domains using scientific claims
    """
    
    # Health domain keywords for classification
    # Updated to match existing database domains
    DOMAIN_KEYWORDS = {
        'gut': [
            'gut', 'intestinal', 'colon', 'bowel', 'digestive', 'gastrointestinal',
            'microbiome', 'microbiota', 'dysbiosis', 'gut barrier', 'intestinal permeability',
            'gut inflammation', 'colitis', 'ibs', 'irritable bowel', 'crohn', 'ibd'
        ],
        'cognitive': [
            'cognitive', 'brain', 'mental', 'neurological', 'neurodegenerative',
            'alzheimer', 'parkinson', 'dementia', 'memory', 'depression', 'anxiety',
            'mood', 'neural', 'neuron', 'gut-brain axis', 'neuroinflammation'
        ],
        'heart': [
            'cardiovascular', 'heart', 'cardiac', 'vascular', 'atherosclerosis',
            'blood pressure', 'hypertension', 'cholesterol', 'lipid', 'coronary',
            'arterial', 'stroke', 'tmao', 'endothelial'
        ],
        'liver': [
            'liver', 'hepatic', 'nafld', 'nash', 'fatty liver', 'cirrhosis',
            'hepatitis', 'bile', 'biliary', 'fibrosis', 'steatosis'
        ],
        'overall': [
            'metabolic', 'metabolism', 'diabetes', 'insulin', 'glucose', 'glycemic',
            'obesity', 'adipose', 'weight', 'metabolic syndrome', 'homa-ir',
            'insulin resistance', 'type 2 diabetes', 't2d', 'prediabetes',
            'overall health', 'general health', 'wellbeing', 'vitality'
        ],
        'immune': [
            'immune', 'immunity', 'immunological', 'inflammation', 'inflammatory',
            'cytokine', 'il-6', 'tnf', 'crp', 'autoimmune', 'allergy', 'allergic'
        ],
        'skin': [
            'skin', 'dermatitis', 'eczema', 'psoriasis', 'acne', 'dermal',
            'cutaneous', 'atopic', 'rash', 'skin barrier'
        ],
        'aging': [
            'aging', 'longevity', 'age-related', 'senescence', 'elderly',
            'frailty', 'lifespan', 'healthspan'
        ]
    }
    
    # Bacteria name patterns to extract from claims
    BACTERIA_PATTERNS = [
        r'\b([A-Z][a-z]+(?:bacterium|bacteria|bacter|coccus|bacillus|clostridium|streptococcus))\b',
        r'\b([A-Z][a-z]+ [a-z]+)\b',  # Genus species format
        r'\b(Bifidobacterium|Lactobacillus|Akkermansia|Faecalibacterium|Bacteroides|Prevotella|Ruminococcus|Roseburia|Clostridium|Escherichia)\w*\b'
    ]
    
    def __init__(self, project_root: Path = None):
        """Initialize mapper with project paths"""
        if project_root is None:
            # Auto-detect project root (3 levels up from this file)
            project_root = Path(__file__).resolve().parent.parent.parent
        
        self.project_root = project_root
        self.data_dir = project_root / "data"
        self.raw_data_dir = self.data_dir / "raw"
        self.processed_data_dir = self.data_dir / "processed"
        self.outputs_dir = self.data_dir / "outputs"
        
        # Create output directory for mappings
        self.mapping_output_dir = self.outputs_dir / "bacteria_domain_mapping"
        self.mapping_output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized BacteriaDomainMapper")
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Data directory: {self.data_dir}")
    
    def load_scientific_claims(self) -> pd.DataFrame:
        """Load scientific claims from processed embeddings or raw data"""
        logger.info("Loading scientific claims...")
        
        # Try loading from processed embeddings first
        embeddings_file = self.processed_data_dir / "embeddings_output" / "claims_embeddings.pkl"
        
        if embeddings_file.exists():
            logger.info(f"Loading claims from: {embeddings_file}")
            with open(embeddings_file, 'rb') as f:
                data = pickle.load(f)
                claims_df = data['claims_data']
            logger.info(f"✅ Loaded {len(claims_df)} claims from embeddings pickle")
        else:
            # Fall back to raw Excel file
            raw_claims_file = self.raw_data_dir / "scientific_claims_extracted.xlsx"
            if raw_claims_file.exists():
                logger.info(f"Loading claims from: {raw_claims_file}")
                claims_df = pd.read_excel(raw_claims_file, sheet_name='Extracted_Claims')
                logger.info(f"✅ Loaded {len(claims_df)} claims from Excel")
            else:
                raise FileNotFoundError(
                    f"Could not find claims data at:\n"
                    f"  - {embeddings_file}\n"
                    f"  - {raw_claims_file}\n"
                    f"Please run the embeddings generation first or check file paths."
                )
        
        logger.info(f"Claims columns: {list(claims_df.columns)}")
        return claims_df
    
    def load_bacteria_metadata(self) -> pd.DataFrame:
        """Load bacteria metadata with reference ranges"""
        logger.info("Loading bacteria metadata...")
        
        metadata_file = self.raw_data_dir / "bacteria_metadata.csv"
        if not metadata_file.exists():
            logger.warning(f"Bacteria metadata not found at: {metadata_file}")
            return pd.DataFrame()
        
        bacteria_meta = pd.read_csv(metadata_file)
        logger.info(f"✅ Loaded {len(bacteria_meta)} bacteria species from metadata")
        return bacteria_meta
    
    def extract_bacteria_from_text(self, text: str) -> Set[str]:
        """Extract bacteria names from text using patterns"""
        if pd.isna(text) or not isinstance(text, str):
            return set()
        
        bacteria_names = set()
        text_lower = text.lower()
        
        # Check for common bacteria genera (most important)
        common_genera = [
            'bifidobacterium', 'lactobacillus', 'akkermansia', 'faecalibacterium',
            'bacteroides', 'prevotella', 'ruminococcus', 'roseburia', 'clostridium',
            'escherichia', 'streptococcus', 'enterococcus', 'parabacteroides',
            'alistipes', 'blautia', 'coprococcus', 'dorea', 'eubacterium',
            'collinsella', 'dialister', 'oscillospira', 'sutterella', 'veillonella',
            'methanobrevibacter', 'christensenella', 'bilophila', 'desulfovibrio'
        ]
        
        for genus in common_genera:
            if genus in text_lower:
                # Get the genus with potential species
                genus_pattern = rf'\b({genus}(?:\s+[a-z]+)?)\b'
                matches = re.findall(genus_pattern, text, re.IGNORECASE)
                for match in matches:
                    bacteria_names.add(match.strip().capitalize())
        
        # Only extract if it's a clear bacteria pattern (Genus species format)
        # Avoid extracting general phrases
        specific_pattern = r'\b([A-Z][a-z]{3,}(?:bacterium|bacteria|bacter|coccus|bacillus)(?:\s+[a-z]+)?)\b'
        matches = re.findall(specific_pattern, text)
        for match in matches:
            # Filter out common false positives
            if not any(skip in match.lower() for skip in ['the ', 'and ', 'with ', 'from ', 'that ']):
                bacteria_names.add(match.strip())
        
        return bacteria_names
    
    def classify_claim_domain(self, claim_text: str) -> List[str]:
        """Classify a claim into health domains based on keywords"""
        claim_lower = claim_text.lower()
        matched_domains = []
        
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in claim_lower:
                    matched_domains.append(domain)
                    break  # Only add domain once
        
        return matched_domains
    
    def determine_impact_direction(self, claim_text: str) -> str:
        """Determine if the bacteria impact is positive or negative"""
        claim_lower = claim_text.lower()
        
        # Positive impact indicators (bacteria is good)
        positive_words = [
            'improve', 'enhance', 'benefit', 'promote', 'support',
            'boost', 'strengthen', 'protect', 'produce scfa', 'produce butyrate',
            'beneficial', 'positive', 'healthy', 'optimal', 'restore',
            'reduce inflammation', 'reduce disease', 'prevent', 'protective'
        ]
        
        # Negative impact indicators (bacteria is bad or effect is negative)
        negative_words = [
            'decrease diversity', 'reduce diversity', 'impair', 'damage', 'worsen',
            'harmful', 'pathogenic', 'increase inflammation', 'cause disease',
            'disorder', 'infection', 'dysbiosis', 'negative', 'depleted',
            'associated with disease', 'elevated', 'overgrowth', 'disrupt'
        ]
        
        positive_count = sum(1 for word in positive_words if word in claim_lower)
        negative_count = sum(1 for word in negative_words if word in claim_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def build_bacteria_domain_mapping(self) -> pd.DataFrame:
        """Build complete bacteria-domain mapping from scientific claims"""
        logger.info("\n" + "="*60)
        logger.info("BUILDING BACTERIA-DOMAIN MAPPING")
        logger.info("="*60)
        
        # Load data
        claims_df = self.load_scientific_claims()
        bacteria_meta = self.load_bacteria_metadata()
        
        # Create mapping structure
        bacteria_domain_map = defaultdict(lambda: defaultdict(lambda: {
            'claim_count': 0,
            'positive_impact': 0,
            'negative_impact': 0,
            'neutral_impact': 0,
            'pmids': [],
            'sample_claims': []
        }))
        
        # Process each claim
        logger.info(f"\nProcessing {len(claims_df)} claims...")
        for idx, row in claims_df.iterrows():
            # Create full claim text
            subject = str(row.get('Subject', ''))
            predicate = str(row.get('Predicate', ''))
            obj = str(row.get('Object', ''))
            claim_text = f"{subject} {predicate} {obj}"
            
            # Extract bacteria names
            bacteria_names = self.extract_bacteria_from_text(claim_text)
            
            # Classify domain
            domains = self.classify_claim_domain(claim_text)
            
            # Determine impact
            impact = self.determine_impact_direction(claim_text)
            
            # Get PMID if available
            pmid = row.get('Paper_ID', row.get('PMID', 'unknown'))
            
            # Store mapping
            for bacteria in bacteria_names:
                for domain in domains:
                    bacteria_domain_map[bacteria][domain]['claim_count'] += 1
                    
                    if impact == 'positive':
                        bacteria_domain_map[bacteria][domain]['positive_impact'] += 1
                    elif impact == 'negative':
                        bacteria_domain_map[bacteria][domain]['negative_impact'] += 1
                    else:
                        bacteria_domain_map[bacteria][domain]['neutral_impact'] += 1
                    
                    if pmid not in bacteria_domain_map[bacteria][domain]['pmids']:
                        bacteria_domain_map[bacteria][domain]['pmids'].append(str(pmid))
                    
                    # Store first 3 sample claims
                    if len(bacteria_domain_map[bacteria][domain]['sample_claims']) < 3:
                        bacteria_domain_map[bacteria][domain]['sample_claims'].append(claim_text[:200])
        
        # Convert to DataFrame
        mapping_records = []
        for bacteria, domains in bacteria_domain_map.items():
            for domain, info in domains.items():
                # Calculate impact score (-1 to +1)
                total = info['positive_impact'] + info['negative_impact'] + info['neutral_impact']
                if total > 0:
                    impact_score = (info['positive_impact'] - info['negative_impact']) / total
                else:
                    impact_score = 0
                
                # Determine evidence strength based on claim count
                if info['claim_count'] >= 5:
                    evidence = 'A'
                elif info['claim_count'] >= 3:
                    evidence = 'B'
                else:
                    evidence = 'C'
                
                mapping_records.append({
                    'bacteria_name': bacteria,
                    'domain': domain,
                    'claim_count': info['claim_count'],
                    'positive_claims': info['positive_impact'],
                    'negative_claims': info['negative_impact'],
                    'neutral_claims': info['neutral_impact'],
                    'impact_score': round(impact_score, 3),
                    'evidence_strength': evidence,
                    'pmid_count': len(info['pmids']),
                    'pmids': ';'.join(info['pmids'][:5]),  # Top 5 PMIDs
                    'sample_claim': info['sample_claims'][0] if info['sample_claims'] else ''
                })
        
        mapping_df = pd.DataFrame(mapping_records)
        
        # Sort by bacteria name and impact score
        mapping_df = mapping_df.sort_values(['bacteria_name', 'impact_score'], ascending=[True, False])
        
        logger.info(f"\n✅ Created mapping with {len(mapping_df)} bacteria-domain associations")
        logger.info(f"   Unique bacteria: {mapping_df['bacteria_name'].nunique()}")
        logger.info(f"   Domains covered: {mapping_df['domain'].nunique()}")
        
        return mapping_df
    
    def save_mapping(self, mapping_df: pd.DataFrame):
        """Save mapping to multiple formats"""
        logger.info("\nSaving bacteria-domain mapping...")
        
        # Save as CSV
        csv_file = self.mapping_output_dir / "bacteria_domain_mapping.csv"
        mapping_df.to_csv(csv_file, index=False)
        logger.info(f"✅ Saved CSV: {csv_file}")
        
        # Save as Excel with multiple sheets
        excel_file = self.mapping_output_dir / "bacteria_domain_mapping.xlsx"
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # Main mapping
            mapping_df.to_excel(writer, sheet_name='Bacteria_Domain_Mapping', index=False)
            
            # Summary by domain
            domain_summary = mapping_df.groupby('domain').agg({
                'bacteria_name': 'count',
                'claim_count': 'sum',
                'impact_score': 'mean'
            }).round(3)
            domain_summary.columns = ['Bacteria_Count', 'Total_Claims', 'Avg_Impact_Score']
            domain_summary.to_excel(writer, sheet_name='Domain_Summary')
            
            # Summary by bacteria
            bacteria_summary = mapping_df.groupby('bacteria_name').agg({
                'domain': 'count',
                'claim_count': 'sum',
                'impact_score': 'mean'
            }).round(3)
            bacteria_summary.columns = ['Domain_Count', 'Total_Claims', 'Avg_Impact_Score']
            bacteria_summary = bacteria_summary.sort_values('Domain_Count', ascending=False).head(50)
            bacteria_summary.to_excel(writer, sheet_name='Top_Bacteria')
        
        logger.info(f"✅ Saved Excel: {excel_file}")
        
        # Save as JSON
        json_file = self.mapping_output_dir / "bacteria_domain_mapping.json"
        mapping_dict = mapping_df.to_dict('records')
        with open(json_file, 'w') as f:
            json.dump(mapping_dict, f, indent=2)
        logger.info(f"✅ Saved JSON: {json_file}")
    
    def print_summary(self, mapping_df: pd.DataFrame):
        """Print summary statistics"""
        print("\n" + "="*60)
        print("BACTERIA-DOMAIN MAPPING SUMMARY")
        print("="*60)
        
        print(f"\n📊 Overall Statistics:")
        print(f"   Total associations: {len(mapping_df)}")
        print(f"   Unique bacteria: {mapping_df['bacteria_name'].nunique()}")
        print(f"   Health domains: {mapping_df['domain'].nunique()}")
        
        print(f"\n🏥 Domain Distribution:")
        domain_counts = mapping_df['domain'].value_counts()
        # Sort by standard domain order
        domain_order = ['gut', 'cognitive', 'heart', 'liver', 'overall', 'immune', 'skin', 'aging']
        for domain in domain_order:
            if domain in domain_counts.index:
                count = domain_counts[domain]
                print(f"   {domain}: {count} bacteria")
        # Show any other domains not in the standard list
        for domain, count in domain_counts.items():
            if domain not in domain_order:
                print(f"   {domain}: {count} bacteria")
        
        print(f"\n🦠 Top 10 Most Studied Bacteria (by claim count):")
        top_bacteria = mapping_df.groupby('bacteria_name')['claim_count'].sum().sort_values(ascending=False).head(10)
        for bacteria, count in top_bacteria.items():
            print(f"   {bacteria}: {count} claims")
        
        print(f"\n💪 Evidence Strength Distribution:")
        evidence_counts = mapping_df['evidence_strength'].value_counts()
        for strength in ['A', 'B', 'C']:
            if strength in evidence_counts.index:
                count = evidence_counts[strength]
                print(f"   Grade {strength}: {count} associations")
        
        print(f"\n🎯 Sample Associations (Top Impact):")
        top_associations = mapping_df.nlargest(5, 'impact_score')
        for _, row in top_associations.iterrows():
            print(f"   {row['bacteria_name']} → {row['domain']}")
            print(f"      Impact: {row['impact_score']:+.3f} | Claims: {row['claim_count']} | Evidence: {row['evidence_strength']}")
        
        print("\n" + "="*60)
        print("✅ COMPATIBLE WITH DATABASE DOMAINS:")
        print("   gut, cognitive, heart, liver, overall, immune, skin, aging")
        print("="*60)
    
    def run(self):
        """Execute complete mapping pipeline"""
        logger.info("\n🚀 Starting Bacteria-Domain Mapping Pipeline\n")
        
        try:
            # Build mapping
            mapping_df = self.build_bacteria_domain_mapping()
            
            # Save results
            self.save_mapping(mapping_df)
            
            # Print summary
            self.print_summary(mapping_df)
            
            logger.info("\n✅ MAPPING COMPLETED SUCCESSFULLY!")
            logger.info(f"📁 Output directory: {self.mapping_output_dir}")
            
            return mapping_df
            
        except Exception as e:
            logger.error(f"\n❌ Error during mapping: {e}")
            raise


def main():
    """Main execution"""
    mapper = BacteriaDomainMapper()
    mapping_df = mapper.run()
    return mapping_df


if __name__ == "__main__":
    main()
