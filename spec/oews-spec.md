# OEWS Streamlit Webapp Specification

## 1. Project Overview

### 1.1 Purpose
Develop a Streamlit web application to visualize Occupational Employment and Wage Statistics (OEWS) data from the U.S. Bureau of Labor Statistics (BLS). The application will allow users to explore employment and wage data across different geographic areas, time periods, and occupations through interactive visualizations.

### 1.2 Scope
- Fetch and process OEWS data from BLS tables (Excel/CSV format)
- Provide interactive filtering capabilities
- Generate comprehensive visualizations
- Deploy on Azure App Service

### 1.3 Target Users
- Labor market researchers
- Economic analysts
- Policy makers
- Job seekers and career counselors
- Business strategists

## 2. Data Sources and Structure

### 2.1 Primary Data Source
- **Source**: Bureau of Labor Statistics (BLS) OEWS Tables
- **URL**: https://www.bls.gov/oes/tables.htm
- **Focus Areas**:
  - State-level data
  - Metropolitan and nonmetropolitan area data

### 2.2 Data Characteristics
- **Coverage**: ~830 occupations
- **Geographic Levels**: Nation, states, ~530 metropolitan/nonmetropolitan areas
- **Classification**: 2018 Standard Occupational Classification (SOC) codes
- **Industry Classification**: 2022 NAICS codes (4-digit level)
- **Update Frequency**: Annual (latest: May 2024)

### 2.3 Data Fields
#### Core Employment Metrics
- **Employment Count**: Total number of workers in occupation
- **Employment RSE**: Relative Standard Error for employment
- **Mean Hourly Wage**: Average hourly wage
- **Mean Annual Wage**: Average annual wage (hourly × 2080 hours)
- **Wage RSE**: Relative Standard Error for wages

#### Wage Distribution Metrics
- **Entry Level Wage** (10th percentile): Hourly and annual
- **Median Wage** (50th percentile): Hourly and annual
- **Experienced Level Wage** (90th percentile): Hourly and annual

#### Geographic Identifiers
- **Area Code**: Unique identifier for geographic area
- **Area Name**: Full name of geographic area
- **Area Type**: State, MSA, or nonmetropolitan area

#### Occupation Identifiers
- **SOC Code**: Standard Occupational Classification code
- **Occupation Title**: Full occupation name
- **Major Group**: High-level occupation category

### 2.4 Data Formats
- **Primary Format**: Excel (.xlsx)
- **Alternative Format**: CSV
- **Typical File Size**: 1-5 MB per geographic area
- **Update Schedule**: Annual release (typically March/April)

### 2.5 Data Limitations
- Excludes: farms, self-employed, military, household workers
- Suppressed data: Occupations with <10 employees
- Data combines 6 survey panels (2021-2024)

## 3. Functional Requirements

### 3.1 Data Acquisition Module
#### 3.1.1 Data Fetching
- **Requirement**: Programmatically download OEWS data files from BLS
- **Input**: Year, geographic area type (state/metropolitan)
- **Output**: Raw Excel/CSV files
- **Error Handling**: Retry logic, timeout handling, validation

#### 3.1.2 Data Processing
- **Requirement**: Parse and clean OEWS data files
- **Functions**:
  - Excel/CSV parsing
  - Data type conversion
  - Missing value handling
  - Data validation
- **Output**: Structured pandas DataFrame

#### 3.1.3 Data Caching
- **Requirement**: Cache processed data to improve performance
- **Strategy**: File-based caching with TTL
- **Cache Key**: Year + Geographic Area + Data Type
- **Refresh Logic**: Manual refresh option + automatic daily check

### 3.2 User Interface Components

#### 3.2.1 Filter Panel
**Geographic Filters**
- **State Selector**: Multi-select dropdown with all 50 states + DC + territories
- **Metropolitan Area Selector**: Dependent on state selection
- **Area Type Toggle**: State vs Metropolitan/Nonmetropolitan

**Temporal Filters**
- **Year Selector**: Range slider or multi-select (2019-2024)
- **Data Vintage**: Option to compare different survey periods

**Occupation Filters**
- **Major Group Selector**: SOC major groups (2-digit codes)
- **Detailed Occupation**: Search/filter by occupation title
- **SOC Code Search**: Direct SOC code input
- **Industry Context**: Optional NAICS industry filter

#### 3.2.2 Visualization Panel
**Chart Types**
- **Employment Bar Charts**: Top N occupations by employment
- **Wage Distribution**: Box plots, histograms, scatter plots
- **Geographic Comparison**: Side-by-side area comparisons
- **Time Series**: Wage/employment trends over years
- **Correlation Analysis**: Employment vs wage relationships

**Interactive Features**
- **Hover Details**: Detailed metrics on hover
- **Click Actions**: Drill-down capabilities
- **Export Options**: PNG, SVG, PDF export
- **Data Tables**: Sortable, filterable data grids

#### 3.2.3 Summary Statistics Panel
- **Key Metrics Display**: Total employment, median wages, top occupations
- **Comparison Metrics**: Year-over-year changes, area rankings
- **Statistical Summaries**: Mean, median, quartiles, standard deviation

### 3.3 Visualization Requirements

#### 3.3.1 Employment Visualizations
- **Bar Charts**: Employment by occupation, sorted by count
- **Tree Maps**: Hierarchical view of occupation categories
- **Geographic Maps**: Choropleth maps for regional employment
- **Bubble Charts**: Employment size vs wage level

#### 3.3.2 Wage Visualizations
- **Box Plots**: Wage distribution by occupation/area
- **Scatter Plots**: Hourly vs annual wage correlations
- **Histograms**: Wage frequency distributions
- **Heat Maps**: Wage levels across occupations and areas

#### 3.3.3 Comparative Visualizations
- **Side-by-side Charts**: Multi-area/multi-year comparisons
- **Ratio Charts**: Employment ratios, wage ratios
- **Ranking Charts**: Top/bottom performers
- **Trend Lines**: Multi-year progression analysis

### 3.4 Data Export Functionality
- **CSV Export**: Filtered data export
- **Excel Export**: Multi-sheet workbooks with charts
- **PDF Reports**: Formatted summary reports
- **Image Export**: High-resolution chart exports

## 4. Technical Architecture

### 4.1 Application Stack
- **Frontend Framework**: Streamlit
- **Backend Language**: Python 3.10+
- **Data Processing**: pandas, numpy
- **Visualization**: plotly, matplotlib, seaborn
- **HTTP Client**: requests, urllib3
- **File Processing**: openpyxl, xlrd

### 4.2 Application Structure
```
oews-streamlit-app/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── config/
│   ├── settings.py       # Configuration management
│   └── constants.py      # BLS URLs, SOC codes, etc.
├── src/
│   ├── data/
│   │   ├── fetcher.py    # BLS data download
│   │   ├── processor.py  # Data cleaning/processing
│   │   └── cache.py      # Caching logic
│   ├── visualization/
│   │   ├── charts.py     # Chart generation
│   │   ├── maps.py       # Geographic visualizations
│   │   └── tables.py     # Data table components
│   └── utils/
│       ├── helpers.py    # Utility functions
│       └── validators.py # Data validation
├── data/
│   ├── cache/           # Cached processed data
│   └── raw/             # Raw downloaded files
├── assets/
│   ├── images/          # Logo, icons
│   └── styles/          # Custom CSS
└── tests/
    ├── test_data.py     # Data processing tests
    └── test_viz.py      # Visualization tests
```

### 4.3 Data Flow Architecture
1. **User Input** → Filter selections via Streamlit widgets
2. **Data Request** → Check cache for requested data
3. **Data Fetch** → Download from BLS if not cached
4. **Data Process** → Clean and structure data
5. **Data Cache** → Store processed data for future use
6. **Visualization** → Generate charts based on processed data
7. **User Output** → Display charts and allow exports

### 4.4 Caching Strategy
- **Level 1**: In-memory caching with streamlit.cache_data
- **Level 2**: Disk-based caching for processed datasets
- **Level 3**: Raw file caching for downloaded BLS files
- **TTL**: 24 hours for processed data, 7 days for raw files
- **Invalidation**: Manual refresh button + automatic daily checks

## 5. Azure Deployment Specification

### 5.1 Azure Services
- **Primary Service**: Azure App Service (Linux)
- **Pricing Tier**: B1 Standard or higher (WebSocket support required)
- **Runtime**: Python 3.10
- **Operating System**: Linux

### 5.2 App Service Configuration
#### 5.2.1 Application Settings
```
WEBSITES_PORT=8000
WEBSITES_ENABLE_APP_SERVICE_STORAGE=true
SCM_DO_BUILD_DURING_DEPLOYMENT=true
STREAMLIT_SERVER_PORT=8000
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
```

#### 5.2.2 Startup Configuration
- **Startup Command**: `python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0 --server.headless true`
- **Enable WebSockets**: True
- **HTTP Version**: 2.0
- **ARR Affinity**: Disabled

### 5.3 Performance Configuration
- **Memory**: 1.75 GB minimum (B1 tier)
- **CPU**: 1 core
- **Scaling**: Manual scaling (1-3 instances)
- **Health Check**: `/health` endpoint

### 5.4 Security Configuration
- **HTTPS Only**: Enabled
- **TLS Version**: 1.2 minimum
- **Environment Variables**: Stored in App Service Configuration
- **Secrets Management**: Azure Key Vault integration for sensitive data

### 5.5 Monitoring and Logging
- **Application Insights**: Enabled for performance monitoring
- **Log Stream**: Real-time application logs
- **Metrics**: CPU, memory, request count, response time
- **Alerts**: Set up for high error rates, performance degradation

## 6. Development Phases

### 6.1 Phase 1: Core Data Integration (Week 1-2)
- Set up development environment
- Implement BLS data fetching module
- Create data processing pipeline
- Implement basic caching
- Unit tests for data components

### 6.2 Phase 2: Basic UI Development (Week 3-4)
- Create Streamlit application structure
- Implement filter components
- Basic data visualization (bar charts, tables)
- Integration testing

### 6.3 Phase 3: Advanced Visualizations (Week 5-6)
- Implement comprehensive chart types
- Add interactive features
- Geographic mapping capabilities
- Export functionality

### 6.4 Phase 4: Azure Deployment (Week 7)
- Azure App Service setup
- Deployment configuration
- Performance optimization
- Production testing

### 6.5 Phase 5: Testing and Optimization (Week 8)
- User acceptance testing
- Performance tuning
- Bug fixes and refinements
- Documentation completion

## 7. Dependencies and Requirements

### 7.1 Python Dependencies
```
streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.17.0
requests>=2.31.0
openpyxl>=3.1.0
xlrd>=2.0.1
numpy>=1.24.0
matplotlib>=3.7.0
seaborn>=0.12.0
folium>=0.14.0
streamlit-folium>=0.15.0
altair>=5.0.0
```

### 7.2 System Requirements
- **Python Version**: 3.10 or higher
- **Memory**: 2GB+ for development, 1.75GB+ for production
- **Storage**: 5GB+ for data caching
- **Network**: Reliable internet for BLS data access

### 7.3 External Dependencies
- **BLS OEWS Data API**: Public access required
- **Azure App Service**: B1 tier or higher
- **Git Repository**: For source code management

## 8. Data Governance and Compliance

### 8.1 Data Usage Policy
- **Source Attribution**: Proper citation of BLS data sources
- **Usage Terms**: Compliance with BLS data usage guidelines
- **Update Frequency**: Sync with official BLS release schedule

### 8.2 Privacy and Security
- **No Personal Data**: Application handles only aggregate statistical data
- **Data Transmission**: HTTPS encryption for all data transfers
- **Storage Security**: Secure cloud storage with access controls

### 8.3 Performance Standards
- **Load Time**: <5 seconds for initial data load
- **Response Time**: <2 seconds for filter interactions
- **Availability**: 99.5% uptime target
- **Concurrent Users**: Support for 10+ simultaneous users

## 9. Success Metrics

### 9.1 Technical Metrics
- **Application Performance**: Load times, response times
- **Data Accuracy**: Validation against source data
- **System Reliability**: Uptime, error rates
- **Cache Hit Ratio**: >80% for frequently accessed data

### 9.2 User Experience Metrics
- **Functionality Coverage**: All major OEWS data dimensions accessible
- **Visualization Quality**: Clear, accurate, interactive charts
- **Export Capability**: Multiple format support
- **Mobile Responsiveness**: Functional on tablet/mobile devices

### 9.3 Business Metrics
- **Data Currency**: Latest available OEWS data integrated
- **Feature Completeness**: All specified filters and visualizations implemented
- **Deployment Success**: Successful Azure App Service deployment
- **Documentation Quality**: Comprehensive user and technical documentation

## 10. Maintenance and Support

### 10.1 Regular Maintenance
- **Data Updates**: Quarterly checks for new BLS data releases
- **Dependency Updates**: Monthly security and feature updates
- **Performance Monitoring**: Weekly performance reviews
- **Backup Procedures**: Daily automated backups

### 10.2 Support Procedures
- **Issue Tracking**: GitHub Issues for bug reports and feature requests
- **Documentation**: User guides and technical documentation
- **Update Notifications**: Communication plan for major updates
- **Rollback Procedures**: Quick rollback capability for failed deployments

This specification provides a comprehensive blueprint for developing and deploying the OEWS Streamlit webapp on Azure, ensuring all technical, functional, and operational requirements are addressed.