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
    function killplot() {
				$('#plot').slideUp().html('Loading image...');

    }
		function renderplot(targetdiv, creationtime) {
			$('#plot').html('Loading image...');
			var div = $('#'+targetdiv);
			$('#properties').slideUp();
			div.html('<img src="/plot/image.png?create=' + creationtime + '" alt="Loading image..." />')
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
				width:$('#plotwidth').val(),
				height:$('#plotheight').val(),				
				rows:$('#plotrows').val(),
				columns:$('#plotcolumns').val(),
				aggregate:$('#plotaggregate').val(),
			}, function(data){
				if (data) seterror(data);
				else $('.error').html('');
			});
			killplot();
		}
		function addsubplot() {
			$.post('addsubplot', {}, seterror);
			killplot();
		}
		function removesubplot(id) {
			$.post('removesubplot', {subplotid:id}, seterror);
			killplot();
		}
		function changeylimit(id) {
			var text = prompt('Enter the y axis limit as min,max, eg. 0.5,1.5.').split(',');
			$.post('changeylim',{subplotid:id,ymin:text[0],ymax:text[1]},seterror);
			killplot();			
		}
		function changelogsite(id) {
			var logsite = $('#logsiteselect_' + id).val();
			$.post('changelogsite',{subplotid:id,logsite:logsite},seterror);
			killplot();
		}
		function exportall_csv() {
			var href = '/plot/exportall.csv?tolerance=' + $('#tolerance_skipper').val();
			//alert(href);
			window.location = href;
		}
		function flotplot() {
			$('#properties').slideUp();
			$.getJSON(
				'/plot/export.json',
				{subplot:0,line:0})
				.done(
					function(data) {
						$.plot('#flotcanvas', [{label:'data',data:data} ],
							{
								xaxis:{
									mode:'time',
								},
						});
				})
				.fail(
					function( jqxhr, textStatus, error ) {
						var err = textStatus + ", " + error;
						$('#error').html(err);
				});

		}
		function RegTime() {
			var href = '/plot/RegularTimeseries.csv?tolerance='+$('#Interpolation_Limit').val() + '&interpolation=' + $('#reg_interpolation').val();
			//alert(href);
			window.location = href;
		}
		function addline(sp) {
			var vt = $('#vtselect_'+sp).val();
			var site = $('#siteselect_'+sp).val();
			var inst = $('#instrumentselect_'+sp).val();
			var level = $('#levelselect_'+sp).val();
			var aggfunc = $('#aggpicker_'+sp).val();
			$.post('addline', {
				subplot:sp,
				valuetypeid:vt,
				siteid:site,
				instrumentid:inst,
				level:level,
				color:$('#colorpicker_'+sp).val(),
				linestyle:$('#linepicker_'+sp).val(),
				marker:$('#markerpicker_'+sp).val(),
				aggfunc:aggfunc,
			},seterror);
			killplot();
		}
		function removeline(subplot,line) {
			$.post('removeline',{subplot:subplot,line:line},seterror);
			killplot();
		}
		function editline(subplot,line) {
			$.post('removeline',{subplot:subplot, line:line, savelineprops:true}, seterror);
		}
		function copyline(subplot,line) {
			$.post('copyline',{subplot:subplot,line:line},seterror);
		}
		function reloadline(subplot,line) {
			$.post('reloadline',{subplot:subplot,line:line},seterror);
			killplot();
		} 
		function showlinedatasets(subplot,line) {
			var content = $('#datasetlist_'+subplot+'_'+line).html();
			$('#datasetlist_'+subplot+'_'+line).slideUp('fast').html('');
			if (content=='') {
				$.getJSON(
					'/plot/linedatasets.json',
					{ subplot: subplot,
						line:line
					},
					function(data){
						var html='';
						$.each(data,function(index,item){
							html+='<li><a href="/dataset/'+item.id + '">' + item.label + '</a></li>';
						});
						$('#datasetlist_'+subplot+'_'+line).html(html)
						$('#datasetlist_'+subplot+'_'+line).slideDown('fast');
					}
				);				
			} 

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

		function popSelect(subplotpos, newlineprops) {

			if ($('#vtselect_'+ subplotpos).length) {

				var vt = $('#vtselect_' + subplotpos).val();
				var site = $('#siteselect_' + subplotpos).val();
				var instrument = $('#instrumentselect_' + subplotpos).val();
				var level = $('#levelselect_' + subplotpos).val();
				var date = ''; //$('#dateselect').val()
				if (newlineprops && !vt) vt=newlineprops.valuetype;
				if (newlineprops && !instrument) instrument=newlineprops.instrument;
				if (newlineprops && !site) site=newlineprops.site;
				if (newlineprops && !level) level=newlineprops.level;

				$.getJSON('/dataset/attrjson',
									{ attribute:'valuetype',
									  site:site,
									  date:date,
									  onlyaccess:true,
									},
									function(data){
										var html='<option class="firstoption" value="">Please select...</option>';
										$.each(data,function(index,item){
											html+='<option value="'+item.id+'">'+item.name+'</option>';
										});
										$('#vtselect_'+subplotpos).html(html).val(vt);
									}
				);
						
				$.getJSON('/dataset/attrjson',
									{ attribute:'source',
										valuetype:vt,
										site:site,
									  date:date,
									  onlyaccess:true,
									},
									function(data) {
										var html='<option class="firstoption" value="">Please select...</option>';
										$.each(data,function(index,item){
											if (item)
												html+='<option value="'+item.id+'">'+item.name+'</option>';
										});
										$('#instrumentselect_'+subplotpos).html(html).val(instrument);
									}
				);
				$.getJSON('/dataset/attrjson',
										{ attribute:'site',
											valuetype:vt,
										  date:date,
									  	onlyaccess:true,
										},
										function(data){
											var html='<option value="">Please select...</option>';
											$.each(data,function(index,item){
												html+='<option value="'+item.id+'">#'+item.id+' ('+item.name+')</option>';
											});										
											$('#siteselect_'+subplotpos).html(html).val(site);
										}
				);
				if (vt!='' && site!='') {
					$.getJSON('/dataset/attrjson',
										{ 
											attribute:'level',
											valuetype:vt,
											date:date,
											site:site,
									  	onlyaccess:true,
										},
										function(data) {
											var show=false;
											var html='<option value="" class="firstoption">Please select...</option>';
											$.each(data,function(index,item){
												if (item!=null) {
													html+='<option value="'+item+'">'+item+'</option>';
													show=true;
												}
											});
											if (show && vt!='' && site!='') {
												$('#levelselect_'+subplotpos).html(html).val(level);
												$('#levelselect_'+subplotpos).parent().show(200);											
											} else {
												$('#levelselect_'+subplotpos).parent().hide(200);
											}
										});
				
					 if (newlineprops) {
					 		var color = newlineprops.color;
						 	var line = newlineprops.linestyle;
						 	var marker = newlineprops.marker; 
						  $('#markerpicker_'+subplotpos).val(marker);
						  $('#linepicker_'+subplotpos).val(line);
						  $('#colorpicker_'+subplotpos).val(color);
					 }
				 
				} else {
						$('#levelselect_'+subplotpos).parent().hide(200);					
				}
				if (site!='' && 
						vt!='') {
					$('#addline_' + subplotpos).removeProp('disabled');
				} else {
					$('#addline_' + subplotpos).prop('disabled','disabled');			
				}
			}
			

		}
		function clearFilter() {
			$('.filter').val('');
			$('#dateselect').val('');
			$('#allsites').val(true);
			popSelect(1);			
		}
		$(function() {
			$('.props').change(changeprops);
			$('#saveplotbutton').click(function() {
				var fn = prompt('The name of the actual plot','new plot');
				if (fn) {
					$.post('saveplot',{filename:fn,overwrite:true},seterror);
				}
			});
			$('#loadplotbutton').click(function() {
				toggle('loadplotdiv');
			});
			$('.loadplotfn').click(function(){
				var fn = $(this).html();
				$.post('loadplot',{filename:fn},seterror);
				killplot();				
			});
			$('#deleteplotbutton').click(function() {
				toggle('killplotdiv');
				
			});
			$('.killplotfn').click(function(){
				var fn = $(this).html();
				if (confirm('Do you really want to delete your plot "' + fn + '" from the server'))
					$.post('deleteplotfile',{filename:fn},seterror);
				
			});
		});

	    
	   
