"""
Bacteria Scoring Engine - Step 3
Maps patient bacteria to health domains and calculates impact scores.

Scoring Logic:
1. Load bacteria-domain mapping (from database or CSV)
2. Load patient bacteria abundance (from Step 2)
3. For each patient bacteria:
   - Find matching domain associations
   - Calculate impact score based on:
     * Abundance level (higher = more impact)
     * Evidence strength (A > B > C)
     * Impact direction (positive vs negative)
4. Aggregate scores by health domain
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dotenv import load_dotenv

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logging.warning("psycopg2 not available. Install with: pip install psycopg2-binary")


class BacteriaScorer:
    """
    Scores patient microbiome data based on bacteria-domain associations.
    
    Features:
    - Maps bacteria to health domains using scientific evidence
    - Calculates impact scores based on abundance and evidence quality
    - Handles partial name matching (genus/species flexibility)
    - Aggregates scores by health domain
    - Provides confidence metrics
    """
    
    # Impact weights for evidence strength
    EVIDENCE_WEIGHTS = {
        'A': 1.0,   # Strong evidence
        'B': 0.7,   # Medium evidence
        'C': 0.5    # Preliminary evidence
    }
    
    # Abundance thresholds for impact scaling
    ABUNDANCE_THRESHOLDS = {
        'very_high': 10.0,    # >10% relative abundance
        'high': 5.0,          # 5-10%
        'medium': 1.0,        # 1-5%
        'low': 0.1,           # 0.1-1%
        'very_low': 0.0       # <0.1%
    }
    
    def __init__(self, 
                 mapping_file: Optional[str] = None,
                 use_database: bool = True,
                 project_root: Optional[Path] = None):
        """
        Initialize the bacteria scorer.
        
        Args:
            mapping_file: Path to bacteria-domain mapping CSV (fallback if database not available)
            use_database: If True, load from database; if False, use CSV file
            project_root: Root directory of the project
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        
        self.project_root = Path(project_root)
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Load environment variables
        load_dotenv(self.project_root / '.env')
        
        self.bacteria_mapping = None
        self.use_database = use_database and PSYCOPG2_AVAILABLE
        
        self.logger.info("Initialized BacteriaScorer")
        self.logger.info(f"Project root: {self.project_root}")
        
        # Try to load mapping from database first
        if self.use_database:
            self._load_mapping_from_database()
        
        # Fallback to CSV if database fails or not requested
        if self.bacteria_mapping is None or self.bacteria_mapping.empty:
            if mapping_file is None:
                mapping_file = self.project_root / 'data' / 'outputs' / 'bacteria_domain_mapping' / 'bacteria_domain_mapping.csv'
            
            self.mapping_file = Path(mapping_file)
            if self.mapping_file.exists():
                self._load_mapping_from_csv()
            else:
                self.logger.warning(f"Mapping file not found: {self.mapping_file}")
                self.logger.warning("Run bacteria_domain_mapper.py first to generate mapping")
    
    def _load_mapping_from_database(self):
        """Load bacteria-domain mapping from PostgreSQL database."""
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT', 5432),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD')
            )
            
            query = """
                SELECT 
                    bacteria_name,
                    domain,
                    association_type,
                    beneficial_count,
                    harmful_count,
                    total_associations,
                    confidence_score,
                    CASE 
                        WHEN confidence_score >= 0.75 THEN 'A'
                        WHEN confidence_score >= 0.50 THEN 'B'
                        ELSE 'C'
                    END as evidence_strength
                FROM vectordb.bacteria_domain_associations
                WHERE association_type IN ('beneficial', 'harmful')
                ORDER BY bacteria_name, domain
            """
            
            self.bacteria_mapping = pd.read_sql(query, conn)
            conn.close()
            
            # Convert association_type to impact_score
            # beneficial = positive impact, harmful = negative impact
            self.bacteria_mapping['impact_score'] = self.bacteria_mapping['association_type'].map({
                'beneficial': 1.0,
                'harmful': -1.0
            }).fillna(0.0)
            
            # Rename for consistency
            self.bacteria_mapping['claim_count'] = self.bacteria_mapping['total_associations']
            
            self.logger.info(f"✅ Loaded mapping from database with {len(self.bacteria_mapping)} associations")
            self.logger.info(f"   Unique bacteria: {self.bacteria_mapping['bacteria_name'].nunique()}")
            self.logger.info(f"   Domains covered: {self.bacteria_mapping['domain'].nunique()}")
            self.logger.info(f"   Beneficial: {(self.bacteria_mapping['association_type'] == 'beneficial').sum()}")
            self.logger.info(f"   Harmful: {(self.bacteria_mapping['association_type'] == 'harmful').sum()}")
            
        except Exception as e:
            self.logger.warning(f"Could not load from database: {e}")
            self.logger.warning("Falling back to CSV file")
            self.bacteria_mapping = None
    
    def _load_mapping_from_csv(self):
        """Load bacteria-domain mapping from CSV file."""
        try:
            self.bacteria_mapping = pd.read_csv(self.mapping_file)
            self.logger.info(f"✅ Loaded mapping from CSV with {len(self.bacteria_mapping)} associations")
            self.logger.info(f"   Unique bacteria: {self.bacteria_mapping['bacteria_name'].nunique()}")
            self.logger.info(f"   Domains covered: {self.bacteria_mapping['domain'].nunique()}")
        except Exception as e:
            self.logger.error(f"Error loading mapping from CSV: {e}")
            self.bacteria_mapping = pd.DataFrame()
    
    def score_patient_bacteria(self, patient_data: pd.DataFrame) -> pd.DataFrame:
        """
        Score patient bacteria data based on domain associations.
        
        Args:
            patient_data: DataFrame with columns:
                - bacteria_name: str
                - relative_abundance: float
                - taxonomy_level: str
                - timepoint: str
                - extraction_confidence: float
        
        Returns:
            DataFrame with columns:
                - bacteria_name: str
                - relative_abundance: float
                - taxonomy_level: str
                - timepoint: str
                - domain: str
                - impact_score: float (-1 to +1)
                - evidence_strength: str
                - abundance_level: str
                - confidence: float (0-1)
        """
        if self.bacteria_mapping is None or self.bacteria_mapping.empty:
            self.logger.error("No bacteria-domain mapping loaded!")
            return pd.DataFrame()
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"SCORING PATIENT BACTERIA")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Patient bacteria to score: {len(patient_data)}")
        
        scored_data = []
        
        for idx, row in patient_data.iterrows():
            bacteria_name = row['bacteria_name']
            abundance = row['relative_abundance']
            
            # Find matching domain associations
            matches = self._find_bacteria_matches(bacteria_name)
            
            if matches.empty:
                self.logger.debug(f"  No domain mapping found for: {bacteria_name}")
                continue
            
            # Calculate impact score for each domain association
            for _, mapping in matches.iterrows():
                impact_score = self._calculate_impact_score(
                    abundance=abundance,
                    base_impact=mapping['impact_score'],
                    evidence_strength=mapping['evidence_strength']
                )
                
                abundance_level = self._categorize_abundance(abundance)
                
                # Combine extraction confidence with evidence strength
                confidence = row['extraction_confidence'] * self.EVIDENCE_WEIGHTS.get(mapping['evidence_strength'], 0.5)
                
                scored_data.append({
                    'bacteria_name': bacteria_name,
                    'relative_abundance': abundance,
                    'taxonomy_level': row['taxonomy_level'],
                    'timepoint': row['timepoint'],
                    'domain': mapping['domain'],
                    'impact_score': impact_score,
                    'evidence_strength': mapping['evidence_strength'],
                    'claim_count': mapping['claim_count'],
                    'abundance_level': abundance_level,
                    'confidence': confidence
                })
        
        result_df = pd.DataFrame(scored_data)
        
        self.logger.info(f"\n✅ Scoring complete:")
        self.logger.info(f"   Total scored entries: {len(result_df)}")
        self.logger.info(f"   Bacteria with domain matches: {result_df['bacteria_name'].nunique()}")
        self.logger.info(f"   Domains identified: {result_df['domain'].nunique()}")
        
        return result_df
    
    def _find_bacteria_matches(self, bacteria_name: str) -> pd.DataFrame:
        """
        Find bacteria in mapping using flexible matching.
        
        Handles:
        - Exact matches
        - Genus-level matches (if species not found)
        - Case-insensitive matching
        """
        bacteria_name_lower = bacteria_name.lower()
        
        # Try exact match first (case-insensitive)
        exact_matches = self.bacteria_mapping[
            self.bacteria_mapping['bacteria_name'].str.lower() == bacteria_name_lower
        ]
        
        if not exact_matches.empty:
            return exact_matches
        
        # Try genus-level match if input is species-level
        if ' ' in bacteria_name:
            genus = bacteria_name.split()[0]
            genus_matches = self.bacteria_mapping[
                self.bacteria_mapping['bacteria_name'].str.lower() == genus.lower()
            ]
            if not genus_matches.empty:
                return genus_matches
        
        # Try partial match (bacteria name starts with...)
        partial_matches = self.bacteria_mapping[
            self.bacteria_mapping['bacteria_name'].str.lower().str.startswith(bacteria_name_lower.split()[0])
        ]
        
        return partial_matches
    
    def _calculate_impact_score(self, 
                                 abundance: float, 
                                 base_impact: float, 
                                 evidence_strength: str) -> float:
        """
        Calculate impact score based on abundance and evidence quality.
        
        Formula:
        impact_score = base_impact * abundance_factor * evidence_weight
        
        Where:
        - base_impact: from scientific claims (-1 to +1)
        - abundance_factor: scaling based on abundance level (0-1)
        - evidence_weight: quality of scientific evidence (0-1)
        
        Returns:
            Float between -1 and +1
        """
        # Get evidence weight
        evidence_weight = self.EVIDENCE_WEIGHTS.get(evidence_strength, 0.5)
        
        # Calculate abundance factor (logarithmic scaling)
        # High abundance = more impact
        if abundance >= self.ABUNDANCE_THRESHOLDS['very_high']:
            abundance_factor = 1.0
        elif abundance >= self.ABUNDANCE_THRESHOLDS['high']:
            abundance_factor = 0.8
        elif abundance >= self.ABUNDANCE_THRESHOLDS['medium']:
            abundance_factor = 0.6
        elif abundance >= self.ABUNDANCE_THRESHOLDS['low']:
            abundance_factor = 0.4
        else:
            abundance_factor = 0.2
        
        # Calculate final impact score
        impact_score = base_impact * abundance_factor * evidence_weight
        
        # Clamp to [-1, 1]
        impact_score = max(-1.0, min(1.0, impact_score))
        
        return impact_score
    
    def _categorize_abundance(self, abundance: float) -> str:
        """Categorize abundance level."""
        if abundance >= self.ABUNDANCE_THRESHOLDS['very_high']:
            return 'very_high'
        elif abundance >= self.ABUNDANCE_THRESHOLDS['high']:
            return 'high'
        elif abundance >= self.ABUNDANCE_THRESHOLDS['medium']:
            return 'medium'
        elif abundance >= self.ABUNDANCE_THRESHOLDS['low']:
            return 'low'
        else:
            return 'very_low'
    
    def aggregate_by_domain(self, scored_data: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate scores by health domain.
        
        Returns:
            DataFrame with columns:
                - domain: str
                - total_impact: float (sum of all impact scores)
                - bacteria_count: int
                - avg_confidence: float
                - positive_bacteria: int
                - negative_bacteria: int
                - dominant_bacteria: str (bacteria with highest impact)
        """
        if scored_data.empty:
            return pd.DataFrame()
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"AGGREGATING SCORES BY DOMAIN")
        self.logger.info(f"{'='*60}")
        
        # Group by domain and timepoint
        domain_scores = []
        
        for timepoint in scored_data['timepoint'].unique():
            timepoint_data = scored_data[scored_data['timepoint'] == timepoint]
            
            for domain in timepoint_data['domain'].unique():
                domain_data = timepoint_data[timepoint_data['domain'] == domain]
                
                # Calculate aggregate metrics
                total_impact = domain_data['impact_score'].sum()
                bacteria_count = len(domain_data)
                avg_confidence = domain_data['confidence'].mean()
                positive_count = (domain_data['impact_score'] > 0).sum()
                negative_count = (domain_data['impact_score'] < 0).sum()
                
                # Find dominant bacteria (highest absolute impact)
                dominant_idx = domain_data['impact_score'].abs().idxmax()
                dominant_bacteria = domain_data.loc[dominant_idx, 'bacteria_name']
                dominant_impact = domain_data.loc[dominant_idx, 'impact_score']
                
                domain_scores.append({
                    'timepoint': timepoint,
                    'domain': domain,
                    'total_impact': total_impact,
                    'bacteria_count': bacteria_count,
                    'avg_confidence': avg_confidence,
                    'positive_bacteria': positive_count,
                    'negative_bacteria': negative_count,
                    'dominant_bacteria': dominant_bacteria,
                    'dominant_impact': dominant_impact
                })
        
        result_df = pd.DataFrame(domain_scores)
        result_df = result_df.sort_values(['timepoint', 'total_impact'], ascending=[True, False])
        
        return result_df
    
    def print_summary(self, scored_data: pd.DataFrame, domain_aggregates: pd.DataFrame):
        """Print scoring summary."""
        print("\n" + "="*60)
        print("BACTERIA SCORING SUMMARY")
        print("="*60)
        
        if scored_data.empty:
            print("\n⚠️  No bacteria could be scored")
            return
        
        print(f"\n📊 Overall Statistics:")
        print(f"   Total scored entries: {len(scored_data)}")
        print(f"   Unique bacteria: {scored_data['bacteria_name'].nunique()}")
        print(f"   Domains covered: {scored_data['domain'].nunique()}")
        print(f"   Timepoints: {scored_data['timepoint'].nunique()}")
        print(f"   Average confidence: {scored_data['confidence'].mean():.2%}")
        
        print(f"\n🎯 Domain Distribution:")
        for domain in scored_data['domain'].unique():
            count = len(scored_data[scored_data['domain'] == domain])
            avg_impact = scored_data[scored_data['domain'] == domain]['impact_score'].mean()
            print(f"   {domain}: {count} bacteria (avg impact: {avg_impact:+.3f})")
        
        print(f"\n🦠 Top 10 Most Impactful Bacteria:")
        top10 = scored_data.nlargest(10, 'impact_score')
        for idx, row in top10.iterrows():
            print(f"   {row['bacteria_name']} ({row['domain']})")
            print(f"      Abundance: {row['relative_abundance']:.2f}% | Impact: {row['impact_score']:+.3f} | Evidence: {row['evidence_strength']}")
        
        if not domain_aggregates.empty:
            print(f"\n📈 Domain Health Scores (by timepoint):")
            for _, row in domain_aggregates.iterrows():
                print(f"\n   {row['timepoint']} - {row['domain'].upper()}:")
                print(f"      Total Impact: {row['total_impact']:+.3f}")
                print(f"      Bacteria: {row['bacteria_count']} ({row['positive_bacteria']} positive, {row['negative_bacteria']} negative)")
                print(f"      Dominant: {row['dominant_bacteria']} ({row['dominant_impact']:+.3f})")
                print(f"      Confidence: {row['avg_confidence']:.2%}")
        
        print("\n" + "="*60)
    
    def save_results(self, scored_data: pd.DataFrame, domain_aggregates: pd.DataFrame, output_dir: str):
        """Save scoring results to files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save detailed scores
        scored_file = output_dir / 'bacteria_scores_detailed.csv'
        scored_data.to_csv(scored_file, index=False)
        self.logger.info(f"✅ Saved detailed scores: {scored_file}")
        
        scored_xlsx = output_dir / 'bacteria_scores_detailed.xlsx'
        scored_data.to_excel(scored_xlsx, index=False)
        self.logger.info(f"✅ Saved detailed scores: {scored_xlsx}")
        
        # Save domain aggregates
        if not domain_aggregates.empty:
            domain_file = output_dir / 'domain_health_scores.csv'
            domain_aggregates.to_csv(domain_file, index=False)
            self.logger.info(f"✅ Saved domain scores: {domain_file}")
            
            domain_xlsx = output_dir / 'domain_health_scores.xlsx'
            domain_aggregates.to_excel(domain_xlsx, index=False)
            self.logger.info(f"✅ Saved domain scores: {domain_xlsx}")


if __name__ == "__main__":
    # Example usage
    scorer = BacteriaScorer()
    
    # Load patient data
    # patient_data = pd.read_csv("patient_bacteria_extracted.csv")
    # scored_data = scorer.score_patient_bacteria(patient_data)
    # domain_scores = scorer.aggregate_by_domain(scored_data)
    # scorer.print_summary(scored_data, domain_scores)
    # scorer.save_results(scored_data, domain_scores, "output/scores")
