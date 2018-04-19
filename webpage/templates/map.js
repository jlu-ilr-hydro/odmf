    // toggle the appeareance of the element with id. Uses jQuery slide
    function toggle(id) {
    	$('#'+id).slideToggle('fast');
    }
    function setpref(data) {
			$.ajaxSetup({ scriptCharset:"utf-8", 
                    contentType:"application/json; charset=utf-8" });
		  $.post('/preferences/update',$.toJSON(data),null,'json');    	
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
				var url = '/site/new';
				url += '?lat=' + loc.lat();
				url += '&lon=' + loc.lng();
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
        $('#infotext').load('/map/sitedescription/' + id, 
            function(response, status, xhr) {
                if (status == "error") {
                    var msg = "Sorry but there was an error: ";
                    $("#infotext").html(msg + xhr.status + " " + xhr.statusText);
                }
        });
        selectedmarker = id;
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
    		if (item.get('id') == selectedmarker) {
    			marker = item;
	    		alert('marker found!' + JSON.stringify(marker));
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
			return new google.maps.MarkerImage('/media/mapicons/selection.png',
														new google.maps.Size(37,37),
														new google.maps.Point(0,0),
														new google.maps.Point(6,30));
		}    
		function setmarkers(source,filter) {
			clearmarker();
			var selectionsymbol = getSelectionSymbol(); 
	    $.getJSON(source,filter,function(data) {
	    	$.each(data,function(index,item) {
					if (!item.icon) {
						icon='unknown.png';
					} else {
						icon = item.icon;
					}
	    		var image = new google.maps.MarkerImage('/media/mapicons/' + icon,
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
	  			if (item.id == selectedmarker) {
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
			var vt = $('#vtselect').val();
			var user = $('#userselect').val();
			var date = $('#dateselect').val();
			var instrument = $('#instrumentselect').val();
			if (vt || user || date) {
					$('#datasetsonly').prop('checked',true);
			}
			$.getJSON('/dataset/attrjson',
								{ attribute:'valuetype',
								  user:user,
								  date:date
								},
								function(data){
									var html='<option class="firstoption" value="">Please select...</option>';
									$.each(data,function(index,item){
										html+='<option value="'+item.id+'">'+item.name+'</option>';
									});
									$('#vtselect').html(html).val(vt);
								}
			);
					
			$.getJSON('/dataset/attrjson',
								{ attribute:'measured_by',
									valuetype:vt,
								  date:date
								},
								function(data) {
									var html='<option class="firstoption" value="">Please select...</option>';
									$.each(data,function(index,item){
										html+='<option value="'+item.username+'">'+item.firstname+' '+item.surname+'</option>';
									});
									$('#userselect').html(html).val(user);
								}
			);
			$.getJSON('/site/getinstalledinstruments',{},function(data){
									var html='<option class="firstoption" value="">Please select...</option>';
									$.each(data,function(index,item){
										html+='<option value="'+item.id+'">'+item.name+'</option>';
									});
									$('#instrumentselect').html(html).val(instrument);
			});
			if ($('#datasetsonly').prop('checked')) {
				setmarkers('/dataset/attrjson',
										{attribute:'site',
										 valuetype:vt,
										 user:user,
										 date:date,
										 instrument:instrument,
									});											
			} else if (instrument){
				setmarkers('/site/with_instrument',{instrumentid:instrument});
			} else {
				setmarkers('/site/json',{});
			}
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
		function toggleInfo() {
			if ($('#openinfo>button').html() == '&lt;') {
				//alert('isOpen');
				$('#openinfo').css('left','0px');
				$('#infopane').fadeOut();
				$('#openinfo>button').html('&gt;');
				$('#map_canvas').removeClass('mapCanvasShort').addClass('mapCanvasWide');
			} else {
				//alert('isClosed, #openInfo>button.html()==' + $('#openinfo>button').html());
				$('#openinfo').css('left','20em');
				$('#infopane').fadeIn();
				$('#openinfo>button').html('&lt;');			
				$('#map_canvas').removeClass('mapCanvasWide').addClass('mapCanvasShort');
			}
		}
		

    function initMap(site) {
			map=null;

			$(".datepicker").datepicker({maxDate:"0", dateFormat: 'dd.mm.yy' });

			$.getJSON('/preferences', {}, function( data ) {
				if (site) {
					data.site = site.id;
					data.map.zoom = 20;
					data.map.lat = site.lat;
					data.map.lng = site.lon;
				}

		    map = createmap(data.map.lat,data.map.lng,data.map.zoom,data.map.type);

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

		$(window).unload(savemappref);
	    $('#openinfo>button').click(toggleInfo);
	    // Get map preferences 
    }
