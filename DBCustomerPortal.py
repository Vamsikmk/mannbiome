# db-customer-portal.py
# Combined API: Customer Portal (microbiome/public) + Domain (vectordb schema)
# FastAPI single app, single Postgres DB (mannbiome). No mocks. Clear HTTP errors.
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, date
import os
import re
from dotenv import load_dotenv
from pathlib import Path
import shutil
import pandas as pd

# Load environment variables from .env file
load_dotenv()
import math
from fastapi.responses import FileResponse, StreamingResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, NextPageTemplate, FrameBreak
from reportlab.platypus import Frame, PageTemplate, KeepInFrame, PageBreak
from reportlab.lib.units import inch
from datetime import datetime
from reportlab.lib.utils import ImageReader
import io
import tempfile
import json
import traceback

# Import the cached recommendation service
from llm_recommendations_cached import CachedRecommendationService
import numpy as np
import skbio.diversity.alpha as alpha

# Import keystone species identifier
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / 'src' / 'patient_processing'))
from keystone_species import is_keystone_species, get_keystone_category

# ============================================================================
# CLINICAL TRIALS SYNONYM DICTIONARY - Domain-Specific Matching
# ============================================================================
CLINICAL_TRIALS_SYNONYMS = {
    "gut": {
        "core_terms": [
            "gut health", "gastrointestinal health", "digestive health", "intestinal health"
        ],
        "microbiome_focused": [
            "gut microbiome", "gut dysbiosis", "microbiota modulation", 
            "fecal microbiota transplantation", "fmt", "probiotics", "prebiotics", 
            "synbiotics", "postbiotics"
        ],
        "disease_specific": [
            "irritable bowel syndrome", "ibs", "inflammatory bowel disease", "ibm",
            "crohn's disease", "ulcerative colitis", "functional gastrointestinal disorders",
            "small intestinal bacterial overgrowth", "sibo"
        ]
    },
    "liver": {
        "core_terms": [
            "liver", "liver health", "hepatic health", "liver function", "hepatic function"
        ],
        "metabolic_inflammatory": [
            "non-alcoholic fatty liver disease", "nafld", "metabolic dysfunction-associated fatty liver disease",
            "mafld", "non-alcoholic steatohepatitis", "nash", "hepatic steatosis", 
            "liver fibrosis", "hepatic inflammation"
        ],
        "cancer_severe": [
            "hepatocellular carcinoma", "hcc", "liver cirrhosis", "chronic liver disease"
        ]
    },
    "cognitive": {
        "core_terms": [
            "brain health", "cognitive health", "neurocognitive function"
        ],
        "neurodegeneration": [
            "alzheimer's disease", "mild cognitive impairment", "mci", "dementia", 
            "parkinson's disease"
        ],
        "mental_health": [
            "depression", "anxiety disorders", "major depressive disorder", "mood disorders"
        ],
        "cognitive_outcomes": [
            "memory function", "executive function", "attention", "learning"
        ]
    },
    "kidney": {
        "core_terms": [
            "kidney health", "renal health", "renal function"
        ],
        "disease_specific": [
            "chronic kidney disease", "ckd", "acute kidney injury", "aki", 
            "diabetic nephropathy", "hypertensive nephropathy"
        ],
        "gut_kidney_axis": [
            "gut-kidney axis", "microbiome-derived uremic toxins"
        ]
    },
    "cardiometabolic": {
        "core_terms": [
            "cardiovascular health", "cardiometabolic health", "metabolic health"
        ],
        "disease_specific": [
            "type 2 diabetes", "type 2 diabetes mellitus", "insulin resistance", 
            "metabolic syndrome", "obesity", "dyslipidemia", "hypertension"
        ],
        "microbiome_links": [
            "microbiome and metabolism", "scfa metabolism", "tmao"
        ]
    },
    "intervention": {
        "all_domains": [
            "probiotic supplementation", "probiotics", "prebiotics", "synbiotics", "nutraceutical",
            "synbiotic therapy", "microbiome-targeted therapy", "microbiome modulation",
            "precision nutrition", "fecal microbiota transplantation", "fmt"
        ]
    }
}

# Flatten all synonyms for quick access
def _get_all_domain_synonyms(domain: str, include_interventions: bool = False) -> List[str]:
    """
    Get all synonyms for a specific domain (case-insensitive)
    
    Args:
        domain: Health domain name
        include_interventions: If True, include universal intervention terms.
                              For domain-specific endpoints, should be False.
                              For cross-domain searches, should be True.
    """
    domain_lower = domain.lower()
    
    # Map aliases
    domain_map = {
        "gut": "gut",
        "heart": "cardiometabolic",
        "cardiovascular": "cardiometabolic",
        "brain": "cognitive",
        "neuro": "cognitive",
        "kidney": "kidney",
        "renal": "kidney",
        "liver": "liver",
        "hepatic": "liver"
    }
    
    domain_key = domain_map.get(domain_lower, domain_lower)
    synonyms = []
    
    if domain_key in CLINICAL_TRIALS_SYNONYMS:
        for category, terms in CLINICAL_TRIALS_SYNONYMS[domain_key].items():
            synonyms.extend(terms)
    
    # Only add intervention terms if explicitly requested
    if include_interventions and domain_key != "intervention":
        synonyms.extend(CLINICAL_TRIALS_SYNONYMS["intervention"]["all_domains"])
    
    return [s.lower() for s in synonyms]

def _matches_any_synonym(title: str, synonyms: List[str]) -> bool:
    """Check if trial title matches any synonym (case-insensitive, word boundary match)"""
    title_lower = title.lower()
    for synonym in synonyms:
        # Use word boundaries to avoid matching substrings like "liver" in "delivered"
        pattern = r'\b' + re.escape(synonym) + r'\b'
        if re.search(pattern, title_lower):
            return True
    return False

def _filter_trials_by_title_only(trials: List[Dict], query_terms: List[str]) -> List[Dict]:
    """
    Filter trials by title only, using OR logic across all query terms
    Returns only trials where ANY query term matches in the TITLE field (word boundary match)
    """
    filtered = []
    for trial in trials:
        title = trial.get('title', '').lower()
        # Use word boundaries to avoid matching substrings
        if any(re.search(r'\b' + re.escape(term.lower()) + r'\b', title) for term in query_terms):
            filtered.append(trial)
    return filtered

# ============================================================================
# App
# ============================================================================
app = FastAPI(title="MannBiome API (Portal + Domain)", version="1.0.0")





app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
# -----------------------------------------------------------------------------
# Database (single engine to `mannbiome`)
# -----------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please configure your .env file.")

engine = None
SessionLocal = None
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"[DB INIT ERROR] {e}")

def get_db():
    if SessionLocal is None:
        # liveness can still be OK, readiness will fail
        yield None
        return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------------------------------------------------------
# Initialize services
# -----------------------------------------------------------------------------
# Initialize the cached recommendation service
cached_recommendation_service = CachedRecommendationService()

# -----------------------------------------------------------------------------
# Health: liveness + readiness
# -----------------------------------------------------------------------------
@app.get("/api/health", tags=["Health"])
def liveness():
    return {"status": "ok", "time": datetime.now().isoformat()}

@app.get("/api/health-check", tags=["Health"])
def readiness(db: Session = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="DB session not initialized")
    checks = {"database_connected": False, "tables": {}}
    try:
        db.execute(text("SELECT 1"))
        checks["database_connected"] = True

        # public
        try:
            db.execute(text("SELECT 1 FROM public.patient_reports LIMIT 1"))
            checks["tables"]["public.patient_reports"] = "OK"
        except Exception as e:
            checks["tables"]["public.patient_reports"] = f"ERROR: {e}"

        # microbiome
        for t in [
            "microbiome.domain_reports",
            "microbiome.health_domains",
            "microbiome.pathway_analysis",
        ]:
            try:
                db.execute(text(f"SELECT 1 FROM {t} LIMIT 1"))
                checks["tables"][t] = "OK"
            except Exception as e:
                checks["tables"][t] = f"ERROR: {e}"

        # vectordb (schema)
        for t in [
            "vectordb.bacteria_domain_associations",
            "vectordb.computed_bacteria_metadata",
            'vectordb."Healthy_Cohort_Bacteria_Metadata"',
            "vectordb.bacteria_disease_associate",
            "vectordb.rules_mappings",
        ]:
            try:
                db.execute(text(f"SELECT 1 FROM {t} LIMIT 1"))
                checks["tables"][t] = "OK"
            except Exception as e:
                checks["tables"][t] = f"ERROR: {e}"

        return {"status": "ready", "time": datetime.now().isoformat(), **checks}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Readiness failed: {e}")

# -----------------------------------------------------------------------------
# Shared helpers (NO mock outputs)
# -----------------------------------------------------------------------------
def _format_date(d: Optional[date]) -> Optional[str]:
    if not d:
        return None
    try:
        # If datetime-like
        return d.strftime("%B %d, %Y")
    except Exception:
        return str(d)

def _fetch_domain_scores_for_customer(customer_id: int, db: Session):
    """
    Returns a dict keyed by domain_id (int) with fields: score, diversity, status.
    Pulls the latest domain scores for this customer from patient_domain_scores.
    
    Score Calculation:
    - Converts total_impact (can be negative) to a normalized 1-5 scale
    - Based on ratio of positive vs negative bacteria
    - Higher positive bacteria = higher score
    
    Diversity Calculation:
    - Uses bacteria_count but normalized to 1-5 scale
    - Represents actual bacterial diversity in the domain
    """
    # Mapping from string domain names (in database) to integer domain IDs (expected by frontend)
    DOMAIN_NAME_TO_ID = {
        'gut': 1,
        'gut_health': 1,
        'liver': 2,
        'liver_health': 2,
        'heart': 3,
        'heart_health': 3,
        'cardiovascular': 3,
        'skin': 4,
        'skin_health': 4,
        'cognitive': 5,
        'cognitive_health': 5,
        'brain': 5,
        'aging': 6,
        'anti_aging': 6,
        'longevity': 6
    }
    
    rows = db.execute(text("""
        SELECT DISTINCT ON (pds.domain)
               pds.domain as domain_name,
               pds.total_impact as raw_impact,
               pds.bacteria_count as total_associations,
               pds.positive_bacteria as positive_count,
               pds.negative_bacteria as negative_count,
               pds.health_status as status,
               pr.created_at
        FROM public.patient_domain_scores pds
        JOIN public.patient_reports pr ON pds.upload_id = pr.upload_id
        WHERE pr.participant_id = :cid
        ORDER BY pds.domain, pr.created_at DESC
    """), {"cid": str(customer_id)}).fetchall()

    print(f"🔍 DEBUG: Fetched {len(rows)} domain score rows for customer {customer_id}")
    
    by_domain = {}
    for r in rows:
        domain_name = str(r.domain_name).lower().strip()
        domain_id = DOMAIN_NAME_TO_ID.get(domain_name)
        
        print(f"   Domain: {domain_name} -> ID: {domain_id} | +ve: {r.positive_count} | -ve: {r.negative_count} | assoc: {r.total_associations}")
        
        if domain_id:
            # Get raw values
            positive = float(r.positive_count) if r.positive_count is not None else 0
            negative = float(r.negative_count) if r.negative_count is not None else 0
            bacteria_count = float(r.total_associations) if r.total_associations is not None else 0
            
            # Calculate score based on positive/negative ratio
            # If both are 0, we don't have this data, so use a heuristic
            total_bacteria = positive + negative
            if total_bacteria > 0:
                # We have positive/negative data
                positive_ratio = positive / total_bacteria
                # Normalize to 1-5 scale
                normalized_score = 1.0 + (positive_ratio * 4.0)
            else:
                # No positive/negative data - use bacteria_count as proxy
                # Assume more bacteria = healthier (up to a point)
                # Score formula: normalized to 1-5 scale
                if bacteria_count > 0:
                    # More bacteria = better, but with diminishing returns
                    import math
                    log_factor = math.log10(bacteria_count + 1) / 2.0  # log scale
                    # Scale: 2.5 baseline + log bonus, capped at 4.0
                    normalized_score = min(4.0, 2.5 + log_factor)
                else:
                    normalized_score = 2.5
            
            # Calculate Shannon diversity for this domain
            domain_bacteria = _get_domain_bacteria_for_diversity(db, customer_id, domain_id)
            diversity_score = calculate_shannon_diversity(domain_bacteria) if domain_bacteria else 0.0
            
            print(f"      -> Score: {normalized_score:.1f}, Shannon Diversity: {diversity_score:.2f}, Bacteria: {bacteria_count}")
            
            by_domain[domain_id] = {
                "score": round(normalized_score, 1),
                "diversity": round(diversity_score, 2),
                "status": str(r.status) if r.status else "unknown"
            }
    return by_domain


def calculate_shannon_diversity(bacteria_list: List[Dict]) -> float:
    """
    Calculate Shannon diversity index from bacteria abundance data.
    Uses scikit-bio's Shannon implementation with natural log (base e).
    
    Args:
        bacteria_list: List of bacteria dicts with 'abundance' or 'relative_abundance' keys
    
    Returns:
        Shannon diversity index (H'). Typical microbiome values: 2-4 (healthy), <2 (low diversity), >4 (high diversity)
    """
    if not bacteria_list:
        return 0.0
    
    # Extract abundances
    abundances = []
    for bacteria in bacteria_list:
        abundance = bacteria.get('relative_abundance') or bacteria.get('abundance') or 0
        abundance = float(abundance)
        
        # Convert percentage to fraction if needed (values > 1 are percentages)
        if abundance > 1.0:
            abundance = abundance / 100.0
        
        if abundance > 0:  # Only include bacteria with non-zero abundance
            abundances.append(abundance)
    
    if not abundances:
        return 0.0
    
    # Calculate Shannon diversity using scikit-bio (base e = natural log)
    try:
        shannon_index = alpha.shannon(np.array(abundances), base=np.e)
        return round(float(shannon_index), 2)
    except Exception as e:
        print(f"Error calculating Shannon diversity: {e}")
        return 0.0


def _get_domain_bacteria_for_diversity(db: Session, customer_id: int, domain_id: int) -> List[Dict]:
    """
    Get bacteria data for a specific domain to calculate Shannon diversity.
    Returns list of bacteria dicts with abundance data.
    """
    try:
        # Map domain_id to domain name
        DOMAIN_ID_TO_NAME = {
            1: 'gut', 2: 'liver', 3: 'heart', 4: 'skin', 5: 'cognitive', 6: 'aging'
        }
        domain_name = DOMAIN_ID_TO_NAME.get(domain_id)
        if not domain_name:
            return []
        
        # Get patient report
        r = _latest_patient_report(db, str(customer_id))
        if not r or not r.bacteria_data:
            return []
        
        # Load domain associations
        assoc = db.execute(text("""
            SELECT bacteria_name, domain
            FROM vectordb.bacteria_domain_associations
            WHERE domain = :domain_name
        """), {"domain_name": domain_name}).fetchall()
        
        associated_bacteria = {a.bacteria_name.lower() for a in assoc}
        
        # Filter bacteria for this domain
        domain_bacteria = []
        for item in r.bacteria_data:
            name = (item or {}).get("bacteria_name", "").strip()
            if name.lower() in associated_bacteria:
                domain_bacteria.append(item)
        
        return domain_bacteria
    except Exception as e:
        print(f"Error getting domain bacteria for diversity: {e}")
        return []


def categorize_bacteria_by_name(bacteria_name: str) -> str:
    s = (bacteria_name or "").lower()
    beneficial = [
        'lactobacillus','bifidobacterium','akkermansia','faecalibacterium',
        'roseburia','eubacterium','butyrivibrio','coprococcus',
        'ruminococcus','bacteroides fragilis','streptococcus thermophilus',
        'lactococcus','enterococcus faecalis'
    ]
    pathogenic = [
        'clostridium difficile','salmonella','shigella','campylobacter',
        'helicobacter pylori','escherichia coli','klebsiella pneumoniae',
        'enterococcus faecium','staphylococcus aureus','pseudomonas','vibrio','yersinia'
    ]
    if any(x in s for x in beneficial): return "beneficial"
    if any(x in s for x in pathogenic): return "pathogenic"
    if "unclassified" in s or "unknown" in s: return "unclassified"
    return "neutral"

def convert_abundance_to_percentage(abundance: float) -> float:
    try:
        pct = (abundance or 0.0) * 100.0
        if pct < 0.001: return round(pct, 6)
        if pct < 0.01:  return round(pct, 4)
        return round(pct, 2)
    except Exception:
        return 0.0

def calculate_visualization_metrics(percentage: float) -> Tuple[float, float]:
    try:
        if not percentage or percentage <= 0:
            return 0.0, 0.0
        if percentage < 0.001:
            logp = math.log10(percentage + 1e-8)
            scaled = max(5, min(85, (logp + 8) * 10))
            return round(scaled, 1), round(min(100, scaled + 5), 1)
        if percentage < 0.1:
            scaled = 10 + (percentage / 0.1) * 70
            return round(scaled, 1), round(min(100, scaled + 5), 1)
        range_fill = min(95, percentage * 10)
        return round(range_fill, 1), round(min(100, range_fill + 5), 1)
    except Exception:
        return 10.0, 15.0

def calculate_bacteria_status(abundance: float, evidence_strength: str, category: str) -> str:
    try:
        pct = convert_abundance_to_percentage(abundance)
        weight = {"A":1.0, "B":0.8, "C":0.6}.get((evidence_strength or "C"), 0.6)
        wp = pct * weight
        if category == "beneficial":
            if wp >= 0.0001: return "good"
            if wp >= 0.00001: return "normal"
            return "low"
        elif category == "pathogenic":
            if wp >= 0.001: return "high"
            if wp >= 0.0001: return "normal"
            return "good"
        else:
            if wp >= 0.001: return "high"
            if wp >= 0.00001: return "normal"
            return "low"
    except Exception:
        pass
    return "normal"

def calculate_overall_health_score(bact: List[Dict]) -> Dict[str, float]:
    """
    Calculate overall health scores.
    
    Score calculation:
    - Based on ratio of beneficial bacteria in good status
    - Penalized by pathogenic bacteria in high concern status
    - Range: 1-5 (higher is better)
    
    Diversity calculation:
    - Shannon diversity index (H') using actual abundance data
    - Typical range: 0-5 for microbiome data (2-4 is healthy)
    """
    try:
        if not bact:
            return {"overall_score": 2.5, "diversity_score": 0.0}
        
        # Count bacteria categories
        bg = len([b for b in bact if b["category"]=="beneficial" and b["status"]=="good"])
        bt = len([b for b in bact if b["category"]=="beneficial"])
        ph = len([b for b in bact if b["category"]=="pathogenic" and b["status"]=="high"])
        pt = len([b for b in bact if b["category"]=="pathogenic"])
        
        # Calculate ratios
        beneficial_ratio = (bg / bt) if bt else 0.5  # Default to neutral if no beneficial
        pathogenic_concern = (ph / pt) if pt else 0.0
        
        # Calculate overall score (1-5 scale)
        # Start at 2.5 (neutral), add for beneficial, subtract for pathogenic
        base_score = 2.5 + (beneficial_ratio * 2.0) - (pathogenic_concern * 2.0)
        overall_score = max(1.0, min(5.0, base_score))
        
        # Calculate Shannon diversity index from actual abundance data
        diversity_score = calculate_shannon_diversity(bact)
        
        return {
            "overall_score": round(overall_score, 1),
            "diversity_score": round(diversity_score, 2),
        }
    except Exception as e:
        print(f"Error in calculate_overall_health_score: {e}")
        return {"overall_score": 2.5, "diversity_score": 0.0}

def group_bacteria_for_carousel(bacteria_analysis: List[Dict]) -> Dict:
    print(f"🔍 group_bacteria_for_carousel received {len(bacteria_analysis)} bacteria")
    for b in bacteria_analysis[:3]:  # Print first 3 for debugging
        print(f"  - {b.get('bacteria_name')}: {b.get('category')} / {b.get('percentage')}")
    try:
        carousel_groups = {
            "bacteria":   {"title": "Top Bacterial Species", "status": "Good", "species": []},
            "probiotics": {"title": "Probiotic Organisms",   "status": "Good", "species": []},
            "pathogens":  {"title": "Pathogenic Bacteria",   "status": "Monitor","species": []},
            "virus":      {"title": "Viral Species",         "status": "Normal","species": []},
            "fungi":      {"title": "Fungal Species",        "status": "Normal","species": []},
            "protozoa":   {"title": "Protozoa Species",      "status": "Normal","species": []},
            "keystone":   {"title": "⭐ Keystone Species",   "status": "Important","species": []},
        }
        for b in bacteria_analysis:
            
            bname = (b["bacteria_name"] or "").lower()
            cat = b["category"]
            is_keystone = b.get("is_keystone", False)
            print(f"Processing: {b['bacteria_name']} -> {b['category']} (Keystone: {is_keystone})")

            # Determine target category
            if cat == "beneficial":
                if any(p in bname for p in ["lactobacillus","bifidobacterium","acidophilus","plantarum",
                                            "rhamnosus","casei","longum","saccharomyces"]):
                    target = "probiotics"
                else:
                    target = "bacteria"
            elif cat == "pathogenic":
                target = "pathogens"
            else:
                if any(v in bname for v in ["phage","virus"]): target = "virus"
                elif any(f in bname for f in ["candida","saccharomyces","malassezia"]): target = "fungi"
                elif any(p in bname for p in ["blastocystis","entamoeba","giardia"]): target = "protozoa"
                else: target = "bacteria"

            range_fill, marker = calculate_visualization_metrics(b["percentage"])
            species_data = {
                "name": b["bacteria_name"],
                "scientific_name": b["bacteria_name"],
                "current_level": b["abundance"],
                "percentage": b["percentage"],
                "status": b["status"],
                "evidence_strength": b["evidence_strength"],
                "msp_id": b["msp_id"],
                "measurement_unit": "relative_abundance_fraction",
                "is_beneficial": cat == "beneficial",
                "range_fill_width": range_fill,
                "marker_position": marker,
                "microbewiki_url": b.get("microbewiki_url"),
                "is_keystone": is_keystone,
                "keystone_category": b.get("keystone_category")
            }
            
            # Add to regular category
            carousel_groups[target]["species"].append(species_data)
            
            # Also add to keystone category if it's a keystone species
            if is_keystone:
                carousel_groups["keystone"]["species"].append(species_data)
                
        print(f"🔍 Final carousel groups: {[(k, len(v['species'])) for k, v in carousel_groups.items()]}")

        # Sort and set status for each group
        for g in carousel_groups.values():
            g["species"].sort(key=lambda x: x["current_level"], reverse=True)
            if g["species"]:
                good = sum(1 for s in g["species"] if s["status"]=="good")
                normal = sum(1 for s in g["species"] if s["status"]=="normal")
                high = sum(1 for s in g["species"] if s["status"]=="high")
                if good > 0: g["status"]="Good"
                elif normal >= high: g["status"]="Normal"
                elif high > 0: g["status"]="Monitor"
                else: g["status"]="Low"
        
        # Remove empty groups (except keystone which we always want to check)
        carousel_groups = {k: v for k, v in carousel_groups.items() if v["species"] or k == "keystone"}
        
        return carousel_groups
    except Exception as e:
        print(f"[carousel group error] {e}")
        return {}

# -----------------------------------------------------------------------------
# ROOT (Portal)
# -----------------------------------------------------------------------------
@app.get("/", tags=["Portal"])
def root():
    return {"message": "MannBiome Customer Portal API", "status": "running", "version": "1.0.0", "docs_url": "/docs"}

# -----------------------------------------------------------------------------
# USER PROFILE (Portal)
# -----------------------------------------------------------------------------
@app.get("/api/user/{user_id}/profile", tags=["Portal"])
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection not available")
    try:
        q = text("""
            SELECT ua.user_id, ua.username, ua.email, ua.first_name, ua.last_name,
                   ua.created_at, ua.last_login, ua.status, ua.age
            FROM public.user_account ua
            WHERE ua.user_id = :uid AND ua.role = 'patient'
        """)
        row = db.execute(q, {"uid": user_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")

        user = dict(row._mapping)
        user["created_at"] = _format_date(user.get("created_at"))
        user["last_updated"] = _format_date(user.get("last_login"))
        fn = (user.get("first_name") or "").strip()
        ln = (user.get("last_name") or "").strip()
        user["full_name"] = f"{fn} {ln}".strip()
        user["initials"] = ((fn[:1] + ln[:1]).upper() or None)
        user["report_id"] = f"MG{user_id:04d}"
        return {"success": True, "user": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving profile: {e}")

# -----------------------------------------------------------------------------
# MICROBIOME DATA (Portal)
# -----------------------------------------------------------------------------
def _latest_patient_report(db: Session, participant_id: str):
    row = db.execute(text("""
        SELECT participant_id, lab_name, upload_date, bacteria_data, total_bacteria_count
        FROM public.patient_reports
        WHERE participant_id = :pid
        ORDER BY upload_date DESC
        LIMIT 1
    """), {"pid": participant_id}).fetchone()
    return row

@app.get("/api/microbiome-data/{customer_id}", tags=["Portal"])
def get_microbiome_data(customer_id: int, db: Session = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection not available")
    try:
        participant_id = str(customer_id)
        row = _latest_patient_report(db, participant_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"No microbiome data for customer {customer_id}")

        bacteria_data = (row.bacteria_data or [])
        analysis = []
        for item in bacteria_data:
            name = (item or {}).get("bacteria_name","").strip()
            # Support both "abundance" and "relative_abundance" fields
            abundance = float((item or {}).get("relative_abundance") or (item or {}).get("abundance") or 0)
            ev = (item or {}).get("evidence_strength","C")
            msp_id = (item or {}).get("msp_id","")
            units = (item or {}).get("units","relative_abundance_fraction")
            wiki_url = (item or {}).get("microbewiki_url")
            cat = categorize_bacteria_by_name(name)
            
            # Check if abundance is already a percentage (>1) or a fraction (0-1)
            # New upload feature stores as percentage (10.61), old data as fraction (0.1061)
            if abundance > 1.0:
                # Already a percentage
                pct = round(abundance, 2)
            else:
                # Fractional abundance, convert to percentage
                pct = convert_abundance_to_percentage(abundance)
            
            status = calculate_bacteria_status(abundance, ev, cat)
            # Check if keystone species
            is_keystone = is_keystone_species(name)
            keystone_category = get_keystone_category(name) if is_keystone else None
            analysis.append({
                "bacteria_name": name, "msp_id": msp_id, "abundance": abundance,
                "percentage": pct, "evidence_strength": ev, "category": cat,
                "status": status, "units": units, "microbewiki_url": wiki_url,
                "is_keystone": is_keystone, "keystone_category": keystone_category
            })
        scores = calculate_overall_health_score(analysis)
        grouped = group_bacteria_for_carousel(analysis)
        return {
            "success": True,
            "report": {
                "participant_id": row.participant_id,
                "lab_name": row.lab_name,
                "upload_date": row.upload_date.isoformat() if row.upload_date else None,
                "total_bacteria_count": row.total_bacteria_count
            },
            "scores": scores,
            "bacteria": analysis,
            "species_carousel": grouped
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving microbiome data: {e}")

@app.get("/api/customer/{customer_id}/microbiome-data", tags=["Portal"])
def get_customer_microbiome_data_frontend(customer_id: int, db: Session = Depends(get_db)):
    return get_microbiome_data(customer_id, db)

@app.get("/api/customer/{customer_id}/keystone-species", tags=["Portal"])
def get_customer_keystone_species(customer_id: int, db: Session = Depends(get_db)):
    """
    Get list of keystone species detected for a customer.
    
    Returns:
    - List of keystone bacteria with their details
    - Count of keystone species found
    - Categories of keystone species present
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection not available")
    try:
        participant_id = str(customer_id)
        row = _latest_patient_report(db, participant_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"No microbiome data for customer {customer_id}")

        bacteria_data = (row.bacteria_data or [])
        keystone_list = []
        
        for item in bacteria_data:
            name = (item or {}).get("bacteria_name", "").strip()
            if not name:
                continue
                
            # Check if keystone species
            if is_keystone_species(name):
                abundance = float((item or {}).get("relative_abundance") or (item or {}).get("abundance") or 0)
                
                # Handle percentage conversion
                if abundance > 1.0:
                    pct = round(abundance, 2)
                else:
                    pct = convert_abundance_to_percentage(abundance)
                
                keystone_list.append({
                    "bacteria_name": name,
                    "keystone_category": get_keystone_category(name),
                    "abundance": abundance,
                    "percentage": pct,
                    "evidence_strength": (item or {}).get("evidence_strength", "C"),
                    "msp_id": (item or {}).get("msp_id", ""),
                    "status": calculate_bacteria_status(abundance, (item or {}).get("evidence_strength", "C"), categorize_bacteria_by_name(name))
                })
        
        # Sort by abundance
        keystone_list.sort(key=lambda x: x["abundance"], reverse=True)
        
        # Get category summary
        categories = {}
        for k in keystone_list:
            cat = k["keystone_category"]
            if cat:
                categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "success": True,
            "customer_id": customer_id,
            "keystone_species_count": len(keystone_list),
            "categories_found": categories,
            "keystone_species": keystone_list
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving keystone species: {e}")

# -----------------------------------------------------------------------------
# PATIENT REPORT UPLOAD ENDPOINT
# -----------------------------------------------------------------------------
@app.post("/api/customer/{customer_id}/upload-report", tags=["Portal"])
async def upload_patient_report(
    customer_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process a patient PDF report.
    
    - Validates customer exists
    - Saves PDF to local storage (S3-compatible path structure)
    - Parses bacteria data from PDF
    - Scores bacteria across 8 health domains
    - Stores results in database
    - Returns processing results immediately (synchronous)
    """
    try:
        # Step 1: Validate customer exists
        result = db.execute(
            text("SELECT customer_id, user_id FROM customers.customer WHERE customer_id = :cid"),
            {"cid": customer_id}
        )
        customer = result.fetchone()
        
        if not customer:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
        
        # Step 2: Validate file is PDF
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Step 3: Create customer-specific upload directory (S3-compatible structure)
        upload_base = os.getenv("UPLOAD_BASE_PATH", "./uploads")
        customer_dir = Path(upload_base) / str(customer_id)
        customer_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"report_{timestamp}.pdf"
        pdf_path = customer_dir / pdf_filename
        
        # Step 4: Save PDF to local storage
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Step 5: Import processing pipeline
        from src.patient_processing.patient_report_parser import PatientReportParser
        from src.patient_processing.bacteria_scorer import BacteriaScorer
        from src.patient_processing.patient_data_inserter import PatientDataInserter
        
        # Step 6: Parse PDF - returns DataFrame
        parser = PatientReportParser()
        bacteria_df = parser.parse_report(str(pdf_path))
        
        if bacteria_df is None or bacteria_df.empty:
            raise HTTPException(
                status_code=400, 
                detail="Failed to extract bacteria data from PDF. Please ensure the PDF is in the correct format."
            )
        
        # Step 7: Score bacteria across domains - expects DataFrame, returns DataFrame with scored bacteria
        scorer = BacteriaScorer()
        scoring_results = scorer.score_patient_bacteria(bacteria_df)
        
        # Check if scoring was successful
        if scoring_results is None or scoring_results.empty:
            # No bacteria were matched to domains, but we can still save the raw bacteria
            domain_scores_df = pd.DataFrame(columns=['domain', 'domain_score', 'bacteria_count'])
        else:
            # Step 8: Calculate domain scores from scored bacteria
            domain_scores_df = scoring_results.groupby('domain').agg({
                'impact_score': 'mean',
                'bacteria_name': 'count'
            }).rename(columns={'impact_score': 'domain_score', 'bacteria_name': 'bacteria_count'}).reset_index()
        
        # Step 9: Check if customer already has a report (overwrite)
        existing_check = db.execute(
            text("SELECT upload_id FROM public.patient_reports WHERE participant_id = :pid"),
            {"pid": str(customer_id)}
        )
        existing_report = existing_check.fetchone()
        
        if existing_report:
            # Delete existing report and related data
            db.execute(
                text("DELETE FROM public.patient_bacteria_scores WHERE participant_id = :pid"),
                {"pid": str(customer_id)}
            )
            db.execute(
                text("DELETE FROM public.patient_domain_scores WHERE participant_id = :pid"),
                {"pid": str(customer_id)}
            )
            db.execute(
                text("DELETE FROM public.patient_reports WHERE participant_id = :pid"),
                {"pid": str(customer_id)}
            )
            db.commit()
        
        # Step 10: Insert into database using PatientDataInserter
        inserter = PatientDataInserter()
        inserter.connect()
        
        try:
            # Insert patient report and get upload_id
            upload_id = inserter.insert_patient_report(
                participant_id=str(customer_id),
                timepoint='Baseline',  # Default timepoint
                bacteria_df=bacteria_df,
                lab_name=None,
                sample_id=None,
                report_date=None,
                original_filename=file.filename,
                extraction_confidence=1.0,
                extraction_notes=None
            )
            
            # Insert bacteria scores if available
            if not scoring_results.empty:
                inserter.insert_bacteria_scores(
                    upload_id=upload_id,
                    participant_id=str(customer_id),
                    bacteria_scores_df=scoring_results
                )
            
            # Insert domain scores if available
            if not domain_scores_df.empty:
                # Add required columns for insert_domain_scores
                domain_scores_df['positive_bacteria'] = domain_scores_df.get('positive_bacteria', 0)
                domain_scores_df['negative_bacteria'] = domain_scores_df.get('negative_bacteria', 0)
                domain_scores_df['dominant_bacteria'] = domain_scores_df.get('dominant_bacteria', None)
                domain_scores_df['dominant_impact'] = domain_scores_df.get('dominant_impact', 0.0)
                domain_scores_df['avg_confidence'] = domain_scores_df.get('avg_confidence', 1.0)
                domain_scores_df['total_impact'] = domain_scores_df['domain_score']  # Rename for inserter
                
                inserter.insert_domain_scores(
                    upload_id=upload_id,
                    participant_id=str(customer_id),
                    domain_scores_df=domain_scores_df
                )
            
            # Commit all changes
            inserter.conn.commit()
            
        except Exception as e:
            inserter.conn.rollback()
            raise Exception(f"Database insertion failed: {str(e)}")
        
        finally:
            inserter.disconnect()
        
        # Step 11: Return processing results
        bacteria_scored = len(scoring_results['bacteria_name'].unique()) if not scoring_results.empty else 0
        
        return {
            "success": True,
            "customer_id": customer_id,
            "upload_timestamp": timestamp,
            "pdf_path": str(pdf_path),
            "processing_results": {
                "total_bacteria": len(bacteria_df),
                "bacteria_scored": bacteria_scored,
                "domains_analyzed": len(domain_scores_df),
                "domain_scores": {
                    row['domain']: {
                        "score": float(row['domain_score']),
                        "bacteria_count": int(row['bacteria_count'])
                    }
                    for _, row in domain_scores_df.iterrows()
                } if not domain_scores_df.empty else {}
            },
            "message": "Report uploaded and processed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up uploaded file if processing fails
        if 'pdf_path' in locals() and Path(pdf_path).exists():
            Path(pdf_path).unlink()
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing report: {str(e)}"
        )

# -----------------------------------------------------------------------------
# DASHBOARD DATA (Portal) — uses real data only (no mock)
# -----------------------------------------------------------------------------
def _status_from_score(score: float) -> str:
    if score >= 3.5: return "good"
    if score >= 2.5: return "warning"
    return "poor"

# @app.get("/api/customer/{customer_id}/dashboard-data", tags=["Portal"])
# def get_customer_dashboard_data(customer_id: int, db: Session = Depends(get_db)):
#     if db is None:
#         raise HTTPException(status_code=503, detail="Database connection not available")
#     # user
#     u = get_user_profile(customer_id, db)
#     # microbiome
#     micro = get_microbiome_data(customer_id, db)
#     if not (u and micro and micro.get("success")):
#         raise HTTPException(status_code=404, detail="Missing profile or microbiome data")

#     ms = micro["scores"]
#     microbiome_data = {
#         "score": ms["overall_score"],
#         "diversity": ms["diversity_score"],
#         "status": _status_from_score(ms["overall_score"])
#     }
#     health_data = {
#         "diversity_score": ms["diversity_score"],
#         "overall_score": ms["overall_score"],
#         "last_updated": micro["report"]["upload_date"],
#         "domains": {
#             "overall": {"score": ms["overall_score"], "diversity": ms["diversity_score"], "status": microbiome_data["status"]},
#             "gut":     {"score": ms["overall_score"], "diversity": ms["diversity_score"], "status": microbiome_data["status"]},
#             "liver":     {"score": ms["overall_score"], "diversity": ms["diversity_score"], "status": microbiome_data["status"]},
#             "skin":     {"score": ms["overall_score"], "diversity": ms["diversity_score"], "status": microbiome_data["status"]},
#             "aging":     {"score": ms["overall_score"], "diversity": ms["diversity_score"], "status": microbiome_data["status"]},
#             "cognitive":     {"score": ms["overall_score"], "diversity": ms["diversity_score"], "status": microbiome_data["status"]},
#             "heart":     {"score": ms["overall_score"], "diversity": ms["diversity_score"], "status": microbiome_data["status"]},
#         },
#         "bacteria_analyzed": len(micro.get("bacteria", [])),
#         "data_source": "REAL_MICROBIOME_DATA"
#     }
#     return {
#         "success": True,
#         "dashboard_data": {
#             "user": u["user"],
#             "health_data": health_data,
#             "customer_id": customer_id,
#             "user_id": customer_id
#         }
#     }
@app.get("/api/customer/{customer_id}/dashboard-data", tags=["Portal"])
def get_customer_dashboard_data(customer_id: int, db: Session = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection not available")

    # user
    u = get_user_profile(customer_id, db)

    # microbiome JSON (still used for top-level overall + fallback)
    micro = get_microbiome_data(customer_id, db)
    if not (u and micro and micro.get("success")):
        raise HTTPException(status_code=404, detail="Missing profile or microbiome data")

    ms = micro["scores"]
    fallback_status = _status_from_score(ms["overall_score"])

    # pull domain scores from DB
    domain_scores = _fetch_domain_scores_for_customer(customer_id, db)

    # Map your canonical ids -> response keys
    DOMAIN_MAP = {
        1: "gut",
        2: "liver",
        3: "heart",
        4: "skin",
        5: "cognitive",
        6: "aging",
        # 7: "immune",   # not shown per your note
        # 8: "overall",  # not used in per-domain reports
    }

    # build domains object using DB where available, fallback to JSON scores otherwise
    domains_out = {
        "overall": {
            "score": ms["overall_score"],
            "diversity": ms["diversity_score"],
            "status": fallback_status,
        }
    }
    for did, name in DOMAIN_MAP.items():
        if did in domain_scores:
            d = domain_scores[did]
            domains_out[name] = {
                "score": d["score"],
                "diversity": d["diversity"],
                "status": d["status"]
            }
        else:
            # fallback so UI still renders even if a domain report is missing
            domains_out[name] = {
                "score": ms["overall_score"],
                "diversity": ms["diversity_score"],
                "status": fallback_status
            }

    health_data = {
        "diversity_score": ms["diversity_score"],
        "overall_score": ms["overall_score"],
        "last_updated": micro["report"]["upload_date"],
        "domains": domains_out,
        "bacteria_analyzed": len(micro.get("bacteria", [])),
        "data_source": "REAL_MICROBIOME_DATA_WITH_DOMAIN_REPORTS"
    }

    return {
        "success": True,
        "dashboard_data": {
            "user": u["user"],
            "health_data": health_data,
            "customer_id": customer_id,
            "user_id": customer_id
        }
    }

# -----------------------------------------------------------------------------
# DOMAIN DETAILS / METRICS / MODALS (Portal)
# -----------------------------------------------------------------------------
@app.get("/api/health-domains/{domain_id}/details", tags=["Portal"])
def get_domain_details_enhanced(domain_id: str, customer_id: Optional[int] = None, db: Session = Depends(get_db)):
    # Keep this as descriptive metadata (non-mock, non-DB)
    info_map = {
        "liver": {
            "title": "Liver Health Analysis",
            "description": "Liver function relates to detoxification, metabolism, and inflammation.",
            "current_status": "—",
            "key_indicators": [
                "Bile acid metabolism", "Phase I & II detox pathways",
                "Metabolic markers", "Inflammatory response"
            ],
        },
        "cognitive": {
            "title": "Cognitive Health Analysis",
            "description": "Brain–gut axis, neurotransmitter balance, neuroinflammation.",
            "current_status": "—",
            "key_indicators": [
                "Neurotransmitter balance", "Gut–brain axis",
                "Neuroinflammation", "Cognitive performance"
            ],
        },
        "aging": {
            "title": "Aging & Longevity",
            "description": "Cellular regeneration, oxidative stress, inflammaging.",
            "current_status": "—",
            "key_indicators": [
                "Antioxidant defense", "Inflammaging", "Metabolic efficiency"
            ],
        },
        "skin": {
            "title": "Skin Health",
            "description": "Barrier function, inflammation, microbiome balance.",
            "current_status": "—",
            "key_indicators": [
                "Barrier integrity", "Inflammation", "Hydration/elasticity"
            ],
        },
        "heart": {
            "title": "Heart / Cardiometabolic",
            "description": "Lipids, inflammation, endothelial function.",
            "current_status": "—",
            "key_indicators": [
                "Lipids", "Inflammation", "Endothelial function"
            ],
        },
        "gut": {
            "title": "Gut Health",
            "description": "Diversity, beneficial vs opportunistic species.",
            "current_status": "—",
            "key_indicators": [
                "Diversity", "Beneficial abundance", "Opportunistic control"
            ],
        }
    }
    return info_map.get(str(domain_id).lower(), {"title": str(domain_id), "description": "Domain", "current_status": "—", "key_indicators": []})

@app.get("/api/health-domains/{domain_id}/metrics/{customer_id}", tags=["Portal"])
def get_domain_metrics(domain_id: int, customer_id: int, db: Session = Depends(get_db)):
    # If domain_reports exist, use them; else compute lightweight metrics from microbiome data
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection not available")
    # Try domain_reports
    dr = db.execute(text("""
    SELECT dr.score, dr.diversity, dr.status
    FROM microbiome.domain_reports dr
    JOIN microbiome.health_reports hr ON dr.report_id = hr.report_id
    WHERE dr.domain_id = :did AND hr.customer_id = :cid
    ORDER BY hr.created_at DESC
    LIMIT 1
"""), {"did": domain_id, "cid": customer_id}).fetchone()
    if dr:
        return {"success": True, "score": float(dr.score), "diversity": float(dr.diversity), "status": dr.status}

    # Fallback to compute from microbiome JSON if present
    micro = get_microbiome_data(customer_id, db)
    if not (micro and micro.get("success")):
        raise HTTPException(status_code=404, detail="No metrics available")
    scores = micro["scores"]
    return {"success": True, "score": scores["overall_score"], "diversity": scores["diversity_score"], "status": _status_from_score(scores["overall_score"])}

def _species_for_domain(customer_id: int, domain_id: int, db: Session) -> List[Dict[str, Any]]:
    # Map patient JSON bacteria to a domain via vectordb.bacteria_domain_associations
    r = _latest_patient_report(db, str(customer_id))
    if not r or not r.bacteria_data:
        return []
    # load associations
    assoc = db.execute(text("""
    SELECT domain, bacteria_name, association_type, confidence_score
    FROM vectordb.bacteria_domain_associations
    WHERE domain IS NOT NULL
""")).fetchall()
    by_name = {}
    for a in assoc:
        by_name.setdefault(a.bacteria_name.lower(), []).append(a)
    # get desired domain label (string) for given domain_id
    dn = db.execute(text("SELECT domain_name FROM microbiome.health_domains WHERE domain_id = :d"), {"d": domain_id}).fetchone()
    if not dn:
        return []
    domain_name = str(dn.domain_name)
    out = []
    for item in r.bacteria_data:
        name = (item or {}).get("bacteria_name","").strip()
        if not name: continue
        # Support both "abundance" and "relative_abundance" fields
        abundance = float((item or {}).get("relative_abundance") or (item or {}).get("abundance") or 0)
        ev = (item or {}).get("evidence_strength","C")
        msp_id = (item or {}).get("msp_id","")  # Add this line
        units = (item or {}).get("units","relative_abundance_fraction")
        matches = by_name.get(name.lower(), [])
        if not any(m.domain == domain_name for m in matches):
            continue
        
        # Check if abundance is already a percentage (>1) or a fraction (0-1)
        if abundance > 1.0:
            # Already a percentage (new upload data)
            pct = round(abundance, 2)
        else:
            # Fractional abundance (old data), convert to percentage
            pct = convert_abundance_to_percentage(abundance)
        
        cat = categorize_bacteria_by_name(name)
        status = calculate_bacteria_status(abundance, ev, cat)
        microbewiki_url = (item or {}).get("microbewiki_url")
        # Check if keystone species
        is_keystone = is_keystone_species(name)
        keystone_category = get_keystone_category(name) if is_keystone else None
        out.append({
            "bacteria_name": name,
            "msp_id": msp_id,  # Add this line
            "abundance": abundance,
            "percentage": pct,
            "evidence_strength": ev,
            "units": units,
            "category": cat,
            "status": status,
            "microbewiki_url": microbewiki_url,
            "is_keystone": is_keystone,
            "keystone_category": keystone_category,
            "description": f"Associated with {domain_name} ({next((m.association_type for m in matches if m.domain == domain_name), 'neutral')})"
        })
    return out

def _pathways_for_domain_report(domain_report_id: int, db: Session) -> List[Dict[str, Any]]:
    rows = db.execute(text("""
        SELECT pathway_category, pathway_title, metric_name, current_level, optimal_level, range_label_low, range_label_high
        FROM microbiome.pathway_analysis
        WHERE domain_report_id = :drid
        ORDER BY pathway_category, pathway_title
    """), {"drid": domain_report_id}).fetchall()
    return [dict(r._mapping) for r in rows]

@app.get("/api/health-domains/{domain_id}/modal-data/{customer_id}", tags=["Portal"])
def get_domain_modal_data(domain_id: int, customer_id: int, db: Session = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection not available")
    
    # latest domain report for this user+domain if available
    dr = db.execute(text("""
        SELECT dr.domain_report_id, dr.score, dr.diversity, dr.status, dr.comment, hd.domain_name, hd.description
        FROM microbiome.domain_reports dr
        JOIN microbiome.health_reports hr ON dr.report_id = hr.report_id
        JOIN microbiome.health_domains hd ON dr.domain_id = hd.domain_id
        WHERE dr.domain_id = :did AND hr.customer_id = :cid
        ORDER BY hr.created_at DESC
        LIMIT 1
    """), {"did": domain_id, "cid": customer_id}).fetchone()
    
    domain_meta = db.execute(text("SELECT domain_name, description FROM microbiome.health_domains WHERE domain_id = :d"), {"d": domain_id}).fetchone()
    if not dr and not domain_meta:
        raise HTTPException(status_code=404, detail="Domain not found or no data")

    # species (from patient JSON + associations)
    species = _species_for_domain(customer_id, domain_id, db)

    # pathway (from pathway_analysis if report exists)
    pathways = _pathways_for_domain_report(dr.domain_report_id, db) if dr else []

    return {
        "success": True,
        "domain": {
            "domain_id": domain_id,
            "domain_name": (dr.domain_name if dr else domain_meta.domain_name),
            "description": (dr.description if dr else domain_meta.description),
            "score": float(dr.score) if dr else None,
            "diversity": float(dr.diversity) if dr else None,
            "status": dr.status if dr else None,
            "comment": dr.comment if dr else None
        },
        "species_carousel": group_bacteria_for_carousel(species),
        "pathway_carousel": pathways
    }

@app.get("/api/health-domains/{domain_id}/species-carousel/{customer_id}", tags=["Portal"])
def get_species_carousel_only(domain_id: int, customer_id: int, db: Session = Depends(get_db)):
    species = _species_for_domain(customer_id, domain_id, db)
    if not species:
        raise HTTPException(status_code=404, detail="No species mapped for this domain/customer")
    return {"success": True, "species_carousel": group_bacteria_for_carousel(species)}

@app.get("/api/health-domains/{domain_id}/pathway-carousel/{customer_id}", tags=["Portal"])
def get_pathway_carousel_only(domain_id: int, customer_id: int, db: Session = Depends(get_db)):
    dr = db.execute(text("""
    SELECT dr.domain_report_id
    FROM microbiome.domain_reports dr
    JOIN microbiome.health_reports hr ON dr.report_id = hr.report_id
    WHERE dr.domain_id = :did AND hr.customer_id = :cid
    ORDER BY hr.created_at DESC
    LIMIT 1
"""), {"did": domain_id, "cid": customer_id}).fetchone()
    if not dr:
        raise HTTPException(status_code=404, detail="No domain report found for pathway data")
    pathways = _pathways_for_domain_report(dr.domain_report_id, db)
    if not pathways:
        raise HTTPException(status_code=404, detail="No pathway data found")
    return {"success": True, "pathway_carousel": pathways}

@app.get("/api/health-domains/{domain_id}/recommendations-only/{customer_id}", tags=["Portal"])
def get_recommendations_only(domain_id: int, customer_id: int, db: Session = Depends(get_db)):
    # If you maintain recommendations in vectordb.rules_mappings keyed by domain, fetch them:
    rows = db.execute(text("""
        SELECT domain, rule_key, recommendation_text
        FROM vectordb.rules_mappings
        WHERE domain = (SELECT domain_name FROM microbiome.health_domains WHERE domain_id = :d)
        ORDER BY rule_key
    """), {"d": domain_id}).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="No recommendations configured for this domain")
    return {"success": True, "recommendations": [dict(r._mapping) for r in rows]}

@app.get("/api/clinical-trials", tags=["Clinical Trials"])
def get_all_trials(limit: int = 50, status: Optional[str] = None, phase: Optional[str] = None):
    """
    TYPE 1: Get all microbiome clinical trials for customer display and registration
    
    Query Parameters:
    - limit: Number of trials to return (default: 50)
    - status: Filter by trial status (RECRUITING, NOT_YET_RECRUITING)
    - phase: Filter by trial phase (PHASE_1, PHASE_2, PHASE_3, PHASE_4)
    
    Returns: All active/recruiting microbiome trials that customer can register for
    """
    try:
        from clinical_trials_service import ClinicalTrialsService
        
        service = ClinicalTrialsService()
        # Fetch comprehensive trials
        studies = service.fetch_microbiome_trials(max_results=500)
        
        # Allowed statuses (only active trials)
        ALLOWED_STATUSES = ['RECRUITING', 'NOT_YET_RECRUITING']
        
        parsed_trials = []
        for study in studies:
            trial = service.parse_trial(study)
            if trial:
                # Filter by allowed status
                trial_status = trial.get('status', '').upper()
                if trial_status in ALLOWED_STATUSES:
                    parsed_trials.append(trial)
        
        # Apply filters
        filtered_trials = parsed_trials
        
        # Filter by status if provided
        if status and status.upper() in ALLOWED_STATUSES:
            filtered_trials = [t for t in filtered_trials if t.get('status', '').upper() == status.upper()]
        
        # Filter by phase if provided
        if phase:
            filtered_trials = [t for t in filtered_trials if t.get('phase', '').upper() == phase.upper()]
        
        # Sort by enrollment (most active first)
        filtered_trials.sort(key=lambda x: x.get('enrollment', 0), reverse=True)
        
        return {
            "success": True,
            "type": "general_trials",
            "description": "All microbiome clinical trials available for registration",
            "filters_applied": {
                "status": status or "RECRUITING, NOT_YET_RECRUITING",
                "phase": phase or "all"
            },
            "trials": filtered_trials[:limit],
            "count": len(filtered_trials[:limit]),
            "total_matched": len(filtered_trials),
            "total_available": len(parsed_trials),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trials: {str(e)}")


@app.get("/api/clinical-trials/by-domain/{domain}", tags=["Clinical Trials"])
def get_trials_by_domain(
    domain: str, 
    limit: int = 50, 
    status: Optional[str] = None, 
    phase: Optional[str] = None
):
    """
    TYPE 2: Get domain-specific clinical trials for customer display and registration
    
    Path Parameters:
    - domain: Health domain (gut, liver, cardiometabolic, cognitive, kidney)
    
    Query Parameters:
    - limit: Number of trials to return (default: 50)
    - status: Filter by trial status (RECRUITING, NOT_YET_RECRUITING)
    - phase: Filter by trial phase (PHASE_1, PHASE_2, PHASE_3, PHASE_4)
    
    Returns: Active/recruiting trials specific to the selected health domain
    Matching is based ONLY on trial titles using predefined synonym lists.
    """
    try:
        from clinical_trials_service import ClinicalTrialsService
        
        service = ClinicalTrialsService()
        all_trials = service.fetch_microbiome_trials(max_results=1000)
        
        # Get domain-specific synonyms (WITHOUT universal intervention terms for precise matching)
        domain_synonyms = _get_all_domain_synonyms(domain, include_interventions=False)
        
        # Allowed statuses
        ALLOWED_STATUSES = ['RECRUITING', 'NOT_YET_RECRUITING']
        
        # Filter trials - TITLE ONLY
        filtered_trials = []
        for study in all_trials:
            trial = service.parse_trial(study)
            if trial:
                # Check status
                trial_status = trial.get('status', '').upper()
                if trial_status not in ALLOWED_STATUSES:
                    continue
                
                # Check domain match by TITLE ONLY using synonyms
                if _matches_any_synonym(trial.get('title', ''), domain_synonyms):
                    filtered_trials.append(trial)
        
        # Apply additional filters
        if status and status.upper() in ALLOWED_STATUSES:
            filtered_trials = [t for t in filtered_trials if t.get('status', '').upper() == status.upper()]
        
        if phase:
            filtered_trials = [t for t in filtered_trials if t.get('phase', '').upper() == phase.upper()]
        
        # Sort by enrollment
        filtered_trials.sort(key=lambda x: x.get('enrollment', 0), reverse=True)
        
        return {
            "success": True,
            "type": "domain_specific_trials",
            "description": f"Clinical trials related to {domain.upper()} health (title-based matching)",
            "domain": domain.lower(),
            "matching_method": "title_only_with_synonyms",
            "synonym_count": len(domain_synonyms),
            "filters_applied": {
                "status": status or "RECRUITING, NOT_YET_RECRUITING",
                "phase": phase or "all"
            },
            "trials": filtered_trials[:limit],
            "count": len(filtered_trials[:limit]),
            "total_matched": len(filtered_trials),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trials for domain: {str(e)}")


@app.get("/api/clinical-trials/search", tags=["Clinical Trials"])
def search_trials(
    q: str, 
    limit: int = 50, 
    status: Optional[str] = None, 
    phase: Optional[str] = None
):
    """
    Search clinical trials by keyword/domain
    
    Supports both simple and compound queries:
    - Simple: "Probiotics" → search synonym-based
    - Compound: "Gut microbiome AND depression" → match both domain AND condition
    
    Query Parameters:
    - q: Search keyword/phrase or compound query (use AND for multiple domains/conditions)
    - limit: Number of trials to return (default: 50)
    - status: Filter by trial status (RECRUITING, NOT_YET_RECRUITING)
    - phase: Filter by trial phase (PHASE_1, PHASE_2, PHASE_3, PHASE_4)
    
    Returns: Matching active/recruiting trials (TITLE-BASED MATCHING ONLY)
    """
    try:
        from clinical_trials_service import ClinicalTrialsService
        
        service = ClinicalTrialsService()
        all_trials = service.fetch_microbiome_trials(max_results=1000)
        
        # Allowed statuses
        ALLOWED_STATUSES = ['RECRUITING', 'NOT_YET_RECRUITING']
        
        # Parse compound query (e.g., "Gut microbiome AND depression")
        query_parts = [part.strip() for part in q.split(" AND ")]
        all_query_synonyms = []
        
        for query_part in query_parts:
            # Check if it's a domain name
            if query_part.lower() in CLINICAL_TRIALS_SYNONYMS:
                synonyms = _get_all_domain_synonyms(query_part.lower())
            else:
                # Treat as free-text search - look for synonyms matching this term
                synonyms = []
                # Search across all domains for matching synonyms
                for domain_key, domain_data in CLINICAL_TRIALS_SYNONYMS.items():
                    for category, terms in domain_data.items():
                        for term in terms:
                            if query_part.lower() in term.lower():
                                synonyms.append(term)
                
                # If no synonyms found, use the query term as-is (partial match)
                if not synonyms:
                    synonyms = [query_part]
            
            all_query_synonyms.extend(synonyms)
        
        # Filter by search query and status - TITLE ONLY
        matched_trials = []
        for study in all_trials:
            trial = service.parse_trial(study)
            if trial:
                # Check status
                trial_status = trial.get('status', '').upper()
                if trial_status not in ALLOWED_STATUSES:
                    continue
                
                # Check search query against TITLE ONLY (word boundary match)
                title = trial.get('title', '').lower()
                if any(re.search(r'\b' + re.escape(synonym.lower()) + r'\b', title) for synonym in all_query_synonyms):
                    matched_trials.append(trial)
        
        # Apply additional filters
        if status and status.upper() in ALLOWED_STATUSES:
            matched_trials = [t for t in matched_trials if t.get('status', '').upper() == status.upper()]
        
        if phase:
            matched_trials = [t for t in matched_trials if t.get('phase', '').upper() == phase.upper()]
        
        # Sort by enrollment
        matched_trials.sort(key=lambda x: x.get('enrollment', 0), reverse=True)
        
        return {
            "success": True,
            "type": "search_results",
            "description": f"Search results for '{q}' (title-based matching with synonyms)",
            "search_query": q,
            "matching_method": "title_only_with_synonyms",
            "query_parts": query_parts,
            "synonyms_used": list(set(all_query_synonyms[:20])),  # Show first 20 unique synonyms
            "filters_applied": {
                "status": status or "RECRUITING, NOT_YET_RECRUITING",
                "phase": phase or "all"
            },
            "trials": matched_trials[:limit],
            "count": len(matched_trials[:limit]),
            "total_matched": len(matched_trials),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching trials: {str(e)}")


@app.get("/api/customer/{customer_id}/clinical-trials", tags=["Clinical Trials"])
def get_customer_relevant_trials(
    customer_id: int, 
    limit: int = 50, 
    status: Optional[str] = None, 
    phase: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """
    Get clinical trials relevant to customer's health domains
    
    Path Parameters:
    - customer_id: Customer ID
    
    Query Parameters:
    - limit: Number of trials to return (default: 50)
    - status: Filter by trial status (RECRUITING, NOT_YET_RECRUITING)
    - phase: Filter by trial phase (PHASE_1, PHASE_2, PHASE_3, PHASE_4)
    
    Returns: Trials matching customer's health profile
    Matching is based ONLY on trial titles using domain-specific synonyms
    """
    try:
        from clinical_trials_service import ClinicalTrialsService
        
        # Get customer's health domains from dashboard
        customer_domains = []
        try:
            dashboard = get_customer_dashboard_data(customer_id, db)
            if dashboard and "dashboard_data" in dashboard:
                domains_dict = dashboard["dashboard_data"]["health_data"]["domains"]
                customer_domains = [d for d in domains_dict.keys() if d != "overall"]
        except:
            # Default fallback
            customer_domains = ["gut"]
        
        # Allowed statuses
        ALLOWED_STATUSES = ['RECRUITING', 'NOT_YET_RECRUITING']
        
        service = ClinicalTrialsService()
        all_trials = service.fetch_microbiome_trials(max_results=1000)
        
        # Collect all synonyms from customer's domains
        all_domain_synonyms = []
        for domain in customer_domains:
            all_domain_synonyms.extend(_get_all_domain_synonyms(domain))
        
        # Remove duplicates while preserving order
        all_domain_synonyms = list(dict.fromkeys(all_domain_synonyms))
        
        # Filter trials by customer domains - TITLE ONLY
        relevant_trials = []
        for study in all_trials:
            trial = service.parse_trial(study)
            if trial:
                # Check status
                trial_status = trial.get('status', '').upper()
                if trial_status not in ALLOWED_STATUSES:
                    continue
                
                # Check domain match by TITLE ONLY using all domain synonyms
                if _matches_any_synonym(trial.get('title', ''), all_domain_synonyms):
                    relevant_trials.append(trial)
        
        # Apply additional filters
        if status and status.upper() in ALLOWED_STATUSES:
            relevant_trials = [t for t in relevant_trials if t.get('status', '').upper() == status.upper()]
        
        if phase:
            relevant_trials = [t for t in relevant_trials if t.get('phase', '').upper() == phase.upper()]
        
        # Sort by enrollment
        relevant_trials.sort(key=lambda x: x.get('enrollment', 0), reverse=True)
        
        return {
            "success": True,
            "type": "customer_personalized_trials",
            "description": "Clinical trials personalized to customer's health domains (title-based matching)",
            "customer_id": customer_id,
            "customer_domains": customer_domains,
            "matching_method": "title_only_with_synonyms",
            "synonym_count": len(all_domain_synonyms),
            "filters_applied": {
                "status": status or "RECRUITING, NOT_YET_RECRUITING",
                "phase": phase or "all"
            },
            "trials": relevant_trials[:limit],
            "count": len(relevant_trials[:limit]),
            "total_matched": len(relevant_trials),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching customer trials: {str(e)}")

# -----------------------------------------------------------------------------
# ----------------------------  DOMAIN API (separate)  ------------------------
# -----------------------------------------------------------------------------
@app.get("/api/customer/{customer_id}/info", tags=["Domain"])
def get_customer_info(customer_id: int, db: Session = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        r1 = db.execute(text("SELECT user_id FROM customers.customer WHERE customer_id = :cid"),
                        {"cid": customer_id}).fetchone()
        if not r1:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
        user_id = r1.user_id

        r2 = db.execute(text("""
            SELECT 
                c.customer_id, c.user_id, c.date_of_birth, c.gender, c.phone,
                c.address, c.city, c.state, c.postal_code, c.country,
                c.created_at as customer_created_at, c.updated_at as customer_updated_at,
                u.username, u.email, u.first_name, u.last_name,
                u.created_at as user_created_at, u.role, u.status, u.age as user_age
            FROM customers.customer c
            JOIN public.user_account u ON c.user_id = u.user_id
            WHERE c.user_id = :uid
        """), {"uid": user_id}).fetchone()
        if not r2:
            raise HTTPException(status_code=404, detail=f"User data not found for customer {customer_id}")

        full_name = f"{(r2.first_name or '').strip()} {(r2.last_name or '').strip()}".strip()
        initials = ((r2.first_name or '')[:1] + (r2.last_name or '')[:1]).upper() or None

        age_calc = None
        if r2.date_of_birth:
            today = datetime.now().date()
            b = r2.date_of_birth
            age_calc = today.year - b.year - ((today.month, today.day) < (b.month, b.day))

        return {
            "success": True,
            "customer_info": {
                "customer_id": r2.customer_id,
                "user_id": r2.user_id,
                "username": r2.username,
                "email": r2.email,
                "first_name": r2.first_name,
                "last_name": r2.last_name,
                "full_name": full_name,
                "initials": initials,
                "age": age_calc if age_calc is not None else r2.user_age,
                "role": r2.role,
                "status": r2.status,
                "address": r2.address,
                "city": r2.city, "state": r2.state, "postal_code": r2.postal_code, "country": r2.country,
                "created_at": r2.customer_created_at.isoformat() if r2.customer_created_at else None,
                "updated_at": r2.customer_updated_at.isoformat() if r2.customer_updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving customer info: {e}")
    
# ===============================================================
# Data Extraction from patient_reports JSONB
# ===============================================================

def get_bacteria_domain_data_from_reports(participant_id: str, db: Session) -> Dict:
    """
    Extract bacteria domain data using your existing patient_reports table
    """
    try:
        print(f"🔬 Extracting bacteria data for participant {participant_id}")
        
        # First, get the patient's bacteria data from patient_reports
        patient_query = text("""
            SELECT 
                upload_id,
                participant_id,
                lab_name,
                upload_date,
                bacteria_data,
                total_bacteria_count
            FROM patient_reports
            WHERE participant_id = :participant_id
            ORDER BY upload_date DESC
            LIMIT 1
        """)
        
        patient_result = db.execute(patient_query, {"participant_id": participant_id}).fetchone()
        
        if not patient_result:
            print(f"❌ No patient reports found for participant {participant_id}")
            return {}
        
        if not patient_result.bacteria_data:
            print(f"❌ No bacteria data found in report for participant {participant_id}")
            return {}
        
        print(f"✅ Found {patient_result.total_bacteria_count} bacteria records for participant {participant_id}")
        
        # Parse the JSONB bacteria data
        bacteria_list = patient_result.bacteria_data
        if isinstance(bacteria_list, str):
            bacteria_list = json.loads(bacteria_list)
        
        # Get domain associations and metadata from foreign tables with case-insensitive msp_id matching
        domain_query = text("""
            SELECT DISTINCT
                bda.domain,
                bda.bacteria_name,
                bda.association_type,
                bda.confidence_score,
                bda.diseases_beneficial,
                bda.diseases_harmful,
                COALESCE(cbm.msp_id, hcbm.msp_id) as msp_id,
                COALESCE(cbm.ideal_min, hcbm.ideal_min) as ideal_min,
                COALESCE(cbm.ideal_max, hcbm.ideal_max) as ideal_max,
                COALESCE(cbm.units, hcbm.units) as units,
                COALESCE(cbm.clinical_context, hcbm.clinical_context) as clinical_context,
                COALESCE(cbm.evidence_strength, hcbm.evidence_strength) as evidence_strength
            FROM vectordb.bacteria_domain_associations bda
            LEFT JOIN vectordb.computed_bacteria_metadata cbm ON bda.bacteria_name = cbm.bacteria_name
            LEFT JOIN vectordb."Healthy_Cohort_Bacteria_Metadata" hcbm ON bda.bacteria_name = hcbm.bacteria_name
            WHERE COALESCE(cbm.msp_id, hcbm.msp_id) IS NOT NULL
            ORDER BY bda.domain, bda.confidence_score DESC
        """)
        
        domain_results = db.execute(domain_query).fetchall()
        
        if not domain_results:
            print("❌ No domain associations found in vectordb foreign tables")
            return {}
        
        print(f"✅ Found {len(domain_results)} bacteria-domain associations")
        
        # Create lookup dictionary for patient bacteria by msp_id
        patient_bacteria_lookup = {}
        for bacteria_item in bacteria_list:
            msp_id = bacteria_item.get('msp_id')
            if msp_id:
                patient_bacteria_lookup[msp_id] = bacteria_item
        
        print(f"✅ Created lookup for {len(patient_bacteria_lookup)} patient bacteria records")
        
        # Organize data by domain
        domain_data = {
            "aging": {"bacteria": [], "scores": {"diversity": 0, "overall": 0, "status": "poor"}},
            "gut": {"bacteria": [], "scores": {"diversity": 0, "overall": 0, "status": "poor"}},
            "liver": {"bacteria": [], "scores": {"diversity": 0, "overall": 0, "status": "poor"}},
            "heart": {"bacteria": [], "scores": {"diversity": 0, "overall": 0, "status": "poor"}},
            "skin": {"bacteria": [], "scores": {"diversity": 0, "overall": 0, "status": "poor"}},
            "cognitive": {"bacteria": [], "scores": {"diversity": 0, "overall": 0, "status": "poor"}},
            # "immune": {"bacteria": [], "scores": {"diversity": 0, "overall": 0, "status": "poor"}},
            # "oral": {"bacteria": [], "scores": {"diversity": 0, "overall": 0, "status": "poor"}},
            # "vaginal": {"bacteria": [], "scores": {"diversity": 0, "overall": 0, "status": "poor"}},
            "overall": {"bacteria": [], "scores": {"diversity": 0, "overall": 0, "status": "poor"}}
        }
        
        # Process each bacteria from domain associations
        for row in domain_results:
            domain = row.domain.lower()
            if domain not in domain_data:
                domain_data[domain] = {"bacteria": [], "scores": {"diversity": 0, "overall": 0, "status": "poor"}}
            
            # Find matching patient bacteria data
            patient_bacteria = patient_bacteria_lookup.get(row.msp_id)
            
            if not patient_bacteria:
                # Skip bacteria not found in patient report
                continue
            
            # Extract abundance from patient data
            abundance = float(patient_bacteria.get('abundance', 0))
            optimal_min = float(row.ideal_min) if row.ideal_min else 0.000001
            optimal_max = float(row.ideal_max) if row.ideal_max else 0.00001
            
            # Determine status based on ideal ranges
            if abundance < optimal_min * 0.8:
                status = "LOW"
            elif abundance > optimal_max * 1.2:
                status = "HIGH"
            else:
                status = "NORMAL"
            
            # Calculate current level and percentage
            current_level = f"{abundance * 1000000:.2f} units"
            
            # Calculate percentage relative to optimal range midpoint
            optimal_mid = (optimal_min + optimal_max) / 2
            percentage = min((abundance / optimal_mid) * 100, 999.9) if optimal_mid > 0 else 0.1
            
            # Determine category based on association type
            if row.association_type == "beneficial":
                category = "beneficial"
            elif row.association_type == "harmful":
                category = "concerning"
            else:
                category = "neutral"
            
            # Create bacteria entry in format.js structure
            bacteria_entry = {
                "msp_id": row.msp_id,
                "bacteria_name": row.bacteria_name.split()[-1] if " " in row.bacteria_name else row.bacteria_name,
                "full_name": row.bacteria_name,
                "abundance": abundance,
                "current_level": current_level,
                "percentage": round(percentage, 3),
                "confidence_level": patient_bacteria.get('evidence_strength', 'C'),
                "status": status,
                "optimal_range": [optimal_min, optimal_max],
                "category": category,
                "description": row.clinical_context or f"Associated with {domain} health",
                "units": patient_bacteria.get('units', 'relative_abundance_fraction')
            }
            
            domain_data[domain]["bacteria"].append(bacteria_entry)
        
        # Calculate domain scores based on bacteria status
        for domain in domain_data:
            bacteria_in_domain = domain_data[domain]["bacteria"]
            if bacteria_in_domain:
                normal_count = sum(1 for b in bacteria_in_domain if b["status"] == "NORMAL")
                total_count = len(bacteria_in_domain)
                
                diversity_score = min(4.0, total_count / 3.0)  # Diversity based on count
                overall_score = (normal_count / total_count) * 4.0 if total_count > 0 else 1.0
                
                if overall_score >= 3.5:
                    status = "excellent"
                elif overall_score >= 2.5:
                    status = "good"
                elif overall_score >= 1.5:
                    status = "warning"
                else:
                    status = "poor"
                
                domain_data[domain]["scores"] = {
                    "diversity": round(diversity_score, 1),
                    "overall": round(overall_score, 1),
                    "status": status
                }
        
        # Limit bacteria per domain for cleaner API responses
        for domain in domain_data:
            if len(domain_data[domain]["bacteria"]) > 15:
                # Keep the most significant ones (sorted by confidence score implicit in query)
                domain_data[domain]["bacteria"] = domain_data[domain]["bacteria"][:15]
        
        print(f"✅ Successfully processed data for {len([d for d in domain_data if domain_data[d]['bacteria']])} domains")
        
        return domain_data
        
    except Exception as e:
        print(f"❌ Error extracting bacteria domain data: {e}")
        traceback.print_exc()
        return {}


@app.get("/api/customer/{customer_id}/bacteria-domains", tags=["Domain"])
def get_customer_bacteria_domains(customer_id: int, db: Session = Depends(get_db)):
    """Get bacteria domain data using existing patient_reports table"""
    try:
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")
        
        participant_id = str(customer_id)  # Convert customer_id to participant_id format
        print(f"🔬 Extracting bacteria domain data for customer {customer_id} (participant {participant_id})")
        
        # Get bacteria domain data from patient_reports
        domain_bacteria = get_bacteria_domain_data_from_reports(participant_id, db)
        
        if not domain_bacteria:
            raise HTTPException(
                status_code=404, 
                detail=f"No bacteria data found for customer {customer_id}. Make sure patient reports exist in the database."
            )
        
        # Calculate overall health metrics
        total_bacteria = sum(len(domain_data["bacteria"]) for domain_data in domain_bacteria.values())
        beneficial_count = 0
        concerning_count = 0
        
        for domain_data in domain_bacteria.values():
            for bacteria in domain_data["bacteria"]:
                if bacteria["category"] == "beneficial":
                    beneficial_count += 1
                elif bacteria["category"] == "concerning":
                    concerning_count += 1
        
        overall_health = {
            "diversity_score": round(min(4.0, total_bacteria / 15.0), 1),
            "overall_score": round(max(1.0, 4.0 - (concerning_count / max(total_bacteria, 1)) * 3), 1),
            "status": "excellent" if concerning_count < beneficial_count * 0.3 else "good" if concerning_count < beneficial_count else "warning" if concerning_count < total_bacteria * 0.6 else "poor",
            "total_bacteria_analyzed": total_bacteria,
            "concerning_bacteria": concerning_count,
            "beneficial_bacteria": beneficial_count,
            "neutral_bacteria": total_bacteria - beneficial_count - concerning_count
        }
        
        return {
            "success": True,
            "customer_id": customer_id,
            "participant_id": participant_id,
            "domain_bacteria": domain_bacteria,
            "overall_health": overall_health,
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error extracting bacteria domain data: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/customer/{customer_id}/complete-profile", tags=["Domain"])
def get_complete_customer_profile(customer_id: int, db: Session = Depends(get_db)):
    try:
        info = get_customer_info(customer_id, db)
        domains = get_customer_bacteria_domains(customer_id, db)
        return {
            "success": True,
            "customer_info": info["customer_info"],
            "domain_bacteria": domains["domain_bacteria"],
            "generated_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating complete profile: {e}")

def add_header_footer(canvas_obj, doc):
    """Add professional header and footer to every page"""
    canvas_obj.saveState()
    
    width, height = A4
    
    # ==================== HEADER ====================
    # Thin professional border line
    canvas_obj.setStrokeColor(colors.HexColor('#E0E0E0'))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(40, height - 80, width - 40, height - 80)
    
    # LEFT: Logo (replace the circle code with this)
    logo_x = 50
    logo_y = height - 35
    logo_width = 120   # Width for horizontal logo
    logo_height = 50  # Height for horizontal logo

    try:
        # Path relative to where you run the Python script
        logo_path = "public/MannBiomeLogo.png"
        
        canvas_obj.drawImage(
            logo_path, 
            logo_x - 5,              # X position (adjusted for horizontal logo)
            logo_y - logo_height/2,  # Y position (centered vertically)
            width=logo_width, 
            height=logo_height, 
            mask='auto',             # Handles transparency
            preserveAspectRatio=True
        )
    except:
        # Draw circle background for logo
        canvas_obj.setFillColor(colors.HexColor('#00BFA5'))
        canvas_obj.setStrokeColor(colors.HexColor('#00BFA5'))
        canvas_obj.setLineWidth(1)
        canvas_obj.circle(logo_x, logo_y, logo_radius, fill=1, stroke=1)
        
        # Logo initials centered in circle
        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont("Helvetica-Bold", 12)
        initials_width = canvas_obj.stringWidth("MB", "Helvetica-Bold", 12)
        canvas_obj.drawString(logo_x - initials_width/2, logo_y - 4, "MB")

    
    
    
    # CENTER: Report Title (perfectly centered)
    canvas_obj.setFont("Helvetica-Bold", 14)
    canvas_obj.setFillColor(colors.HexColor('#1A365D'))
    report_title = getattr(doc, 'report_title', 'Health Analysis Report')
    title_width = canvas_obj.stringWidth(report_title, "Helvetica-Bold", 14)
    canvas_obj.drawString((width - title_width) / 2, height - 45, report_title)
    
    # RIGHT: Patient Info (properly right-aligned with email)
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(colors.HexColor('#555555'))
    
    patient_name = getattr(doc, 'patient_name', 'N/A')
    report_id = getattr(doc, 'report_id', 'N/A')
    patient_email = getattr(doc, 'patient_email', 'N/A')
    report_date = getattr(doc, 'report_date', datetime.now().strftime("%B %d, %Y"))
    
    # Calculate right alignment (from right edge)
    right_margin = 50
    y_start = height - 30
    line_height = 10
    
    # Draw each line right-aligned
    lines = [
        f"Patient: {patient_name}",
        f"Email: {patient_email}",
        f"ID: {report_id}",
        f"Date: {report_date}"
    ]
    
    y_pos = y_start
    for line in lines:
        line_width = canvas_obj.stringWidth(line, "Helvetica", 8)
        canvas_obj.drawString(width - right_margin - line_width, y_pos, line)
        y_pos -= line_height
    
    # ==================== FOOTER ====================
    # Thin border line
    canvas_obj.setStrokeColor(colors.HexColor('#E0E0E0'))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(40, 45, width - 40, 45)
    
    # Footer text
    canvas_obj.setFont("Helvetica", 7)
    canvas_obj.setFillColor(colors.HexColor('#666666'))
    
    # Left: Company info
    canvas_obj.drawString(40, 30, "MannBiome Inc. | support@mannbiome.com")
    
    # Center: Confidential
    confidential = "CONFIDENTIAL - For Patient Use Only"
    conf_width = canvas_obj.stringWidth(confidential, "Helvetica", 7)
    canvas_obj.drawString((width - conf_width) / 2, 30, confidential)
    
    # Right: Page number
    page_text = f"Page {canvas_obj.getPageNumber()}"
    page_width = canvas_obj.stringWidth(page_text, "Helvetica", 7)
    canvas_obj.drawString(width - page_width - 40, 30, page_text)
    
    canvas_obj.restoreState()



def create_health_overview_table(domain_scores: dict, styles) -> Table:
    """
    Create a professional health overview table with unified column headers
    Handles both full and filtered domain lists
    """
    table_data = []
    
    # Main header row with column titles - center-aligned
    table_data.append([
        "",  # Empty cell for domain names column
        Paragraph("<b>Score</b>", styles['Normal']),
        Paragraph("<b>Diversity</b>", styles['Normal']),
        Paragraph("<b>Status</b>", styles['Normal'])
    ])
    
    # Section 1: Complete Health Overview (subheader)
    table_data.append([
        Paragraph("<b>Complete Health Overview</b>", styles['Normal']),
        "",
        "",
        ""
    ])
    
    # Overall data row
    overall_data = domain_scores.get("overall", {})
    table_data.append([
        "Overall",
        f"{overall_data.get('score', 'N/A')}/5.0",
        f"{overall_data.get('diversity', 'N/A')}/5.0",
        overall_data.get('status', 'Unknown').title()
    ])
    
    # Section 2: Domain-Specific Analysis (subheader)
    domain_section_row = len(table_data)  # Track where domain section starts
    table_data.append([
        Paragraph("<b>Domain-Specific Analysis</b>", styles['Normal']),
        "",
        "",
        ""
    ])
    
    # Domain rows - dynamically add based on what's in domain_scores
    domain_order = ["gut", "liver", "heart", "skin", "cognitive", "aging"]
    domain_data_rows = []
    
    for domain in domain_order:
        if domain in domain_scores:
            domain_data = domain_scores[domain]
            domain_data_rows.append([
                domain.title(),
                f"{domain_data.get('score', 'N/A')}/5.0",
                f"{domain_data.get('diversity', 'N/A')}/5.0",
                domain_data.get('status', 'Unknown').title()
            ])
    
    table_data.extend(domain_data_rows)
    
    # Create table
    health_table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    
    # Build style list dynamically
    style_commands = [
        # Font styling
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        
        # Main column headers (row 0) - bold and colored
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1A365D')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5F5F5')),
        
        # Section subheaders (rows 1 and domain_section_row)
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 11),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#1A365D')),
        ('SPAN', (0, 1), (-1, 1)),  # Merge "Complete Health Overview"
        
        ('FONTNAME', (0, domain_section_row), (-1, domain_section_row), 'Helvetica-Bold'),
        ('FONTSIZE', (0, domain_section_row), (-1, domain_section_row), 11),
        ('TEXTCOLOR', (0, domain_section_row), (-1, domain_section_row), colors.HexColor('#1A365D')),
        ('SPAN', (0, domain_section_row), (-1, domain_section_row)),  # Merge "Domain-Specific Analysis"
        
        # Subtle horizontal lines
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#E0E0E0')),  # Below headers
        ('LINEBELOW', (0, 2), (-1, 2), 0.5, colors.HexColor('#F0F0F0')),  # Below Overall
        
        # Padding - reduced for section headers
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, 1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 4),
        ('TOPPADDING', (0, domain_section_row), (-1, domain_section_row), 4),
        ('BOTTOMPADDING', (0, domain_section_row), (-1, domain_section_row), 4),
        ('TOPPADDING', (0, 2), (-1, 2), 6),
        ('BOTTOMPADDING', (0, 2), (-1, 2), 6),
        
        # Alignment
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 2), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    
    # Add domain-specific padding and lines dynamically
    if len(domain_data_rows) > 0:
        first_domain_row = domain_section_row + 1
        last_domain_row = first_domain_row + len(domain_data_rows) - 1
        
        style_commands.extend([
            ('TOPPADDING', (0, first_domain_row), (-1, last_domain_row), 6),
            ('BOTTOMPADDING', (0, first_domain_row), (-1, last_domain_row), 6),
            ('LINEBELOW', (0, first_domain_row), (-1, last_domain_row), 0.5, colors.HexColor('#F0F0F0')),
        ])
        
        # Alternating background for domain rows
        for i, row_idx in enumerate(range(first_domain_row, last_domain_row + 1)):
            if i % 2 == 0:
                style_commands.append(
                    ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#FAFAFA'))
                )
    
    health_table.setStyle(TableStyle(style_commands))
    
    return health_table

def create_compact_bacteria_table(bacteria_list, category_name, bg_color, max_rows=15):
    """Create compact bacteria table with smaller fonts and tighter spacing"""
    if not bacteria_list:
        return None
    
    bacteria_list = bacteria_list[:max_rows]
    
    # Header
    data = [["Bacteria", "Abund.", "St.", "Ev."]]
    
    # Data rows with abbreviations
    for b in bacteria_list:
        # Shorten bacteria name
        full_name = b.get('bacteria_name', 'Unknown')
        short_name = ' '.join(full_name.split()[:2])
        
        # Fix status mapping - handle all cases
        status_raw = b.get('status', 'unknown').lower()
        status_map = {
            'good': 'OK',
            'high': 'HI', 
            'normal': 'NR',
            'low': 'LO',
            'unknown': 'NK'
        }
        status = status_map.get(status_raw, 'NK')
        
        data.append([
            Paragraph(f"<i>{short_name}</i>", 
                     ParagraphStyle('Compact', fontSize=7, leading=8)),
            f"{b.get('percentage', 0):.3f}%",
            status,
            b.get('evidence_strength', 'C')
        ])
    
    # Tighter column widths
    table = Table(data, colWidths=[1.5*inch, 0.6*inch, 0.35*inch, 0.3*inch])
    
    table.setStyle(TableStyle([
        # Header
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('BACKGROUND', (0, 0), (-1, 0), bg_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        
        # Data
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
        ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 6.5),
        
        # Tight padding
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        
        # Alignment
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Minimal borders
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#555555')),
        ('LINEBELOW', (0, 1), (-1, -1), 0.25, colors.HexColor('#DDDDDD')),
    ]))
    
    return table

@app.post("/api/reports/generate", tags=["Portal"])
def generate_pdf_report(report_request: dict, customer_id: int = None, db: Session = Depends(get_db)):
    """Generate PDF report with proper frame management"""
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection not available")
    
    try:
        # Extract parameters
        report_type = report_request.get("type", "full")
        requested_domains = report_request.get("domains", [])
        
        if not customer_id:
            customer_id = report_request.get("customer_id")
        if not customer_id:
            raise HTTPException(status_code=400, detail="Customer ID required")
        
        # Get data
        user_profile = get_user_profile(customer_id, db)
        dashboard_data = get_customer_dashboard_data(customer_id, db)
        
        if not user_profile.get("success"):
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Get bacteria
        bacteria = []
        
        if report_type == "domain" and requested_domains:
            domain_name_to_id = {
                "gut": 1, "liver": 2, "heart": 3,
                "skin": 4, "cognitive": 5, "aging": 6
            }
            
            for domain_name in requested_domains:
                domain_id = domain_name_to_id.get(domain_name.lower())
                if domain_id:
                    domain_bacteria = _species_for_domain(customer_id, domain_id, db)
                    bacteria.extend(domain_bacteria)
            
            # Remove duplicates
            seen = set()
            unique_bacteria = []
            for b in bacteria:
                identifier = b.get('msp_id') or b.get('bacteria_name')
                if identifier and identifier not in seen:
                    seen.add(identifier)
                    unique_bacteria.append(b)
            bacteria = unique_bacteria
            
            if not bacteria:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No bacteria data found for domains: {', '.join(requested_domains)}"
                )
        else:
            microbiome_data = get_microbiome_data(customer_id, db)
            if not microbiome_data.get("success"):
                raise HTTPException(status_code=404, detail="Microbiome data not found")
            bacteria = microbiome_data.get("bacteria", [])
        
        # Setup PDF
        buffer = io.BytesIO()
    
        width, height = A4
        
        # PAGE 1 TEMPLATE: Single column for health table
        single_frame = Frame(
            40, 55,
            width - 80,
            height - 145,
            id='single_col'
        )
        
        single_page = PageTemplate(
            id='SingleCol',
            frames=[single_frame],
            onPage=add_header_footer
        )
        
        # PAGE 2+ TEMPLATE: Header frame + Two columns for bacteria
        # Top frame for full-width header content
        # Top frame for full-width header content
        header_frame = Frame(
            40, height - 175,  # Changed from height - 160
            width - 80,
            65,  # Changed from 50
            id='header_frame',
            showBoundary=0
        )
        
        # Two column frames below the header
        column_width = (width - 100) / 2
        left_frame = Frame(
            40, 55,
            column_width,
            height - 235,  # Changed from height - 220
            id='left_col'
        )
        right_frame = Frame(
            50 + column_width, 55,
            column_width,
            height - 235,  # Changed from height - 220
            id='right_col'
        )
        
        bacteria_page = PageTemplate(
            id='BacteriaPage',
            frames=[header_frame, left_frame, right_frame],
            onPage=add_header_footer
        )
        
        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=90,
            bottomMargin=55,
            leftMargin=40,
            rightMargin=40
        )
        
        doc.addPageTemplates([single_page, bacteria_page])
        
        # Metadata
        user = user_profile["user"]
        if report_type == "domain" and requested_domains:
            domain_titles = ", ".join([d.title() for d in requested_domains])
            doc.report_title = f"Domain Analysis: {domain_titles}"
        else:
            doc.report_title = "Full Health Analysis Report"
            
        doc.patient_name = user.get("full_name", "N/A")
        doc.report_id = user.get("report_id", "N/A")
        doc.patient_email = user.get("email", "N/A")
        doc.report_date = datetime.now().strftime("%B %d, %Y")
        
        # Build story
        story = []
        styles = getSampleStyleSheet()
        
        # Get domain scores
        health_data = dashboard_data["dashboard_data"]["health_data"]
        domain_scores = health_data.get("domains", {})
        
        # Filter if needed
        if report_type == "domain" and requested_domains:
            filtered_scores = {"overall": domain_scores.get("overall", {})}
            for domain in requested_domains:
                if domain in domain_scores:
                    filtered_scores[domain] = domain_scores[domain]
            domain_scores = filtered_scores
        
        # PAGE 1: Health table (single column, full width)
        health_table = create_health_overview_table(domain_scores, styles)
        story.append(health_table)
        
        # Switch to bacteria page layout
        story.append(NextPageTemplate('BacteriaPage'))
        story.append(PageBreak())
        
        # Categorize bacteria
        beneficial = [b for b in bacteria if b.get("category") == "beneficial"]
        pathogenic = [b for b in bacteria if b.get("category") == "pathogenic"]
        neutral = [b for b in bacteria if b.get("category") == "neutral"]
        
        # HEADER FRAME (full width): Title, summary, legend
        story.append(Paragraph(
            "<b>Bacteria Analysis</b>",
            ParagraphStyle('PageTitle', fontSize=14, textColor=colors.HexColor('#1A365D'),
                          spaceAfter=4, fontName='Helvetica-Bold', alignment=1)
        ))
        
        # Summary stats in one line
        summary_text = (
            f"Total Bacteria Species: <b>{len(bacteria)}</b> | "
            f"Beneficial Species: <b>{len(beneficial)}</b> | "
            f"Concerning Species: <b>{len(pathogenic)}</b> | "
            f"Other Species: <b>{len(neutral)}</b>"
        )
        story.append(Paragraph(
            summary_text,
            ParagraphStyle('SummaryLine', fontSize=8, textColor=colors.HexColor('#666666'),
                          spaceAfter=3, alignment=1)
        ))
        
        # Legend for abbreviations
        legend_text = (
            "<i>Abund. = Abundance (relative %), "
            "St. = Status (OK/HI/LO/NR), "
            "Ev. = Evidence Strength (A/B/C)</i>"
        )
        story.append(Paragraph(
            legend_text,
            ParagraphStyle('Legend', fontSize=7, textColor=colors.HexColor('#888888'),
                          spaceAfter=0, alignment=1)
        ))
        
        # Move to LEFT COLUMN
        story.append(FrameBreak())
        
        # LEFT COLUMN: Beneficial bacteria
        story.append(Paragraph(
            f"<b>Beneficial Species</b> <font size=8 color='#666666'>({len(beneficial)} detected)</font>",
            ParagraphStyle('ColumnHeading', fontSize=10, textColor=colors.HexColor('#10B981'),
                          spaceAfter=6, fontName='Helvetica-Bold')
        ))
        
        if beneficial:
            beneficial_table = create_compact_bacteria_table(
                beneficial,
                'beneficial',
                colors.HexColor('#10B981'),
                max_rows=30
            )
            story.append(beneficial_table)
        else:
            story.append(Paragraph("No beneficial bacteria detected", styles['Normal']))
        
        # Switch to RIGHT COLUMN
        story.append(FrameBreak())
        
        # RIGHT COLUMN: Pathogenic bacteria
        story.append(Paragraph(
            f"<b>Concerning Species</b> <font size=8 color='#666666'>({len(pathogenic)} detected)</font>",
            ParagraphStyle('ColumnHeading', fontSize=10, textColor=colors.HexColor('#EF4444'),
                          spaceAfter=6, fontName='Helvetica-Bold')
        ))
        
        if pathogenic:
            pathogenic_table = create_compact_bacteria_table(
                pathogenic,
                'pathogenic',
                colors.HexColor('#EF4444'),
                max_rows=12
            )
            story.append(pathogenic_table)
        else:
            story.append(Paragraph("No concerning bacteria detected", styles['Normal']))
        
        story.append(Spacer(1, 12))
        
        # Other bacteria
        if neutral:
            story.append(Paragraph(
                f"<b>Other Species</b> <font size=8 color='#666666'>({len(neutral)} detected)</font>",
                ParagraphStyle('ColumnHeading', fontSize=10, textColor=colors.HexColor('#6B7280'),
                              spaceAfter=6, fontName='Helvetica-Bold')
            ))
            
            neutral_table = create_compact_bacteria_table(
                neutral,
                'neutral',
                colors.HexColor('#6B7280'),
                max_rows=15
            )
            story.append(neutral_table)
        
        # Add Recommendations Section
        story.append(NextPageTemplate('SingleCol'))
        story.append(PageBreak())
        
        # Get recommendations for report
        try:
            # Determine which domains to get recommendations for
            if report_type == "domain" and requested_domains:
                domains_to_get = requested_domains
            else:
                domains_to_get = ["gut", "liver", "heart", "skin", "cognitive", "aging"]
            
            # Page title for recommendations
            story.append(Paragraph(
                "<b>Personalized Recommendations</b>",
                ParagraphStyle('PageTitle', fontSize=16, textColor=colors.HexColor('#1A365D'),
                              spaceAfter=12, fontName='Helvetica-Bold', alignment=1)
            ))
            
            # Get and add recommendations for each domain
            for domain_name in domains_to_get:
                try:
                    result = cached_recommendation_service.get_recommendations(
                        customer_id=customer_id,
                        domain_name=domain_name,
                        db=db,
                        force_regenerate=False
                    )
                    
                    if result.get("success") and result.get("recommendations"):
                        rec_data = result["recommendations"]
                        
                        # Domain header
                        story.append(Paragraph(
                            f"<b>{domain_name.title()} Health Recommendations</b>",
                            ParagraphStyle('DomainHeader', 
                                          fontSize=12, 
                                          textColor=colors.HexColor('#2563EB'),
                                          spaceAfter=8, 
                                          fontName='Helvetica-Bold')
                        ))
                        
                        # Dietary Recommendations
                        if rec_data.get("dietary_recommendations"):
                            story.append(Paragraph(
                                "<b>Dietary Recommendations:</b>",
                                ParagraphStyle('SubHeader', fontSize=10, fontName='Helvetica-Bold', spaceAfter=4)
                            ))
                            
                            for item in rec_data["dietary_recommendations"][:3]:  # Limit to 3 items
                                story.append(Paragraph(
                                    f"- <b>{item.get('item', 'N/A')}</b> - {item.get('rationale', 'N/A')}",
                                    ParagraphStyle('RecommendationItem', fontSize=9, leftIndent=12, spaceAfter=3)
                                ))
                        
                        # Lifestyle Recommendations
                        if rec_data.get("lifestyle_recommendations"):
                            story.append(Paragraph(
                                "<b>Lifestyle Recommendations:</b>",
                                ParagraphStyle('SubHeader', fontSize=10, fontName='Helvetica-Bold', spaceAfter=4, spaceBefore=6)
                            ))
                            
                            for item in rec_data["lifestyle_recommendations"][:2]:  # Limit to 2 items
                                story.append(Paragraph(
                                    f"- <b>{item.get('activity', 'N/A')}</b> - {item.get('rationale', 'N/A')}",
                                    ParagraphStyle('RecommendationItem', fontSize=9, leftIndent=12, spaceAfter=3)
                                ))
                        
                        # Summary
                        if rec_data.get("summary"):
                            story.append(Paragraph(
                                f"<b>Key Takeaway:</b> <i>{rec_data['summary']}</i>",
                                ParagraphStyle('Summary', fontSize=9, textColor=colors.HexColor('#4B5563'), 
                                             spaceBefore=6, spaceAfter=12)
                            ))
                        
                        story.append(Spacer(1, 8))
                        
                except Exception as e:
                    print(f"Error getting recommendations for {domain_name}: {e}")
                    continue
            
            # Add disclaimer
            story.append(Spacer(1, 20))
            story.append(Paragraph(
                "<b>Disclaimer:</b> These recommendations are for informational purposes only. "
                "Please consult with your healthcare provider before making significant changes to your diet or lifestyle.",
                ParagraphStyle('Disclaimer', fontSize=8, textColor=colors.HexColor('#6B7280'), 
                              alignment=0)
            ))
            
        except Exception as e:
            print(f"Error adding recommendations section: {e}")
            # Add a simple message if recommendations fail
            story.append(Paragraph(
                "Recommendations are currently unavailable. Please try again later.",
                styles['Normal']
            ))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if report_type == "domain" and requested_domains:
            domain_suffix = "_".join(requested_domains)
            filename = f"mannbiome_{domain_suffix}_report_{user.get('report_id', customer_id)}_{timestamp}.pdf"
        else:
            filename = f"mannbiome_report_{user.get('report_id', customer_id)}_{timestamp}.pdf"
        
        return StreamingResponse(
            io.BytesIO(buffer.read()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
    

# Alternative endpoint with customer_id in URL
@app.post("/api/customer/{customer_id}/reports/generate", tags=["Portal"])
def generate_customer_pdf_report(
    customer_id: int,
    report_request: dict,
    db: Session = Depends(get_db)
):
    """Generate PDF report for specific customer"""
    return generate_pdf_report(report_request, customer_id, db)
# -----------------------------------------------------------------------------
# No /api/debug/* or /api/test/* endpoints (removed by request)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# AI: Cached LLM Recommendations
# -----------------------------------------------------------------------------

@app.get("/api/customer/{customer_id}/llm-recommendations", tags=["AI"])
async def get_llm_recommendations(
    customer_id: int,
    domain: str,
    force_regenerate: bool = False,  # Query param to force refresh
    db: Session = Depends(get_db)
):
    """
    Get personalized recommendations - uses cache if available
    """
    try:
        result = cached_recommendation_service.get_recommendations(
            customer_id=customer_id,
            domain_name=domain,
            db=db,
            force_regenerate=force_regenerate
        )
        
        return {
            "success": result["success"],
            "customer_id": customer_id,
            "domain": domain,
            "source": result.get("source", "unknown"),
            "recommendations": result.get("recommendations"),
            "generated_at": result.get("generated_at"),
            "expires_at": result.get("expires_at"),
            "model": result.get("model")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/customer/{customer_id}/generate-all-recommendations", tags=["AI"])
async def generate_all_recommendations_on_login(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate recommendations for ALL domains
    Call this when customer logs in
    """
    try:
        result = cached_recommendation_service.generate_all_domains_on_login(
            customer_id=customer_id,
            db=db
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/customer/{customer_id}/recommendation-cache-status", tags=["AI"])
async def get_recommendation_cache_status(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """
    Get cache status for all domains for a customer
    Useful for debugging and monitoring
    """
    try:
        result = cached_recommendation_service.get_cache_status(
            customer_id=customer_id,
            db=db
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/cleanup-expired-recommendations", tags=["AI", "Admin"])
async def cleanup_expired_recommendations(
    db: Session = Depends(get_db)
):
    """
    Clean up expired recommendations (maintenance endpoint)
    """
    try:
        result = cached_recommendation_service.cleanup_expired_recommendations(db)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# __main__
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MannBiome Unified API (Portal + Domain)")
    uvicorn.run(app, host="127.0.0.1", port=8001)
