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

### 3.1 Database Management Module
#### 3.1.1 Database Initialization
- **Requirement**: Set up and populate database from existing Excel files
- **Input**: Excel files from data/ directory
- **Output**: Fully populated relational database
- **Database Engine**: SQLite for development, PostgreSQL for production

#### 3.1.2 Data Loading Pipeline
- **Requirement**: Bulk load OEWS data from Excel files into database
- **Functions**:
  - Excel parsing and validation
  - Dimension table population (areas, occupations, industries)
  - Fact table bulk insert with data integrity checks
  - Data quality validation and error reporting
- **Output**: Normalized relational database with indexed tables

#### 3.1.3 Database Query Layer
- **Requirement**: Efficient data retrieval through optimized queries
- **Features**:
  - Pre-built view definitions for common queries
  - Query optimization for filter combinations
  - Connection pooling and caching
- **Performance**: Sub-second response times for typical queries

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

### 4.0 Database-First Approach Benefits

#### 4.0.1 Performance Advantages
- **Sub-second Queries**: Direct database queries vs file parsing eliminate load times
- **Efficient Filtering**: SQL WHERE clauses vs pandas filtering on large datasets
- **Indexed Lookups**: Database indexes provide O(log n) vs O(n) search performance
- **Memory Efficiency**: Load only required data vs entire Excel files into memory

#### 4.0.2 Scalability Benefits
- **Concurrent Users**: Database handles multiple simultaneous queries efficiently
- **Data Growth**: Easy to add new years of data without performance degradation
- **Query Complexity**: Complex aggregations and joins handled by database engine
- **Caching**: Database query cache provides automatic performance optimization

#### 4.0.3 Development Benefits
- **Standard SQL**: Use familiar query language vs complex pandas operations
- **Data Integrity**: Foreign key constraints ensure data consistency
- **Backup/Recovery**: Standard database backup procedures
- **Version Control**: Schema migrations track database changes over time

### 4.1 Application Stack
- **Frontend Framework**: Streamlit
- **Backend Language**: Python 3.10+
- **Database**: SQLite (development), PostgreSQL (production)
- **Data Processing**: pandas, numpy
- **Visualization**: plotly, matplotlib, seaborn
- **Database ORM/Client**: SQLAlchemy, psycopg2
- **File Processing**: openpyxl (for initial data loading)

### 4.2 Application Structure
```
oews-streamlit-app/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── database_schema.sql    # Database schema definition
├── config/
│   ├── settings.py       # Configuration management
│   ├── database.py       # Database connection settings
│   └── constants.py      # SOC codes, NAICS mappings, etc.
├── src/
│   ├── database/
│   │   ├── connection.py # Database connection management
│   │   ├── loader.py     # Excel to database loading
│   │   ├── queries.py    # Pre-built query functions
│   │   └── models.py     # Data model definitions
│   ├── visualization/
│   │   ├── charts.py     # Chart generation
│   │   ├── maps.py       # Geographic visualizations
│   │   └── tables.py     # Data table components
│   └── utils/
│       ├── helpers.py    # Utility functions
│       └── validators.py # Data validation
├── data/
│   ├── *.xlsx           # Source Excel files
│   └── oews.db          # SQLite database (development)
├── migrations/
│   └── *.sql            # Database migration scripts
├── assets/
│   ├── images/          # Logo, icons
│   └── styles/          # Custom CSS
└── tests/
    ├── test_database.py # Database operation tests
    ├── test_loading.py  # Data loading tests
    └── test_viz.py      # Visualization tests
```

### 4.3 Data Flow Architecture
1. **User Input** → Filter selections via Streamlit widgets
2. **Query Builder** → Construct SQL queries based on filters
3. **Database Query** → Execute optimized queries against database
4. **Data Retrieval** → Return structured pandas DataFrame
5. **Data Processing** → Apply any additional transformations
6. **Visualization** → Generate charts based on processed data
7. **User Output** → Display charts and allow exports

#### Database Setup Flow (One-time)
1. **Schema Creation** → Create tables and indexes
2. **Dimension Loading** → Populate lookup tables (areas, occupations, industries)
3. **Fact Loading** → Bulk insert employment/wage data from Excel files
4. **Index Optimization** → Create performance indexes
5. **View Creation** → Set up materialized views for common queries

### 4.4 Database Performance Strategy
- **Level 1**: Database connection pooling and prepared statements
- **Level 2**: Strategic database indexes on common filter columns
- **Level 3**: Materialized views for complex aggregations
- **Level 4**: Streamlit @st.cache_data for expensive computations
- **Query Optimization**: Pre-built optimized queries for common use cases
- **Data Updates**: Incremental loading for new annual data releases

## 5. Azure Deployment Specification

### 5.1 Azure Services
- **Primary Service**: Azure App Service (Linux)
- **Database Service**: Azure Database for PostgreSQL (Flexible Server)
- **Pricing Tier**: B1 Standard or higher (WebSocket support required)
- **Database Tier**: Burstable B1ms (1 vCore, 2 GiB RAM) minimum
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

# Database Configuration
DATABASE_URL=postgresql://username:password@hostname:5432/oews_db
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
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

### 6.1 Phase 1: Database Setup and Data Loading (Week 1-2)
- Set up development environment with database tools
- Create database schema and tables
- Implement Excel to database loading pipeline
- Load all historical OEWS data (2011-2024) into database
- Create database indexes and views for optimal performance
- Unit tests for database operations

### 6.2 Phase 2: Database Query Layer and Basic UI (Week 3-4)
- Implement database connection and query management
- Create query builder for dynamic filtering
- Develop Streamlit application structure
- Implement basic filter components with database integration
- Basic data visualization (bar charts, tables)
- Integration testing with real database queries

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

### 6.5 Phase 5: Testing, Optimization, and Deployment (Week 8)
- Database query performance optimization
- User acceptance testing
- Production database setup and migration
- Bug fixes and refinements
- Documentation completion including database schema docs

## 7. Dependencies and Requirements

### 7.1 Python Dependencies
```
# Core application
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0

# Database
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0  # PostgreSQL adapter
alembic>=1.12.0         # Database migrations

# Data processing
openpyxl>=3.1.0        # Excel file reading

# Visualization
plotly>=5.17.0
matplotlib>=3.7.0
seaborn>=0.12.0
folium>=0.14.0
streamlit-folium>=0.15.0
altair>=5.0.0

# Development and testing
pytest>=7.0.0
pytest-cov>=4.0.0
black>=23.0.0           # Code formatting
flake8>=6.0.0           # Linting
```

### 7.2 System Requirements
- **Python Version**: 3.10 or higher
- **Memory**: 2GB+ for development, 1.75GB+ for production
- **Storage**: 5GB+ for data caching
- **Network**: Reliable internet for BLS data access

### 7.3 External Dependencies
- **Database Server**: SQLite (included) or PostgreSQL 14+
- **Azure App Service**: B1 tier or higher
- **Azure Database for PostgreSQL**: For production deployment
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