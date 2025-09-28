-- OEWS Database Schema Design
-- Optimized for fast queries and efficient storage

-- Geographic Areas dimension table
CREATE TABLE geographic_areas (
    area_code VARCHAR(10) PRIMARY KEY,
    area_title VARCHAR(255) NOT NULL,
    area_type INTEGER NOT NULL, -- 1=US, 2=State, 3=Territory, 4=MSA, 6=Nonmetropolitan
    primary_state VARCHAR(2), -- State code or 'US' for national
    INDEX idx_area_type (area_type),
    INDEX idx_primary_state (primary_state)
);

-- Occupations dimension table
CREATE TABLE occupations (
    occ_code VARCHAR(10) PRIMARY KEY,
    occ_title VARCHAR(255) NOT NULL,
    o_group VARCHAR(20) NOT NULL, -- total, major, minor, broad, detailed
    INDEX idx_o_group (o_group)
);

-- Industries dimension table
CREATE TABLE industries (
    naics_code VARCHAR(10) PRIMARY KEY,
    naics_title VARCHAR(255) NOT NULL,
    i_group VARCHAR(20) NOT NULL, -- cross-industry, sector, 3-digit, 4-digit, etc.
    INDEX idx_i_group (i_group)
);

-- Ownership types lookup table
CREATE TABLE ownership_types (
    own_code INTEGER PRIMARY KEY,
    own_description VARCHAR(255) NOT NULL
);

-- Data vintages to track which files have been loaded
CREATE TABLE data_vintages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name VARCHAR(255) NOT NULL,
    survey_year INTEGER NOT NULL,
    survey_month VARCHAR(20) NOT NULL,
    load_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_records INTEGER,
    UNIQUE(file_name)
);

-- Main fact table for employment and wage data
CREATE TABLE employment_wage_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Foreign keys to dimension tables
    area_code VARCHAR(10) NOT NULL,
    occ_code VARCHAR(10) NOT NULL,
    naics_code VARCHAR(10) NOT NULL,
    own_code INTEGER NOT NULL,

    -- Survey metadata
    survey_year INTEGER NOT NULL,
    survey_month VARCHAR(20) NOT NULL DEFAULT 'May',

    -- Employment metrics
    total_employment INTEGER,
    employment_prse DECIMAL(5,2), -- Percent relative standard error
    jobs_per_1000 DECIMAL(10,4),
    location_quotient DECIMAL(10,4),
    pct_total DECIMAL(5,2),
    pct_reporting DECIMAL(5,2),

    -- Wage metrics (hourly)
    mean_hourly_wage DECIMAL(10,2),
    hourly_10th_pct DECIMAL(10,2),
    hourly_25th_pct DECIMAL(10,2),
    hourly_median DECIMAL(10,2),
    hourly_75th_pct DECIMAL(10,2),
    hourly_90th_pct DECIMAL(10,2),

    -- Wage metrics (annual)
    mean_annual_wage INTEGER,
    annual_10th_pct INTEGER,
    annual_25th_pct INTEGER,
    annual_median INTEGER,
    annual_75th_pct INTEGER,
    annual_90th_pct INTEGER,

    -- Wage metadata
    wage_prse DECIMAL(5,2), -- Percent relative standard error for wages
    annual_only BOOLEAN DEFAULT FALSE,
    hourly_only BOOLEAN DEFAULT FALSE,

    -- Indexes for fast querying
    FOREIGN KEY (area_code) REFERENCES geographic_areas(area_code),
    FOREIGN KEY (occ_code) REFERENCES occupations(occ_code),
    FOREIGN KEY (naics_code) REFERENCES industries(naics_code),
    FOREIGN KEY (own_code) REFERENCES ownership_types(own_code),

    INDEX idx_area_year (area_code, survey_year),
    INDEX idx_occ_year (occ_code, survey_year),
    INDEX idx_naics_year (naics_code, survey_year),
    INDEX idx_employment (total_employment),
    INDEX idx_mean_wage (mean_annual_wage),
    INDEX idx_year (survey_year),
    INDEX idx_area_occ (area_code, occ_code),

    -- Composite index for common query patterns
    INDEX idx_area_occ_year (area_code, occ_code, survey_year)
);

-- Insert ownership type lookup data
INSERT INTO ownership_types (own_code, own_description) VALUES
(1, 'Federal Government'),
(2, 'State Government'),
(3, 'Local Government'),
(5, 'Private'),
(35, 'Private and Local Government'),
(57, 'Private, Local Government Gambling Establishments, and Local Government Casino Hotels'),
(58, 'Private plus State and Local Government Hospitals'),
(59, 'Private and Postal Service'),
(123, 'Federal, State, and Local Government'),
(235, 'Private, State, and Local Government'),
(1235, 'Federal, State, and Local Government and Private Sector');

-- Views for common queries

-- View for latest data only
CREATE VIEW latest_employment_data AS
SELECT
    ewd.*,
    ga.area_title,
    ga.area_type,
    ga.primary_state,
    occ.occ_title,
    occ.o_group,
    ind.naics_title,
    ind.i_group,
    own.own_description
FROM employment_wage_data ewd
JOIN geographic_areas ga ON ewd.area_code = ga.area_code
JOIN occupations occ ON ewd.occ_code = occ.occ_code
JOIN industries ind ON ewd.naics_code = ind.naics_code
JOIN ownership_types own ON ewd.own_code = own.own_code
WHERE ewd.survey_year = (SELECT MAX(survey_year) FROM employment_wage_data);

-- View for state-level data only
CREATE VIEW state_employment_data AS
SELECT *
FROM latest_employment_data
WHERE area_type = 2; -- State level

-- View for metropolitan area data only
CREATE VIEW metro_employment_data AS
SELECT *
FROM latest_employment_data
WHERE area_type = 4; -- Metropolitan Statistical Area

-- View for summary statistics by occupation
CREATE VIEW occupation_summary AS
SELECT
    occ_code,
    occ_title,
    o_group,
    survey_year,
    COUNT(*) as area_count,
    SUM(total_employment) as total_national_employment,
    AVG(mean_annual_wage) as avg_annual_wage,
    MIN(mean_annual_wage) as min_annual_wage,
    MAX(mean_annual_wage) as max_annual_wage,
    STDDEV(mean_annual_wage) as wage_std_dev
FROM latest_employment_data
WHERE total_employment IS NOT NULL
    AND mean_annual_wage IS NOT NULL
    AND area_type IN (2, 4) -- States and Metro areas only
GROUP BY occ_code, occ_title, o_group, survey_year;