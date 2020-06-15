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
        mindate:$('#recordmindate').val() + ' ' + $('#recordmintime').val(),
        maxdate:$('#recordmaxdate').val() + ' ' + $('#recordmaxtime').val(),
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

    $.get(odmf_ref('/dataset/plot'), {
        id: id,
        start: $('#plotstart').val() + 'T' + $('#plotstart_t').val(),
        end: $('#plotend').val() + 'T' + $('#plotend_t').val(),
        marker: $('#markerpicker').val(),
        line: $('#linepicker').val(),
        color: $('#colorpicker').val(),
        interactive: $('#interactive').is(':checked')
    }, function(html) {
        $('#plot-div').html(html);
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

function load_calibration() {

}

/***************************
 * On load
 */
$(function() {
    const dsid = parseInt($("#dsid").html());
    $(".timepicker").attr('placeholder', '00:00');
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
    let url = document.location.toString();
    if (url.match('#')) {
        $('#tabs a[href="#'+url.split('#')[1]+ '"]').tab('show') ;
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
    $('#select-calibration-source').change(function() {
        let sourceid = $(this).val();
        // $.get('calibration/sourceproperties', {target: dsid, source: sourceid}, function(data) {
        //      $('#calibrate-source-properties').show();
        //      $('#calibrate-source-properties div span').html(data.count);
        // });
        if (sourceid) {
            $('#calibrate-source-count').html('1');
            $('#calibrate-source-properties').removeClass('d-none');
        } else {
            $('#calibrate-source-properties').addClass('d-none');
        }

    });

});


