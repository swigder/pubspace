let metadata = {}

window.onload = function (e) {
    $.ajax({
        url: `data/metadata.json`,
        async: false,
        dataType: 'json',
        success: data => {
            metadata = data;
            window.dispatchEvent(new CustomEvent("filters-data", {
                detail: metadata.filters,
            }));
        }
    })
}

let details = {}

function loadDetails() {
    $.ajax({
        url: `data/pops.json`,
        async: false,
        dataType: 'json',
        success: data => {
            details = data;
        }
    })
}

loadDetails()

// TODO: Check that retina display tiles do not cause problems on non-retina devices (`@2x` below).
mapboxgl.accessToken = 'pk.eyJ1Ijoic3dpZ2RlciIsImEiOiJja29hbnI2bmQwMm0zMm91aHhlNHlhOHF2In0.FaLm4CYTTue7x4-NWm8p5g';
let map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/golmschenk/ckoss0cw40zbg17pen2nl0zv3',
    center: [-73.98, 40.75],
    zoom: 12,
    minZoom: 2,
    maxZoom: 18,
});

map.addControl(
    new MapboxGeocoder({
        accessToken: mapboxgl.accessToken,
        mapboxgl: mapboxgl,
        flyTo: {
            duration: 0,
        },
        placeholder: 'Jump to location',
        countries: 'US',
        marker: false,
    })
);
map.addControl(
    new mapboxgl.ScaleControl({
        unit: 'imperial',
    })
);
map.addControl(
    new mapboxgl.GeolocateControl({
        positionOptions: {
            enableHighAccuracy: true
        },
        trackUserLocation: false,
        showUserHeading: false
    })
);
map.dragRotate.disable();
map.touchZoomRotate.disableRotation();

map.on('load', getNewData);

let fullData = new Map()
let clickedLocation = null

function onMarkerClick(e) {
    clickedLocation = e.lngLat
    let id = e.features[0].properties.id
    let properties = new Map(Object.entries(details[id]))
    dispatchDetails(properties)
}

let currentHover = null

function onMarkerHover(e) {
    map.getCanvas().style.cursor = 'pointer';

    let newHover = {
        id: e.features[0].id,
        source: e.features[0].layer.source,
    }

    if (!currentHover || currentHover.id !== newHover.id || currentHover.source !== newHover.source) {
        if (currentHover) {
            map.setFeatureState(currentHover, {hover: false});
        }
        currentHover = newHover;
        map.setFeatureState(newHover, {hover: true});
    }
}

function onMarkerUnhover(e) {
    map.getCanvas().style.cursor = '';

    if (currentHover) {
        map.setFeatureState(currentHover, {hover: false});
    }
    currentHover = null;
}

function dispatchDetails(properties) {
    window.dispatchEvent(new CustomEvent("details-data", {
        detail: Object.fromEntries(properties),
    }));
    $("#details-tab").click()
}

function getNewData() {
    map.addSource('data/pops.geojson', {
        'type': 'geojson',
        'data': 'data/pops.geojson',
        'cluster': false,
        'generateId': true,
    });
    map.addLayer({
        id: 'pops',
        type: 'circle',
        source: 'data/pops.geojson',
        'paint': {
            'circle-opacity': .8,
            'circle-color': '#3bb2d0',
            'circle-radius': {
                stops: [[4, 1], [10, 3], [13, 6], [16, 8]]
            },
            'circle-stroke-width': [
                'case',
                ['boolean', ['feature-state', 'hover'], false,],
                2,
                0,
            ],
            'circle-stroke-color': '#3bb2d0'
        },
    });
    map.on('click', 'pops', onMarkerClick);
    map.on('mousemove', 'pops', onMarkerHover);
    map.on('mouseleave', 'pops', onMarkerUnhover);
}

const filters = {
    'amenity': new Set()
}

$(document).on("click", ".filter-button", function () {
    let button = $(this)
    button.toggleClass('is-selected');
    let filter = button.attr("data-filter-type")
    let value = button.attr("data-filter-value")
    if (button.hasClass('is-selected')) {
        filters[filter].add(value);
    } else {
        filters[filter].delete(value);
    }
    map.setFilter('pops', ['all'].concat([...filters[filter]].map(f => ['in', f, ['string', ['get', 'amenities']]])));
});
