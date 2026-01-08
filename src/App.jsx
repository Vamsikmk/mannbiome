// App.jsx - Updated with Clinical Trials as separate page
import React from 'react';
import Header from './components/Header/Header';
import SideNav from './components/Navigation/SideNav';
import Dashboard from './pages/Dashboard/Dashboard';
import Analysis from './pages/Analysis/Analysis';
import Recommendations from './pages/Recommendations/Recommendations';
import Download from './pages/Download/Download';
import ClinicalTrials from './pages/ClinicalTrials/ClinicalTrials';
import HealthModal from './components/Modal/HealthModal';
import { AppProvider } from './context'; // Import from barrel export
import { useAppContext } from './context';
import './styles/globals.css';
import './App.css';

// API Status Component
const ApiStatus = () => {
  const { state } = useAppContext();
  
  if (state.loading) {
    return (
      <div style={{
        position: 'fixed',
        top: '10px',
        right: '10px',
        background: '#ffc107',
        color: 'white',
        padding: '8px 12px',
        borderRadius: '4px',
        fontSize: '12px',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <div style={{
          width: '12px',
          height: '12px',
          border: '2px solid rgba(255,255,255,0.3)',
          borderRadius: '50%',
          borderTop: '2px solid white',
          animation: 'spin 1s linear infinite'
        }}></div>
        Loading...
      </div>
    );
  }

  return (
    <div style={{
      position: 'fixed',
      top: '10px',
      right: '10px',
      background: state.apiConnected ? '#28a745' : '#dc3545',
      color: 'white',
      padding: '8px 12px',
      borderRadius: '4px',
      fontSize: '12px',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      gap: '6px'
    }}>
      <div style={{
        width: '8px',
        height: '8px',
        background: 'white',
        borderRadius: '50%'
      }}></div>
      {state.apiConnected ? 'API Connected' : 'Offline Mode'}
    </div>
  );
};

// Main App Content Component
const AppContent = () => {
  const { state } = useAppContext();

  // Show Clinical Trials page separately
  if (state.currentPage === 'clinical-trials') {
    return (
      <div className="app">
        <Header />
        <ApiStatus />
        
        {state.error && (
          <div style={{
            background: '#fff3cd',
            color: '#856404',
            padding: '10px 20px',
            textAlign: 'center',
            borderBottom: '1px solid #ffeaa7',
            fontSize: '14px'
          }}>
            ⚠️ {state.error}
          </div>
        )}
        
        {/* Clinical Trials Full Page */}
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 20px' }}>
          <ClinicalTrials />
        </div>
        <HealthModal />
        
        {/* Add spinning animation CSS */}
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Default report page
  return (
    <div className="app">
      <Header />
      <ApiStatus />
      
      {state.error && (
        <div style={{
          background: '#fff3cd',
          color: '#856404',
          padding: '10px 20px',
          textAlign: 'center',
          borderBottom: '1px solid #ffeaa7',
          fontSize: '14px'
        }}>
          ⚠️ {state.error}
        </div>
      )}
      
      <div className="portal-container">
        {/* Hide sidebar while loading */}
        {!state.loading && <SideNav />}
        <main className="content-area">
          <Dashboard />
          {!state.loading && (
            <>
              <div className="section-divider"></div>
              <Analysis />
              <div className="section-divider"></div>
              <Recommendations />
              <div className="section-divider"></div>
              <Download />
            </>
          )}
        </main>
      </div>
      <HealthModal />
      
      {/* Add spinning animation CSS */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}

export default App;