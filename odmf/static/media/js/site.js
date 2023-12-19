function createMap() {
    console.log(site);
    var latlng = new google.maps.LatLng(site.lat, site.lon);
    var mapOptions = {
        zoom: 20,
        center: latlng,
        mapTypeId: 'hybrid'
    };
    var map = new google.maps.Map(document.getElementById("map_canvas"), mapOptions);

    if (!site.icon) {
        icon='unknown.png';
    } else {
        icon = site.icon;
    }

    var image = new google.maps.MarkerImage(
        odmf_ref('/media/mapicons/') + icon,
        new google.maps.Size(24, 24),
        new google.maps.Point(0,0),
        new google.maps.Point(0, 24));

    map.data.addGeoJson(site_geometry);
    map.data.setStyle(feature => {
        return {
            strokeWeight: feature.getProperty('strokeWidth') || 2,
            strokeColor: feature.getProperty('strokeColor') || '#FFF',
            strokeOpacity: feature.getProperty('strokeOpacity') || 0.8,
            fillColor: feature.getProperty('fillColor') || '#FFF',
            fillOpacity: feature.getProperty('fillOpacity') || 0.3,
        }
    })

    var marker = new google.maps.Marker(
        {
            position: new google.maps.LatLng(site.lat,site.lon),
            title:'#' + site.id + '(' + site.name + ')',
            map:map,
            icon:image,
        });


}


$(function() {
    $('#site-tab a').on('click', function (e) {
        e.preventDefault()
        $(this).tab('show')
    });

    // Javascript to enable link to tab (from: https://stackoverflow.com/a/9393768/3032680)
    var hash = location.hash.replace(/^#/, '');  // ^ means starting, meaning only match the first hash
    if (hash) {
        let elem = $('.nav-pills a[href="#' + hash + '"]')
        elem.tab('show');
    }
    // Change hash for page-reload
    $('.nav-pills a').on('shown.bs.tab', function (e) {
        window.location.hash = e.target.hash;
    })
    $('.icon-button').on('click', e => {
        let icon = $(e.currentTarget).data('icon')
        $('#currenticon').attr('src',odmf_ref('/media/mapicons/') + icon);
        $('#iconfile').val(icon);
    })
    $('.installation-remove-button').on('click', e => {
        let t = $(e.currentTarget)
        $.post(odmf_ref('/site/removeinstrument'),
            {
                date:escape($('#installationdate').val()),
                siteid:t.data('site'),
                installationid:t.data('installation'),
                instrumentid: t.data('instrument')
            }
        ).done(response => {
            console.debug(response)
            location.reload()
        }).fail(jqhxr => {
            console.warn(jqhxr.responseText)
            $('.error').html(jqhxr.responseText)
        })
    });
    $('#add-instrument-button').on('click', e => {
        $.post(odmf_ref('/site/addinstrument'),
            {
                instrumentid:$('#instrumentselect').val(),
                date:escape($('#installationdate').val()),
                siteid:$('#actualsite-input').val(),
                comment:$('#instrument-comment').val(),
                installationid:$(e.currentTarget).data('installation')
            }
        ).done(response => {
            console.debug(response)
            location.reload()
        }).fail(jqhxr => {
            console.warn(jqhxr.responseText)
            $('.error').html(jqhxr.responseText)
        })
    })

});
