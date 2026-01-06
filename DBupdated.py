#!/usr/bin/env python3
"""
Complete FastAPI Application for Bacteria Analysis
Using patient_reports and computed_bacteria_metadata tables
"""

from fastapi import FastAPI, Query, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import traceback

# Initialize FastAPI app
app = FastAPI(
    title="Bacteria Analysis API", 
    version="1.0.0",
    description="Analyze patient bacteria data using computed metadata"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your actual domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Two Database connections
import os
from dotenv import load_dotenv

load_dotenv()
MANNBIOME_DB_URL = os.getenv("DATABASE_URL")
VECTORDB_URL = os.getenv("VECTORDB_URL", MANNBIOME_DB_URL.replace("/mannbiome", "/vectordb") if MANNBIOME_DB_URL else None)

if not MANNBIOME_DB_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# MannBiome DB connection (for patient_reports)
try:
    mannbiome_engine = create_engine(MANNBIOME_DB_URL)
    MannBiomeSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=mannbiome_engine)
    print("✅ MannBiome Database connection configured successfully")
except Exception as e:
    print(f"⚠️ MannBiome Database connection error: {e}")
    mannbiome_engine = None
    MannBiomeSessionLocal = None

# VectorDB connection (for computed_bacteria_metadata, rules_mappings, outcomesIndex)
try:
    vectordb_engine = create_engine(VECTORDB_URL)
    VectorDBSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=vectordb_engine)
    print("✅ VectorDB Database connection configured successfully")
except Exception as e:
    print(f"⚠️ VectorDB Database connection error: {e}")
    vectordb_engine = None
    VectorDBSessionLocal = None

# Dependencies to get DB sessions
def get_mannbiome_db():
    if MannBiomeSessionLocal is None:
        yield None
        return
    
    db = MannBiomeSessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"MannBiome database session error: {e}")
        db.rollback()
    finally:
        db.close()

def get_vectordb():
    if VectorDBSessionLocal is None:
        yield None
        return
    
    db = VectorDBSessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"VectorDB database session error: {e}")
        db.rollback()
    finally:
        db.close()

# Legacy function for backward compatibility
def get_db():
    """Legacy function - use get_mannbiome_db() or get_vectordb() instead"""
    yield from get_mannbiome_db()

# =======================
# UTILITY FUNCTIONS
# =======================

def map_customer_to_participant(customer_id: int) -> str:
    """Map customer_id to participant_id format"""
    return f"PART-{customer_id}"

def determine_bacteria_status(patient_abundance: float, ideal_min: float, ideal_max: float) -> str:
    """Determine if bacteria abundance is HIGH, LOW, or NORMAL"""
    try:
        if patient_abundance < ideal_min:
            return "LOW"
        elif patient_abundance > ideal_max:
            return "HIGH"
        else:
            return "NORMAL"
    except Exception as e:
        print(f"Error determining bacteria status: {e}")
        return "UNKNOWN"

def find_partial_bacteria_match(patient_name: str, metadata_dict: dict):
    """Find partial matches for bacteria names"""
    try:
        patient_lower = patient_name.lower()
        
        # Try different matching strategies
        for ref_name_lower, metadata in metadata_dict.items():
            ref_name = metadata["bacteria_name"]
            
            # Strategy 1: Patient name contains reference name
            if ref_name_lower in patient_lower:
                print(f"Partial match found: '{patient_name}' matched with '{ref_name}' (contains)")
                return metadata
            
            # Strategy 2: Reference name contains patient name
            if patient_lower in ref_name_lower:
                print(f"Partial match found: '{patient_name}' matched with '{ref_name}' (contained)")
                return metadata
            
            # Strategy 3: Match by genus if available
            if "unclassified" in patient_lower and metadata.get("genus"):
                genus_lower = metadata["genus"].lower()
                if genus_lower in patient_lower:
                    print(f"Genus match found: '{patient_name}' matched with '{ref_name}' via genus '{metadata['genus']}'")
                    return metadata
        
        return None
        
    except Exception as e:
        print(f"Error in find_partial_bacteria_match: {e}")
        return None

def calculate_simple_health_score(status_counts: dict, total_bacteria: int) -> float:
    """Calculate a simple health score based on bacteria status distribution"""
    try:
        if total_bacteria == 0:
            return 50.0  # Neutral score
        
        normal_ratio = status_counts["NORMAL"] / total_bacteria
        concerning_ratio = (status_counts["HIGH"] + status_counts["LOW"]) / total_bacteria
        
        # Score from 0-100 based on normal bacteria percentage
        base_score = normal_ratio * 100
        
        # Penalty for concerning bacteria
        penalty = concerning_ratio * 30
        
        final_score = max(0, min(100, base_score - penalty))
        return round(final_score, 1)
        
    except Exception as e:
        print(f"Error calculating health score: {e}")
        return 50.0

# =======================
# CORE ANALYSIS FUNCTIONS
# =======================

def analyze_patient_bacteria(bacteria_data: list, vectordb: Session) -> list:
    """Analyze patient bacteria against computed_bacteria_metadata ranges in VectorDB"""
    try:
        bacteria_analysis = []
        
        # Get all bacteria metadata from VectorDB
        metadata_query = text("""
            SELECT 
                bacteria_name,
                msp_id,
                genus,
                ideal_min,
                ideal_max,
                units,
                evidence_strength,
                baseline_variability,
                prevalence
            FROM public.computed_bacteria_metadata
            WHERE ideal_min IS NOT NULL AND ideal_max IS NOT NULL
        """)
        
        metadata_results = vectordb.execute(metadata_query).fetchall()
        
        # Create lookup dictionary for faster matching
        metadata_dict = {}
        for row in metadata_results:
            metadata_dict[row.bacteria_name.lower()] = {
                "bacteria_name": row.bacteria_name,
                "msp_id": row.msp_id,
                "genus": row.genus,
                "ideal_min": row.ideal_min,
                "ideal_max": row.ideal_max,
                "units": row.units,
                "evidence_strength": row.evidence_strength,
                "baseline_variability": row.baseline_variability,
                "prevalence": row.prevalence
            }
        
        print(f"Loaded {len(metadata_dict)} bacteria from computed_bacteria_metadata (VectorDB)")
        
        # Analyze each bacteria in patient data
        for bacteria_item in bacteria_data:
            bacteria_name = bacteria_item.get('bacteria_name', '').strip()
            patient_abundance = float(bacteria_item.get('abundance', 0))
            patient_units = bacteria_item.get('units', 'relative_abundance_fraction')
            
            # Try exact match first
            metadata = metadata_dict.get(bacteria_name.lower())
            
            # If no exact match, try partial matching
            if not metadata:
                metadata = find_partial_bacteria_match(bacteria_name, metadata_dict)
            
            if metadata:
                # Ensure units match
                if metadata["units"] == patient_units:
                    # Determine status by comparing with ideal ranges
                    status = determine_bacteria_status(
                        patient_abundance, 
                        metadata["ideal_min"], 
                        metadata["ideal_max"]
                    )
                    
                    # Calculate deviation
                    ideal_mid = (metadata["ideal_min"] + metadata["ideal_max"]) / 2
                    deviation_percent = ((patient_abundance - ideal_mid) / ideal_mid * 100) if ideal_mid > 0 else 0
                    
                    analysis_result = {
                        "bacteria_name": bacteria_name,
                        "matched_reference": metadata["bacteria_name"],
                        "patient_abundance": patient_abundance,
                        "ideal_min": metadata["ideal_min"],
                        "ideal_max": metadata["ideal_max"],
                        "ideal_range": f"{metadata['ideal_min']:.2e} - {metadata['ideal_max']:.2e}",
                        "units": patient_units,
                        "status": status,
                        "deviation_percentage": round(deviation_percent, 2),
                        "evidence_strength": metadata["evidence_strength"],
                        "genus": metadata["genus"],
                        "msp_id": metadata["msp_id"],
                        "prevalence": metadata["prevalence"]
                    }
                    
                    bacteria_analysis.append(analysis_result)
                    print(f"✓ Analyzed: {bacteria_name} -> {status}")
                else:
                    print(f"⚠ Unit mismatch for {bacteria_name}: {patient_units} vs {metadata['units']}")
            else:
                print(f"✗ No metadata found for: {bacteria_name}")
        
        # Sort by status priority (HIGH/LOW issues first)
        status_priority = {"HIGH": 1, "LOW": 2, "NORMAL": 3}
        bacteria_analysis.sort(key=lambda x: (status_priority.get(x["status"], 4), x["bacteria_name"]))
        
        print(f"Successfully analyzed {len(bacteria_analysis)} bacteria")
        return bacteria_analysis
        
    except Exception as e:
        print(f"Error in analyze_patient_bacteria: {e}")
        traceback.print_exc()
        return []

def get_bacteria_health_associations(bacteria_name: str, status: str, vectordb: Session) -> list:
    """Get health associations from rules_mappings table in VectorDB"""
    try:
        if status == "NORMAL":
            return []
        
        # Query rules_mappings for this bacteria in VectorDB
        rules_query = text("""
            SELECT 
                rm.recommended_action,
                rm.confidence_level,
                oi."Outcome (User-Friendly)" as outcome_name,
                oi."Definition (Simple Language)" as outcome_definition
            FROM public.rules_mappings rm
            LEFT JOIN public."outcomesIndex" oi ON rm.disease_code = oi."Disease Code"
            WHERE LOWER(rm.bacteria_name) LIKE LOWER(:bacteria_pattern)
            AND rm.abundance_threshold_type = :status_type
            ORDER BY rm.rule_weight DESC
            LIMIT 5
        """)
        
        status_type = status.lower()
        bacteria_pattern = f"%{bacteria_name}%"
        
        rules_results = vectordb.execute(rules_query, {
            "bacteria_pattern": bacteria_pattern,
            "status_type": status_type
        }).fetchall()
        
        associations = []
        for rule in rules_results:
            associations.append({
                "outcome": rule.outcome_name,
                "description": rule.outcome_definition,
                "recommended_action": rule.recommended_action,
                "confidence": rule.confidence_level
            })
        
        return associations
        
    except Exception as e:
        print(f"Error getting health associations: {e}")
        return []

# =======================
# API ENDPOINTS
# =======================

@app.get("/")
def read_root():
    return {
        "message": "Bacteria Analysis API", 
        "status": "running",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/api/health-check")
def health_check():
    """API health check endpoint"""
    mannbiome_status = "connected" if mannbiome_engine is not None else "disconnected"
    vectordb_status = "connected" if vectordb_engine is not None else "disconnected"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "databases": {
            "mannbiome": mannbiome_status,
            "vectordb": vectordb_status
        },
        "message": "Bacteria Analysis API is running"
    }

@app.get("/api/customer/{customer_id}/microbiome-data")
def get_customer_microbiome_data(
    customer_id: int, 
    mannbiome_db: Session = Depends(get_mannbiome_db),
    vectordb: Session = Depends(get_vectordb)
):
    """Get customer's bacteria analysis using both databases"""
    try:
        if mannbiome_db is None or vectordb is None:
            return {
                "success": False,
                "error": "Database connections not available",
                "message": "Please check database configuration for both MannBiome and VectorDB"
            }
        
        # Map customer_id to participant_id
        participant_id = map_customer_to_participant(customer_id)
        
        # Get patient report from MannBiome DB
        query = text("""
            SELECT 
                upload_id,
                participant_id,
                lab_name,
                upload_date,
                bacteria_data,
                total_bacteria_count,
                extraction_status,
                analysis_status
            FROM public.patient_reports 
            WHERE participant_id = :participant_id
            ORDER BY upload_date DESC
            LIMIT 1
        """)
        
        result = mannbiome_db.execute(query, {"participant_id": participant_id}).fetchone()
        
        if not result:
            return {
                "success": False,
                "error": f"No patient report found for participant_id: {participant_id}",
                "message": f"Customer {customer_id} (participant {participant_id}) not found in MannBiome database"
            }
        
        report_data = dict(result._mapping)
        bacteria_data = report_data['bacteria_data']  # JSONB array
        
        print(f"Found report for {participant_id} with {len(bacteria_data)} bacteria")
        
        # Analyze bacteria using VectorDB metadata
        bacteria_analysis = analyze_patient_bacteria(bacteria_data, vectordb)
        
        # Calculate summary statistics
        total_analyzed = len(bacteria_analysis)
        high_count = len([b for b in bacteria_analysis if b["status"] == "HIGH"])
        low_count = len([b for b in bacteria_analysis if b["status"] == "LOW"])
        normal_count = len([b for b in bacteria_analysis if b["status"] == "NORMAL"])
        
        # Create response
        response_data = {
            "participant_id": participant_id,
            "lab_name": report_data.get('lab_name', 'Unknown Lab'),
            "upload_date": report_data['upload_date'].strftime('%B %d, %Y') if report_data.get('upload_date') else "Unknown Date",
            "total_bacteria_in_report": report_data.get('total_bacteria_count', 0),
            "bacteria_analyzed": total_analyzed,
            "summary": {
                "high_abundance": high_count,
                "low_abundance": low_count,
                "normal_abundance": normal_count,
                "not_found_in_reference": report_data.get('total_bacteria_count', 0) - total_analyzed
            },
            "bacteria_analysis": bacteria_analysis
        }
        
        return {
            "success": True,
            "data": response_data,
            "message": f"Analyzed {total_analyzed} bacteria using dual database setup (MannBiome + VectorDB)"
        }
        
    except Exception as e:
        print(f"Error in get_customer_microbiome_data: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "message": "Error analyzing bacteria data"
        }

@app.get("/api/customer/{customer_id}/bacteria/{bacteria_name}")
def get_bacteria_details(
    customer_id: int, 
    bacteria_name: str, 
    mannbiome_db: Session = Depends(get_mannbiome_db),
    vectordb: Session = Depends(get_vectordb)
):
    """Get detailed analysis for a specific bacteria using both databases"""
    try:
        if mannbiome_db is None or vectordb is None:
            return {"success": False, "message": "Database connections not available"}
        
        participant_id = map_customer_to_participant(customer_id)
        
        # Get patient data from MannBiome DB
        patient_query = text("""
            SELECT bacteria_data 
            FROM public.patient_reports 
            WHERE participant_id = :participant_id
            ORDER BY upload_date DESC
            LIMIT 1
        """)
        
        patient_result = mannbiome_db.execute(patient_query, {"participant_id": participant_id}).fetchone()
        
        if not patient_result:
            return {"success": False, "message": "Patient data not found"}
        
        # Find the specific bacteria in patient data
        bacteria_data = patient_result.bacteria_data
        patient_bacteria = None
        
        for bacteria_item in bacteria_data:
            if bacteria_item.get('bacteria_name', '').lower() == bacteria_name.lower():
                patient_bacteria = bacteria_item
                break
        
        if not patient_bacteria:
            return {"success": False, "message": f"Bacteria '{bacteria_name}' not found in patient report"}
        
        # Get metadata for this bacteria from VectorDB
        metadata_query = text("""
            SELECT * FROM public.computed_bacteria_metadata
            WHERE LOWER(bacteria_name) = LOWER(:bacteria_name)
            LIMIT 1
        """)
        
        metadata_result = vectordb.execute(metadata_query, {"bacteria_name": bacteria_name}).fetchone()
        
        if not metadata_result:
            return {"success": False, "message": f"No reference data found for '{bacteria_name}'"}
        
        metadata = dict(metadata_result._mapping)
        patient_abundance = float(patient_bacteria.get('abundance', 0))
        
        # Calculate detailed analysis
        status = determine_bacteria_status(patient_abundance, metadata["ideal_min"], metadata["ideal_max"])
        ideal_mid = (metadata["ideal_min"] + metadata["ideal_max"]) / 2
        deviation_percent = ((patient_abundance - ideal_mid) / ideal_mid * 100) if ideal_mid > 0 else 0
        
        # Check for potential health associations from VectorDB
        health_associations = get_bacteria_health_associations(bacteria_name, status, vectordb)
        
        detailed_analysis = {
            "bacteria_name": bacteria_name,
            "patient_abundance": patient_abundance,
            "ideal_min": metadata["ideal_min"],
            "ideal_max": metadata["ideal_max"],
            "status": status,
            "deviation_percentage": round(deviation_percent, 2),
            "evidence_strength": metadata["evidence_strength"],
            "genus": metadata["genus"],
            "clinical_context": metadata["clinical_context"],
            "baseline_variability": metadata["baseline_variability"],
            "prevalence": metadata["prevalence"],
            "health_associations": health_associations
        }
        
        return {
            "success": True,
            "bacteria_details": detailed_analysis
        }
        
    except Exception as e:
        print(f"Error in get_bacteria_details: {e}")
        return {"success": False, "error": str(e)}
        print(f"Error in get_bacteria_details: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/customer/{customer_id}/bacteria-summary")
def get_bacteria_summary(customer_id: int, mannbiome_db: Session = Depends(get_mannbiome_db), vectordb: Session = Depends(get_vectordb)):
    """Get summary statistics of bacteria analysis using both databases"""
    try:
        # Get the full analysis
        full_analysis = get_customer_microbiome_data(customer_id, mannbiome_db, vectordb)
        
        if not full_analysis.get("success"):
            return full_analysis
        
        bacteria_analysis = full_analysis["data"]["bacteria_analysis"]
        
        # Calculate summary statistics
        status_counts = {"HIGH": 0, "LOW": 0, "NORMAL": 0}
        evidence_counts = {"A": 0, "B": 0, "C": 0}
        concerning_bacteria = []
        
        for bacteria in bacteria_analysis:
            status_counts[bacteria["status"]] += 1
            evidence_counts[bacteria.get("evidence_strength", "C")] += 1
            
            if bacteria["status"] in ["HIGH", "LOW"]:
                concerning_bacteria.append({
                    "name": bacteria["bacteria_name"],
                    "status": bacteria["status"],
                    "deviation": bacteria["deviation_percentage"]
                })
        
        # Sort concerning bacteria by deviation magnitude
        concerning_bacteria.sort(key=lambda x: abs(x["deviation"]), reverse=True)
        
        summary = {
            "participant_id": full_analysis["data"]["participant_id"],
            "total_bacteria_analyzed": len(bacteria_analysis),
            "status_distribution": status_counts,
            "evidence_quality": evidence_counts,
            "top_concerning_bacteria": concerning_bacteria[:10],
            "health_score": calculate_simple_health_score(status_counts, len(bacteria_analysis))
        }
        
        return {
            "success": True,
            "summary": summary
        }
        
    except Exception as e:
        print(f"Error in get_bacteria_summary: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/debug/patient-reports")
def debug_patient_reports(mannbiome_db: Session = Depends(get_mannbiome_db)):
    """Debug endpoint to check available patient reports in MannBiome DB"""
    try:
        if mannbiome_db is None:
            return {"error": "No MannBiome database connection"}
        
        query = text("""
            SELECT 
                participant_id,
                lab_name,
                upload_date,
                total_bacteria_count,
                extraction_status,
                analysis_status
            FROM public.patient_reports
            ORDER BY upload_date DESC
            LIMIT 10
        """)
        
        results = mannbiome_db.execute(query).fetchall()
        
        reports = []
        for row in results:
            reports.append({
                "participant_id": row.participant_id,
                "lab_name": row.lab_name,
                "upload_date": str(row.upload_date),
                "total_bacteria_count": row.total_bacteria_count,
                "extraction_status": row.extraction_status,
                "analysis_status": row.analysis_status
            })
        
        return {
            "success": True,
            "database": "MannBiome",
            "total_reports": len(reports),
            "patient_reports": reports
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/debug/bacteria-metadata-count")
def debug_bacteria_metadata_count(vectordb: Session = Depends(get_vectordb)):
    """Debug endpoint to check bacteria metadata count in VectorDB"""
    try:
        if vectordb is None:
            return {"error": "No VectorDB connection"}
        
        query = text("""
            SELECT 
                COUNT(*) as total_bacteria,
                COUNT(CASE WHEN ideal_min IS NOT NULL AND ideal_max IS NOT NULL THEN 1 END) as with_ranges,
                COUNT(DISTINCT genus) as unique_genera
            FROM public.computed_bacteria_metadata
        """)
        
        result = vectordb.execute(query).fetchone()
        
        return {
            "success": True,
            "database": "VectorDB",
            "metadata_stats": {
                "total_bacteria": result.total_bacteria,
                "bacteria_with_ranges": result.with_ranges,
                "unique_genera": result.unique_genera
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/debug/rules-mappings-count")
def debug_rules_mappings_count(vectordb: Session = Depends(get_vectordb)):
    """Debug endpoint to check rules mappings count in VectorDB"""
    try:
        if vectordb is None:
            return {"error": "No VectorDB connection"}
        
        query = text("""
            SELECT 
                COUNT(*) as total_rules,
                COUNT(DISTINCT bacteria_name) as unique_bacteria,
                COUNT(CASE WHEN confidence_level = 'High' THEN 1 END) as high_confidence,
                COUNT(CASE WHEN confidence_level = 'Moderate' THEN 1 END) as moderate_confidence,
                COUNT(CASE WHEN confidence_level = 'Low' THEN 1 END) as low_confidence
            FROM public.rules_mappings
        """)
        
        result = vectordb.execute(query).fetchone()
        
        return {
            "success": True,
            "database": "VectorDB",
            "rules_stats": {
                "total_rules": result.total_rules,
                "unique_bacteria": result.unique_bacteria,
                "high_confidence": result.high_confidence,
                "moderate_confidence": result.moderate_confidence,
                "low_confidence": result.low_confidence
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# =======================
# ERROR HANDLERS
# =======================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "success": False}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled exception: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "success": False, "error": str(exc)}
    )

# =======================
# MAIN APPLICATION RUNNER
# =======================

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Bacteria Analysis API...")
    print("📚 API Documentation: http://localhost:8002/docs")
    print("🔍 Health Check: http://localhost:8002/api/health-check")
    print("🧬 Test endpoint: http://localhost:8002/api/customer/3091/microbiome-data")
    print("🐛 Debug reports: http://localhost:8002/api/debug/patient-reports")
    uvicorn.run(app, host="0.0.0.0", port=8002)