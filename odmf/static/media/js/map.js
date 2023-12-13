// toggle the appeareance of the element with id. Uses jQuery slide
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
	$.each(markers,function(index,marker) {
		marker.setMap(null);
	});
	markers.length = 0;
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
			item.setShadow(selectionSymbol);
		} else {
			item.setShadow(null);
		}
	});
	setpref({site:id});
	$('#title').html('Map <a href="/site/'+ id + '">site #' + id + '</a>');

}
function zoomToSelected() {
	var marker=null;
	alert(markers[0]);
	$.each(markers,function(index,item){
		if (item.get('id') == $('#map_canvas').data('site')) {
			marker = item;
			alert('marker found!' + JSON.stringify(marker, null, 4));
			return false;
		}
	});
	if (marker) {
		map.setCenter(marker.getPosition());
		map.setZoom(20);
	} else {
		alert('no marker!');
	}
}
function getSelectionSymbol() {
	return new google.maps.MarkerImage(odmf_ref('/media/mapicons/selection.png'),
		new google.maps.Size(37,37),
		new google.maps.Point(0,0),
		new google.maps.Point(6,30));
}
function setmarkers(source, filter) {
	clearmarker();
	map.data.forEach(feature => {
		map.data.remove(feature)
	})
	let selectionsymbol = getSelectionSymbol();
	let selectedsite = $('#map_canvas').data('site')
	$.getJSON(source, filter, function(data) {
		$.each(data.features, function(index,feature) {
			map.data.addGeoJson(feature)

			let item = feature.properties
			if (!item.icon) {
				icon='unknown.png';
			} else {
				icon = item.icon;
			}
			var image = new google.maps.MarkerImage(odmf_ref('/media/mapicons/') + icon,
				new google.maps.Size(24, 24),
				new google.maps.Point(0,0),
				new google.maps.Point(0, 24));
			var marker = new google.maps.Marker(
				{
					position: new google.maps.LatLng(item.lat,item.lon),
					title:'#' + item.id + '(' + item.name + ')',
					map:map,
					icon:image,
				}
			);
			marker.set('id',item.id);
			if (item.id == selectedsite) {
				marker.setShadow(selectionsymbol);
			}
			(function(eventmarker,id){
				google.maps.event.addListener(marker,'click',function() {
					selectsite(item.id);
				});
			}(marker,item.id));
			(function(eventmarker,id){
				google.maps.event.addListener(marker,'dblclick',function() {
					map.setCenter(marker.getPosition());
					map.setZoom(map.getZoom()+2);
				})
			})(marker,item.id);
			markers.push(marker)
		});
	});
}

function popSelect() {
	let filter = {
		valuetype: $('#vtselect').val(),
		user: $('#userselect').val(),
		max_data_age: $('#max_data_age').val(),
		instrument: $('#instrumentselect').val(),
		date: $('#dateselect').val(),
		fulltext: $('#fulltext').val()
	}


	let options = (data, get_value, get_name) => {
		let html = '<option class="firstoption" value="">Please select...</option>\n';
		$.each(data, (index, item) => {
			html += '<option value="' + get_value(item) + '">' + get_name(item) + '</option>\n';
		});
		return html

	}
	let fmt = {
		id: x=>x ? x.id : '',
		name: x=>x ? x.name : '',
		site: x => x ? '#' + x.id + ' (' + x.name + ')' : '#???',
		user: x=>x.firstname + ' ' + x.surname,
		self: x => x
	}

	$('#datasetsonly').prop('checked',(filter.valuetype || filter.user || filter.date || filter.max_data_age));

	$.getJSON(
		odmf_ref('/dataset/attributes'),
		{
			valuetype: filter.valuetype,
			user:filter.user,
			date:filter.date,
		},
		data => {
			$('#vtselect').html(options(data.valuetype, fmt.id, fmt.name)).val(filter.valuetype);
			$('#userselect').html(options(data.measured_by, x=>x.username, fmt.user)).val(filter.user)
		}
	);
	$.get(odmf_ref('/site/getinstalledinstruments'),{},function(data){
		data.unshift({id: 'any', name: 'any'})
		data.unshift({id: 'installed', name: 'any installed instrument'})
		let html = options(data, fmt.id, fmt.name)
		$('#instrumentselect').html(html).val(filter.instrument);
	}).fail(jqhxr => seterror(jqhxr.responseText));

	setmarkers(odmf_ref('/site/geojson'),filter);
}
function clearFilter() {
	$('.filter').val('');
	$('#dateselect').val('');

	$('#datasetsonly').prop('checked',false);

	popSelect();
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
			}
		})
		markers = [];
		$('.filter').val('');
		$('#dateselect').val('');
		$('#datasetsonly').prop('checked',false);

		if (data.site) {
			selectsite(data.site);
		}

		popSelect();

	}).fail(function( jqxhr, textStatus, error){

		$('#map_canvas').html('JSONerror:' + textStatus + ',' + error);
	});

	$(window).on("beforeunload", savemappref);
	// Get map preferences
}
