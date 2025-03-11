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
        new google.maps.Point(0, 24)
        );
    if (site_geometry.geometry.type != 'Point') {
    
        map.data.addGeoJson(site_geometry);
        map.data.setStyle(feature => {
            return {
                strokeWeight: feature.getProperty('strokeWidth'),
                strokeColor: feature.getProperty('strokeColor'),
                strokeOpacity: feature.getProperty('strokeOpacity'),
                fillColor: feature.getProperty('fillColor'),
                fillOpacity: feature.getProperty('fillOpacity'),
            }
        })
    
    }

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
        $.post(odmf_ref('removeinstrument'),
            {
                date:$('#installationdate').val(),
                //siteid:t.data('site'),
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
        $.post(odmf_ref('addinstrument'),
            {
                instrumentid:$('#instrumentselect').val(),
                date:$('#installationdate').val(),
                // siteid:$('#actualsite-input').val(),
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
