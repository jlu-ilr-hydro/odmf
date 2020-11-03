/**
 * @author philkraf
 */


function seterror(jqhxr ,textStatus, errorThrown) {
	if (textStatus) {
		$('#error').html(textStatus);
		$('#error-row').slideDown();
	} else {
		$('#error-row').slideUp(() => {$('#error').html('');});
	}
}

function renderplot(creationtime) {
	$('#plot').html('Loading image...');
	$.ajax({
      method: 'POST',
      url: odmf_ref('/plot/image_d3'),
      contentType: 'application/json',
      processData: false,
      data: JSON.stringify(plot),
      dataType: 'html'
    })
	.done((result) => {
		$('#plot').html(result);
	})
	.fail(seterror);
}
function gettime(startOrEnd) {
	let res = $('#'+ startOrEnd + 'date').val();
	if (res) {
		res += ' ' + ($('#'+ startOrEnd + 'time').val() || '00:00');
	} else {
		res = '';
	}
	return res;
}

var plot = {
	start:gettime('start'),
	end:gettime('end'),
	columns:parseInt($('#prop-columns').val()),
	aggregate:$('#plotaggregate').val(),
	height: 640,
	width: 480,
	subplots: [{
		lines: [],
		ylim: null,
		logsite: null,
	}],
}

function plot_change() {
	if (plot.columns > plot.subplots.length) {
		plot.columns = Math.max(1, plot.subplots.length);
	}
	let txt_plot = JSON.stringify(plot, null, 4);
	render_content_tree(plot);
	sessionStorage.setItem('plot', txt_plot);
	$('#json-row pre').html(txt_plot);

}

function render_content_tree(plot) {
	plot.subplots.forEach((subplot, index) => {
		let txt = $('#subplot-template').html()
			.replace(/§position§/g, index + 1)
			.replace(/§logsite§/g, subplot.logsite)
		let obj = $(txt);
		let line_template = $('#line-template').html()
		subplot.lines.forEach((line, lineindex) => {
			let line_html = line_template.replace(/§sp_pos§/g, index + 1).replace(/§i§/g, lineindex)
			for (let k in line) {
				line_html = line_html.replace('§' + k + '§', line[k])
			}
			let ul = obj.find('#line-list');
			let nl = ul.find('.newline')
			nl.before(line_html);
		})
		$('#content-tree .subplot').remove();
		$('#ct-new-subplot').before(obj);


	})
}

function addsubplot() {
	plot.subplots.push({lines: [], ylim: null, logsite: null});
	plot_change();

}
function removesubplot(id) {
	plot.subplots.splice(id - 1, 1);
	plot_change();

}
function changeylimit(id) {
	let text = prompt('Enter the y axis limit as min,max, eg. 0.5,1.5.').split(',');
	try {
		plot.subplots[id - 1].ylim = [parseFloat(text[0]), parseFloat(text[1])];
	} catch (e) {
		$('#error').html('Edit line failed: ' + e.toString());
	}
	plot_change();

}
function changelogsite(id) {
	let logsite = $('#logsiteselect_' + id).val();
	try {
		plot.subplots[id - 1].logsite = parseInt(logsite);
	} catch (e) {
		$('#error').html('Edit line failed: ' + e.toString());
	}
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

function subplot_from_line_dialog() {
	return sp = parseInt($('#newline-subplot').text()) - 1;
}

function line_to_dialog(subplot, line) {
	$('#newline-subplot').html(subplot);
	$('#nl-value').val(line.valuetypeid);
	$('#nl-site').val(line.siteid);
	$('#nl-instrument').val(line.instrumentid);
	$('#nl-level').val(line.level);
	$('#nl-color').val(line.color);
	$('#nl-linestyle').val(line.linestyle);
	$('#nl-marker').val(line.marker);
	$('#nl-aggregation').val(line.aggfunc);
}

function open_line_dialog() {
	$('#newline-dialog').modal('show');
}

function addline(sp, line) {
	while (plot.subplots.length < sp) {
		addsubplot();
	}
	plot.subplots[sp].lines.push(line);
}

function removeline(subplot,line) {
	let sp = plot.subplots[subplot];
	sp.lines.splice(line, 1);
	plot_change()
}
function editline(subplot,line_no) {
	try {
		let line = plot.subplots[subplot].lines[line_no];
		line_to_dialog(subplot, line);
		open_line_dialog(line);
		plot.subplots[subplot].lines.splice(line_no, 1);
		plot_change();
	} catch (e) {
		$('#error').html('Edit line failed: ' + e.toString());
	}
}

function copyline(subplot,line) {
	try {
		let line = plot.subplots[subplot].lines[line_no];
		line_to_dialog(subplot, line);
		open_line_dialog(line);
	} catch (e) {
		$('#error').html('Edit line failed: ' + e.toString());
	}
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
function timerange(step) {
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

	let saved_plot = JSON.parse(sessionStorage.getItem('plot'))
	if (saved_plot) {
		plot = saved_plot
	} else {
		plot_change()
	}
	$(".date").datetimepicker({format: 'YYYY-MM-DD HH:mm'})
	$('#addsubplot').prop('disabled', false);

	$('#btn-clf').click(function() {
		plot.subplots = [{
			lines: [],
			ylim: null,
			logsite: null,
		}];
	});
    // Fluid layout doesn't seem to support 100% height; manually set it
    $(window).resize(() => {
    	let plotElement = $('#plot');
    	let po = plotElement.offset();
    	po.totalHeight = $(window).height();
		po.em1 = parseFloat(getComputedStyle(plotElement[0]).fontSize);
    	let plotHeight = po.totalHeight - po.top - 2 * po.em1;
    	plotElement.height(plotHeight);
    	plot.height = plotHeight;
    	plot.width = plotElement.width();
    	plot_change();

    });

    $('#nl-OK').click((event) => {
    	addline(subplot_from_line_dialog(), line_from_dialog());
    	plot_change();
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
		plot_change();
	});
	$('.loadplotfn').click(function(){
		var fn = $(this).html();
		$.post('loadplot',{filename:fn},seterror);

	});

	$('#property-dialog').on('show.bs.modal', event => {
		if (plot.start) {
			$('#startdate').val(plot.start.split(' ')[0])
			$('#starttime').val(plot.start.split(' ')[1])
		}
		if (plot.end) {
			$('#enddate').val(plot.end.split(' ')[0])
			$('#endtime').val(plot.end.split(' ')[1])
		}

		$('#prop-columns').val(plot.columns).attr('max', Math.max(1, plot.subplots.length))
		$('#plotaggregate').val(plot.aggregate)
		$('#prop-description').val(plot.description)
	})
	$('#prop-OK').click(event => {
		plot.start = gettime('start')
		plot.end = gettime('end')
		plot.columns = parseInt($('#prop-columns').val())
		plot.aggregate = $('#plotaggregate').val()
		plot_change()
	});

	$('.killplotfn').click(function(){
		var fn = $(this).html();
		if (confirm('Do you really want to delete your plot "' + fn + '" from the server'))
			$.post('deleteplotfile',{filename:fn},seterror);

	});
});

	    
	   
