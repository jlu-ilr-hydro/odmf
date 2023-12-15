// toggle the appeareance of the element with id. Uses jQuery slide
let markers = []
let selected_marker = null
function toggle(id) {
	$('#'+id).slideToggle('fast');
}
function seterror(text) {
	$('#error').html(text).removeClass('d-none')
}
function setpref(data) {
	$.ajaxSetup({ scriptCharset:"utf-8",
		contentType:"application/json; charset=utf-8" });
	$.post(odmf_ref('/preferences/update'),JSON.stringify(data, null, 4),null,'json');
}
// Saves the actual map preferences to the session / file
function savemappref() {
	if (map) {
		var center = map.getCenter();
		var data = {item:'map',
			lat:center.lat(),
			lng:center.lng(),
			zoom:map.getZoom(),
			type:map.getMapTypeId()
		};
		setpref(data);
	}
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
	$('#infotext').load(odmf_ref('/map/sitedescription/') + id,
		function(response, status, xhr) {
			if (status == "error") {
				var msg = "Sorry but there was an error: ";
				$("#infotext").html(msg + xhr.status + " " + xhr.statusText);
			}
		});
	$('#map_canvas').data('site', id);
	var selectionSymbol = getSelectionSymbol();
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
	setpref({site:id});
	$('#title').html('Map <a href="/site/'+ id + '">site #' + id + '</a>');

}
function getSelectionSymbol() {
	return new google.maps.MarkerImage(odmf_ref('/media/mapicons/selection.png'),
		new google.maps.Size(37,37),
		new google.maps.Point(0,0),
		new google.maps.Point(6,30));
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
function createmap(lat,lng,zoom,type) {
	var latlng = new google.maps.LatLng(lat, lng);
	var mapOptions = {
		zoom: zoom,
		center: latlng,
		mapTypeId: type
	};

	var map=new google.maps.Map(document.getElementById("map_canvas"), mapOptions);
	google.maps.event.addListener(map,'dblclick',function(event) {
		map_dblclick(event.latLng);
	});
	google.maps.event.addListener(map,'mousemove',function(event) {
		map_mousemove(event.latLng);
	});
	return map

}


function initMap(site) {
	map=null;

	$.getJSON(odmf_ref('/preferences'), {}, function( data ) {
		if (site) {
			data.site = site.id;
			data.map.zoom = 20;
			data.map.lat = site.lat;
			data.map.lng = site.lon;
		}

		map = createmap(data.map.lat,data.map.lng,data.map.zoom,data.map.type);
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
		if (data.site) {
			selectsite(data.site);
		}
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

	}).fail(function( jqxhr, textStatus, error){

		$('#map_canvas').html('JSONerror:' + textStatus + ',' + error);
	});

	$(window).on("beforeunload", savemappref);
	// Get map preferences
}
