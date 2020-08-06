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

function renderplot(creationtime) {
	$('#plot').html('Loading image...');
	// TODO: Transfer Plot data from client => render = save
	$.get(odmf_ref('/plot/image.d3'), {creationtime: creationtime}, (result) => {
		$('#plot').html(result);
	});
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

var plot = {
	start:gettime('start'),
	end:gettime('end'),
	columns:$('#plotcolumns').val(),
	aggregate:$('#plotaggregate').val(),
	subplots: [{
		lines: [],
		ylim: null,
		logsite: null,
	}],
}

function plot_change() {
	let txt_plot = JSON.stringify(plot);
	sessionStorage.setItem('plot', txt_plot);
	$('#json-row pre').html(txt_plot);

}

function addsubplot() {
	$.post('addsubplot', {}, seterror);
	plot.subplots.push({lines: [], ylim: null, logsite: null});
	plot_change();

}
function removesubplot(id) {
	$.post('removesubplot', {subplotid:id}, seterror);
	plot.subplots.splice(id - 1, 1);
	plot_change();

}
function changeylimit(id) {
	var text = prompt('Enter the y axis limit as min,max, eg. 0.5,1.5.').split(',');
	$.post('changeylim',{subplotid:id,ymin:text[0],ymax:text[1]},seterror);
	plot_change();

}
function changelogsite(id) {
	var logsite = $('#logsiteselect_' + id).val();
	$.post('changelogsite',{subplotid:id,logsite:logsite},seterror);
	plot_change();

}
function exportall_csv() {
	var href = odmf_ref('/plot/exportall.csv?tolerance=') + $('#tolerance_skipper').val();
	//alert(href);
	window.location = href;
}

function RegTime() {
	var href = odmf_ref('/plot/RegularTimeseries.csv?tolerance=')+$('#Interpolation_Limit').val() + '&interpolation=' + $('#reg_interpolation').val();
	//alert(href);
	window.location = href;
}

function line_from_dialog() {
	return {
		valuetypeid: parseInt($('#nl-value').val()),
		siteid: parseInt($('#nl-site').val()),
		instrumentid: parseInt($('#nl-instrument').val()),
		level:parseFloat($('#nl-level').val()),
		color:$('#nl-color').val(),
		linestyle:$('#nl-linestyle').val(),
		marker:$('#nl-marker').val(),
		aggfunc:$('#nl-aggregation').val()
	}
}

function line_to_dialog(line) {
	$('#nl-value').val(line.valuetypeid);
	$('#nl-site').val(line.siteid);
	$('#nl-instrument').val(line.instrumentid);
	$('#nl-level').val(line.level);
	$('#nl-color').val(line.color);
	$('#nl-linestyle').val(line.linestyle);
	$('#nl-marker').val(line.marker);
	$('#nl-aggregation').val(line.aggfunc);
}

function open_line_dialog(line) {
	if (line) {
		line_to_dialog(line);
	}
	$('#newline-dialog').modal('show');
}

function removeline(subplot,line) {
	let sp = plot.subplots[subplot];
	sp.lines.splice(line, 1);
	plot_change()
}
function editline(subplot,line_no) {
	try {
		let line = plot.subplots[subplot].lines[line_no];
		open_line_dialog(line);
		plot.subplots[subplot].lines.splice(line_no, 1);
		plot_change();
	} catch (e) {
		$('#error').html('Edit line failed: ' + e.toString());
	}


	$.post('removeline',{subplot:subplot, line:line_no, savelineprops:true}, seterror);
}
function copyline(subplot,line) {
	$.post('copyline',{subplot:subplot,line:line},seterror);
}
function reloadline(subplot,line) {
	$.post('reloadline',{subplot:subplot,line:line},seterror);

}
function showlinedatasets(subplot,line) {
	var content = $('#datasetlist_'+subplot+'_'+line).html();
	$('#datasetlist_'+subplot+'_'+line).slideUp('fast').html('');
	if (content=='') {
		$.getJSON(
			odmf_ref('/plot/linedatasets.json'),
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
		var vt = $('#nl-value').val();
		var site = $('#nl-site').val();
		var instrument = $('#nl-instrument').val();
		var level = $('#nl-level').val();
		var date = ''; //$('#dateselect').val()
		if (newlineprops && !vt) vt=newlineprops.valuetype;
		if (newlineprops && !instrument) instrument=newlineprops.instrument;
		if (newlineprops && !site) site=newlineprops.site;
		if (newlineprops && !level) level=newlineprops.level;

		$.getJSON(odmf_ref('/dataset/attrjson'),
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
				$('#nl-value').html(html).val(vt);
			}
		);

		$.getJSON(odmf_ref('/dataset/attrjson'),
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
				$('#nl-instrument').html(html).val(instrument);
			}
		);
		$.getJSON(odmf_ref('/dataset/attrjson'),
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
				$('#nl-site').html(html).val(site);
			}
		);
		if (vt!='' && site!='') {
			$.getJSON(odmf_ref('/dataset/attrjson'),
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
						$('#nl-level').html(html).val(level);
						$('#nl-level').parent().show(200);
					} else {
						$('#nl-level').parent().hide(200);
					}
				});

			if (newlineprops) {
				$('#nl-marker').val(newlineprops.marker);
				$('#nl-linestyle').val(newlineprops.line);
				$('#nl-color').val(newlineprops.color);
			}

		} else {
			$('#nl-level').parent().hide(200);
		}

		if (site != '' && vt != '') {
			$('#nl-OK').prop('disabled', false);
		} else {
			$('#nl-OK').prop('disabled', true);
		}


}
function clearFilter() {
	$('.filter').val('');
	$('#dateselect').val('');
	$('#allsites').val(true);
	popSelect(1);
}
$(() => {
	$(".timepicker").autocomplete({source: timerange(15)});
	$('#addsubplot').prop('disabled', false);

	$('#btn-clf').click(function() {
		$.post('clf',{},seterror);
	});
    // Fluid layout doesn't seem to support 100% height; manually set it
    $(window).resize(() => {
    	let po = $('#plot').offset();
    	po.totalHeight = $(window).height();
		po.em1 = parseFloat(getComputedStyle($('#plot')[0]).fontSize);
    	let plotHeight = po.totalHeight - po.top - 2 * po.em1;
    	$('#plot').height(plotHeight);

    });

    $('#nl-OK').click((event) => {
    	let sp = parseInt($('#newline-subplot').text());
    	while (plot.subplots.length < sp) {
    		plot.subplots.push([]);
		}
		let line = line_from_dialog();
		plot.subplots[sp - 1].lines.push(line);
		$.post('addline', line,seterror);

	});

    $(window).resize();

    $('#newline-dialog').on('show.bs.modal', (event) => {
    	let button = $(event.relatedTarget);
    	let sp_number = parseInt(button.data('subplot'));
    	$('#newline-subplot').html(sp_number);
    	popSelect(sp_number, null);
	});

    $('#newline-dialog .form-control').change(() => {
    	let sp_number = parseInt($('#newline-subplot').html());
    	popSelect(sp_number, null);
	});

	$('#saveplotbutton').click(function() {
		var fn = prompt('The name of the actual plot','new plot');
		if (fn) {
			$.post('saveplot',{filename:fn,overwrite:true},seterror);
		}
	});
	$('#reload_plot').click(() => {
		let now = new Date().toISOString()
		renderplot(now);
	});
	$('#loadplotbutton').click(function() {
		toggle('loadplotdiv');
	});
	$('.loadplotfn').click(function(){
		var fn = $(this).html();
		$.post('loadplot',{filename:fn},seterror);

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

	    
	   
