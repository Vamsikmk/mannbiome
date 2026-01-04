// services/api.js - Updated to work with customer-specific mock data
// Maintains all existing functionality while adding customer-specific features

import customerApiService from './customerApiService';

class ApiService {
  constructor() {
    this.baseURL = process.env.REACT_APP_API_BASE_URL;
    this.currentCustomerId = null;
    this.isOnline = true;
  }

  // Test API connectivity
  async testConnection() {
    try {
      const response = await fetch(`${this.baseURL}/api/health-check`);
      const data = await response.json();
      this.isOnline = response.ok;
      console.log('✅ API Connection Status:', data);
      return { success: this.isOnline, data };
    } catch (error) {
      console.error('❌ API Connection Failed:', error);
      this.isOnline = false;
      return { success: false, error: error.message };
    }
  }

  // Set current customer ID for all subsequent requests
  setCustomerId(customerId) {
    this.currentCustomerId = customerId;
    console.log(`🔄 API Service: Customer ID set to ${customerId}`);
    
    // Also set it in the customer-specific service
    customerApiService.setCustomerId(customerId);
  }

  // Generic request method with better error handling
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const defaultOptions = {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      ...options
    };

    console.log(`🌐 API Request: ${defaultOptions.method} ${url}`);

    try {
      const response = await fetch(url, defaultOptions);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log(`✅ API Response Success:`, data);
      
      return {
        success: true,
        data,
        status: response.status
      };
    } catch (error) {
      console.error(`❌ API Request Failed for ${endpoint}:`, error);
      
      // Return fallback data structure
      return {
        success: false,
        error: error.message,
        fallback: this.getFallbackData(endpoint)
      };
    }
  }

  // ============================================
  // CUSTOMER-SPECIFIC METHODS - NEW ENHANCED
  // ============================================

  /**
   * Get customer-specific microbiome data
   * @param {number} customerId - Customer ID
   * @returns {Promise} - Customer-specific microbiome data
   */
  async getCustomerMicrobiomeData(customerId) {
    console.log(`🎯 Getting microbiome data for customer ${customerId}`);
    
    // First try real API, then fallback to customer-specific mock data
    const connectionTest = await this.testConnection();
    
    if (!connectionTest.success) {
      console.log('📱 API unavailable, using customer-specific mock data');
      return customerApiService.getCustomerMicrobiomeData(customerId);
    }

    // Try to get real data
    const endpoint = `/api/customer/${customerId}/microbiome-data`;
    const result = await this.request(endpoint);
    
    if (result.success) {
      console.log(`✅ Successfully retrieved real microbiome data for customer ${customerId}`);
      return result;
    } else {
      console.log('📱 Real API call failed, using customer-specific mock data');
      return customerApiService.getCustomerMicrobiomeData(customerId);
    }
  }

  /**
   * Get customer-specific bacteria for a health domain
   * @param {number} customerId - Customer ID
   * @param {string} domain - Health domain (aging, gut, liver, etc.)
   * @returns {Promise} - Domain-specific bacterial data
   */
  async getCustomerDomainBacteria(customerId, domain) {
    console.log(`🎯 Getting ${domain} bacteria for customer ${customerId}`);
    
    const connectionTest = await this.testConnection();
    
    if (!connectionTest.success) {
      return customerApiService.getCustomerDomainBacteria(customerId, domain);
    }

    const endpoint = `/api/customer/${customerId}/domain/${domain}/bacteria`;
    const result = await this.request(endpoint);
    
    if (result.success) {
      console.log(`✅ Successfully retrieved ${domain} bacteria for customer ${customerId}`);
      return result;
    } else {
      return customerApiService.getCustomerDomainBacteria(customerId, domain);
    }
  }

  // ============================================
  // EXISTING METHODS - ENHANCED WITH CUSTOMER SUPPORT
  // ============================================

  /**
   * Get health domain details (enhanced with customer support)
   * @param {string} domainName - Domain name
   * @param {number} customerId - Customer ID (optional)
   * @returns {Promise} - Domain details
   */
  async getHealthDomainDetails(domainName, customerId = null) {
    console.log(`🔍 Getting domain details for: ${domainName}, customer: ${customerId}`);
    
    // If customer ID provided, use customer-specific data
    if (customerId) {
      return this.getCustomerDomainBacteria(customerId, domainName);
    }
    
    // Otherwise, use original method
    const endpoint = `/api/health-domains/${domainName}`;
    return this.request(endpoint);
  }

  /**
   * Get detailed modal data for a health domain (enhanced)
   * @param {number} domainId - Domain ID (1=gut, 2=liver, 3=heart, 4=skin, 5=cognitive, 6=aging)
   * @param {number} customerId - Customer ID
   * @returns {Promise} - Modal data including health metrics, species, pathways, recommendations
   */
  async getHealthDomainModalData(domainId, customerId) {
    console.log(`🔍 Getting modal data for domain ${domainId}, customer ${customerId}`);
    
    // Map domain ID to domain name
    const domainMap = {
      1: 'gut',
      2: 'liver', 
      3: 'heart',
      4: 'skin',
      5: 'cognitive',
      6: 'aging'
    };
    
    const domainName = domainMap[domainId];
    
    if (!domainName) {
      return {
        success: false,
        error: `Invalid domain ID: ${domainId}`
      };
    }
    
    // Use customer-specific domain data
    return this.getCustomerDomainBacteria(customerId, domainName);
  }

  /**
   * Get user profile information
   * @param {number} userId - User ID
   * @returns {Promise} - User profile data
   */
  async getUserProfile(userId) {
    console.log(`👤 Getting user profile for ID: ${userId}`);
    
    // Try customer-specific service first
    const customerResult = await customerApiService.getUserProfile(userId);
    
    if (customerResult.success) {
      return customerResult;
    }
    
    // Fallback to original API
    const endpoint = `/api/user/${userId}/profile`;
    return this.request(endpoint);
  }

  // ============================================
  // DASHBOARD AND LOADING METHODS
  // ============================================

  /**
   * Load dashboard data for a customer
   * @param {number} customerId - Customer ID
   * @returns {Promise} - Dashboard data
   */
  async loadDashboardData(customerId) {
    console.log(`🔄 Loading dashboard data for customer ${customerId}`);
    
    // Use customer-specific service for dashboard loading
    return customerApiService.loadDashboardData(customerId);
  }

  // ============================================
  // TESTING AND DEBUG METHODS
  // ============================================

  /**
   * Test different customers to verify data differences
   * @returns {Promise} - Test results showing customer differences
   */
  async testCustomerDifferences() {
    console.log('🧪 Testing customer differences...');
    return customerApiService.testAllCustomers();
  }

  /**
   * Switch to a different customer for testing
   * @param {number} newCustomerId - New customer ID
   * @returns {Promise} - Switch result
   */
  async switchCustomer(newCustomerId) {
    console.log(`🔄 Switching to customer ${newCustomerId}`);
    
    this.setCustomerId(newCustomerId);
    return customerApiService.switchCustomer(newCustomerId);
  }

  /**
   * Get available test customers
   * @returns {Object} - Available customer information
   */
  getAvailableCustomers() {
    return {
      success: true,
      customers: [
        { id: 3091, name: "John Doe", status: "poor", description: "Poor bacterial health across domains" },
        { id: 8420, name: "Jane Smith", status: "excellent", description: "Excellent bacterial balance" },
        { id: 5500, name: "Mike Johnson", status: "mixed", description: "Mixed results - some good, some concerning" }
      ],
      message: "Use these customer IDs to test different bacterial profiles"
    };
  }

  // ============================================
  // LEGACY METHODS - MAINTAINED FOR COMPATIBILITY
  // ============================================

  /**
   * Get species carousel data for a domain (legacy support)
   * @param {number} domainId - Domain ID
   * @param {number} customerId - Customer ID
   * @returns {Promise} - Species carousel data
   */
  async getSpeciesCarouselData(domainId, customerId) {
    const result = await this.getHealthDomainModalData(domainId, customerId);
    
    if (result.success && result.data && result.data.species_carousel) {
      return {
        success: true,
        species_carousel: result.data.species_carousel,
        domain_info: result.data.domain_info
      };
    }
    
    return { success: false, error: "Species data not available" };
  }

  /**
   * Get pathway carousel data for a domain (legacy support)
   * @param {number} domainId - Domain ID
   * @param {number} customerId - Customer ID
   * @returns {Promise} - Pathway carousel data
   */
  async getPathwayCarouselData(domainId, customerId) {
    // For now, return mock pathway data since we're focusing on species
    return {
      success: true,
      pathway_carousel: {
        "LPS": {
          "title": "LPS (Lipopolysaccharide) Pathway",
          "status": "Normal",
          "metrics": []
        },
        "neurotransmitter": {
          "title": "Neurotransmitter Pathway", 
          "status": "Good",
          "metrics": []
        }
      },
      domain_info: { domain_id: domainId }
    };
  }

  /**
   * Get recommendations data for a domain (legacy support)
   * @param {number} domainId - Domain ID
   * @param {number} customerId - Customer ID
   * @returns {Promise} - Recommendations data
   */
  async getRecommendationsData(domainId, customerId) {
    // Return basic recommendations structure
    return {
      success: true,
      recommendations: {
        supplements: [],
        lifestyle: [],
        dietary: []
      },
      domain_info: { domain_id: domainId }
    };
  }

  /**
   * TYPE 1: Get all microbiome clinical trials
   * @param {number} limit - Number of trials to return (default: 50)
   * @param {string} status - Filter by status (RECRUITING, NOT_YET_RECRUITING)
   * @param {string} phase - Filter by phase (PHASE_1, PHASE_2, PHASE_3, PHASE_4)
   * @returns {Promise} - All clinical trials data
   */
  async getAllClinicalTrials(limit = 50, status = null, phase = null) {
    try {
      let endpoint = `/api/clinical-trials?limit=${limit}`;
      if (status) endpoint += `&status=${status}`;
      if (phase) endpoint += `&phase=${phase}`;
      
      const result = await this.request(endpoint);
      
      if (result.success && result.data) {
        return {
          success: true,
          trials: this.transformTrials(result.data.trials || []),
          count: result.data.count,
          total_matched: result.data.total_matched,
          total_available: result.data.total_available,
          type: result.data.type
        };
      }
      
      return { success: false, trials: [], message: "No trials available" };
    } catch (error) {
      console.error('Error fetching all clinical trials:', error);
      return { success: false, trials: [], error: error.message };
    }
  }

  /**
   * TYPE 2: Get domain-specific clinical trials
   * @param {string} domain - Health domain (gut, liver, heart, cognitive, skin, aging)
   * @param {number} limit - Number of trials to return (default: 50)
   * @param {string} status - Filter by status (RECRUITING, NOT_YET_RECRUITING)
   * @param {string} phase - Filter by phase (PHASE_1, PHASE_2, PHASE_3, PHASE_4)
   * @returns {Promise} - Domain-specific clinical trials
   */
  async getDomainClinicalTrials(domain, limit = 50, status = null, phase = null) {
    try {
      let endpoint = `/api/clinical-trials/by-domain/${domain}?limit=${limit}`;
      if (status) endpoint += `&status=${status}`;
      if (phase) endpoint += `&phase=${phase}`;
      
      const result = await this.request(endpoint);
      
      if (result.success && result.data) {
        return {
          success: true,
          trials: this.transformTrials(result.data.trials || []),
          domain: result.data.domain,
          count: result.data.count,
          total_matched: result.data.total_matched,
          type: result.data.type
        };
      }
      
      return { success: false, trials: [], message: `No trials found for domain: ${domain}` };
    } catch (error) {
      console.error(`Error fetching clinical trials for domain ${domain}:`, error);
      return { success: false, trials: [], error: error.message };
    }
  }

  /**
   * Search clinical trials by keyword
   * @param {string} query - Search query
   * @param {number} limit - Number of trials to return (default: 50)
   * @param {string} status - Filter by status
   * @param {string} phase - Filter by phase
   * @returns {Promise} - Search results
   */
  async searchClinicalTrials(query, limit = 50, status = null, phase = null) {
    try {
      let endpoint = `/api/clinical-trials/search?q=${encodeURIComponent(query)}&limit=${limit}`;
      if (status) endpoint += `&status=${status}`;
      if (phase) endpoint += `&phase=${phase}`;
      
      const result = await this.request(endpoint);
      
      if (result.success && result.data) {
        return {
          success: true,
          trials: this.transformTrials(result.data.trials || []),
          search_query: result.data.search_query,
          count: result.data.count,
          total_matched: result.data.total_matched,
          type: result.data.type
        };
      }
      
      return { success: false, trials: [], message: "No matching trials found" };
    } catch (error) {
      console.error('Error searching clinical trials:', error);
      return { success: false, trials: [], error: error.message };
    }
  }

  /**
   * Get customer-specific personalized clinical trials
   * @param {number} customerId - Customer ID
   * @param {number} limit - Number of trials to return (default: 50)
   * @param {string} status - Filter by status
   * @param {string} phase - Filter by phase
   * @returns {Promise} - Personalized clinical trials
   */
  async getCustomerClinicalTrials(customerId, limit = 50, status = null, phase = null) {
    try {
      let endpoint = `/api/customer/${customerId}/clinical-trials?limit=${limit}`;
      if (status) endpoint += `&status=${status}`;
      if (phase) endpoint += `&phase=${phase}`;
      
      const result = await this.request(endpoint);
      
      if (result.success && result.data) {
        return {
          success: true,
          trials: this.transformTrials(result.data.trials || []),
          customer_id: result.data.customer_id,
          customer_domains: result.data.customer_domains,
          count: result.data.count,
          total_matched: result.data.total_matched,
          type: result.data.type
        };
      }
      
      return { success: false, trials: [], message: "No personalized trials available" };
    } catch (error) {
      console.error('Error fetching customer clinical trials:', error);
      return { success: false, trials: [], error: error.message };
    }
  }

  /**
   * Transform backend trial data to frontend format
   * @param {array} trials - Raw trials from API
   * @returns {array} - Transformed trials
   */
  transformTrials(trials) {
    return (trials || []).map(trial => ({
      trial_id: trial.nct_id,
      nct_id: trial.nct_id,
      name: trial.title,
      title: trial.title,
      description: trial.description || '',
      status: this.mapStatus(trial.status),
      status_raw: trial.status,
      phase: this.mapPhase(trial.phase),
      phase_raw: trial.phase,
      enrollment: trial.enrollment || 0,
      participants: Math.floor((trial.enrollment || 0) * 0.6), // Estimate current participants
      max_participants: trial.enrollment || 100,
      completion_percentage: Math.floor(Math.random() * 100), // Placeholder
      conditions: trial.conditions || [],
      interventions: trial.interventions || [],
      sponsor: trial.sponsor || 'Unknown Sponsor',
      vendor: trial.sponsor || 'Unknown Sponsor',
      start_date: trial.start_date,
      completion_date: trial.completion_date,
      countries: trial.countries || ['Unknown'],
      url: trial.url || `https://clinicaltrials.gov/study/${trial.nct_id}`,
      trial_code: trial.nct_id,
      duration: this.calculateDuration(trial.start_date, trial.completion_date),
      key_findings: trial.description ? trial.description.substring(0, 100) + '...' : ''
    }));
  }

  /**
   * Map API status to UI status
   */
  mapStatus(apiStatus) {
    const statusMap = {
      'RECRUITING': 'open',
      'NOT_YET_RECRUITING': 'pending',
      'ACTIVE_NOT_RECRUITING': 'closed',
      'COMPLETED': 'closed',
      'WITHDRAWN': 'closed'
    };
    return statusMap[apiStatus] || 'active';
  }

  /**
   * Map API phase to UI phase
   */
  mapPhase(apiPhase) {
    const phaseMap = {
      'PHASE_1': 'none',
      'PHASE_2': 'ongoing',
      'PHASE_3': 'proven',
      'PHASE_4': 'proven'
    };
    return phaseMap[apiPhase] || 'ongoing';
  }

  /**
   * Calculate duration between dates
   */
  calculateDuration(startDate, endDate) {
    if (!startDate || !endDate) return 'Duration N/A';
    try {
      const start = new Date(startDate);
      const end = new Date(endDate);
      const months = Math.round((end - start) / (1000 * 60 * 60 * 24 * 30));
      return `${months} months`;
    } catch {
      return 'Duration N/A';
    }
  }

  /**
   * Legacy method for backward compatibility
   */
  async getClinicalTrials(domainName) {
    if (domainName && domainName !== 'all') {
      return this.getDomainClinicalTrials(domainName);
    }
    return this.getAllClinicalTrials();
  }

  // ============================================
  // FALLBACK DATA METHODS
  // ============================================

  /**
   * Get fallback data when API is unavailable
   * @param {string} endpoint - API endpoint that failed
   * @returns {Object} - Fallback data structure
   */
  getFallbackData(endpoint) {
    console.log(`📱 Generating fallback data for: ${endpoint}`);
    
    return {
      success: false,
      message: "API unavailable, using fallback data",
      data: {
        domain_info: {
          domain_name: "Health Domain",
          description: "Fallback data - API unavailable",
          score: 2.5,
          diversity: 2.0,
          status: "warning"
        },
        health_metrics: [],
        species_carousel: {},
        metadata: {
          data_source: "FALLBACK_DATA",
          endpoint: endpoint
        }
      }
    };
  }
}

// Create and export the service instance
const apiService = new ApiService();

// Expose globally for easy testing in browser console
if (typeof window !== 'undefined') {
  window.apiService = apiService;
  window.customerApiService = customerApiService;
}

export default apiService;