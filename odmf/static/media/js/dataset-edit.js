function loadstatistics(dsid) {
    $.getJSON(odmf_ref('/dataset/statistics/'),{id:dsid},function(data){
        $('#mean').html(data.mean.toPrecision(4));
        $('#std').html(data.std.toPrecision(4));
        $('#splitthreshold').val(data.std.toPrecision(4));
        $('#n').html(data.n);
    });
}

function loadrecords(dsid) {
    var threshold = null;
    var limit = $('#recordlimit').val();
    if ($('#splitUseThreshold').prop('checked')) {
        threshold = $('#splitthreshold').val();
    }

    var params={dataset:dsid,
        mindate:$('#recordmindate').val() + 'T' + $('#recordmintime').val(),
        maxdate:$('#recordmaxdate').val() + 'T' + $('#recordmaxtime').val(),
        minvalue:$('#recordminvalue').val(),
        maxvalue:$('#recordmaxvalue').val(),
        threshold:threshold,
        limit:limit
    };
    $('#recordlist').load(odmf_ref('/dataset/records'),params);
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

function reload(error) {
    if (error) {
        if (error.substring(0,5)=='goto:') {
            window.location.href = odmf_ref(error.substring(5));
        } else {
            $('.error').html(error);
        }
    } else {
        window.location.reload(true);
    }
}

function plotds(id) {

    $.post(odmf_ref('/dataset/plot'), {
        id: id,
        start: $('#plotstart').val() + 'T' + $('#plotstart_t').val(),
        end: $('#plotend').val() + 'T' + $('#plotend_t').val(),
        marker: $('#markerpicker').val(),
        line: $('#linepicker').val(),
        color: $('#colorpicker').val(),
        interactive: $('#interactive').is(':checked')
    }, function(html) {
        $('#plot-div').html(html);
    }).fail(jqhxr => {
        $('#plot-div').html('<div class="alert alert-danger">' + jqhxr.responseText + '</div>')
    });
}
function removeds(dsid,dsname,reccount) {
    var msg = 'Are you absolutly sure to delete ' + dsname + '?' +
        'It has ' + reccount + ' records!'
    var really=confirm(msg)
    if (really) {
        $.post(odmf_ref('/dataset/remove/') + dsid, function(data) {
            if (data) {
                $('.error').html(data);
            } else {
                window.back();
            }
        });
    }
}

/***************************
 * Calibration
 */

function do_calibration(targetid, sourceid, limit, ask_to_calibrate=false) {
    let record_count = +($('#calibrate-source-count').html());
    let max_records = 100;
    if (record_count > 100 && ask_to_calibrate &&
        confirm(`Your calibration source has ${record_count} records. Do you really want to calibrate?`)) {
        max_records = record_count;
    }
    $.get(
        odmf_ref('/dataset/calibration_source_info'),
        { targetid: targetid, sourceid: sourceid, limit: limit, max_source_count: max_records },
        function(data) {
            $('#calibrate-source-properties').removeClass('d-none');
            $('#calibrate-source-count').html(data.count);
            $('#error').html(data.error);
            if (data.count > 100) {
                $('#calibrate-source-count:parent').addClass('alert-warning');
            } else {
                $('#calibrate-source-count:parent').removeClass('alert-warning');
            }
            if (data.result && data.result.count) {
                // Show result div
                $('#calibration-result').removeClass('d-none');
                // Set units
                $('#calibration-result .unit').html(data.unit);
                $.each(data.result, function(key, value) {
                    if (! isNaN(value)) {
                        $('#calibration-result-' + key).html(+value.toPrecision(4));
                    }

                });
            } else {
                $('#calibration-result').addClass('d-none');
            }
        }
    );

}

function apply_calibration(targetid, sourceid, slope, offset) {
        $.post(
        // TODO: Get slope and offset from DOM
        odmf_ref('/dataset/apply_calibration'),
        {
            targetid: targetid,
            sourceid: sourceid,
            slope: slope,
            offset: offset
        }, function(error) {
            if (error) {
                $('#error').html(error);
            } else {
                let timestamp = new Date().toISOString();
                window.location.href=odmf_ref(`/dataset/${targetid}?_=${timestamp}#edit`);
            }
        });

}

/***************************
 * On load
 */
$(function() {
    const dsid = parseInt($("#dsid").html());
    $(".timepicker").attr('placeholder', '00:00');

    $('#create-transformation').click(e => {
        $.post(odmf_ref('/dataset/create_transformation/'),
            {sourceid: $('#id-input').val()}
        ).done(data => {
            location.href = odmf_ref(data)
        }).fail(jqhxr => {
            $('#error').html(jqhxr.responseText)
            $('#error-row').removeClass('d-none')
        })
    })
    $('#trans_help').hide();
    $('.transhelpparent').focusin(function(){
        $('#trans_help').slideDown('fast');
    });
    $('.transhelpparent').focusout(function(){
        $('#trans_help').hide();
    });
    $('#trans_sources').change(function() {
        $('#trans_add_source').prop('disabled', !($(this).val() > 0));
    });
    loadstatistics(dsid);
    $('#goto').change(function(event) {
        window.location.href=odmf_ref('/dataset/') + $('#goto').val();
    });
    $('#gotods-btn').click(function() {
        window.location.href=odmf_ref('/dataset/') + $('#goto').val();;
    });
    $('#find-records').click(function() {
       loadrecords(dsid);
    });
    // Javascript to enable link to tab
    if (window.location.hash) {
        $(`#tabs a[href="${window.location.hash}"`).tab('show') ;
    }

    // With HTML5 history API, we can easily prevent scrolling!
    $('#tabs a').on('shown', function (e) {
        if (history.pushState) {
            history.pushState(null, null, e.target.hash);
        } else {
            window.location.hash = e.target.hash; //Polyfill for old browsers
        }
    });

    /*********************
     * Calibration
     */
    $('#calibrate-select-source').change(function() {
        let sourceid = $(this).val();
        let limit = $('#calibrate-limit-time-error').val();
        $('#calibration-result .value').removeClass('bg-warning');
        if (sourceid) {
            do_calibration(dsid, sourceid, limit);
        } else {
            $('#calibrate-source-properties').addClass('d-none');
            $('#calibration-result').addClass('d-none');
        }

    });
    $('#calibrate-button-start').click(function() {
        let sourceid = $('#calibrate-select-source').val();
        let limit = $('#calibrate-limit-time-error').val();
        if (sourceid) {
            do_calibration(dsid, sourceid, limit, true);
        }
    });
    $('.do-calibration').click(function() {
        let sourceid= +$('#calibrate-select-source').val();
        let offset = 0;
        let slope = 0;
        if ($(this).prop('id').match("offset")) {
            offset = + $('#calibration-result-meanoffset').html();
            slope = 1.0;
        } else {
            offset = + $('#calibration-result-offset').html();
            slope = + $('#calibration-result-slope').html();
        }
        apply_calibration(dsid, sourceid, slope, offset);
    });

});


