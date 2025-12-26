"""
Patient Data Inserter - Step 5
Inserts parsed patient reports and calculated scores into PostgreSQL database
"""

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_batch, Json
import pandas as pd
import json
import uuid
from datetime import datetime, date
from pathlib import Path
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple

class PatientDataInserter:
    """
    Handles insertion of patient microbiome data into PostgreSQL
    Inserts: patient_reports, patient_bacteria_scores, patient_domain_scores
    """
    
    def __init__(self, db_config: Optional[Dict] = None):
        """
        Initialize database connection
        
        Args:
            db_config: Database connection parameters. If None, loads from .env
        """
        if db_config is None:
            load_dotenv()
            db_config = {
                'host': os.getenv('DB_HOST'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD')
            }
        
        self.db_config = db_config
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor()
            print(f"✓ Connected to database: {self.db_config['database']}")
        except psycopg2.Error as e:
            print(f"✗ Database connection failed: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")
    
    def insert_patient_report(
        self,
        participant_id: str,
        timepoint: str,
        bacteria_df: pd.DataFrame,
        lab_name: Optional[str] = None,
        sample_id: Optional[str] = None,
        report_date: Optional[date] = None,
        original_filename: Optional[str] = None,
        extraction_confidence: Optional[float] = None,
        extraction_notes: Optional[str] = None
    ) -> str:
        """
        Insert patient report into patient_reports table
        
        Args:
            participant_id: Patient identifier (e.g., 'MG0202')
            timepoint: Sample timepoint (e.g., 'First Year', 'Second Year')
            bacteria_df: DataFrame with columns: bacteria_name, relative_abundance, taxonomy_level
            lab_name: Laboratory name
            sample_id: Sample identifier
            report_date: Date of report
            original_filename: Original PDF filename
            extraction_confidence: Confidence score 0-1
            extraction_notes: Additional notes
        
        Returns:
            upload_id: UUID of inserted report
        """
        # Convert bacteria DataFrame to JSONB format
        bacteria_data = bacteria_df.to_dict('records')
        
        # Generate UUID
        upload_id = str(uuid.uuid4())
        
        insert_query = """
            INSERT INTO patient_reports (
                upload_id, participant_id, lab_name, sample_id, timepoint,
                report_date, original_filename, bacteria_data,
                extraction_status, analysis_status, extraction_method,
                extraction_confidence, extraction_notes
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (participant_id, timepoint) 
            DO UPDATE SET
                lab_name = EXCLUDED.lab_name,
                sample_id = EXCLUDED.sample_id,
                report_date = EXCLUDED.report_date,
                original_filename = EXCLUDED.original_filename,
                bacteria_data = EXCLUDED.bacteria_data,
                extraction_confidence = EXCLUDED.extraction_confidence,
                extraction_notes = EXCLUDED.extraction_notes,
                updated_at = CURRENT_TIMESTAMP
            RETURNING upload_id;
        """
        
        try:
            self.cursor.execute(insert_query, (
                upload_id,
                participant_id,
                lab_name,
                sample_id,
                timepoint,
                report_date,
                original_filename,
                Json(bacteria_data),  # Convert to JSONB
                'COMPLETED',
                'PENDING',
                'pdfplumber',
                extraction_confidence,
                extraction_notes
            ))
            
            result = self.cursor.fetchone()
            final_upload_id = result[0] if result else upload_id
            
            print(f"  ✓ Inserted patient_reports: {participant_id} - {timepoint} (upload_id: {final_upload_id})")
            return final_upload_id
            
        except psycopg2.Error as e:
            print(f"  ✗ Error inserting patient_reports: {e}")
            raise
    
    def insert_bacteria_scores(
        self,
        upload_id: str,
        participant_id: str,
        bacteria_scores_df: pd.DataFrame
    ) -> int:
        """
        Insert bacteria scores into patient_bacteria_scores table
        
        Args:
            upload_id: UUID from patient_reports
            participant_id: Patient identifier
            bacteria_scores_df: DataFrame with columns:
                - bacteria_name, relative_abundance, taxonomy_level, timepoint,
                - domain, impact_score, evidence_strength, claim_count,
                - abundance_level, confidence
        
        Returns:
            Number of rows inserted
        """
        # First delete existing scores for this upload_id to avoid duplicates
        delete_query = "DELETE FROM patient_bacteria_scores WHERE upload_id = %s"
        self.cursor.execute(delete_query, (upload_id,))
        
        insert_query = """
            INSERT INTO patient_bacteria_scores (
                upload_id, participant_id, bacteria_name, relative_abundance,
                taxonomy_level, domain, impact_score, evidence_strength,
                claim_count, abundance_level, confidence
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            );
        """
        
        # Prepare batch data
        batch_data = []
        for _, row in bacteria_scores_df.iterrows():
            batch_data.append((
                upload_id,
                participant_id,
                row['bacteria_name'],
                float(row['relative_abundance']) if pd.notna(row['relative_abundance']) else None,
                row['taxonomy_level'],
                row['domain'],
                float(row['impact_score']) if pd.notna(row['impact_score']) else None,
                row['evidence_strength'] if pd.notna(row['evidence_strength']) else None,
                int(row['claim_count']) if pd.notna(row['claim_count']) else None,
                row['abundance_level'] if pd.notna(row['abundance_level']) else None,
                float(row['confidence']) if pd.notna(row['confidence']) else None
            ))
        
        try:
            execute_batch(self.cursor, insert_query, batch_data, page_size=100)
            row_count = len(batch_data)
            print(f"  ✓ Inserted {row_count} bacteria scores")
            return row_count
            
        except psycopg2.Error as e:
            print(f"  ✗ Error inserting bacteria scores: {e}")
            raise
    
    def insert_domain_scores(
        self,
        upload_id: str,
        participant_id: str,
        domain_scores_df: pd.DataFrame
    ) -> int:
        """
        Insert domain health scores into patient_domain_scores table
        
        Args:
            upload_id: UUID from patient_reports
            participant_id: Patient identifier
            domain_scores_df: DataFrame with columns:
                - domain, total_impact, bacteria_count, avg_confidence,
                - positive_bacteria, negative_bacteria, dominant_bacteria, dominant_impact
        
        Returns:
            Number of rows inserted
        """
        # First delete existing scores for this upload_id
        delete_query = "DELETE FROM patient_domain_scores WHERE upload_id = %s"
        self.cursor.execute(delete_query, (upload_id,))
        
        insert_query = """
            INSERT INTO patient_domain_scores (
                upload_id, participant_id, domain, total_impact,
                bacteria_count, positive_bacteria, negative_bacteria,
                dominant_bacteria, dominant_impact, avg_confidence, health_status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            );
        """
        
        # Prepare batch data
        batch_data = []
        for _, row in domain_scores_df.iterrows():
            # Calculate health status based on total_impact
            total_impact = float(row['total_impact']) if pd.notna(row['total_impact']) else 0
            health_status = self._calculate_health_status(total_impact)
            
            batch_data.append((
                upload_id,
                participant_id,
                row['domain'],
                float(row['total_impact']) if pd.notna(row['total_impact']) else None,
                int(row['bacteria_count']) if pd.notna(row['bacteria_count']) else None,
                int(row['positive_bacteria']) if pd.notna(row['positive_bacteria']) else None,
                int(row['negative_bacteria']) if pd.notna(row['negative_bacteria']) else None,
                row['dominant_bacteria'] if pd.notna(row['dominant_bacteria']) else None,
                float(row['dominant_impact']) if pd.notna(row['dominant_impact']) else None,
                float(row['avg_confidence']) if pd.notna(row['avg_confidence']) else None,
                health_status
            ))
        
        try:
            execute_batch(self.cursor, insert_query, batch_data, page_size=100)
            row_count = len(batch_data)
            print(f"  ✓ Inserted {row_count} domain scores")
            return row_count
            
        except psycopg2.Error as e:
            print(f"  ✗ Error inserting domain scores: {e}")
            raise
    
    def _calculate_health_status(self, total_impact: float) -> str:
        """
        Calculate health status category based on total impact score
        
        Args:
            total_impact: Sum of all bacteria impact scores for a domain
        
        Returns:
            Health status: 'critical', 'poor', 'moderate', 'good', 'excellent'
        """
        if total_impact < -15:
            return 'critical'
        elif total_impact < -5:
            return 'poor'
        elif total_impact < 5:
            return 'moderate'
        elif total_impact < 15:
            return 'good'
        else:
            return 'excellent'
    
    def update_analysis_status(self, upload_id: str, status: str):
        """
        Update analysis_status in patient_reports
        
        Args:
            upload_id: Report UUID
            status: 'PENDING', 'PROCESSING', 'COMPLETED', 'ERROR'
        """
        update_query = """
            UPDATE patient_reports 
            SET analysis_status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE upload_id = %s;
        """
        
        try:
            self.cursor.execute(update_query, (status, upload_id))
            print(f"  ✓ Updated analysis_status to: {status}")
        except psycopg2.Error as e:
            print(f"  ✗ Error updating analysis_status: {e}")
            raise
    
    def insert_patient_data_from_csv(
        self,
        participant_id: str,
        timepoint: str,
        bacteria_csv_path: str,
        bacteria_scores_csv_path: str,
        domain_scores_csv_path: str,
        **report_metadata
    ) -> Tuple[str, int, int]:
        """
        Complete pipeline: Insert patient data from CSV files
        
        Args:
            participant_id: Patient identifier
            timepoint: Sample timepoint
            bacteria_csv_path: Path to extracted bacteria CSV
            bacteria_scores_csv_path: Path to bacteria scores CSV
            domain_scores_csv_path: Path to domain scores CSV
            **report_metadata: Additional metadata (lab_name, sample_id, etc.)
        
        Returns:
            Tuple of (upload_id, bacteria_scores_count, domain_scores_count)
        """
        try:
            # Start transaction
            print(f"\n{'='*70}")
            print(f"Inserting data for: {participant_id} - {timepoint}")
            print('='*70)
            
            # Load CSV files
            bacteria_df = pd.read_csv(bacteria_csv_path)
            bacteria_scores_df = pd.read_csv(bacteria_scores_csv_path)
            domain_scores_df = pd.read_csv(domain_scores_csv_path)
            
            print(f"Loaded data:")
            print(f"  - {len(bacteria_df)} bacteria records")
            print(f"  - {len(bacteria_scores_df)} bacteria scores")
            print(f"  - {len(domain_scores_df)} domain scores")
            
            # Insert patient report
            upload_id = self.insert_patient_report(
                participant_id=participant_id,
                timepoint=timepoint,
                bacteria_df=bacteria_df,
                **report_metadata
            )
            
            # Filter scores for this specific timepoint
            timepoint_bacteria_scores = bacteria_scores_df[
                bacteria_scores_df['timepoint'] == timepoint
            ].copy() if 'timepoint' in bacteria_scores_df.columns else bacteria_scores_df.copy()
            
            timepoint_domain_scores = domain_scores_df[
                domain_scores_df['timepoint'] == timepoint
            ].copy() if 'timepoint' in domain_scores_df.columns else domain_scores_df.copy()
            
            # Insert bacteria scores
            bacteria_count = self.insert_bacteria_scores(
                upload_id=upload_id,
                participant_id=participant_id,
                bacteria_scores_df=timepoint_bacteria_scores
            )
            
            # Insert domain scores
            domain_count = self.insert_domain_scores(
                upload_id=upload_id,
                participant_id=participant_id,
                domain_scores_df=timepoint_domain_scores
            )
            
            # Update analysis status to COMPLETED
            self.update_analysis_status(upload_id, 'COMPLETED')
            
            # Commit transaction
            self.conn.commit()
            print(f"\n✓ Transaction committed successfully!")
            print(f"  - upload_id: {upload_id}")
            print(f"  - {bacteria_count} bacteria scores inserted")
            print(f"  - {domain_count} domain scores inserted")
            
            return upload_id, bacteria_count, domain_count
            
        except Exception as e:
            # Rollback on error
            self.conn.rollback()
            print(f"\n✗ Transaction rolled back due to error: {e}")
            raise
    
    def get_patient_summary(self, participant_id: str) -> Dict:
        """
        Get summary of patient data in database
        
        Args:
            participant_id: Patient identifier
        
        Returns:
            Dictionary with patient summary
        """
        summary_query = """
            SELECT 
                pr.upload_id,
                pr.timepoint,
                pr.report_date,
                pr.total_bacteria_count,
                pr.analysis_status,
                COUNT(DISTINCT pbs.bacteria_name) as unique_bacteria_scored,
                COUNT(DISTINCT pds.domain) as domains_analyzed
            FROM patient_reports pr
            LEFT JOIN patient_bacteria_scores pbs ON pr.upload_id = pbs.upload_id
            LEFT JOIN patient_domain_scores pds ON pr.upload_id = pds.upload_id
            WHERE pr.participant_id = %s
            GROUP BY pr.upload_id, pr.timepoint, pr.report_date, pr.total_bacteria_count, pr.analysis_status
            ORDER BY pr.report_date DESC;
        """
        
        try:
            self.cursor.execute(summary_query, (participant_id,))
            results = self.cursor.fetchall()
            
            summary = {
                'participant_id': participant_id,
                'total_reports': len(results),
                'reports': []
            }
            
            for row in results:
                summary['reports'].append({
                    'upload_id': row[0],
                    'timepoint': row[1],
                    'report_date': row[2],
                    'total_bacteria': row[3],
                    'analysis_status': row[4],
                    'bacteria_scored': row[5],
                    'domains_analyzed': row[6]
                })
            
            return summary
            
        except psycopg2.Error as e:
            print(f"✗ Error getting patient summary: {e}")
            raise

def main():
    """Example usage"""
    print("="*70)
    print("Patient Data Inserter - Ready for Use")
    print("="*70)
    print("\nThis module provides PatientDataInserter class for database insertion.")
    print("Use it in your pipeline scripts or test files.")
    print("\nExample:")
    print("  inserter = PatientDataInserter()")
    print("  inserter.connect()")
    print("  inserter.insert_patient_data_from_csv(...)")
    print("  inserter.disconnect()")

if __name__ == "__main__":
    main()
