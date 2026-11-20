# Sentinel Tree Monitor

A small, self-contained tree-monitoring project built on **10-band Sentinel-1/2 imagery** from the Google Earth Engine Sentinel API.

It uses exactly two datasets:

| Data | Where | Used for |
|---|---|---|
| 50 human-labelled areas (Bangladesh, Feb 2025) | `data/labelled/` | training the 10-band land-cover U-Net |
| 300 hand-counted squares (Reyad's Gazipur count) | `data/gazipur/` | calibrating tree counts (small / big / total, cover %) |

## Run

```
pip install -r requirements.txt
python app.py            (or double-click run.bat)
```
Open http://127.0.0.1:5060

| Page | What it does |
|---|---|
| **Collect Data** `/historical` | Draw an area. You get a 10-band GeoTIFF for Feb 2025 plus an Esri high-resolution screenshot of the same area. |
| **Manual Labeling** `/labeling` | Draw class polygons on the screenshot. You get masks aligned with the GeoTIFF and a dataset ZIP. |
| **AI Monitor** `/monitor` | Analyse a collected area, a Gazipur square, a labelled area or an uploaded `.tif`. You get a land-cover map, tree cover % and an estimated tree count. |

New collections need Earth Engine. Put your project ID in `.env` as `EARTH_ENGINE_PROJECT_ID=...` and run `earthengine authenticate` once. The monitor works without it. Collected areas are saved in `collected/`.

## The 10 bands

`B4, B3, B2` (Sentinel-2 RGB), `NDVI, EVI, NBR` (vegetation and burn indices), `VV, VH, VV/VH, VV−VH` (Sentinel-1 radar). The data is a February median composite at 10 m. No-data pixels are `-inf`.

## Train / retrain

```
python ai/train_segmentation.py     # 50 labelled areas -> models/segmentation_10band.pt
python ai/train_counter.py          # 300 Gazipur squares -> models/tree_counter.json
python ai/predict.py some_area.tif --save-png out.png
```

**How it works**

1. A small U-Net (about 1.9M parameters) classifies every 10 m pixel into 10 classes: water, tree, grass/crop, bare soil, sand, building, road, shrub, shadow and other. Bands are z-scored with global training-set statistics.
2. For each Gazipur square, the predicted tree, shrub and grass fractions plus per-band mean and standard deviation become features. A ridge regression maps those features to trees per hectare, the big-tree share and tree cover %. The count for any area is trees/ha × area, split into big and small trees by the predicted share.

## Current accuracy (honest numbers)

**Land cover**, measured on 10 held-out labelled areas the model never trained on:

- Pixel accuracy: 73.9%
- mIoU: 0.40
- IoU by class: tree 0.69, water 0.82, building 0.81, grass/crop 0.52, sand 0.38
- Road, shrub, shadow and bare soil are close to 0, because there are too few labelled pixels of them.

**Tree counting**, measured with 5-fold cross-validation on the 300 Gazipur squares:

| | R² | Mean abs. error | Baseline error (always guess the average) |
|---|---|---|---|
| Total trees per square | 0.72 | ±99 trees | ±238 |
| Big trees per square | 0.67 | ±101 trees | ±236 |
| Small trees per square | 0.38 | ±35 trees | ±50 |
| Tree cover % | 0.94 | ±5.4 % | ±25.8 % |

Counts are calibrated on 100 m squares. Applying them to much larger areas assumes a similar tree density per hectare. A tree count from 10 m pixels is a statistical estimate, not one detection per tree.

## Layout

```
app.py                 Flask app (collect + label + monitor)
services/              Earth Engine 10-band collection, screenshot, labeling
ai/core.py             bands, normalisation, U-Net, inference, counting
ai/train_*.py          the two trainers
models/                trained model + accuracy reports
data/labelled/         50 labelled areas (see data/labelled_selection.json)
data/gazipur/          gazipur_counts.csv + 300 squares (10-band .tif + screenshot)
```

**How the 50 areas were chosen:** 57 complete labelled folders were available. One was removed as a byte-identical duplicate (Jhenaidah), and the 50 with the most labelled pixels were kept. The 6 smallest were dropped; `data/labelled_selection.json` lists them.
