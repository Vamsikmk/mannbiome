// services/customerApiService.js - Updated to use real backend APIs
// Switches from mock data to actual backend endpoints at localhost:8001

// Import mock data service as fallback only
import mockDataService from '../data/mockPatients/mockDataService';

class CustomerApiService {
  constructor() {
    // this.baseURL = 'https://gnss5bq5km.us-east-2.awsapprunner.com';
    this.baseURL = 'http://127.0.0.1:8001';
    this.currentCustomerId = null;
    this.mockDataService = mockDataService; // Keep as fallback only
  }

  // Set customer ID
  setCustomerId(customerId) {
    this.currentCustomerId = customerId;
    // console.log(`🔄 Customer set to: ${customerId}`);
  }

  // Test API connectivity
  async testConnection() {
    try {
      const response = await fetch(`${this.baseURL}/api/health-check`);
      const isConnected = response.ok;
      console.log(`🌐 API Connection: ${isConnected ? 'Connected' : 'Failed'}`);
      return { success: isConnected };
    } catch (error) {
      console.log('📱 API unavailable, will use fallback');
      return { success: false };
    }
  }

  // Generic request method with error handling
  async request(endpoint, options = {}) {
    try {
      const url = `${this.baseURL}${endpoint}`;
      // console.log(`📡 API Request: ${url}`);

      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      // console.log(`✅ API Response received for: ${endpoint}`);
      return { success: true, data, source: 'REAL_API' };

    } catch (error) {
      // console.error(`❌ API Error for ${endpoint}:`, error.message);
      return { success: false, error: error.message, source: 'API_ERROR' };
    }
  }

  // Get customer profile/info
  async getUserProfile(customerId) {
    console.log(`👤 Getting user profile for customer ${customerId}`);

    // Try real API - no fallback
    const result = await this.request(`/api/customer/${customerId}/info`);

    if (result.success) {
      // Transform backend response to expected frontend format
      const customerInfo = result.data.customer_info;
      return {
        success: true,
        user: {
          customer_id: customerInfo.customer_id,
          user_id: customerInfo.user_id,
          email: customerInfo.email,
          first_name: customerInfo.first_name,
          last_name: customerInfo.last_name,
          full_name: customerInfo.full_name,
          initials: customerInfo.initials,
          report_id: customerInfo.report_id,
          created_at: customerInfo.created_at,
          last_updated: customerInfo.last_updated,
          status: customerInfo.status,
          age: customerInfo.age
        },
        source: 'REAL_API'
      };
    }

    // Don't fall back - throw error instead
    throw new Error(`Failed to get user profile from API: ${result.error}`);
  }

  // Get customer microbiome data (overall)
  async getCustomerMicrobiomeData(customerId) {
    console.log(`🎯 Getting microbiome data for customer ${customerId}`);

    // Try real API - no fallback
    const result = await this.request(`/api/customer/${customerId}/microbiome-data`);

    if (result.success) {
      console.log('✅ Real microbiome data received');
      return result;
    }

    // Don't fall back - throw error instead
    throw new Error(`Failed to get microbiome data from API: ${result.error}`);
  }

  // Get domain-specific bacteria data
  async getCustomerDomainBacteria(customerId, domain) {
    // console.log(`🎯 Getting ${domain} bacteria for customer ${customerId}`);

    // Special handling for "overall" domain
    if (domain.toLowerCase() === 'overall') {
      return this.getOverallHealthSummary(customerId);
    }

    // Map domain names to domain IDs for backend API
    const domainIdMap = {
      'gut': 1,
      'liver': 2,
      'heart': 3,
      'skin': 4,
      'cognitive': 5,
      'aging': 6
    };

    const domainId = domainIdMap[domain.toLowerCase()];

    if (!domainId) {
      // console.error(`❌ Invalid domain: ${domain}`);
      throw new Error(`Invalid domain: ${domain}`);
    }

    try {
      // Get modal data (species, pathways, etc.)
      const modalResult = await this.request(`/api/health-domains/${domainId}/modal-data/${customerId}`);
      
      if (!modalResult.success) {
        throw new Error(`Failed to get ${domain} modal data: ${modalResult.error}`);
      }

      // Get recommendations for this domain
      console.log(`🧠 Getting ${domain} recommendations for customer ${customerId}`);
      const recommendationsResult = await this.request(`/api/customer/${customerId}/llm-recommendations?domain=${domain}&force_regenerate=false`);
      
      console.log('🔍 Full recommendations response:', recommendationsResult);
      console.log('🔍 Recommendations data structure:', recommendationsResult.data);
      
      if (recommendationsResult.success && recommendationsResult.data && recommendationsResult.data.recommendations) {
        // Add recommendations to the modal data
        modalResult.data.recommendations = recommendationsResult.data.recommendations;
        console.log(`✅ Added ${domain} recommendations to modal data`);
      } else {
        console.warn(`⚠️ No recommendations available for ${domain}:`, recommendationsResult);
        modalResult.data.recommendations = null;
      }

      // console.log(`✅ Complete ${domain} data received (with recommendations)`);
      return modalResult;

    } catch (error) {
      // console.error(`❌ Error getting ${domain} data:`, error);
      throw error;
    }
  }

  // Get overall health summary (aggregate of all domains)
  async getOverallHealthSummary(customerId) {
    try {
      console.log(`📊 Getting overall health summary for customer ${customerId}`);
      
      // Get overall microbiome data
      const overallResult = await this.request(`/api/customer/${customerId}/microbiome-data`);
      
      if (overallResult.success) {
        // Structure the data similar to domain-specific data
        const overallData = {
          domain: {
            domain_id: 0,
            domain_name: 'overall',
            description: 'Overall health summary across all domains', 
            score: overallResult.data.scores?.overall_score || 3.5,
            diversity: overallResult.data.scores?.diversity_score || 3.0,
            status: this._getStatusFromScore(overallResult.data.scores?.overall_score || 3.5),
            comment: 'Your overall microbiome health summary'
          },
          species_carousel: overallResult.data.species_carousel || {
            bacteria: { title: 'Top Bacterial Species', status: 'Normal', species: [] },
            probiotics: { title: 'Probiotic Organisms', status: 'Normal', species: [] },
            pathogens: { title: 'Pathogenic Bacteria', status: 'Normal', species: [] },
            virus: { title: 'Viral Species', status: 'Normal', species: [] },
            fungi: { title: 'Fungal Species', status: 'Normal', species: [] },
            protozoa: { title: 'Protozoa Species', status: 'Normal', species: [] }
          },
          pathway_carousel: [], // Overall microbiome data doesn't have pathway carousel
          recommendations: null // Overall doesn't have specific recommendations
        };

        console.log(`✅ Overall health summary prepared`);
        return {
          success: true,
          data: overallData,
          source: 'REAL_API'
        };
      } else {
        throw new Error(`Failed to get overall health data: ${overallResult.error}`);
      }
    } catch (error) {
      console.error(`❌ Error getting overall health summary:`, error);
      throw error;
    }
  }

  // Load complete dashboard data
  async loadDashboardData(customerId) {
    console.log(`📄 Loading dashboard data for customer ${customerId}...`);

    try {
      // Try real API first
      const result = await this.request(`/api/customer/${customerId}/dashboard-data`);

      if (result.success) {
        console.log('✅ Real dashboard data loaded');
        console.log('🔍 Raw backend data structure:', result.data);

        // Transform backend response to expected frontend format
        const backendData = result.data;

        // The data is nested under dashboard_data
        const dashboardData = backendData.dashboard_data;

        // Extract user data
        const userData = {
          name: dashboardData.user.full_name,
          initials: dashboardData.user.initials,
          reportId: dashboardData.user.report_id,
          lastUpdated: dashboardData.user.last_updated
        };

        // Extract health data
        const healthData = {
          diversityScore: dashboardData.health_data.diversity_score,
          overallScore: dashboardData.health_data.overall_score,
          last_updated: dashboardData.health_data.last_updated, // Add this line
          domains: {
            // Add overall domain if not present
            overall: {
              score: dashboardData.health_data.overall_score || 3.5,
              diversity: dashboardData.health_data.diversity_score || 3.0,
              status: this._getStatusFromScore(dashboardData.health_data.overall_score || 3.5),
              comment: 'Your overall health indicators show positive trends with room for improvement in specific areas.'
            },
            // Include existing domains
            ...dashboardData.health_data.domains
          }
        };

        console.log('✅ Transformed data:', { userData, healthData });

        return {
          success: true,
          data: {
            user: userData,
            healthData: healthData
          },
          source: 'REAL_API'
        };
      }

    } catch (error) {
      console.error('❌ Dashboard API error:', error);
      console.log('❌ Stopping fallback - will only use real API or fail');
      throw error; // Don't fall back to mock - fail if API doesn't work
    }

    // Remove fallback - force API only
    throw new Error('Dashboard API failed - no fallback allowed');

    try {
      // Get user profile from mock
      const profileResult = await this.getUserProfile(customerId);

      if (!profileResult.success) {
        throw new Error('Failed to load user profile');
      }

      const userInfo = profileResult.user;

      // Get domain scores from mock data
      const domainScores = {};
      const domains = ['liver', 'aging', 'skin', 'cognitive', 'gut', 'heart'];

      for (const domain of domains) {
        const domainResult = await this.getCustomerDomainBacteria(customerId, domain);

        if (domainResult.success && domainResult.data) {
          const domainInfo = domainResult.data.domain_info;
          domainScores[domain] = {
            score: domainInfo.score,
            diversity: domainInfo.diversity,
            status: domainInfo.status
          };
        } else {
          // Default fallback scores
          domainScores[domain] = {
            score: 2.5,
            diversity: 2.0,
            status: 'warning'
          };
        }
      }

      // Calculate overall scores
      const scores = Object.values(domainScores);
      const avgScore = scores.reduce((sum, s) => sum + s.score, 0) / scores.length;
      const avgDiversity = scores.reduce((sum, s) => sum + s.diversity, 0) / scores.length;

      return {
        success: true,
        data: {
          user: {
            name: userInfo.full_name,
            initials: userInfo.initials,
            reportId: userInfo.report_id,
            lastUpdated: userInfo.last_updated
          },
          healthData: {
            diversityScore: Number(avgDiversity.toFixed(1)),
            overallScore: Number(avgScore.toFixed(1)),
            domains: domainScores
          }
        },
        source: 'MOCK_FALLBACK'
      };

    } catch (error) {
      console.error('❌ Error loading dashboard data:', error);
      throw error;
    }
  }

  // Get bacteria domains data (for backend compatibility)
  async getCustomerBacteriaDomains(customerId) {
    console.log(`🧬 Getting bacteria domains for customer ${customerId}`);

    // Try real API first
    const result = await this.request(`/api/customer/${customerId}/bacteria-domains`);

    if (result.success) {
      console.log('✅ Real bacteria domains data received');
      return result;
    }

    // Fallback - build from individual domain calls
    console.log('📱 Building domains from mock data');
    const domains = ['liver', 'aging', 'skin', 'cognitive', 'gut', 'heart'];
    const domainBacteria = {};

    for (const domain of domains) {
      const domainResult = await this.getCustomerDomainBacteria(customerId, domain);
      if (domainResult.success) {
        domainBacteria[domain] = domainResult.data;
      }
    }

    return {
      success: true,
      data: {
        customer_id: customerId,
        domain_bacteria: domainBacteria
      },
      source: 'MOCK_FALLBACK'
    };
  }

  // Switch customer for testing
  async switchCustomer(newCustomerId) {
    console.log(`🔄 Switching to customer ${newCustomerId}`);

    this.setCustomerId(newCustomerId);

    // Get customer information
    const customerResult = await this.getUserProfile(newCustomerId);

    if (customerResult.success) {
      const customerInfo = customerResult.user;
      console.log(`✅ Switched to: ${customerInfo.full_name} (${newCustomerId})`);

      return {
        success: true,
        message: `Switched to ${customerInfo.full_name}`,
        customerInfo: customerInfo,
        source: customerResult.source
      };
    }

    return {
      success: false,
      error: 'Failed to switch customer',
      source: 'ERROR'
    };
  }

  // Debug method to test all customers
  async testAllCustomers() {
    const customers = [3091, 8420, 5500]; // Known test customers
    const results = {};

    for (const customerId of customers) {
      try {
        const profileResult = await this.getUserProfile(customerId);
        const overallData = await this.getCustomerMicrobiomeData(customerId);
        const agingData = await this.getCustomerDomainBacteria(customerId, 'aging');

        results[customerId] = {
          name: profileResult.user?.full_name || `Customer ${customerId}`,
          profile_source: profileResult.source,
          overall_score: overallData.data?.domain_info?.score || 'N/A',
          overall_source: overallData.source,
          aging_score: agingData.data?.domain_info?.score || 'N/A',
          aging_source: agingData.source,
          success: true
        };
      } catch (error) {
        results[customerId] = {
          name: `Customer ${customerId}`,
          error: error.message,
          success: false
        };
      }
    }

    return {
      success: true,
      message: "All customers tested - showing data sources",
      results: results
    };
  }

  // Get available test customers
  getAvailableCustomers() {
    return {
      success: true,
      customers: [
        { id: 3091, name: "John Doe", status: "poor", description: "Test customer with poor health indicators" },
        { id: 8420, name: "Jane Smith", status: "excellent", description: "Test customer with excellent health" },
        { id: 5500, name: "Mike Johnson", status: "mixed", description: "Test customer with mixed results" }
      ],
      message: "Available test customers (will use real API if data exists, otherwise mock data)"
    };
  }

  // Helper method to determine status from score
  _getStatusFromScore(score) {
    if (score >= 4.0) return 'good';
    if (score >= 3.0) return 'warning';
    if (score >= 2.0) return 'poor';
    return 'critical';
  }
}

// Create and export instance
const customerApiService = new CustomerApiService();

// Expose globally for testing in browser console
if (typeof window !== 'undefined') {
  window.customerApiService = customerApiService;
  window.mockDataService = mockDataService;
}

export default customerApiService;