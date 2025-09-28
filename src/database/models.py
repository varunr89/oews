"""
SQLAlchemy ORM models for OEWS database tables.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Index, Text, DECIMAL
)
from sqlalchemy.orm import relationship
from config.database import Base

class GeographicArea(Base):
    """Geographic areas dimension table."""
    __tablename__ = "geographic_areas"

    area_code = Column(String(10), primary_key=True)
    area_title = Column(String(255), nullable=False)
    area_type = Column(Integer, nullable=False)  # 1=US, 2=State, 3=Territory, 4=MSA, 6=Nonmetropolitan
    primary_state = Column(String(2))  # State code or 'US' for national

    # Indexes
    __table_args__ = (
        Index('idx_area_type', 'area_type'),
        Index('idx_primary_state', 'primary_state'),
    )

    # Relationships
    employment_data = relationship("EmploymentWageData", back_populates="geographic_area")

    def __repr__(self):
        return f"<GeographicArea(area_code='{self.area_code}', title='{self.area_title}')>"

class Occupation(Base):
    """Occupations dimension table."""
    __tablename__ = "occupations"

    occ_code = Column(String(10), primary_key=True)
    occ_title = Column(String(255), nullable=False)
    o_group = Column(String(20), nullable=False)  # total, major, minor, broad, detailed

    # Indexes
    __table_args__ = (
        Index('idx_o_group', 'o_group'),
    )

    # Relationships
    employment_data = relationship("EmploymentWageData", back_populates="occupation")

    def __repr__(self):
        return f"<Occupation(occ_code='{self.occ_code}', title='{self.occ_title}')>"

class Industry(Base):
    """Industries dimension table."""
    __tablename__ = "industries"

    naics_code = Column(String(10), primary_key=True)
    naics_title = Column(String(255), nullable=False)
    i_group = Column(String(20), nullable=False)  # cross-industry, sector, 3-digit, 4-digit, etc.

    # Indexes
    __table_args__ = (
        Index('idx_i_group', 'i_group'),
    )

    # Relationships
    employment_data = relationship("EmploymentWageData", back_populates="industry")

    def __repr__(self):
        return f"<Industry(naics_code='{self.naics_code}', title='{self.naics_title}')>"

class OwnershipType(Base):
    """Ownership types lookup table."""
    __tablename__ = "ownership_types"

    own_code = Column(Integer, primary_key=True)
    own_description = Column(String(255), nullable=False)

    # Relationships
    employment_data = relationship("EmploymentWageData", back_populates="ownership_type")

    def __repr__(self):
        return f"<OwnershipType(own_code={self.own_code}, description='{self.own_description}')>"

class DataVintage(Base):
    """Data vintages to track which files have been loaded."""
    __tablename__ = "data_vintages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False, unique=True)
    survey_year = Column(Integer, nullable=False)
    survey_month = Column(String(20), nullable=False)
    load_date = Column(DateTime, default=datetime.utcnow)
    total_records = Column(Integer)

    def __repr__(self):
        return f"<DataVintage(file_name='{self.file_name}', year={self.survey_year})>"

class EmploymentWageData(Base):
    """Main fact table for employment and wage data."""
    __tablename__ = "employment_wage_data"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys to dimension tables
    area_code = Column(String(10), ForeignKey("geographic_areas.area_code"), nullable=False)
    occ_code = Column(String(10), ForeignKey("occupations.occ_code"), nullable=False)
    naics_code = Column(String(10), ForeignKey("industries.naics_code"), nullable=False)
    own_code = Column(Integer, ForeignKey("ownership_types.own_code"), nullable=False)

    # Survey metadata
    survey_year = Column(Integer, nullable=False)
    survey_month = Column(String(20), nullable=False, default="May")

    # Employment metrics
    total_employment = Column(Integer)
    employment_prse = Column(DECIMAL(5, 2))  # Percent relative standard error
    jobs_per_1000 = Column(DECIMAL(10, 4))
    location_quotient = Column(DECIMAL(10, 4))
    pct_total = Column(DECIMAL(5, 2))
    pct_reporting = Column(DECIMAL(5, 2))

    # Wage metrics (hourly)
    mean_hourly_wage = Column(DECIMAL(10, 2))
    hourly_10th_pct = Column(DECIMAL(10, 2))
    hourly_25th_pct = Column(DECIMAL(10, 2))
    hourly_median = Column(DECIMAL(10, 2))
    hourly_75th_pct = Column(DECIMAL(10, 2))
    hourly_90th_pct = Column(DECIMAL(10, 2))

    # Wage metrics (annual)
    mean_annual_wage = Column(Integer)
    annual_10th_pct = Column(Integer)
    annual_25th_pct = Column(Integer)
    annual_median = Column(Integer)
    annual_75th_pct = Column(Integer)
    annual_90th_pct = Column(Integer)

    # Wage metadata
    wage_prse = Column(DECIMAL(5, 2))  # Percent relative standard error for wages
    annual_only = Column(Boolean, default=False)
    hourly_only = Column(Boolean, default=False)

    # Relationships
    geographic_area = relationship("GeographicArea", back_populates="employment_data")
    occupation = relationship("Occupation", back_populates="employment_data")
    industry = relationship("Industry", back_populates="employment_data")
    ownership_type = relationship("OwnershipType", back_populates="employment_data")

    # Indexes for fast querying
    __table_args__ = (
        Index('idx_area_year', 'area_code', 'survey_year'),
        Index('idx_occ_year', 'occ_code', 'survey_year'),
        Index('idx_naics_year', 'naics_code', 'survey_year'),
        Index('idx_employment', 'total_employment'),
        Index('idx_mean_wage', 'mean_annual_wage'),
        Index('idx_year', 'survey_year'),
        Index('idx_area_occ', 'area_code', 'occ_code'),
        Index('idx_area_occ_year', 'area_code', 'occ_code', 'survey_year'),
    )

    def __repr__(self):
        return (f"<EmploymentWageData(area='{self.area_code}', "
                f"occ='{self.occ_code}', year={self.survey_year})>")

    @property
    def employment_density(self) -> float:
        """Calculate employment density (jobs per 1000) if available."""
        return float(self.jobs_per_1000) if self.jobs_per_1000 else 0.0

    @property
    def wage_range(self) -> tuple:
        """Get the wage range (10th to 90th percentile) for this record."""
        if self.annual_10th_pct and self.annual_90th_pct:
            return (int(self.annual_10th_pct), int(self.annual_90th_pct))
        return (0, 0)

    def is_wage_data_available(self) -> bool:
        """Check if wage data is available for this record."""
        return (self.mean_annual_wage is not None or
                self.mean_hourly_wage is not None)

    def is_employment_data_available(self) -> bool:
        """Check if employment data is available for this record."""
        return self.total_employment is not None