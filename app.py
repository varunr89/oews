"""
OEWS Streamlit Web Application
Main entry point for the Occupational Employment and Wage Statistics visualization app.
"""

import streamlit as st
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database.connection import DatabaseManager
from config.settings import Settings

def main():
    """Main application entry point."""

    # Page configuration
    st.set_page_config(
        page_title="OEWS Data Explorer",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Application title
    st.title("📊 OEWS Data Explorer")
    st.markdown("### Occupational Employment and Wage Statistics Analysis")

    # Initialize database connection
    try:
        db_manager = DatabaseManager()
        if not db_manager.is_connected():
            st.error("❌ Database connection failed. Please check your configuration.")
            return

        st.success("✅ Database connection established")

    except Exception as e:
        st.error(f"❌ Application initialization failed: {str(e)}")
        return

    # Sidebar for filters
    with st.sidebar:
        st.header("Filters")
        st.markdown("Configure your data selection:")

        # Year filter
        year_options = [2024, 2023, 2022, 2021, 2020, 2019]
        selected_year = st.selectbox("Select Year", year_options, index=0)

        # Area type filter
        area_types = {
            "All Areas": None,
            "National": 1,
            "States": 2,
            "Metropolitan Areas": 4,
            "Nonmetropolitan Areas": 6
        }
        selected_area_type = st.selectbox("Area Type", list(area_types.keys()))

        # Occupation group filter
        occ_groups = {
            "All Occupations": None,
            "Major Groups": "major",
            "Minor Groups": "minor",
            "Broad Groups": "broad",
            "Detailed Occupations": "detailed"
        }
        selected_occ_group = st.selectbox("Occupation Level", list(occ_groups.keys()))

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Data Overview")
        st.info("🚧 Visualization components coming soon! Database setup completed.")

        # Display current filter selections
        st.markdown("**Current Selections:**")
        st.write(f"- Year: {selected_year}")
        st.write(f"- Area Type: {selected_area_type}")
        st.write(f"- Occupation Level: {selected_occ_group}")

    with col2:
        st.subheader("Quick Stats")
        st.metric("Database Status", "Connected", "✅")
        st.metric("Available Years", "2011-2024", "13 years")
        st.metric("Data Sources", "Excel Files", "~750MB")

    # Footer
    st.markdown("---")
    st.markdown("**Data Source:** U.S. Bureau of Labor Statistics (BLS) - Occupational Employment and Wage Statistics")

if __name__ == "__main__":
    main()