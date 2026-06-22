# ETL-001: ChileCompra Data Processing

## Overview
This document outlines the process for extracting, transforming, and loading data from ChileCompra, a public procurement database in Chile. The goal is to standardize the data format for further analysis and integration with other datasets.

## Extract
### Source
The data source is the official ChileCompra API or dataset files.
- **API Endpoint:** [Provide actual endpoint if available]
- **Dataset Files:** CSV/JSON files (name, location)

### Extraction Methods
- Automated scripts using `requests` and `pandas`
- Scheduled jobs for recurring data imports

## Transform
### Data Cleaning
- Remove duplicates
- Standardize formatting of dates, names, and codes
- Handle missing or invalid data

### Data Mapping
- Map source fields to standardized schema fields
- Apply business logic for data enrichment (e.g., categorization)

### Validation
- Validate data types
- Cross-check with existing datasets
- Audit records for anomalies

## Load
### Target Database
The transformed data is loaded into our PostgreSQL database.
- **Schema:** `chilecompra` schema
- **Tables:**
  - `tenders`: Records of tenders/procurements
  - `bids`: Bid information
  - `suppliers`: Supplier details
  - `buyers`: Buyer (entity) information

### Load Strategy
- Incremental updates for continuous data flow
- Batch loading for historical data
- Error handling and logging for failed records

## Metadata
This process is part of the ETL pipeline for managing public procurement data.