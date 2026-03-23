# CDN Resources (Local Copies)

This folder contains local copies of third-party libraries to avoid external CDN dependencies.

## Files

- **tailwindcss.js** - Tailwind CSS framework (from https://cdn.tailwindcss.com)
  - ⚠️ Production warning has been removed for cleaner console output
  - Size: ~397 KB
- **chart.js** - Chart.js charting library (from https://cdn.jsdelivr.net/npm/chart.js)
  - Size: ~204 KB

## Purpose

These files are used by the WeClaw Admin dashboard to provide:
- Tailwind CSS for styling
- Chart.js for data visualization

## Maintenance

To update these files, re-download from their respective sources:
```powershell
# Download Tailwind CSS
Invoke-WebRequest -Uri "https://cdn.tailwindcss.com" -OutFile "tailwindcss.js"

# Download Chart.js
Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/chart.js" -OutFile "chart.js"
```
