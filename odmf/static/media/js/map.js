// toggle the appeareance of the element with id. Uses jQuery slide
let markers = []
let selected_marker = null
let map = null
function toggle(id) {
	$('#'+id).slideToggle('fast');
}
function seterror(text) {
	$('#map-error').html(text).removeClass('d-none')
}

// Shows the actual map coordinates in div #coordinates. Event handler
function map_mousemove(loc) {
	$('#coordinates').html(loc.lat().toFixed(6) + '°N, ' + loc.lng().toFixed(6) + '°E');
}
// Handles double click on the map
// If checkbox #createsite is checked, a new site is created, else zoom in
function map_dblclick(loc) {
	if ($('#createsite').prop('checked')) {
		var url = odmf_ref('/site/new');
		url += '?lat=' + loc.lat();
		url += '&lon=' + loc.lng();
		url += '#edit';
		window.location.href = url;
	} else {
		map.setCenter(loc);
		map.setZoom(map.getZoom() + 1);
	}
}
// Clears the markers from the map
function clearmarker() {
	if (markers) {
		$.each(markers, function (index, marker) {
			marker.setMap(null);
		});
		markers.length = 0;
	}
}

function selectsite(id) {
	localStorage.setItem('map-selected-site', id)
	if (id) {
		$('#infotext').load(odmf_ref('/map/sitedescription/') + id,
			function(response, status, xhr) {
				if (status == "error") {
					var msg = "Sorry but there was an error: ";
					$("#infotext").html(msg + xhr.status + " " + xhr.statusText);
				}
			});
		$('#map_canvas').data('site', id);
		$.each(markers,function(index,item) {
			if (item.get('id') == id) {
				if (selected_marker) {
					selected_marker.set('position', new google.maps.LatLng(item.position.lat(), item.position.lng()))
				} else {
					selected_marker = new google.maps.Marker({
						position: new google.maps.LatLng(item.position.lat(), item.position.lng()),
						map: map,
						icon: {
							url: odmf_ref('/media/mapicons/selection.png'),
							size: new google.maps.Size(37,37),
							origin: new google.maps.Point(0,0),
							anchor: new google.maps.Point(6,30)
						}

					})
				}

			}
		});

	} else {
		selected_marker = null
		$('#infotext').html('<h3>No site selected</h3>')
	}

}
function setmarkers(data) {
	clearmarker();
	map.data.forEach(feature => {
		map.data.remove(feature)
	})
	let selectedsite = $('#map_canvas').data('site')

	$.each(data.features, (index,feature) => {
		if (feature.geometry.type != 'Point')
			map.data.addGeoJson(feature)

		let item = feature.properties
		if (!item.icon) {
			icon='unknown.png';
		} else {
			icon = item.icon;
		}
		let marker = new google.maps.Marker(
			{
				position: new google.maps.LatLng(item.lat,item.lon),
				title:'#' + item.id + '(' + item.name + ')',
				map:map,
				icon:{
					url: odmf_ref('/media/mapicons/') + icon,
					size: new google.maps.Size(24, 24),
					origin: new google.maps.Point(0,0),
					anchor: new google.maps.Point(0, 24)
				},
				zIndex: 100,
			}
		);
		marker.set('id',item.id);
		if (item.id == selectedsite) {
			if (selected_marker) {
				selected_marker.position = new google.maps.LatLng(item.lat, item.lon)
			} else {
				selected_marker = new google.maps.Marker({
					position: new google.maps.LatLng(item.lat, item.lon),
					map: map,
					icon: {
						url: odmf_ref('/media/mapicons/selection.png'),
						size: new google.maps.Size(37,37),
						origin: new google.maps.Point(0,0),
						anchor: new google.maps.Point(6,30)
					}

				})
			}

		}
		google.maps.event.addListener(marker,'click',function() {
			selectsite(item.id);
		});
		google.maps.event.addListener(marker,'dblclick',function() {
				map.setCenter(marker.getPosition());
				map.setZoom(map.getZoom()+2);
		})
		markers.push(marker)
	});

}

function zoomToMarkers() {
	var latlngbounds = new google.maps.LatLngBounds();
	$.each(markers,function(index,item){
		latlngbounds.extend(item.getPosition());
	});
	map.setCenter(latlngbounds.getCenter());
	map.fitBounds(latlngbounds);
}

function saveOptions() {
	localStorage.setItem('map', JSON.stringify(
		{
			center: map.getCenter(),
			zoom: map.getZoom(),
			mapTypeId: map.getMapTypeId()
		}
	))

}
function initMap(site) {


	mapOptions = JSON.parse(localStorage.getItem('map'))
	map = new google.maps.Map(document.getElementById("map_canvas"), mapOptions);
	google.maps.event.addListener(map,'dblclick',function(event) {
		map_dblclick(event.latLng);
	});
	google.maps.event.addListener(map,'mousemove',function(event) {
		map_mousemove(event.latLng);
	});
	google.maps.event.addListener(map, 'bounds_changed', saveOptions)
	map.data.setStyle(feature => {
		return {
			strokeWeight: feature.getProperty('strokeWidth') || 2,
			strokeColor: feature.getProperty('strokeColor') || '#FFF',
			strokeOpacity: feature.getProperty('strokeOpacity') || 0.8,
			fillColor: feature.getProperty('fillColor') || '#FFF',
			fillOpacity: feature.getProperty('fillOpacity') || 0.3,
			zIndex: 10
		}
	})
	markers = [];
	function applyFilter() {
		filter = new SiteFilter().populate_form()
		filter.apply((data)=>{
			setmarkers(data)
			$('#site-count').html(data.features.length)
		}, odmf_ref('/site/geojson'))
	}
	$('.filter').on('change', applyFilter)
	$('#zoom-home').on('click', zoomToMarkers)
	clearFilter()
	applyFilter()
	if (!mapOptions ||!mapOptions.center) {
		zoomToMarkers()
	}
	selectsite(localStorage.getItem('map-selected-site'))

}
