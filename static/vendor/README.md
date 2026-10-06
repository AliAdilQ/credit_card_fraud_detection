# Vendored frontend libraries

Bootstrap **5.3.8** and Chart.js **4.5.1** are served locally so the demo works without a CDN connection. Both use the MIT license; their original license files accompany their distributions. Files are fetched from fixed npm package URLs by `python scripts/fetch_vendor.py`. There is no frontend build step. Review upstream changes before updating the versions.
