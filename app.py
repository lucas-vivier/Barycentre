import json
import urllib.parse

import folium
import streamlit as st
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Barycentre",
    page_icon="\U0001f4cd",
    layout="wide",
)

PARIS_CENTER = [48.8566, 2.3522]
DEFAULT_ZOOM = 11


@st.cache_data(show_spinner=False)
def geocode_address(address: str) -> tuple[float, float] | None:
    try:
        geolocator = Nominatim(user_agent="barycentre-streamlit-app")
        location = geolocator.geocode(address, timeout=10)
        if location:
            return (location.latitude, location.longitude)
        return None
    except (GeocoderTimedOut, GeocoderUnavailable, Exception):
        return None


# ---------------------------------------------------------------------------
# Session state initialisation + URL parameter loading
# ---------------------------------------------------------------------------

def _load_from_url_params() -> list[dict] | None:
    params = st.query_params
    friends_json = params.get("friends", None)
    if friends_json:
        try:
            friends = json.loads(friends_json)
            if isinstance(friends, list):
                return [
                    {"name": f.get("name", ""), "address": f.get("address", "")}
                    for f in friends
                    if isinstance(f, dict) and f.get("address")
                ]
        except (json.JSONDecodeError, TypeError):
            pass
    return None


if "friends" not in st.session_state:
    url_friends = _load_from_url_params()
    st.session_state["friends"] = url_friends if url_friends else []

# ---------------------------------------------------------------------------
# Sidebar – input form + friends list
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("Barycentre")
    st.markdown("Find the best place to meet your friends!")
    st.divider()

    st.subheader("Add a friend")
    with st.form("add_friend_form", clear_on_submit=True):
        name = st.text_input("Name", placeholder="Alice")
        address = st.text_input("Address", placeholder="10 Rue de Rivoli, Paris")
        submitted = st.form_submit_button("Add", use_container_width=True)

        if submitted and address.strip():
            st.session_state["friends"].append(
                {"name": name.strip() or "Friend", "address": address.strip()}
            )
            st.rerun()

    if st.session_state["friends"]:
        st.divider()
        st.subheader("Friends")
        for i, friend in enumerate(st.session_state["friends"]):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{friend['name']}**  \n{friend['address']}")
            with col2:
                if st.button("\u2715", key=f"remove_{i}", help="Remove"):
                    st.session_state["friends"].pop(i)
                    st.rerun()

        # Share link
        st.divider()
        friends_encoded = urllib.parse.quote(json.dumps(st.session_state["friends"]))
        st.query_params["friends"] = json.dumps(st.session_state["friends"])
        share_url = f"?friends={friends_encoded}"
        st.text_input("Share link", value=share_url, disabled=True)
    else:
        if "friends" in st.query_params:
            del st.query_params["friends"]
        st.info("Add friends to find your barycentre!")

# ---------------------------------------------------------------------------
# Geocoding + barycentre computation
# ---------------------------------------------------------------------------

geocoded = []
errors = []

for friend in st.session_state["friends"]:
    coords = geocode_address(friend["address"])
    if coords:
        geocoded.append({**friend, "lat": coords[0], "lon": coords[1]})
    else:
        errors.append(friend)

barycentre = None
if len(geocoded) >= 2:
    avg_lat = sum(f["lat"] for f in geocoded) / len(geocoded)
    avg_lon = sum(f["lon"] for f in geocoded) / len(geocoded)
    barycentre = (avg_lat, avg_lon)

# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

m = folium.Map(location=PARIS_CENTER, zoom_start=DEFAULT_ZOOM)

if geocoded:
    for f in geocoded:
        folium.Marker(
            location=[f["lat"], f["lon"]],
            popup=f"<b>{f['name']}</b><br>{f['address']}",
            tooltip=f["name"],
            icon=folium.Icon(color="blue", icon="user", prefix="fa"),
        ).add_to(m)

    if barycentre:
        folium.Marker(
            location=[barycentre[0], barycentre[1]],
            popup="<b>Barycentre</b><br>The meeting point!",
            tooltip="Barycentre",
            icon=folium.Icon(color="red", icon="star", prefix="fa"),
        ).add_to(m)

    lats = [f["lat"] for f in geocoded]
    lons = [f["lon"] for f in geocoded]
    if barycentre:
        lats.append(barycentre[0])
        lons.append(barycentre[1])
    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=[50, 50])

st_folium(m, use_container_width=True, height=600, returned_objects=[])

for err in errors:
    st.warning(
        f"Could not find address for **{err['name']}**: '{err['address']}'. "
        "Please check the spelling and try again."
    )
