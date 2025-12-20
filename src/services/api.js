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
   * Get clinical trials for a specific health domain (legacy support)
   * @param {string} domainName - Domain name
   * @returns {Promise} - Clinical trials data
   */
  async getClinicalTrials(domainName) {
    const endpoint = `/api/clinical-trials/${domainName}`;
    const result = await this.request(endpoint);
    
    if (result.success) {
      return result;
    }
    
    // Return mock clinical trials
    return {
      success: true,
      trials: [],
      message: "No clinical trials data available"
    };
  }

  /**
   * Get clinical trials for a specific domain with customer ID
   * @param {string} domainId - Domain ID
   * @param {number} customerId - Customer ID
   * @returns {Promise} - Clinical trials data
   */
  async getDomainClinicalTrials(domainId, customerId) {
    try {
      // Use the generic clinical trials endpoint (domain-specific endpoint not available in backend)
      const endpoint = `/api/clinical-trials`;
      const result = await this.request(endpoint);
      
      if (result.success) {
        return {
          success: true,
          trials: result.data || [],
          message: result.message || "No clinical trials data available"
        };
      }
      
      // Return empty clinical trials as fallback
      return {
        success: true,
        trials: [],
        message: "No clinical trials data available for this domain"
      };
    } catch (error) {
      console.warn(`⚠️ Clinical trials request failed, returning empty list:`, error);
      // Return empty data instead of throwing error
      return {
        success: true,
        trials: [],
        message: "Clinical trials data not available"
      };
    }
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