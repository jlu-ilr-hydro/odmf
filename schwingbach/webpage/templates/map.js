    function toggle(id) {
    	$('#'+id).slideToggle('fast');
    }
    function setpref(data) {
			$.ajaxSetup({ scriptCharset:"utf-8", 
                    contentType:"application/json; charset=utf-8" });
		  $.post('/preferences/update',$.toJSON(data),null,'json');    	
    }
		function savemappref() {
			var center = map.getCenter();
			var data = {item:'map',
				   			 	lat:center.lat(),
				   			 	lng:center.lng(),
				   			 	zoom:map.getZoom(),
				   			 	type:map.getMapTypeId()
				   			};
			setpref(data);
		}
		function map_mousemove(loc) {
			$('#coordinates').html(loc.lat().toFixed(6) + '°N, ' + loc.lng().toFixed(6) + '°E');
		}
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
        }
		function setmarkers(source,filter) {
			clearmarker();
			var selectionsymbol = new google.maps.MarkerImage('/media/mapicons/selection.png',
														new google.maps.Size(37,37),
														new google.maps.Point(0,0),
														new google.maps.Point(6,30));
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
	  			if (item.id == selectedmarker) {
	  				marker.setShadow(selectionsymbol);
	  			}
	  			(function(eventmarker,id){
		  			google.maps.event.addListener(marker,'click',function() {
						selectsite(item.id);
		  				$.each(markers,function(index,item) {
		  					item.setShadow(null);
		  				});
		  				eventmarker.setShadow(selectionsymbol);
							setpref({site:id});
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
			var vt = $('#vtselect').val()
			var user = $('#userselect').val()
			var date = $('#dateselect').val()
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
			if ($('#datasetsonly').prop('checked')) {
				setmarkers('/dataset/attrjson',
										{attribute:'site',
										 valuetype:vt,
										 user:user,
										 date:date,
									});											
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
		

    $(function() {
			$(".datepicker").datepicker({maxDate:"0", dateFormat: 'dd.mm.yy' });
 	    $.getJSON('/preferences',{},function(data){
		    map = createmap(data.map.lat,data.map.lng,data.map.zoom,data.map.type);
				selectedmarker = 0;
		    markers = [];
				$('.filter').val('');
				$('#dateselect').val('');
				$('#datasetsonly').prop('checked',false);
 	    	if (data.site) {
                selectsite(data.site);
    		}
	    	popSelect();
    	});
	    $(window).unload(savemappref);
	    // Get map preferences 
    });
