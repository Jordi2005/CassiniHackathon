# CassiniHackathon - Water Quality Analysis System

**Gespeta Team** - Cassini Hackathon Project

A Python-based system for processing Sentinel-2 satellite imagery to analyze water quality indices and detect algal blooms across coastal regions.

## Overview

This project processes multispectral satellite data from Copernicus Sentinel-2 to compute advanced water quality metrics. It automatically calculates multiple water quality indices and identifies areas of concern based on configurable thresholds, supporting environmental monitoring for regions like Murcia, Tarragona and Galicia.

## Key Features

- **Multispectral Processing**: Loads and processes Sentinel-2 bands (B02, B03, B04, B05, B08) in GeoTIFF format
- **Advanced Water Quality Indices**:
  - NDWI (Normalized Difference Water Index) - water detection
  - NDVI (Normalized Difference Vegetation Index) - vegetation presence
  - NDTI (Normalized Difference Turbidity Index) - water turbidity
  - NDCI (Normalized Difference Chlorophyll Index) - chlorophyll concentration
  - CHLA (Chlorophyll-a) - polynomial-based concentration modeling
  - SABI (Surface Algal Bloom Index) - algal bloom detection
  - EPI (Eutrophication Potential Index) - water eutrophication risk assessment
- **Alert Detection**: Automatic identification of pixels with high pollution/bloom indicators
- **CSV Export**: Summarized results with statistical information

## Technology Stack

- **Python 3.x**
- **rioxarray** - Raster data I/O with xarray integration
- **xarray** - Multi-dimensional array operations
- **rasterio** - Geospatial raster data handling
- **pandas** - Data processing and CSV export
- **numpy** - Numerical computations

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd CassiniHackathon
```

2. Install dependencies:
```bash
pip install rioxarray xarray rasterio pandas numpy
```

## Usage

### Prepare Data

1. Download Sentinel-2 raw bands from [EO Browser](https://browser.sentinelhub.com/) or similar service
2. Extract the following bands for your region:
   - B02 (Blue) - `*_B02_(Raw).tiff`
   - B03 (Green) - `*_B03_(Raw).tiff`
   - B04 (Red) - `*_B04_(Raw).tiff`
   - B05 (Vegetation Edge) - `*_B05_(Raw).tiff`
   - B08 (NIR) - `*_B08_(Raw).tiff`
3. Place bands in the appropriate raw input directory:
   - `raw_bands_in_Tarragona/` for Tarragona region
   - `raw_bands_in_Galicia/` for Galicia region

### Run Processing

```bash
python main.py
```

The script will:
- Load all available bands from the configured raw directory
- Calculate all water quality indices
- Apply detection masks for water and alert conditions
- Export results to CSV

### Configuration

Edit `main.py` to modify:
- **RAW_BANDS_DIR**: Input directory for raw satellite bands
- **OUTPUT_DIR**: Output directory for processed images and results
- **CONST_A**: Parameter for EPI formula (default: 1.0)
- **Detection Thresholds**:
  - Water detection: `ndwi > 0.0`
  - Alert threshold: `epi > 0.4`

## Project Structure

```
CassiniHackathon/
├── main.py                          # Main processing script
├── README.md                        # This file
├── raw_bands_in/                    # Raw Sentinel-2 bands input (general)
├── raw_bands_in_Tarragona/          # Raw bands for Tarragona region
├── raw_bands_in_Galicia/            # Raw bands for Galicia region
├── processed_img_Tarragona/         # Processed outputs for Tarragona
│   └── results_resum.csv           # Summary results
├── processed_img_Galicia/           # Processed outputs for Galicia
├── processed_images/                # General processed outputs
│   └── results_resum.csv
└── processed_images_Tarragona/      # Alternative output directory
    └── results_resum.csv
```

## Output Format

### CSV Results (results_resum.csv)

Contains filtered pixels meeting alert criteria with these columns:
- **ndwi**: Normalized Difference Water Index (water presence)
- **ndvi**: Normalized Difference Vegetation Index
- **ndti**: Normalized Difference Turbidity Index
- **ndci**: Normalized Difference Chlorophyll Index
- **chla**: Chlorophyll-a concentration (mg/m³)
- **sabi**: Surface Algal Bloom Index (raw)
- **sabinorm**: Normalized SABI (0-1 scale)
- **epi**: Eutrophication Potential Index

### Geospatial Data

Processed xarray Datasets preserve geospatial coordinates and can be saved as GeoTIFF or NetCDF for further analysis.

## Water Quality Index Descriptions

### NDWI (Normalized Difference Water Index)
Distinguishes water bodies from land. Values > 0.0 indicate water presence.

### NDVI (Normalized Difference Vegetation Index)
Measures vegetation health and density. Range: -1 to 1.

### NDTI (Normalized Difference Turbidity Index)
Estimates water turbidity/suspended sediment. Higher values indicate more turbid water.

### NDCI (Normalized Difference Chlorophyll Index)
Sensitive indicator of chlorophyll concentration in relatively clear water.

### CHLA (Chlorophyll-a Concentration)
Advanced polynomial model: `CHLA = 826.57×NDCI³ - 176.43×NDCI² + 19×NDCI + 4.071`
Units: mg/m³

### SABI (Surface Algal Bloom Index)
Combines NIR/Red and Green/Blue ratios to detect algal blooms.
Formula: `SABI = (B08-B04)/(B08+B04) - (B03-B02)/(B03+B02)`

### EPI (Eutrophication Potential Index)
Composite index measuring eutrophication risk considering chlorophyll concentration, algal bloom presence, and water turbidity.

## Notes

- **Band B02 requirement**: The B02 (Blue) band is essential for SABI calculation and must be downloaded separately if not included in your dataset
- **Resolution adjustment**: B05 is automatically reprojected to match B04 resolution (10m) to handle 20m B05 downloads
- **Data type**: All bands are converted to float32 to prevent division-by-zero errors in index calculations
- **Processing time**: Varies based on image resolution and system performance
- **Regional configuration**: Currently set to process Tarragona data; modify paths in main.py for other regions

## Issues & Troubleshooting

### "No s'han trobat totes les bandes" (Bands not found)
- Verify all 5 required bands (B02, B03, B04, B05, B08) are in the raw input directory
- Check band filename format matches expected pattern: `*_B0X_(Raw).tiff`
- Ensure B02 is downloaded from EO Browser

### No alert pixels detected
- Adjust thresholds in main.py:
  - Lower the `epi > 0.4` threshold to capture borderline cases
  - Modify CONST_A parameter to tune EPI sensitivity
- Verify input data quality and band values are in expected range

## Contributing

Gespeta Team contributions welcome. For significant changes, please open an issue first to discuss proposed modifications.

## License

[Specify your license here - e.g., MIT, GPL, CC-BY-4.0]

## References

- Sentinel-2 MSI Technical Documentation: [ESA](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi)
- Water Quality Indices: Standard remote sensing indices for inland and coastal water monitoring
- Copernicus: [EO Browser](https://browser.sentinelhub.com/)
