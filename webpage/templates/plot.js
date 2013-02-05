/**
 * @author philkraf
 */

    function toggle(id) {
    	$('#'+id).slideToggle('fast');
    }
    function seterror(data) {
				if (data) {
					$('#error').html(data);
				} else {
					window.location.reload();
				}    	
    }
		function renderplot(targetdiv, creationtime) {
			var div = $('#'+targetdiv);
			$('#properties').slideUp();
			div.html('<img src="/plot/image.png?create=creationtime" alt="Loading image..." />')
			div.slideDown();
		}
		function gettime(startOrEnd) {		
			var res = $('#'+ startOrEnd + 'date').val();
			if (res>'') {
				res += ' ' + $('#'+ startOrEnd + 'time').val();
			} else {
				res = '';
			}
			return res; 
		}
		function changeprops() {
			$.post('changeplot', {
				start:gettime('start'),
				end:gettime('end'),
				size:$('#sizeselect').val()
			}, seterror);
			

		}
		function addsubplot() {
			$.post('addsubplot', {}, seterror);
		}
		function removesubplot(id) {
			$.post('removesubplot', {subplotid:id}, function(data) {
				if (data) {
					$('#error').html(data);
				} else {
					window.location.reload();
				}
			});
		}
		function getstyle() {
			return $('#colorpicker').val() + $('#linepicker').val() + $('#markerpicker').val();
		}
		function addline() {
			var sp = $('#subplotselect').val();
			var vt = $('#vtselect').val();
			var site = $('#siteselect').val();
			var inst = $('#instrumentselect').val();
			$.post('addline', {
				subplot:sp,
				valuetypeid:vt,
				siteid:site,
				instrumentid:inst,
				style:getstyle()
			},seterror);
		}
		function removeline(subplot,line) {
			$.post('removeline',{subplot:subplot,line:line},seterror)
		}
		
		function timerange(step)
		{
		    if (step == null) {step=60;}
		    var foo = [];
		    for (var i = 0; i <= 60*24; i+=step) {
		    	var m = i % 60;
		    	var h = (i-m)/60;
		    	if (h<10) { h='0' + h;} else {h='' + h;}
		    	if (m<10) { m='0' + m;} else {m='' + m;}
		    	foo.push(h+':'+m);
		    }	    		
		    return foo;
		}

		function popSelect() {
			var vt = $('#vtselect').val();
			var site = $('#siteselect').val();
			var instrument = $('#instrumentselect').val();
			var date = ''; //$('#dateselect').val()
			$.getJSON('/dataset/attrjson',
								{ attribute:'valuetype',
								  site:site,
								  date:date,
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
								{ attribute:'source',
									valuetype:vt,
									site:site,
								  date:date
								},
								function(data) {
									var html='<option class="firstoption" value="">Please select...</option>';
									$.each(data,function(index,item){
										if (item)
											html+='<option value="'+item.id+'">'+item.name+'</option>';
									});
									$('#instrumentselect').html(html).val(instrument);
								}
			);
			$.getJSON('/dataset/attrjson',
									{ attribute:'site',
										valuetype:vt,
									  date:date
									},
									function(data){
										var html='<option value="">Please select...</option>';
										$.each(data,function(index,item){
											html+='<option value="'+item.id+'">#'+item.id+' ('+item.name+')</option>';
										});
										$('#siteselect').html(html).val(site);
									}
			);
			

		}
		function clearFilter() {
			$('.filter').val('');
			$('#dateselect').val('');
			$('#allsites').val(true);
			popSelect();
		}

	    
	   
