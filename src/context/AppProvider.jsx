// context/AppProvider.jsx - Updated with customer-specific mock data
// MAINTAINS EXACT SAME STRUCTURE AND STYLING - Only data changes

import React, { useReducer, useEffect, useCallback } from 'react';
import { AppContext } from './AppContext';
import apiService from '../services/api';

// Import the new customer-specific service  
import customerApiService from '../services/customerApiService';

// Initial State - SAME AS BEFORE
const initialState = {
  user: {
    name: 'Loading...',
    initials: 'L',
    reportId: 'Loading...',
    lastUpdated: 'Loading...'
  },
  healthData: {
    diversityScore: 2.8,
    overallScore: 3.5,
    domains: {
      liver: { score: 2.8, diversity: 2.5, status: 'poor' },
      aging: { score: 2.6, diversity: 2.4, status: 'poor' },
      skin: { score: 2.9, diversity: 2.7, status: 'warning' },
      cognitive: { score: 3.8, diversity: 3.2, status: 'good' },
      gut: { score: 3.2, diversity: 3.0, status: 'good' },
      heart: { score: 3.5, diversity: 3.0, status: 'good' }
    }
  },
  modal: {
    isOpen: false,
    content: null,
    title: ''
  },
  activeSection: 'current-report',
  currentPage: 'report',
  loading: true,
  error: null,
  apiConnected: false,
  customerId: null,
  userId: null,
  username: null
};

// Action Types - SAME AS BEFORE
const ACTIONS = {
  SET_ACTIVE_SECTION: 'SET_ACTIVE_SECTION',
  SET_CURRENT_PAGE: 'SET_CURRENT_PAGE',
  SET_CUSTOMER_DATA: 'SET_CUSTOMER_DATA',
  OPEN_MODAL: 'OPEN_MODAL',
  CLOSE_MODAL: 'CLOSE_MODAL',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  UPDATE_HEALTH_DATA: 'UPDATE_HEALTH_DATA',
  UPDATE_USER: 'UPDATE_USER',
  SET_API_CONNECTED: 'SET_API_CONNECTED',
  LOAD_DASHBOARD_DATA: 'LOAD_DASHBOARD_DATA'
};

// Reducer Function - SAME AS BEFORE
function appReducer(state, action) {
  switch (action.type) {
    case ACTIONS.SET_ACTIVE_SECTION:
      return { ...state, activeSection: action.payload };
    
    case ACTIONS.SET_CURRENT_PAGE:
      return { ...state, currentPage: action.payload };
    
    case ACTIONS.SET_CUSTOMER_DATA:
      return { 
        ...state, 
        customerId: action.payload.customerId,
        userId: action.payload.userId,
        username: action.payload.username
      };
    
    case ACTIONS.OPEN_MODAL:
      return {
        ...state,
        modal: {
          isOpen: true,
          content: action.payload.content,
          title: action.payload.title
        }
      };
    
    case ACTIONS.CLOSE_MODAL:
      return {
        ...state,
        modal: {
          isOpen: false,
          content: null,
          title: ''
        }
      };
    
    case ACTIONS.SET_LOADING:
      return { ...state, loading: action.payload };
    
    case ACTIONS.SET_ERROR:
      return { ...state, error: action.payload };
    
    case ACTIONS.UPDATE_HEALTH_DATA:
      return { ...state, healthData: { ...state.healthData, ...action.payload } };
    
    case ACTIONS.UPDATE_USER:
      return { ...state, user: { ...state.user, ...action.payload } };
    
    case ACTIONS.SET_API_CONNECTED:
      return { ...state, apiConnected: action.payload };
    
    case ACTIONS.LOAD_DASHBOARD_DATA:
      return {
        ...state,
        user: action.payload.user,
        healthData: action.payload.healthData,
        loading: false,
        error: null
      };
    
    default:
      return state;
  }
}

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // UPDATED: Resolve customer ID from URL or default to test customer
  const resolveCustomerFromURL = useCallback(async () => {
    console.log('🔍 Resolving customer ID from URL...');
    
    try {
      let customerId = null;
      
      // Check query parameter first: ?customer=264
      const urlParams = new URLSearchParams(window.location.search);
      const customerIdFromQuery = urlParams.get('customer');
      
      if (customerIdFromQuery) {
        customerId = parseInt(customerIdFromQuery);
        console.log(`📝 Customer ID from query parameter: ${customerId}`);
      } else {
        // Check path-based URL: /customer/264
        const pathMatch = window.location.pathname.match(/\/customer\/(\d+)/);
        if (pathMatch && pathMatch[1]) {
          customerId = parseInt(pathMatch[1]);
          console.log(`📝 Customer ID from URL path: ${customerId}`);
        } else {
          // Default to John Doe for testing
          customerId = 3091;
          console.log(`📝 Using default customer ID: ${customerId}`);
        }
      }
      
      // Set customer ID in both services
      customerApiService.setCustomerId(customerId);
      
      dispatch({
        type: ACTIONS.SET_CUSTOMER_DATA,
        payload: {
          customerId: customerId,
          userId: customerId,
          username: `customer_${customerId}`
        }
      });
      
      return customerId;
    } catch (error) {
      console.error('❌ Error resolving customer ID:', error);
      // Fallback to default customer
      const defaultCustomerId = 3091;
      customerApiService.setCustomerId(defaultCustomerId);
      
      dispatch({
        type: ACTIONS.SET_CUSTOMER_DATA,
        payload: {
          customerId: defaultCustomerId,
          userId: defaultCustomerId,
          username: `customer_${defaultCustomerId}`
        }
      });
      
      return defaultCustomerId;
    }
  }, []);

  // NEW: Generate recommendations when customer logs in
  const generateRecommendationsOnLogin = useCallback(async (customerId) => {
    try {
      console.log(`🧠 Generating recommendations for customer ${customerId}...`);
      
      // Call the new cached recommendations endpoint in background
      const response = await fetch(`${customerApiService.baseURL}/api/customer/${customerId}/generate-all-recommendations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Recommendations generated:', data);
        
        // Optionally show a subtle notification
        if (data.success) {
          console.log(`🎯 Generated recommendations for ${data.domains_processed} domains`);
        }
      } else {
        console.warn('⚠️ Recommendation generation failed (non-blocking):', response.status);
      }
    } catch (error) {
      console.error('⚠️ Recommendation generation failed (non-blocking):', error);
      // Don't throw - this is a background operation that shouldn't block login
    }
  }, []);

  // UPDATED: Load dashboard data using customer-specific service
  const loadDashboardData = useCallback(async () => {
    if (!state.customerId) {
      console.log('⚠️ No customer ID available for dashboard loading');
      return;
    }

    console.log(`🔄 Loading dashboard data for customer ${state.customerId}...`);
    
    try {
      dispatch({ type: ACTIONS.SET_LOADING, payload: true });
      dispatch({ type: ACTIONS.SET_ERROR, payload: null });

      // Use the new customer-specific API service
      const result = await customerApiService.loadDashboardData(state.customerId);
      
      if (result.success) {
        console.log(`✅ Dashboard data loaded successfully for customer ${state.customerId}`);
        
        dispatch({
          type: ACTIONS.LOAD_DASHBOARD_DATA,
          payload: result.data
        });
        
        dispatch({ type: ACTIONS.SET_API_CONNECTED, payload: true });
        console.log(`📊 Data source: ${result.source}`);
        
      } else {
        throw new Error(result.error || 'Failed to load dashboard data');
      }
      
    } catch (error) {
      console.error(`❌ Error loading dashboard data for customer ${state.customerId}:`, error);
      
      // Load fallback data
      loadFallbackData();
      
      dispatch({ type: ACTIONS.SET_ERROR, payload: error.message });
      dispatch({ type: ACTIONS.SET_API_CONNECTED, payload: false });
      console.log('📱 Using offline data.');
    }
  }, [state.customerId]);

  // UPDATED: Load fallback data with customer-specific defaults
  const loadFallbackData = () => {
    console.log('📱 Loading fallback data...');
    
    // Get customer-specific fallback from mock service
    const customerInfo = customerApiService.mockDataService?.getCustomerInfo(state.customerId);
    
    const fallbackName = customerInfo?.name || state.username || 'John Doe';
    const fallbackInitials = customerInfo?.initials || 
      (state.username ? state.username.substring(0, 2).toUpperCase() : 'JD');
    
    dispatch({
      type: ACTIONS.LOAD_DASHBOARD_DATA,
      payload: {
        user: {
          name: fallbackName,
          initials: fallbackInitials,
          reportId: customerInfo?.report_id || 'MG0003',
          lastUpdated: customerInfo?.last_updated || 'March 12, 2025'
        },
        healthData: {
          diversityScore: 2.8,
          overallScore: 3.5,
          domains: {
            liver: { score: 2.8, diversity: 2.5, status: 'poor' },
            aging: { score: 2.6, diversity: 2.4, status: 'poor' },
            skin: { score: 2.9, diversity: 2.7, status: 'warning' },
            cognitive: { score: 3.8, diversity: 3.2, status: 'good' },
            gut: { score: 3.2, diversity: 3.0, status: 'good' },
            heart: { score: 3.5, diversity: 3.0, status: 'good' }
          }
        }
      }
    });
    
    console.log('✅ Fallback data loaded');
  };

  // Initialize app - SAME PATTERN AS BEFORE
  useEffect(() => {
    const initializeApp = async () => {
      console.log('🎬 Initializing app...');
      
      const customerId = await resolveCustomerFromURL();
      console.log(`✅ Customer resolved: ${customerId}`);
      
      // Generate recommendations in background (don't block UI)
      generateRecommendationsOnLogin(customerId);
    };
    
    initializeApp();
  }, [resolveCustomerFromURL, generateRecommendationsOnLogin]);

  // Trigger dashboard load when customer ID changes - SAME AS BEFORE
  useEffect(() => {
    if (state.customerId) {
      console.log(`🔄 Customer ID changed to ${state.customerId}, loading dashboard data...`);
      loadDashboardData();
    }
  }, [state.customerId, loadDashboardData]);

  // Helper functions - SAME AS BEFORE
  const setActiveSection = (section) => {
    dispatch({ type: ACTIONS.SET_ACTIVE_SECTION, payload: section });
  };

  const navigateToPage = (page) => {
    dispatch({ type: ACTIONS.SET_CURRENT_PAGE, payload: page });
  };

  // UPDATED: openModal function to use customer-specific microbiome data
  const openModal = async (content, title) => {
    console.log('🔍 Opening modal with content:', content, 'title:', title);
    
    // Check if this is a domain request - use customer-specific data
    if (typeof content === 'string' && ['liver', 'aging', 'skin', 'cognitive', 'gut', 'heart', 'overall'].includes(content)) {
      console.log(`🎯 Domain modal detected: ${content} - fetching customer-specific data for ${state.customerId}`);
      
      try {
        dispatch({ type: ACTIONS.SET_LOADING, payload: true });
        
        // Use customer-specific API service
        const result = await customerApiService.getCustomerDomainBacteria(state.customerId, content);
        
        if (result.success) {
          console.log(`✅ Customer-specific ${content} data received:`, result.data);
          
          dispatch({ 
            type: ACTIONS.OPEN_MODAL, 
            payload: { 
              content: result.data,  // Pass the customer-specific data object
              title: `${content.charAt(0).toUpperCase() + content.slice(1)} Health Details`
            } 
          });
          
          console.log(`✅ Successfully loaded customer-specific data for: ${content} (Customer ${state.customerId})`);
          console.log(`📊 Data source: ${result.source}`);
        } else {
          throw new Error('Failed to load customer-specific domain data');
        }
      } catch (error) {
        console.error(`❌ Error loading customer-specific data for ${content}:`, error);
        
        // Fallback to basic modal
        dispatch({ 
          type: ACTIONS.OPEN_MODAL, 
          payload: { 
            content: `<div style="padding: 20px; text-align: center;">Error loading ${content} data for customer ${state.customerId}</div>`, 
            title: `${content.charAt(0).toUpperCase() + content.slice(1)} Health Details (Error)` 
          } 
        });
      } finally {
        dispatch({ type: ACTIONS.SET_LOADING, payload: false });
      }
      
      return;
    }
    
    // Handle other modal content types - SAME AS BEFORE
    console.log('🔍 Opening modal with regular content');
    dispatch({ type: ACTIONS.OPEN_MODAL, payload: { content, title } });
  };

  const closeModal = () => {
    dispatch({ type: ACTIONS.CLOSE_MODAL });
  };

  const setLoading = (loading) => {
    dispatch({ type: ACTIONS.SET_LOADING, payload: loading });
  };

  const setError = (error) => {
    dispatch({ type: ACTIONS.SET_ERROR, payload: error });
  };

  const updateHealthData = (data) => {
    dispatch({ type: ACTIONS.UPDATE_HEALTH_DATA, payload: data });
  };

  const updateUser = (userData) => {
    dispatch({ type: ACTIONS.UPDATE_USER, payload: userData });
  };

  // SAME VALUE OBJECT AS BEFORE
  const value = {
    state,
    dispatch,
    setActiveSection,
    navigateToPage,
    openModal,
    closeModal,
    setLoading,
    setError,
    updateHealthData,
    updateUser,
    loadDashboardData,
    resolveCustomerFromURL,
    apiService,
    customerApiService // Add the new service for direct access
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}