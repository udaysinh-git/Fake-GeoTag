// Initialize map
const map = L.map('map').setView([20, 0], 2);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap'
}).addTo(map);
let marker;

map.on('click', function(e) {
    const {lat, lng} = e.latlng;
    document.querySelector('input[name="latitude"]').value = lat;
    document.querySelector('input[name="longitude"]').value = lng;
    if (marker) marker.setLatLng(e.latlng);
    else marker = L.marker(e.latlng).addTo(map);
});

document.getElementById('getLocation').onclick = function() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(pos) {
            const lat = pos.coords.latitude;
            const lng = pos.coords.longitude;
            document.querySelector('input[name="latitude"]').value = lat;
            document.querySelector('input[name="longitude"]').value = lng;
            map.setView([lat, lng], 13);
            if (marker) marker.setLatLng([lat, lng]);
            else marker = L.marker([lat, lng]).addTo(map);
        });
    }
};

// Add html2canvas script dynamically if not present
if (!window.html2canvas) {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
    document.head.appendChild(script);
}

// Helper to wait for all map tiles to load
function waitForTilesLoaded(mapDiv) {
    return new Promise(resolve => {
        const tiles = mapDiv.querySelectorAll('img.leaflet-tile');
        let loaded = 0;
        if (tiles.length === 0) return resolve();
        tiles.forEach(tile => {
            if (tile.complete && tile.naturalWidth !== 0) loaded++;
            else tile.addEventListener('load', () => {
                loaded++;
                if (loaded === tiles.length) resolve();
            });
        });
        if (loaded === tiles.length) resolve();
    });
}

document.getElementById('uploadForm').onsubmit = async function(e) {
    e.preventDefault();
    const form = e.target;
    const data = new FormData(form);
    document.getElementById('result').innerHTML = 'Processing...';
    // Wait for html2canvas to load if not already
    if (!window.html2canvas) {
        await new Promise(resolve => {
            const check = () => window.html2canvas ? resolve() : setTimeout(check, 100);
            check();
        });
    }
    // Screenshot the map (wait for tiles to load)
    const mapDiv = document.getElementById('map');
    await waitForTilesLoaded(mapDiv);
    // Optionally hide controls for a clean screenshot
    const controls = mapDiv.querySelectorAll('.leaflet-control-container');
    controls.forEach(ctrl => ctrl.style.visibility = 'hidden');
    const canvas = await window.html2canvas(mapDiv, {backgroundColor: null, useCORS: true});
    controls.forEach(ctrl => ctrl.style.visibility = '');
    // Convert canvas to blob and append to form data
    await new Promise(resolve => {
        canvas.toBlob(blob => {
            data.append('map_image', blob, 'map.png');
            resolve();
        }, 'image/png');
    });
    // Now send the form data as before
    const resp = await fetch('/api/fake-metadata', {
        method: 'POST',
        body: data
    });
    if (resp.ok) {
        const blob = await resp.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.get('file').name;
        a.textContent = 'Download Modified Image';
        document.getElementById('result').innerHTML = '';
        document.getElementById('result').appendChild(a);
    } else {
        const err = await resp.json();
        document.getElementById('result').textContent = 'Error: ' + (err.error || 'Unknown error');
    }
};
