import rasterio as rio
from .. import db
from . import Path as OPath


class RasterReader:
    def __init__(self, tiffile, band=1):
        self.ds = rio.open(tiffile)
        self.band = self.ds.read(band)

    def __getitem__(self, item):
        return self.band[self.ds.index(*item)]


def add_missing_heights(demfile='datafiles/geodata/dgm1/DGM1_gladbacherhof_.tif'):
    """
    Gets height information from a digital elevation model in a GeoTiff for each site
    missing height information. The site's description is extended about the

    The raster data needs to be in UTM-Coordinates.
    """

    rr = RasterReader(demfile)
    try:
        op = OPath(demfile).parent()
    except:
        op = OPath('/')

    with db.session_scope() as session:
        for s in session.query(db.Site).filter(~(db.Site.height > -300)).order_by(db.Site.id):
            s: db.Site
            zone, x, y = s.as_UTM()
            s.height = float(rr[x, y])
            s.comment += f'\n\nHeight information derived from digital elevation model {op.markdown}\n'
