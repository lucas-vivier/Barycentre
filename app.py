import json
import urllib.request

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
MARKER_COLORS = [
    "#4285F4", "#EA4335", "#FBBC05", "#34A853",
    "#FF6D01", "#46BDC6", "#7B1FA2", "#C2185B",
]


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


@st.cache_data(show_spinner=False)
def reverse_geocode(lat: float, lon: float) -> str | None:
    try:
        geolocator = Nominatim(user_agent="barycentre-streamlit-app")
        location = geolocator.reverse((lat, lon), timeout=10)
        if location:
            return location.address
        return None
    except (GeocoderTimedOut, GeocoderUnavailable, Exception):
        return None


@st.cache_data(show_spinner=False)
def get_route_info(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float] | None:
    """Get driving distance (km) and duration (min) via OSRM."""
    try:
        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{lon1},{lat1};{lon2},{lat2}?overview=false"
        )
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            distance_km = route["distance"] / 1000
            duration_min = route["duration"] / 60
            return (round(distance_km, 1), round(duration_min))
        return None
    except Exception:
        return None


def _make_marker_icon(letter: str, color: str) -> folium.DivIcon:
    html = (
        f'<div style="background:{color}; width:30px; height:30px; '
        f'border-radius:50%; display:flex; align-items:center; '
        f'justify-content:center; color:white; font-weight:bold; '
        f'font-size:14px; border:2px solid white; '
        f'box-shadow:0 1px 3px rgba(0,0,0,0.3);">'
        f'{letter}</div>'
    )
    return folium.DivIcon(html=html, icon_size=(30, 30), icon_anchor=(15, 15))


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
# Sidebar – input + friends list
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
                color = MARKER_COLORS[i % len(MARKER_COLORS)]
                st.markdown(
                    f'<span style="color:{color}; font-size:18px;">\u25cf</span> '
                    f"**{friend['name']}**  \n{friend['address']}",
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("\u2715", key=f"remove_{i}", help="Remove"):
                    st.session_state["friends"].pop(i)
                    st.rerun()

        # Clear all
        if st.button("Clear all", use_container_width=True):
            st.session_state["friends"] = []
            st.rerun()

        # Keep URL in sync for sharing
        st.query_params["friends"] = json.dumps(st.session_state["friends"])
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
barycentre_address = None
if len(geocoded) >= 2:
    avg_lat = sum(f["lat"] for f in geocoded) / len(geocoded)
    avg_lon = sum(f["lon"] for f in geocoded) / len(geocoded)
    barycentre = (avg_lat, avg_lon)
    barycentre_address = reverse_geocode(avg_lat, avg_lon)

# ---------------------------------------------------------------------------
# Title + map
# ---------------------------------------------------------------------------

st.markdown(
    '<h1 style="text-align:center; margin-bottom:0;">Barycentre</h1>'
    '<p style="text-align:center; color:gray; margin-top:0;">'
    'Pour jouer \u00e0 la coinche avec les potes</p>',
    unsafe_allow_html=True,
)

if barycentre_address:
    st.markdown(
        f'<p style="text-align:center;">\u2b50 Point de rendez-vous : <b>{barycentre_address}</b></p>',
        unsafe_allow_html=True,
    )

m = folium.Map(location=PARIS_CENTER, zoom_start=DEFAULT_ZOOM)

if geocoded:
    for idx, f in enumerate(geocoded):
        color = MARKER_COLORS[idx % len(MARKER_COLORS)]
        letter = f["name"][0].upper() if f["name"] else "?"
        folium.Marker(
            location=[f["lat"], f["lon"]],
            popup=f"<b>{f['name']}</b><br>{f['address']}",
            tooltip=f["name"],
            icon=_make_marker_icon(letter, color),
        ).add_to(m)

        # Draw line to barycentre
        if barycentre:
            folium.PolyLine(
                locations=[[f["lat"], f["lon"]], [barycentre[0], barycentre[1]]],
                color=color,
                weight=2,
                opacity=0.5,
                dash_array="8",
            ).add_to(m)

    if barycentre:
        popup_text = "<b>Barycentre</b><br>The meeting point!"
        if barycentre_address:
            popup_text = f"<b>Barycentre</b><br>{barycentre_address}"
        folium.Marker(
            location=[barycentre[0], barycentre[1]],
            popup=popup_text,
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

# ---------------------------------------------------------------------------
# Travel info + errors
# ---------------------------------------------------------------------------

if barycentre and geocoded:
    rows = []
    for idx, f in enumerate(geocoded):
        route = get_route_info(f["lat"], f["lon"], barycentre[0], barycentre[1])
        if route:
            rows.append({"Name": f["name"], "Distance": f"{route[0]} km", "Travel time": f"{route[1]:.0f} min"})
        else:
            rows.append({"Name": f["name"], "Distance": "N/A", "Travel time": "N/A"})
    st.markdown("#### Travel to the meeting point")
    st.dataframe(rows, use_container_width=True, hide_index=True)

for err in errors:
    st.warning(
        f"Could not find address for **{err['name']}**: '{err['address']}'. "
        "Please check the spelling and try again."
    )
