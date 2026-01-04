#!/usr/bin/env python3
"""
Clinical Trials Integration Module for MannBiome Customer Portal
Fetches microbiome-related clinical trials from ClinicalTrials.gov API
and integrates with the customer portal
"""

import requests
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection (same as DBCustomerPortal.py)
DATABASE_URL = "postgresql://postgres:db_admin@vendor-portal-db.cszf6hop4o2t.us-east-2.rds.amazonaws.com:5432/mannbiome"
engine = create_engine(DATABASE_URL)


class ClinicalTrialsService:
    """Service to fetch and manage clinical trials data"""
    
    def __init__(self):
        self.api_url = "https://clinicaltrials.gov/api/v2/studies"
        # Default query set; keep focused on microbiome only
        self.base_queries = [
            "microbiome",
        ]

    def _fetch_query(self, query: str, max_results: int = 1000):
        """Fetch studies for a single query string with pagination."""
        page_size = 100
        collected = []

        # First request to learn total count
        params = {
            'pageSize': 1,
            'countTotal': 'true',
            'query.cond': query
        }

        response = requests.get(self.api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        total_count = data.get('totalCount', 0)
        logger.info(f"📊 Query '{query}' total found: {total_count}")

        num_pages = min((total_count + page_size - 1) // page_size, max_results // page_size)
        next_token = data.get('nextPageToken') or data.get('pageToken')

        for page in range(num_pages):
            page_params = {
                'pageSize': page_size,
                'countTotal': 'false',
                'query.cond': query
            }
            if next_token:
                page_params['pageToken'] = next_token

            resp = requests.get(self.api_url, params=page_params, timeout=10)
            resp.raise_for_status()
            page_data = resp.json()
            studies = page_data.get('studies', [])
            collected.extend(studies)
            logger.info(f"✅ Query '{query}' page {page + 1}/{num_pages} - Fetched {len(studies)} trials")

            next_token = page_data.get('nextPageToken') or page_data.get('pageToken')
            if not next_token or len(collected) >= max_results:
                break

        return collected[:max_results]
    
    def fetch_microbiome_trials(self, max_results=1000):
        """Fetch microbiome-related clinical trials (deduped by NCT ID)."""

        logger.info("🔍 Fetching clinical trials for queries: %s", self.base_queries)
        try:
            combined = []
            for q in self.base_queries:
                combined.extend(self._fetch_query(q, max_results=max_results))

            # Deduplicate by NCT ID so downstream filters see a clean list
            deduped = {}
            for study in combined:
                nct_id = (
                    study.get('protocolSection', {})
                    .get('identificationModule', {})
                    .get('nctId')
                ) or f"study-{id(study)}"
                if nct_id not in deduped:
                    deduped[nct_id] = study

            logger.info(f"✅ Total fetched (deduped): {len(deduped)} trials")
            return list(deduped.values())[:max_results]

        except Exception as e:
            logger.error(f"❌ Error fetching trials: {e}")
            return []
    
    def parse_trial(self, study):
        """Parse trial data from API response"""
        
        try:
            protocol = study.get('protocolSection', {})
            
            # Identification
            id_module = protocol.get('identificationModule', {})
            nct_id = id_module.get('nctId', 'N/A')
            title = id_module.get('briefTitle', 'N/A')
            
            # Status
            status_module = protocol.get('statusModule', {})
            status = status_module.get('overallStatus', 'N/A')
            
            # Dates - Get from startDateStruct and primaryCompletionDateStruct
            start_date_struct = status_module.get('startDateStruct', {})
            start_date = start_date_struct.get('date', None)
            
            primary_completion_struct = status_module.get('primaryCompletionDateStruct', {})
            primary_completion = primary_completion_struct.get('date', None)
            
            # Organization - Use sponsorCollaboratorsModule
            sponsor_module = protocol.get('sponsorCollaboratorsModule', {})
            lead_sponsor = sponsor_module.get('leadSponsor', {})
            sponsor_name = lead_sponsor.get('name', 'N/A')
            
            # Phase - Get from designModule.phases (array of strings like ["PHASE1", "PHASE2"])
            design_module = protocol.get('designModule', {})
            phases = design_module.get('phases', [])
            # Take first phase or 'N/A' if no phases
            phase = phases[0] if phases else 'N/A'
            
            # Enrollment - Get from designModule.enrollmentInfo
            enrollment_info = design_module.get('enrollmentInfo', {})
            enrollment = enrollment_info.get('count', 0)
            
            # Conditions
            conditions_module = protocol.get('conditionsModule', {})
            conditions = conditions_module.get('conditions', [])
            
            # Interventions
            intervention_module = protocol.get('armsInterventionsModule', {})
            interventions = intervention_module.get('interventions', []) if intervention_module else []
            
            # Location
            contact_module = protocol.get('contactsLocationsModule', {})
            locations = contact_module.get('locations', [])
            countries = list(set([loc.get('country', 'N/A') for loc in locations]))
            
            # Description
            description_module = protocol.get('descriptionModule', {})
            brief_summary = description_module.get('briefSummary', '')
            
            return {
                'nct_id': nct_id,
                'title': title,
                'status': status,
                'phase': phase,  # New: Add phase
                'start_date': start_date,
                'completion_date': primary_completion,
                'sponsor': sponsor_name,
                'enrollment': enrollment,
                'conditions': json.dumps(conditions),
                'interventions': json.dumps([i.get('name', '') for i in interventions]),
                'countries': json.dumps(countries),
                'description': brief_summary,
                'url': f"https://clinicaltrials.gov/ct2/show/{nct_id}",
                'created_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error parsing trial {study.get('nctId', 'unknown')}: {e}")
            return None
    
    def save_to_database(self, trials_data):
        """Save clinical trials to PostgreSQL database"""
        
        logger.info("💾 Saving trials to database...")
        
        try:
            # Create trials table if not exists
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS clinical_trials (
                        id SERIAL PRIMARY KEY,
                        nct_id VARCHAR(255) UNIQUE NOT NULL,
                        title TEXT NOT NULL,
                        status VARCHAR(100),
                        start_date DATE,
                        completion_date DATE,
                        sponsor VARCHAR(255),
                        enrollment INTEGER,
                        conditions JSONB,
                        interventions JSONB,
                        countries JSONB,
                        description TEXT,
                        url VARCHAR(500),
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.commit()
            
            # Convert to DataFrame
            df = pd.DataFrame(trials_data)
            
            # Bulk upsert using PostgreSQL's INSERT ... ON CONFLICT
            if len(df) > 0:
                # Create temporary table for bulk insert with proper type conversion
                df.to_sql('temp_trials', engine, if_exists='replace', index=False)
                
                with engine.connect() as conn:
                    # Upsert using ON CONFLICT with explicit type casting
                    conn.execute(text("""
                        INSERT INTO clinical_trials (
                            nct_id, title, status, start_date, completion_date, 
                            sponsor, enrollment, conditions, interventions, 
                            countries, description, url, created_at
                        )
                        SELECT 
                            nct_id, title, status, 
                            NULLIF(TRIM(start_date), '')::DATE,
                            NULLIF(TRIM(completion_date), '')::DATE,
                            sponsor, enrollment::INTEGER, conditions, interventions,
                            countries, description, url, created_at
                        FROM temp_trials
                        ON CONFLICT (nct_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            status = EXCLUDED.status,
                            start_date = EXCLUDED.start_date,
                            completion_date = EXCLUDED.completion_date,
                            sponsor = EXCLUDED.sponsor,
                            enrollment = EXCLUDED.enrollment,
                            conditions = EXCLUDED.conditions,
                            interventions = EXCLUDED.interventions,
                            countries = EXCLUDED.countries,
                            description = EXCLUDED.description,
                            url = EXCLUDED.url,
                            updated_at = NOW()
                    """))
                    conn.commit()
                    
                # Drop temporary table
                with engine.connect() as conn:
                    conn.execute(text("DROP TABLE IF EXISTS temp_trials"))
                    conn.commit()
            
            logger.info(f"✅ Saved/Updated {len(df)} trials in database")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving to database: {e}")
            return False
    
    def get_trials_by_domain(self, domain):
        """Get trials related to specific health domain"""
        
        domain_keywords = {
            'gut': ['microbiome', 'dysbiosis', 'probiotics', 'prebiotic', 'gastrointestinal'],
            'liver': ['liver', 'hepatic', 'cirrhosis', 'microbiota'],
            'heart': ['cardiovascular', 'microbiota', 'heart health'],
            'cognitive': ['brain', 'gut-brain', 'neurotransmitter', 'neuroinflammation'],
            'skin': ['dermatology', 'skin microbiome', 'dermatitis'],
            'aging': ['aging', 'longevity', 'senescence']
        }
        
        keywords = domain_keywords.get(domain.lower(), [])
        
        try:
            with engine.connect() as conn:
                # Build query
                conditions = " OR ".join([f"title ILIKE '%{kw}%'" for kw in keywords])
                conditions += " OR " + " OR ".join([f"description ILIKE '%{kw}%'" for kw in keywords])
                
                result = conn.execute(text(f"""
                    SELECT * FROM clinical_trials 
                    WHERE ({conditions})
                    ORDER BY enrollment DESC
                    LIMIT 50
                """))
                
                trials = [dict(row._mapping) for row in result.fetchall()]
                logger.info(f"Found {len(trials)} trials for domain: {domain}")
                
                return trials
                
        except Exception as e:
            logger.error(f"Error fetching trials for domain {domain}: {e}")
            return []


# API Endpoints for FastAPI (to add to DBCustomerPortal.py)

"""
# Add these endpoints to DBCustomerPortal.py:

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/clinical-trials", tags=["Clinical Trials"])

@router.get("/fetch-and-update", tags=["Clinical Trials"])
def fetch_and_update_trials(db: Session = Depends(get_db)):
    '''Fetch latest microbiome clinical trials from ClinicalTrials.gov'''
    try:
        service = ClinicalTrialsService()
        studies = service.fetch_microbiome_trials(max_results=2000)
        
        parsed_trials = []
        for study in studies:
            trial = service.parse_trial(study)
            if trial:
                parsed_trials.append(trial)
        
        service.save_to_database(parsed_trials)
        
        return {
            "success": True,
            "message": f"Successfully fetched and saved {len(parsed_trials)} clinical trials",
            "count": len(parsed_trials)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/by-domain/{domain}", tags=["Clinical Trials"])
def get_trials_by_domain(domain: str, db: Session = Depends(get_db)):
    '''Get clinical trials related to a specific health domain'''
    try:
        service = ClinicalTrialsService()
        trials = service.get_trials_by_domain(domain)
        
        return {
            "success": True,
            "domain": domain,
            "trials": trials,
            "count": len(trials)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/all", tags=["Clinical Trials"])
def get_all_trials(limit: int = 100, db: Session = Depends(get_db)):
    '''Get all microbiome clinical trials'''
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f'''
                SELECT * FROM clinical_trials 
                ORDER BY enrollment DESC, created_at DESC
                LIMIT {limit}
            '''))
            
            trials = [dict(row._mapping) for row in result.fetchall()]
            
            return {
                "success": True,
                "trials": trials,
                "count": len(trials)
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/search", tags=["Clinical Trials"])
def search_trials(q: str, db: Session = Depends(get_db)):
    '''Search for clinical trials by keyword'''
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f'''
                SELECT * FROM clinical_trials 
                WHERE title ILIKE '%{q}%' OR description ILIKE '%{q}%'
                ORDER BY enrollment DESC
                LIMIT 50
            '''))
            
            trials = [dict(row._mapping) for row in result.fetchall()]
            
            return {
                "success": True,
                "query": q,
                "trials": trials,
                "count": len(trials)
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
"""


if __name__ == "__main__":
    # Main execution
    service = ClinicalTrialsService()
    
    # Fetch trials
    studies = service.fetch_microbiome_trials(max_results=2000)
    
    # Parse and save
    if studies:
        parsed_trials = []
        for study in studies:
            trial = service.parse_trial(study)
            if trial:
                parsed_trials.append(trial)
        
        # Save to database
        service.save_to_database(parsed_trials)
        
        logger.info("✅ Clinical trials integration complete!")
    else:
        logger.error("❌ No trials fetched")
