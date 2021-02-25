/**
 * @author philkraf
 *
 * TODO: Move line dialog to extra template and fill on server side
 */


function seterror(jqhxr ,textStatus, errorThrown) {
	if (textStatus) {
		$('#error').html(textStatus);
		$('#error-row').slideDown();
	} else {
		$('#error-row').slideUp(() => {$('#error').html('');});
	}
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

function download_on_post(url,  data) {
	let form = $('<form>').attr("action", url).attr("method", "POST").attr("target", "_blank")
	$.each(data, (key, value) => {
		let input = $('<input>').attr("type", "hidden").attr("name", key).val(value)
		form.append(input)
	})
	console.debug(form.html())
	$(form).appendTo('body').submit()
}

function set_content_tree_handlers() {
	$('.removeline').click(event => {
		let btn = $(event.currentTarget);
		window.plot.removeline(btn.data('subplot'), btn.data('lineno')).apply()
	})
	$('.exportline').click(event => {
		let btn = $(event.currentTarget);
		download_on_post('export_csv', {plot: JSON.stringify(window.plot, null, 4), subplot: btn.data('subplot'), line: btn.data('lineno')})
	})

	$('.showdataset').click(event => {
		let btn = $(event.currentTarget)
		let sp = btn.data('subplot')
		let line = btn.data('lineno')
		let dsl = $(`#datasetlist_${sp}_${line}`)
		if (!dsl.html()) {
			$.getJSON(
				'linedatasets.json',
				{
					subplot: sp,
					line: line,
					plot: JSON.stringify(window.plot, null, 4)
				},
				data => {
					let home = odmf_ref('/dataset')
					let html = ''
					if (data)
						html += data.map(item => `<li><a href="${home}/${item.id}">${item.label}</a></li>`).reduce((acc, v) => acc + '\n' + v);
					$(`#datasetlist_${sp}_${line}`).html(html)
				}
			);
		} else {
			dsl.html('');
		}

	});
	$('.sp-logsite-button').click(event =>{
		let subplot=$(event.currentTarget).data('subplot');
		let html = `<div class="dropdown-item sp-logsite-item" data-subplot="${subplot}">no logs</div>\n` +
			window.plot.get_sites(subplot).map(
			value => `<div class="dropdown-item sp-logsite-item" data-subplot="${subplot}" data-site="${value}">#${value}</div>`
			).reduce((acc, v)=>acc + '\n' + v)
		$(`.sp-logsite-list[data-subplot=${subplot}]`).html(html)
		$(`.sp-logsite-item[data-subplot=${subplot}]`).click(event =>{
			let div = $(event.currentTarget)
			let subplot=div.data('subplot');
			let site = div.data('site');
			window.plot.subplots[subplot].logsite = site || null;
			window.plot.apply()
		});
	});

	$('.sp-remove-button').click(event=>{
		window.plot.removesubplot(
			$(event.currentTarget).data('subplot')
		);
	})
	$('.sp-changeylimit-button').click(event=>{
		window.plot.changeylimit($(event.currentTarget).data('subplot'))
	})

}

class Plot {
	constructor() {
		let saved_plot = JSON.parse(sessionStorage.getItem('plot'))
		if (saved_plot && !$.isEmptyObject(saved_plot)) {
			this.name =   saved_plot.name || ''
			this.start =  saved_plot.start || gettime('start')
			this.end =  saved_plot.end || gettime('end')
			this.columns =  saved_plot.columns || 1
			this.aggregate =  saved_plot.aggregate ||''
			this.height =  saved_plot.height || 640
			this.width =  saved_plot.width || 480
			this.subplots =  saved_plot.subplots || []

		} else {
			this.name =  ''
			this.start = gettime('start')
			this.end =  gettime('end')
			this.columns =  1
			this.aggregate = ''
			this.height =  640
			this.width =  480
			this.subplots = [{
				lines: [],
				ylim: null,
				logsite: null,
			}]

		}
	}
	update(obj) {
		for (let key in obj) {
			if (obj.hasOwnProperty(key)) {
				this[key] = obj[key]
			}
		}
		this.apply()
		return this
	}
	render() {
		$('#plot').html('Loading image...');
		$.ajax({
			method: 'POST',
			url: odmf_ref('/plot/figure'),
			contentType: 'application/json',
			processData: false,
			data: JSON.stringify(this, null, 4),
			dataType: 'html'
		})
			.done((result) => {
				$('#plot').html(result);
				$('#plot-reload-button').addClass('d-none')
				$('#plot').removeClass('semitransparent')
			})
			.fail(seterror);
		return this.apply()
	}

	addsubplot() {
		this.subplots.push({lines: [], ylim: null, logsite: null});
		return this.apply()
	}

	apply(width, height) {
		if (width) {
			this.width = width
		}
		if (height)
			this.height = height
		if (this.columns > this.subplots.length) {
			this.columns = Math.max(1, this.subplots.length);
		}
		let txt_plot = JSON.stringify(this, null, 4);
		$('#plot-name').html(this.name)
		$('#content-tree .subplot').remove();
		this.subplots.forEach((subplot, index) => {
			let txt = $('#subplot-template').html()
				.replace(/§position§/g, index)
				.replace(/§logsite§/g, subplot.logsite || ' -?-')
			let obj = $(txt);
			let line_template = $('#line-template').html()
			subplot.lines.forEach((line, lineindex) => {
				let line_html = line_template.replace(/§sp_pos§/g, index).replace(/§i§/g, lineindex).replace(/§linename§/g, line.name)
				for (let k in line) {
					line_html = line_html.replace('§' + k + '§', line[k])
				}
				let ul = obj.find('#line-list');
				let nl = ul.find('.newline')
				nl.before(line_html);
			})
			$('#ct-new-subplot').before(obj);
		})
		sessionStorage.setItem('plot', txt_plot);
		$('#json-row pre').html(txt_plot);
		$('#plot-reload-button').css('top',this.height / 2).css('left', this.width / 3).removeClass('d-none')
		$('#plot').addClass('semitransparent')
		set_content_tree_handlers();
		return this
	}
	removesubplot(id) {
		this.subplots.splice(id, 1);
		return this.apply()
	}
	changeylimit(subplot) {
		let text = prompt('Enter the y axis limit as min,max, eg. 0.5,1.5.').split(',');
		try {
			this.subplots[subplot].ylim = [parseFloat(text[0]), parseFloat(text[1])];
		} catch (e) {
			$('#error').html('Edit line failed: ' + e.toString());
		}
		return this.apply()

	}

	get_sites(subplot) {
		// Creates
		return Array.from(
			new Set(
				this.subplots[subplot].lines.map(line => line.site)
			)
		)
	}


	// *********************************************
	// Line management
	removeline(subplot,line) {
		let sp = this.subplots[subplot];
		if (sp && line >= 0)
			sp.lines.splice(line, 1);
		return this
	}
}

function line_from_dialog() {
	let get_name_from_line_dialog = function() {
		let name = $('#nl-name').val();
		if (!name) {
			name = 	$('#nl-value option:selected').text() + ' at #' + $('#nl-site').val()
			let level = $('#nl-level').val();
			if (level) {
				name += '(' + level + ' m)'
			}
			let instrument = $('#nl-instrument option:selected').text()
			if (instrument) {
				name += ' using ' + instrument;
			}
			let aggregatefunction = $('#nl-aggregation').val();
			if (aggregatefunction) {
				name += '(' + aggregatefunction + ')'
			}
		}
		return name;
	}

	return {
		name: get_name_from_line_dialog(),
		valuetype: parseInt($('#nl-value').val()),
		site: parseInt($('#nl-site').val()),
		instrument: parseInt($('#nl-instrument').val()),
		level:parseFloat($('#nl-level').val()),
		color:$('#nl-color').val(),
		linestyle:$('#nl-linestyle').val(),
		marker:$('#nl-marker').val(),
		aggregatefunction:$('#nl-aggregation').val()
	}
}

function line_to_dialog(line) {
	let dlg =$('#newline-dialog')
	let sp = dlg.data('subplot')
	let ln = dlg.data('lineno')
	let repl = dlg.data('replace')
	$('#newline-subplot').html(`${sp} line ${ln} - ${repl}`);
	$('#nl-value').val(line.valuetype)
	$('#nl-site').val(line.site)
	$('#nl-instrument').val(line.instrument)
	$('#nl-level').val(line.level)

	$('#nl-color').val(line.color);
	$('#nl-linestyle').val(line.linestyle);
	$('#nl-marker').val(line.marker);
	$('#nl-aggregation').val(line.aggregatefunction);
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

function make_option_html(data, get_value, get_name) {
	let html='<option class="firstoption" value="">Please select...</option>\n';
	$.each(data,function(index,item){
		html+=`<option value="${get_value(item)}">${get_name(item)}</option>\n`;
	});
	return html
}

function lineDialogPopSelect(valuetype, site, set_values) {
	$('#newline-dialog .form-control').prop('disabled', true)
	$.getJSON(
		odmf_ref('/dataset/attributes'),
		{
			valuetype: valuetype,
			site: site,
			onlyaccess:true,
		},
		(data) => {
			$('#nl-value').html(
				make_option_html(data.valuetype,x => x ? x.id: null, x => x ? x.name: '')
			);
			$('#nl-instrument').html(
				make_option_html(data.source, x => x ? x.id: null, x => x ? x.name: '')
			)
			$('#nl-site').html(
				make_option_html(data.site, x => x ? x.id: null, x => `#${x.id} (${x.name})`)
			)

			let nl_level = $('#nl-level')
			// Check if there are levels in the available datasets
			if (data.level.some(x => x)) {
				nl_level.html(
					make_option_html(data.level, x => x ? x.toString() : null, x => x ? x.toString() : 'N/A')
				)
				nl_level.parents('.row').show(200)
			} else {
				nl_level.parents('.row').hide(200)
			}

			if (set_values) {
				set_values()
			}
			$('#newline-dialog .form-control').prop('disabled', false)

		}
	);


}


function set_line_dialog_handlers() {
	$('#newline-dialog').on('show.bs.modal', (event) => {
		let button = $(event.relatedTarget);
		let dlg =$('#newline-dialog')
		let sp = button.data('subplot')
		let ln = button.data('lineno')
    	dlg.data('subplot', sp);
    	dlg.data('lineno', ln);
    	dlg.data('replace', button.data('replace'));
    	let plot = window.plot;
    	let line = {}
    	if (!(sp >= 0)) {
    		$('#error').html('#' + button.id + ' has no subplot').parent().parent().fadeIn()
		}
    	else if (ln >= 0) {
    		line = plot.subplots[sp].lines[ln]
		}
		lineDialogPopSelect(line.valuetype, line.site, ()=>{line_to_dialog(line)})

    });

    $('#newline-dialog .dataset-select').change(() => {
		let dlg =$('#newline-dialog')
		let line = line_from_dialog()
		let	valuetype = parseInt($('#nl-value').val())
		let site = parseInt($('#nl-site').val())
		lineDialogPopSelect(valuetype, site, () => {line_to_dialog(line)})

		if (site && valuetype) {
			$('#nl-OK').prop('disabled', false);
		} else {
			$('#nl-OK').prop('disabled', true);
		}

	});

    $('#nl-color').change(event => {
    	$('#nl-color-text').html($(event.currentTarget).val())
	})


    $('#nl-OK').click(() => {
    	let dlg =$('#newline-dialog')
    	let plot = window.plot
		let line = line_from_dialog()
		let sp_no = dlg.data('subplot')
		let line_no = dlg.data('lineno')
		let replace = dlg.data('replace')
		if (!(sp_no >=0)) console.warn('Somehow the dialog was opened but received no subplot')

		let sp = plot.subplots[sp_no]

		if (replace == 'replace') {
			sp.lines[line_no] = line
		} else {
			sp.lines.push(line)
		}
		plot.apply()
	});

}

function get_all_lines() {
	return window.plot.subplots.map(sp => sp.lines).flat()
}

function makeExportDialog() {
	$('#export-method').remove('.timeindex_from_line').append(
		get_all_lines().map(
			(line, index) => $(`<option value="${index}" class="timeindex_from_line">Timesteps from ${line.name}</option>`)
		)
	)
	$('#export-plot').val(JSON.stringify(window.plot))
	$('#export-method').change(e => {
		if ($(e.currentTarget).val() === 'regular') {
			$('#export-grid').parents('.row').show(200)
		} else {
			$('#export-grid').parents('.row').hide(200)
		}
	}).val('union').change()
	$('#export-interpolation-method').change(e => {
		if ($(e.currentTarget).val()) {
			$('#export-interpolation-limit').parents('.row').show(200)
		} else {
			$('#export-interpolation-limit').parents('.row').hide(200)
		}
	}).val('').change()

}

$(() => {
	window.plot = new Plot()
	window.plot.apply()
	// $(".date").datetimepicker({format: 'YYYY-MM-DD HH:mm'})
	$('#addsubplot').prop('disabled', false);

	$('#btn-clf').click(function() {
		let plot = window.plot
		plot.subplots = [{
			lines: [],
			ylim: null,
			logsite: null,
		}];
		plot.apply()
	});
    // Fluid layout doesn't seem to support 100% height; manually set it
    $(window).resize(() => {
    	let plotElement = $('#plot');
    	let po = plotElement.offset();
    	po.totalHeight = $(window).height();
		po.em1 = parseFloat(getComputedStyle(plotElement[0]).fontSize);
    	let plotHeight = po.totalHeight - po.top - 2 * po.em1;
    	plotElement.height(plotHeight);
		window.plot.apply(plotElement.width(), plotHeight)
    });

    $(window).resize();

	set_line_dialog_handlers()

	$('#reload_plot').click(() => {
		window.plot.render()
	});


	$('#fig-export button').click(event => {
		let fmt=$(event.currentTarget).data('format');
		if (fmt) {
			download_on_post('image', {format: fmt, plot: JSON.stringify(window.plot, null, 4)})
		}
	})

	$('#property-dialog').on('show.bs.modal', event => {
		$('#property-dialog-content').load('property/')
	})

	$('#file-dialog').on('show.bs.modal', event => {
		$('#file-dialog-content').load('filedialog/')
	})
	$('#export-dialog').on('show.bs.modal', makeExportDialog)

	$('.killplotfn').click(function() {
		var fn = $(this).html();
		if (confirm('Do you really want to delete your plot "' + fn + '" from the server'))
			$.post('deleteplotfile',{filename:fn},seterror);
	});
});

	    
	   
