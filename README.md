# Barycentre

Find the best place to meet your friends by computing the geographic midpoint of everyone's addresses.

## How it works

1. Add friends with their name and address
2. The app geocodes each address and places a colored marker on the map
3. When 2+ friends are added, a red star shows the **barycentre** (average of all coordinates)
4. Copy the share link to send pre-filled addresses to others

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Create a new app pointing to `app.py`

No API keys or secrets needed — geocoding uses OpenStreetMap's free Nominatim service.

## Tech stack

- [Streamlit](https://streamlit.io/) — UI
- [Folium](https://python-visualization.github.io/folium/) + [streamlit-folium](https://github.com/randyzwitch/streamlit-folium) — interactive map
- [GeoPy](https://geopy.readthedocs.io/) + Nominatim — address geocoding
