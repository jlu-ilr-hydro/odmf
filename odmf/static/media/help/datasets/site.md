# !fa-map-location Site

Sites locate datasets in space. Usually sites are points with lon / lat coordinates (WGS84 reference ellipsoid) but sites
can also contain a more complex geometry like a line or a polygon. Sites should have a name (that might change) and have an ID
that is unique in the ODMF instance. Before you can create a dataset, its location must be available in ODMF.

## Creating sites one by one

A new site is either created with the "new Site" button at ~/site/ or at the map by with the checkbox "new site". If "new site" is enabled on the map, a doule click on the map creates a new site at that location, with the "new site" button you need to fill out the location by hand. Choose a name and an icon for the site. You can save additional icons in your app directory in media/mapicons. The Mapicons are .png files with 32x32 pixels resolution. A description (comment) helps the users what to expect on that site.

### Adding geometry

If the site describes a line or an area, you can copy a geometry in GeoJSON format in the "add geometry" part of the site editor. Here you can also set the visual appearance of the geometry on the map. Use lower fill opacities to keep overlapping geometries visible.

## Import sites

You can also import sites from files with the import button on the site list.

### Import tabular data

When you import sites, note that the tabular data must have the columns name, lat, lon. Lat and lon are the geographic coordinates on a WGS84 reference ellipsoid. Optionally the column names height, icon, comment are used.

### Import geojson data

If you are importing geospatial data in geojson form, the projection of the data must be given and translatable in WGS84 (EPSG:4326). Each feature must have a name property. Optionally property names height, icon, comment are used to describe the site and strokewidth, strokecolor, strokeopacity, fillcolor, fillopacity can be given for the appearance of the geometry. GeoJSON files can be created with QGIS from most geospatial data, tutorials are simple to find with common search machines, like this one: [How_to_create_a_GeoJSON_in_QGIS](https://support.tygron.com/wiki/How_to_create_a_GeoJSON_in_QGIS) 
