// components/Header/Header.jsx - Enhanced with mobile support
import React, { useState, useEffect, useRef } from 'react';
import { useAppContext } from '../../context';
import './Header.css';

const Header = () => {
  const { state, navigateToPage } = useAppContext();
  const { user } = state;
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const profileRef = useRef(null);

  // Detect mobile screen size
  useEffect(() => {
    const checkIsMobile = () => {
      setIsMobile(window.innerWidth <= 768);
      // Close mobile menu when switching to desktop
      if (window.innerWidth > 768) {
        setIsMobileMenuOpen(false);
      }
    };

    checkIsMobile();
    window.addEventListener('resize', checkIsMobile);
    return () => window.removeEventListener('resize', checkIsMobile);
  }, []);

  // Close mobile menu and profile dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (isMobileMenuOpen && !event.target.closest('.mobile-tabs-wrapper') && !event.target.closest('.mobile-nav-toggle')) {
        setIsMobileMenuOpen(false);
      }
      if (isProfileOpen && profileRef.current && !profileRef.current.contains(event.target)) {
        setIsProfileOpen(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [isMobileMenuOpen, isProfileOpen]);

  // Close mobile menu on escape key
  useEffect(() => {
    const handleEscape = (event) => {
      if (event.key === 'Escape' && isMobileMenuOpen) {
        setIsMobileMenuOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isMobileMenuOpen]);

  const tabs = [
    { 
      id: 'report', 
      label: 'Report', 
      icon: 'report', 
      page: 'report'
    },
    { 
      id: 'clinical-trials', 
      label: 'Clinical Trials', 
      icon: 'activity', 
      page: 'clinical-trials'
    }
  ];

  const renderIcon = (iconType) => {
    const iconPaths = {
      report: (
        <>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
          <polyline points="10 9 9 9 8 9"></polyline>
        </>
      ),
      pulse: <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>,
      activity: <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>,
      'map-pin': (
        <>
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
          <circle cx="12" cy="10" r="3"></circle>
        </>
      ),
      hamburger: (
        <>
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <line x1="3" y1="12" x2="21" y2="12"></line>
          <line x1="3" y1="18" x2="21" y2="18"></line>
        </>
      ),
      close: (
        <>
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </>
      )
    };
    
    return iconPaths[iconType] || null;
  };

  const handleTabClick = (tab) => {
    console.log(`Navigating to page: ${tab.page}`);
    navigateToPage(tab.page);
    // Close mobile menu after navigation
    if (isMobile) {
      setIsMobileMenuOpen(false);
    }
  };

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const handleLogout = () => {
    console.log('Logout clicked');
    setIsProfileOpen(false);
    if (isMobile) setIsMobileMenuOpen(false);
  };

  const handleMyTrials = () => {
    navigateToPage('my-trials');
    setIsProfileOpen(false);
    if (isMobile) setIsMobileMenuOpen(false);
  };

  return (
    <header className="portal-header">
      <nav className="main-nav">
        <div className="nav-content">
          <div className="left-section">
            <img src="/assets/images/logo.png" alt="MannBiome Logo" />
            {!isMobile && (
              <a href="#home" className="nav-link">Home</a>
            )}
          </div>
          
          {/* Desktop Tabs - Hidden on mobile */}
          {!isMobile && (
            <div className="tabs-section">
              {tabs.map((tab) => (
                <div
                  key={tab.id}
                  className={`tab ${state.currentPage === tab.page ? 'active' : ''}`}
                  onClick={() => handleTabClick(tab)}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    {renderIcon(tab.icon)}
                  </svg>
                  {tab.label}
                </div>
              ))}
            </div>
          )}

          {/* Mobile Menu Toggle - Hidden on desktop */}
          {isMobile && (
            <button 
              className="mobile-nav-toggle"
              onClick={toggleMobileMenu}
              aria-label={isMobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={isMobileMenuOpen}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {renderIcon(isMobileMenuOpen ? 'close' : 'hamburger')}
              </svg>
            </button>
          )}
          
          <div className="user-menu" ref={profileRef}>
            <div
              className="user-icon"
              tabIndex="0"
              role="button"
              aria-label={`User ${user.name}`}
              aria-expanded={isProfileOpen}
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setIsProfileOpen(!isProfileOpen); }}
            >
              {user.initials}
            </div>
            <div className="user-name">{user.name}</div>

            {isProfileOpen && (
              <div className="profile-dropdown">
                <button className="profile-dropdown-item" onClick={handleMyTrials}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"></path>
                    <rect x="9" y="3" width="6" height="4" rx="1"></rect>
                    <path d="M9 12h6M9 16h4"></path>
                  </svg>
                  My Trials
                </button>
                <div className="profile-dropdown-divider"></div>
                <button className="profile-dropdown-item profile-dropdown-logout" onClick={handleLogout}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"></path>
                    <polyline points="16 17 21 12 16 7"></polyline>
                    <line x1="21" y1="12" x2="9" y2="12"></line>
                  </svg>
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Mobile Tabs Menu - Only shown on mobile */}
        {isMobile && (
          <div className="mobile-tabs-wrapper">
            <div className={`tabs-section mobile ${isMobileMenuOpen ? 'open' : ''}`}>
              {/* Home link in mobile menu */}
              <a 
                href="#home" 
                className="nav-link" 
                onClick={() => setIsMobileMenuOpen(false)}
              >
                Home
              </a>
              
              {/* Tab items in mobile menu */}
              {tabs.map((tab) => (
                <div
                  key={tab.id}
                  className={`tab ${state.currentPage === tab.page ? 'active' : ''}`}
                  onClick={() => handleTabClick(tab)}
                  role="button"
                  tabIndex="0"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleTabClick(tab);
                    }
                  }}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    {renderIcon(tab.icon)}
                  </svg>
                  {tab.label}
                </div>
              ))}
            </div>
          </div>
        )}
      </nav>
    </header>
  );
};

export default Header;