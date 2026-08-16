# DRID — Drug Research Intelligence Dashboard

DRID is a web-based pharmaceutical research intelligence dashboard designed to organize, connect, and explore drug, molecular target, indication, clinical trial, and pharmaceutical development data.

The project is being developed as a long-term portfolio project combining **pharmaceutical science, biomedical data, and software development**.

## Current Status

**Version:** 0.2  
**Status:** In active development

DRID has progressed beyond the initial prototype and now integrates multiple publicly available pharmaceutical and biomedical data sources.

## Tech Stack

- Python
- Flask
- SQLite
- HTML
- CSS
- Jinja2
- REST APIs

## Current Features

### Pharmaceutical Database

- Drug database containing 1,000+ compounds
- Drug search functionality
- Drug detail/profile pages
- Development phase and regulatory status
- Drug-target relationships
- Drug-indication relationships

### Molecular Intelligence

- PubChem integration
- PubChem Compound IDs
- Molecular formulas
- Molecular weights
- Canonical SMILES
- Molecular data provenance

### Clinical Research

- ClinicalTrials.gov integration
- Clinical trial records associated with compounds
- Trial status
- Clinical development phase
- Study type
- Study conditions
- Study sponsors
- Trial counts and active-trial statistics

### Dashboard Analytics

- Total compounds
- Approved drugs
- Research targets
- Indications
- Clinical trial statistics
- PubChem enrichment statistics
- Development-phase distribution
- Paginated compound database
- Search across compounds, targets, and indications

### Data Integration

DRID currently works with publicly available data from sources including:

- U.S. Food & Drug Administration / openFDA
- PubChem
- ClinicalTrials.gov
- ChEMBL

The database currently contains approximately:

- **1,140 drugs**
- **199 targets**
- **694 drug-target relationships**
- **1,541 indications**
- **13,049 drug-indication relationships**
- **14,169 clinical trials**

These numbers will change as the database continues to be enriched.

## Project Structure

```text
drid/
├── app.py
├── database.py
├── config.py
├── README.md
├── .gitignore
├── drid.db
├── templates/
│   ├── index.html
│   ├── drug.html
    ├── therapetic_areas.html
    └── trials.html
└── static/
    └── style.css