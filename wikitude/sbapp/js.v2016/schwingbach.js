//Server von dem die JSON-Datei fuer die POIs bezogen wird

var POIURL="http://fb09-pasig.umwelt.uni-giessen.de/sbapp/app/Poidata.json";
var World = {
	loaded: false,
	init: function initFn() {
		//  Sensoren fuer die Geoobjekte (Kompass, Lagesensoren, GPS etc.) sind angeschaltet bei true
		AR.context.services.sensors = true;
		this.createOverlays();
	},

	//Erstellung der Overlays fuer Video/Audio/Bilder
	createOverlays: function createOverlaysFn() {
		
		// Initialisiert den Tracker - die WTC-Datei bzw. Target-Datei - 
        // beinhaltet Dateinamen und Erkennungsalgorithemen der Tracking-Objekte - die einzeln aufgerufen werden
        // wtc - Datei wird von online Serive bei Wikitude aus Bilddatei erstellt.
        // Der Tracker enth�lt alle trackable vorlagen, von QR-Code bis Brennessel
		this.tracker = new AR.Tracker("assets/SBT.wtc.5.1", {
			onLoaded: this.worldLoaded
		});

		//Erstes Video Naehrstoffe Gewaesser
		// Ein transparentes Video-Drawable wird erstellt
		var lutzvid1 = new AR.VideoDrawable("assets/Lutz_2_naehrstoffe.mp4", 0.9, {
			offsetX: -0.2,
			offsetY: -0.12,
			isTransparent: true
		});
        World.lutzvid1 = lutzvid1;

		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var LutzNButton = this.createWwwLinkButton("http://www.uni-ulm.de/LiLL/3.0/D/WASSER/FOLGE.htm", 0.15, {
			offsetX: -0.25,
			offsetY: 0.3,
			zOrder: 1
		});
		lutzvid1.play(-1);
		lutzvid1.pause();

		var LutzN = new AR.Trackable2DObject(this.tracker, "wasser_stickstoff_urtica_dioica", {
			drawables: {
				cam: [lutzvid1, LutzNButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				lutzvid1.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				lutzvid1.pause();
			}
		});


		//Zweites Video Wasserhaushalt des Waldes
		// Ein transparentes Video-Drawable wird erstellt
		var lutzvid2 = new AR.VideoDrawable("assets/Lutz_wald.mp4", 1.2, {
			offsetX: 0.0,
			offsetY: -0.12,
			isTransparent: true
		});
        World.lutzvid2 = lutzvid2;
		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var LutzWButton = this.createWwwLinkButton("http://fb09-pasig.umwelt.uni-giessen.de/sbapp/app/assets/wald_links.html", 0.2, {
			offsetX: -0.2,
			offsetY: 0.35,
			zOrder: 1
		});
		lutzvid2.play(-1);
		lutzvid2.pause();

		var LutzW = new AR.Trackable2DObject(this.tracker, "wasser_wald", {
			drawables: {
				cam: [lutzvid2, LutzWButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				lutzvid2.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				lutzvid2.pause();
			}
		});


		//Drittes Video Abfluss Gewaesser
		// Ein transparentes Video-Drawable wird erstellt
		var lutzvid3 = new AR.VideoDrawable("assets/Lutz_abfluss.mp4", 1.9, {
			offsetX: -0.35,
			offsetY: -0.12,
			isTransparent: true
		});
        World.lutzvid3 = lutzvid3;

		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var LutzAButton = this.createWwwLinkButton("http://www.hydroskript.de/html/_index.html?page=/html/hykp0705.html", 0.2, {
			offsetX: 0.2,
			offsetY: 0.4,
			zOrder: 1
		});
		lutzvid3.play(-1);
		lutzvid3.pause();

		var LutzN = new AR.Trackable2DObject(this.tracker, "qr_code_abfluss", {
			drawables: {
				cam: [lutzvid3, LutzAButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
                alert('LutzVideoAbfluss');
				lutzvid3.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				lutzvid3.pause();
			}
		});


		//Viertes Video - Boden -Loess links
		// Ein transparentes Video-Drawable wird erstellt
		var sylvid4 = new AR.VideoDrawable("assets/Sylvie_Boden.mp4", 1.4, {
			offsetX: -0.3,
			offsetY: -0.12,
			isTransparent: true
		});
        World.sylvid4 = sylvid4;
		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var SylVButton = this.createWwwLinkButton("http://de.wikipedia.org/wiki/Boden_(Bodenkunde)", 0.2, {
			offsetX: 0.2,
			offsetY: 0.4,
			zOrder: 1
		});
		sylvid4.play(-1);
		sylvid4.pause();

		var SylvieR = new AR.Trackable2DObject(this.tracker, "qr_code_boden", {
			drawables: {
				cam: [sylvid4, SylVButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				sylvid4.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				sylvid4.pause();
			}
		});


		//Fuenftes Video - Boden vielfalt rechts - Landnutzung
		// Ein transparentes Video-Drawable wird erstellt
		var sylvid5 = new AR.VideoDrawable("assets/Sylvie_Landnutzung.mp4", 1.4, {
			offsetX: -0.2,
			offsetY: -0.12,
			isTransparent: true
		});
        World.sylvid5 = sylvid5;
		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var SylYButton = this.createWwwLinkButton("http://de.wikipedia.org/wiki/Landnutzung", 0.2, {
			offsetX: 0.2,
			offsetY: 0.4,
			zOrder: 1
		});
		sylvid5.play(-1);
		sylvid5.pause();

		var SylvieS = new AR.Trackable2DObject(this.tracker, "boden_vielfalt_rechts", {
			drawables: {
				cam: [sylvid5, SylYButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				sylvid5.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				sylvid5.pause();
			}
		});


		//Sechstes Video - Boden Geologie
		// Ein transparentes Video-Drawable wird erstellt
		var sylvid6 = new AR.VideoDrawable("assets/Sylvie_Geologie.mp4", 0.9, {
			offsetX: -0.2,
			offsetY: -0.12,
			isTransparent: true
		});
        World.sylvid6 = sylvid6;
		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var SylZButton = this.createWwwLinkButton("http://de.wikipedia.org/wiki/L%C3%B6ss", 0.1, {
			offsetX: 0.1,
			offsetY: 0.25,
			zOrder: 1
		});
		sylvid6.play(-1);
		sylvid6.pause();

		var SylvieT = new AR.Trackable2DObject(this.tracker, "boden_loess_links", {
			drawables: {
				cam: [sylvid6, SylZButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				sylvid6.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				sylvid6.pause();
			}
		});
		
		
		//Siebtes Video Boden Loess - Bodentyp
		// Ein transparentes Video-Drawable wird erstellt
		var sylvid7 = new AR.VideoDrawable("assets/Sylvie_Bodentyp.mp4", 2.1, {
			offsetX: -0.2,
			offsetY: -0.12,
			isTransparent: true
		});
        World.sylvid7 = sylvid7;
		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var SylAButton = this.createWwwLinkButton("http://de.wikipedia.org/wiki/Bodentyp", 0.3, {
			offsetX: -0.4,
			offsetY: 0.7,
			zOrder: 1
		});
		sylvid7.play(-1);
		sylvid7.pause();

		var SylvieN = new AR.Trackable2DObject(this.tracker, "boden_loess_rechts", {
			drawables: {
				cam: [sylvid7, SylAButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				sylvid7.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				sylvid7.pause();
			}
		});
	
		//Achtes Video Wasser - Piezometer
		// Ein transparentes Video-Drawable wird erstellt
		var sbvid1 = new AR.VideoDrawable("assets/mehr_als_nur_ein_loch.mp4", 0.2, {
			offsetX: -0.2,
			offsetY: -0.12,
			isTransparent: true
		});
        World.sbvid1 = sbvid1;
		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var sbNButton = this.createWwwLinkButton("http://www.youtube.com/watch?v=Ci6Za_F-w4Q", 0.2, {
			offsetX: -0.05,
			offsetY: 0.2,
			zOrder: 1
		});
		sbvid1.play(-1);
		sbvid1.pause();

		var SbN = new AR.Trackable2DObject(this.tracker, "wasser_piezometer_mehr_als_ein_loch_2", {
			drawables: {
				cam: [sbvid1, sbNButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				sbvid1.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				sbvid1.pause();
			}
		});
			
		//Neuntes Video Wasser - So fliesst SB
		// Ein transparentes Video-Drawable wird erstellt
		var sbvid2 = new AR.VideoDrawable("assets/so_fliesst_sb.mp4", 0.2, {
			offsetX: -0.2,
			offsetY: -0.12,
			isTransparent: true
		});
        World.sbvid2 = sbvid2;
		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var sbMButton = this.createWwwLinkButton("http://www.nabu.de/themen/fluesse/wasserrahmenrichtlinie/", 0.3, {
			offsetX: 0.6,
			offsetY: -0.4,
			zOrder: 1
		});
		sbvid2.play(-1);
		sbvid2.pause();

		var SbM = new AR.Trackable2DObject(this.tracker, "wasser_so_fliesst_sb", {
			drawables: {
				cam: [sbvid2, sbMButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				sbvid2.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				sbvid2.pause();
			}
		});


		//Zehntes Video Landschaft Streuobst Steinkauz
		// Ein transparentes Video-Drawable wird erstellt
		var sovid1 = new AR.VideoDrawable("assets/Steinkauz_Tembrock_Guenther_1322.mp4", 0.2, {
			offsetX: -0.2,
			offsetY: -0.12,
			isTransparent: true
		});
        World.sovid1 = sovid1;
		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var soAButton = this.createWwwLinkButton("http://de.wikipedia.org/wiki/Steinkauz", 0.2, {
			offsetX: -0.1,
			offsetY: -0.4,
			zOrder: 1
		});
		sovid1.play(-1);
		sovid1.pause();

		var SoA = new AR.Trackable2DObject(this.tracker, "landschaft_streuobst_steinkauz", {
			drawables: {
				cam: [sovid1, soAButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				sovid1.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				sovid1.pause();
			}
		});

		//Elftes Video Landschaft Streuobst Buntspecht
		// Ein transparentes Video-Drawable wird erstellt
		var sovid2 = new AR.VideoDrawable("assets/Buntspecht_Tembrock_Guenther_0182.mp4", 0.2, {
			offsetX: -0.2,
			offsetY: -0.12,
			isTransparent: true
		});
        World.sovid2 = sovid2;
		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var soBButton = this.createWwwLinkButton("http://de.wikipedia.org/wiki/Buntspecht", 0.2, {
			offsetX: 0.3,
			offsetY: -0.3,
			zOrder: 1
		});
		sovid2.play(-1);
		sovid2.pause();

		var SoB = new AR.Trackable2DObject(this.tracker, "landschaft_streuobst_buntspecht", {
			drawables: {
				cam: [sovid2, soBButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				sovid2.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				sovid2.pause();
			}
		});
		
		//Zwoelftes Video Landschaft Streuobst Igel
		// Ein transparentes Video-Drawable wird erstellt
		var sovid3 = new AR.VideoDrawable("assets/Igel_Tembrock_Guenter_0606.mp4", 0.2, {
			offsetX: -0.2,
			offsetY: -0.12,
			isTransparent: true
		});
        World.sovid3 = sovid3;
		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var soCButton = this.createWwwLinkButton("http://de.wikipedia.org/wiki/Igel", 0.2, {
			offsetX: -0.35,
			offsetY: -0.3,
			zOrder: 1
		});
		sovid3.play(-1);
		sovid3.pause();

		var SoC = new AR.Trackable2DObject(this.tracker, "landschaft_streuobst_igel", {
			drawables: {
				cam: [sovid3, soCButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				sovid3.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				sovid3.pause();
			}
		});
		
		//Dreizehntes Video Landschaft Streuobst Kleiber
		// Ein transparentes Video-Drawable wird erstellt
		var sovid4 = new AR.VideoDrawable("assets/Kleiber_Tembrock_Guenther_0696.mp4", 0.2, {
			offsetX: -0.2,
			offsetY: -0.12,
			isTransparent: true
		});
        World.sovid4 = sovid4;
		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var soDButton = this.createWwwLinkButton("http://de.wikipedia.org/wiki/Kleiber_(Art)", 0.2, {
			offsetX: -0.2,
			offsetY: 0.3,
			zOrder: 1
		});
		sovid4.play(-1);
		sovid4.pause();

		var SoD = new AR.Trackable2DObject(this.tracker, "landschaft_streuobst_kleiber", {
			drawables: {
				cam: [sovid4, soDButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				sovid4.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				sovid4.pause();
			}
		});
		
		//Vierzehntes Video Landschaft Streuobst Siebenschlaefer
		// Ein transparentes Video-Drawable wird erstellt
		var sovid5 = new AR.VideoDrawable("assets/Siebenschlaefer_Tembrock_Guenther_1258.mp4", 0.2, {
			offsetX: -0.2,
			offsetY: -0.12,
			isTransparent: true
		});
        World.sovid5 = sovid5;
		// Der WWW-Link Button wird erstellt
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var soEButton = this.createWwwLinkButton("http://de.wikipedia.org/wiki/Siebenschl%C3%A4fer", 0.2, {
			offsetX: -0.15,
			offsetY: -0.45,
			zOrder: 1
		});
		sovid5.play(-1);
		sovid5.pause();
		//Alles wird zusammengesetzt und die Bedingungen onenter/onexit werden gesetzt
		var SoE = new AR.Trackable2DObject(this.tracker, "landschaft_streuobst_siebenschlaefer", {
			drawables: {
				cam: [sovid5, soEButton]
			},
			onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
				sovid5.resume();
			},
			onExitFieldOfVision: function onExitFieldOfVisionFn() {
				sovid5.pause();
			}
		});


		//Ackerwildkraut-Memo-Spiel (Awm)
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");

		var imgAwm = new AR.ImageResource("assets/AckerwildkrautMemoScreenshot.png");
		var overlayAwm = new AR.ImageDrawable(imgAwm, 1, {
			offsetX: -0.15,
			offsetY: 0
		});
		var pageAwmButton = this.createWwwLinkButton("http://fb09-pasig.umwelt.uni-giessen.de/sbapp/app/assets/Quiz/Ackerwildkrautmemo.html", 0.2, {
			offsetX: 0,
			offsetY: -0.45,
			zOrder: 1
		});
		var pageAwm = new AR.Trackable2DObject(this.tracker, "landschaft_lebensraum_ackerwildkraut_memo", {
			drawables: {
				cam: [overlayAwm, pageAwmButton]
			}
		});
		

		//Startpunkt Rundweg 2 -Hinweis auf Geocache - Elemente einer Kulturlandschaft (Eek)
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");

		var imgEek = new AR.ImageResource("assets/StartGeocache.jpg");
		var overlayEek = new AR.ImageDrawable(imgEek, 1, {
			offsetX: -0.15,
			offsetY: 0
		});

		var pageEekButton = this.createWwwLinkButton("http://www.geocaching.com/geocache/GC5BD0G_studienlandschaft-schwingbachtal?guid=f6917d82-379d-413a-a52d-9874808d2cac", 0.4, {
			offsetX: -0.25,
			offsetY: -0.45,
			zOrder: 1
		});

		var pageEek = new AR.Trackable2DObject(this.tracker, "elemente_kulturlandschaft", {
			drawables: {
				cam: [overlayEek, pageEekButton]
			}
		});


		//Tipping Bucket - Wie funktioniert eine Regenkippwaage
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var imgTip = new AR.ImageResource("assets/Tipping2.jpg");
		var overlayTip = new AR.ImageDrawable(imgTip, 1, {
			offsetX: 0,
			offsetY: 0
		});
		var pageTipButton = this.createWwwLinkButton("http://de.wikipedia.org/wiki/Niederschlagsmesser#Digitale_Niederschlagsmesser", 0.2, {
			offsetX: 0.4,
			offsetY: -0.55,
			zOrder: 1
		});
		var pageTip = new AR.Trackable2DObject(this.tracker, "niederschlagsmesser", {
			drawables: {
				cam: [overlayTip, pageTipButton]
			}
		});


		//Klimastation RHB - QR-Code - Deckel (Rqr)
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var imgRqr = new AR.ImageResource("assets/Daten-Live.jpg");
		var overlayRqr = new AR.ImageDrawable(imgRqr, 1, {
			offsetX: -0.15,
			offsetY: 0
		});
		var pageRqrButton = this.createWwwLinkButton("http://fb09-pasig.umwelt.uni-giessen.de:8081/html/kiosk.html", 0.4, {
			offsetX: -0.15,
			offsetY: -0.4,
			zOrder: 1
		});
		var pageRqr = new AR.Trackable2DObject(this.tracker, "qr_code_klimastation_rhb", {
			drawables: {
				cam: [overlayRqr, pageRqrButton]
			}
		});
		

		//Insektenhotel Eselspfad (InE)
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");

		var imgIne = new AR.ImageResource("assets/Insektenhotel.jpg");
		var overlayIne = new AR.ImageDrawable(imgIne, 1, {
			offsetX: -0.15,
			offsetY: 0
		});
		var pageIneButton = this.createWwwLinkButton("http://fb09-pasig.umwelt.uni-giessen.de/sbapp/app/assets/insektenhotel_links.html", 0.3, {
			offsetX: -0.15,
			offsetY: -0.4,
			zOrder: 1
		});
		var pageIne = new AR.Trackable2DObject(this.tracker, "eselspfad_insektenhotel", {
			drawables: {
				cam: [overlayIne, pageIneButton]
			}
		});


		//Bodenerosion (Ber)
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");

		var imgBer = new AR.ImageResource("assets/Links_Bodenerosion.jpg");
		var overlayBer = new AR.ImageDrawable(imgBer, 1.5, {
			offsetX: -0.15,
			offsetY: 0
		});

		var pageBerButton = this.createWwwLinkButton("http://fb09-pasig.umwelt.uni-giessen.de/sbapp/app/assets/bodenerosion_links.html", 0.4, {
			offsetX: -0.1,
			offsetY: -0.65,
			zOrder: 1
		});

		var pageBer = new AR.Trackable2DObject(this.tracker, "boden_erosion", {
			drawables: {
				cam: [overlayBer, pageBerButton]
			}
		});


		//Abflussrechner - Bild (Abr)		
		this.imgButton = new AR.ImageResource("assets/wwwLink.png");
		var imgAbr = new AR.ImageResource("assets/Abflussrechner.jpg");
		var overlayAbr = new AR.ImageDrawable(imgAbr, 0.7, {
			offsetX: -0.15,
			offsetY: 0
		});
		var pageAbrButton = this.createWwwLinkButton("http://fb09-pasig.umwelt.uni-giessen.de/sbapp/app/assets/BerechnungAbflussmenge.html", 0.4, {
			offsetX: -0.25,
			offsetY: -0.25,
			zOrder: 1
		});

		var pageAbr = new AR.Trackable2DObject(this.tracker, "wasser_tropfen_abflussrechner", {
			drawables: {
				cam: [overlayAbr, pageAbrButton]
			}
		});

		//Wetter Widget Live-Daten (Wwi)
		var imgWwi = new AR.ImageResource("assets/imageWeatherWidget.png");
		var overlayWwi = new AR.ImageDrawable(imgWwi, 0.25, {
			offsetX: 0.12,
			offsetY: -0.01
		});
		var pageWwiButton = this.createWwwLinkButton("http://fb09-pasig.umwelt.uni-giessen.de:8081/html/kiosk.html", 0.15, {
			offsetX: 0.2,
			offsetY: -0.65,
			zOrder: 1
		});
		var weatherSpecialWidget = new AR.HtmlDrawable({
			uri: "assets/weather_special.html"
		}, 1.0, {
			viewportWidth: 320,
			viewportHeight: 320,
			backgroundColor: "#FFFFFF",
			offsetX: +0.68,
			offsetY: 0.45,
			zOrder: 0,
			scale: 1,
			opacity: 0.8,
			horizontalAnchor: AR.CONST.HORIZONTAL_ANCHOR.RIGHT,
			verticalAnchor: AR.CONST.VERTICAL_ANCHOR.TOP,
			clickThroughEnabled: true,
			allowDocumentLocationChanges: false,
			onDocumentLocationChanged: function onDocumentLocationChangedFn(uri) {
				AR.context.openInBrowser(uri);
			}
		});
		var pageWwi = new AR.Trackable2DObject(this.tracker, "IMG_20140807_110544-008", {
			drawables: {
				cam: [overlayWwi, pageWwiButton, weatherSpecialWidget]
			}
		});


		//Sensoren Wetterstation Live-Daten (Swi)
		var imgSwi = new AR.ImageResource("assets/imageWeatherWidget.png");
		var overlaySwi = new AR.ImageDrawable(imgSwi, 0.25, {
			offsetX: 0.12,
			offsetY: -0.01
		});
		var pageSwiButton = this.createWwwLinkButton("http://fb09-pasig.umwelt.uni-giessen.de/sbapp/app/assets/sensoren_erklaerung.html", 0.15, {
			offsetX: -0.55,
			offsetY: -0.3,
			zOrder: 1
		});
		var weatherSensorsWidget = new AR.HtmlDrawable({
			uri: "assets/sensoren_station.html"
		}, 0.85, {
			viewportWidth: 320,
			viewportHeight: 320,
			backgroundColor: "#FFFFFF",
			offsetX: +0.36,
			offsetY: 0.45,
			zOrder: 0,
			scale: 1.1,
			opacity: 0.7,
			horizontalAnchor: AR.CONST.HORIZONTAL_ANCHOR.RIGHT,
			verticalAnchor: AR.CONST.VERTICAL_ANCHOR.TOP,
			clickThroughEnabled: true,
			allowDocumentLocationChanges: false,
			onDocumentLocationChanged: function onDocumentLocationChangedFn(uri) {
				AR.context.openInBrowser(uri);
			}
		});
		var pageSwi = new AR.Trackable2DObject(this.tracker, "tafel_wind_weht_rhb-001", {
			drawables: {
				cam: [overlaySwi, pageSwiButton, weatherSensorsWidget]
			}
		});
	},

	//WWW-Button wird durch Hilfsfunktion erstellt
	createWwwLinkButton: function createWwwLinkButtonFn(url, size, options) {
		options.onClick = function() {
			AR.context.openInBrowser(url);
		};
		return new AR.ImageDrawable(this.imgButton, size, options);
	},

	//POI
	//  Letzte bekannte Position des Benutzers, die ueber userLocation.latitude, userLocation.longitude, userLocation.altitude zugaenglich war.
	userLocation: null,

	// Daten werden nur einmal vom Server angefordert.
	isRequestingData: false,

	// false=Daten wurden noch nicht abgerufen/true=Daten wurden abgerufen
	initiallyLoadedData: false,

	// verschiedene POI-Marker-Eigenschaften
	markerDrawable_idle: null,
	markerDrawable_selected: null,
	markerDrawable_directionIndicator: null,

	// Liste der GeoObjekte, die derzeit in der Welt angezeigt werden
	markerList: [],

	// Der zuletzt ausgewaehlte Marker
	currentMarker: null,

	locationUpdateCounter: 0,
	updatePlacemarkDistancesEveryXLocationUpdates: 10,

	clickedRadar: function clickedRadarFn(){
		AR.context.openInBrowser('http://fb09-pasig.umwelt.uni-giessen.de/sbapp/app/assets/Karte/index.html');
	},
	// Ruft die Einbindung neuer POI-Daten auf
	loadPoisFromJsonData: function loadPoisFromJsonDataFn(poiData) {
	
		// Zeigt Radar & setzt einen Click-Listener
		PoiRadar.show();
		$('#radarContainer').unbind('click');
		$("#radarContainer").click(PoiRadar.clickedRadar);

		// Leert die Liste der sichtbaren Marker
		World.markerList = [];

		// laedt die Marker-Eigenschaften
		World.markerDrawable_idle = new AR.ImageResource("assets/marker_idle.png");
		World.markerDrawable_selected = new AR.ImageResource("assets/marker_selected.png");
		World.markerDrawable_directionIndicator = new AR.ImageResource("assets/indi.png");

		// Erstellt eine Schleife durch die POI-Informationen-JSON und erstellt ein AR.GeoObject fuer jeden POI
		for (var currentPlaceNr = 0; currentPlaceNr < poiData.length; currentPlaceNr++) {
			var singlePoi = {
				"id": poiData[currentPlaceNr].id,
				"latitude": parseFloat(poiData[currentPlaceNr].lat),
				"longitude": parseFloat(poiData[currentPlaceNr].lon),
				"title": poiData[currentPlaceNr].name,
				"description": poiData[currentPlaceNr].comment,
				"height":parseFloat(poiData[currentPlaceNr].height),
				"web": poiData[currentPlaceNr].web,
				"icon": poiData[currentPlaceNr].icon,
				"category": poiData[currentPlaceNr].cat,
                "video": poiData[currentPlaceNr].video
			};

			World.markerList.push(new Marker(singlePoi));
		}

		// Update der Entfernung von allen POI's zum User
		World.updateDistanceToUserValues();

		// Setzt die Entfernung des Sliders auf 100%
		$("#panel-distance-range").val(100);
		$("#panel-distance-range").slider("refresh");
	},

	// Setzt und aktualisiert die Entfernung von allen Markern - so stehen sie schneller zur Verfuegung als z.B. Aufrufe wie die distanceToUser() Methode
	updateDistanceToUserValues: function updateDistanceToUserValuesFn() {
		for (var i = 0; i < World.markerList.length; i++) {
			World.markerList[i].distanceToUser = World.markerList[i].markerObject.locations[0].distanceToUser();
		}
	},

	// Standort-Updates werden jedes Mal abgegeben, wenn "architectView.setLocation ()" in der nativen Umgebung aufgerufen wird
	locationChanged: function locationChangedFn(lat, lon, alt, acc) {
		// Speichert den aktuellen Standort des Benutzers in World.userLocation - so ist immer bekannt, wo der Benutzer sich befindet
		World.userLocation = {
			'latitude': lat,
			'longitude': lon,
			'altitude': alt,
			'accuracy': acc
		};

		// Fordert Daten an, wenn sie nicht bereits vorhanden sind
		if (!World.initiallyLoadedData) {
			World.requestDataFromServer(lat, lon);
			World.initiallyLoadedData = true;
		} else if (World.locationUpdateCounter === 0) {
			// Updatet Entfernungsinformationen
			World.updateDistanceToUserValues();
		}

		// Helfer, welcher definiert ist, bei jedem now and then Entfernungsinformationen upzudaten 
		World.locationUpdateCounter = (++World.locationUpdateCounter % World.updatePlacemarkDistancesEveryXLocationUpdates);
	},

	// Wenn der Benutzer den Marker im Kamera-Modus drueckt, wird folgendes ausgeloest:
	onMarkerSelected: function onMarkerSelectedFn(marker) {
		World.currentMarker = marker;

		// Update der Informationen fuer die POI-Details
		$("#poi-detail-title").html(marker.poiData.title);
		$("#poi-detail-description").html(marker.poiData.description);
		if(marker.poiData.web!=null)$("#poi-detail-web").html('<a href='+'"'+"javascript:AR.context.openInBrowser(" +"'"+ marker.poiData.web +"'"+ ", true)"+'"'+'>Weitere Informationen zum Thema<a/>');
		else $("#poi-detail-web").html('');
		if(marker.poiData.icon!=null)$("#poi-detail-icon").html("<img src='" + marker.poiData.icon + "'/>");
		else $("#poi-detail-icon").html('');
		var distanceToUserValue = (marker.distanceToUser > 999) ? ((marker.distanceToUser / 1000).toFixed(2) + " km") : (Math.round(marker.distanceToUser) + " m");
		$("#poi-detail-distance").html(distanceToUserValue);
		// Zeigt auf der Unterseite Panel-Poidetail
		$("#panel-poidetail").panel("open", 123);
		
		$( ".ui-panel-dismiss" ).unbind("mousedown");

		$("#panel-poidetail").on("panelbeforeclose", function(event, ui) {
            if (World.currentMarker.poiData.video) {
                World[World.currentMarker.poiData.video].pause()
            }
			World.currentMarker.setDeselected(World.currentMarker);
		});
        if (marker.poiData.video) {
            var video = World[marker.poiData.video]
            /*
            var text =  marker.poiData.video + ': ' + video.getUri();
            $("#poi-detail-description").html(text); 
            */
            video.resume();
        }
	},

	// Click-Funktion, wenn kein Objekt getroffen wurde
	onScreenClick: function onScreenClickFn() {
	},

	// Ausgabe der Entfernung eines Markers vom Nutzer in Metern mit 1,1 multipliziert
	getMaxDistance: function getMaxDistanceFn() {

		// Sortiert Marker der Entfernung nach absteigend
		World.markerList.sort(World.sortByDistanceSortingDescending);
		var maxDistanceMeters = World.markerList[0].distanceToUser;
		return maxDistanceMeters * 1.1;
	},

	// Updatet die angezeigten Werte im Range-Panel
	updateRangeValues: function updateRangeValuesFn() {

		// Fragt den aktuellen Slider-Parameter ab zwischen 0 und 100
		var slider_value = $("#panel-distance-range").val();
		// Maximale Entfernung entsprechend zu der Entfernung von allen sichtbaren Markern
		var maxRangeMeters = Math.round(World.getMaxDistance() * (slider_value / 100));
		// Entfernung in Metern/Kilometern
		var maxRangeValue = (maxRangeMeters > 999) ? ((maxRangeMeters / 1000).toFixed(2) + " km") : (Math.round(maxRangeMeters) + " m");
		// Anzahl der Marker in der maximalen Reichweite
		var placesInRange = World.getNumberOfVisiblePlacesInRange(maxRangeMeters);
		// Updatet Label entsprechend
		$("#panel-distance-value").html(maxRangeValue);
		$("#panel-distance-places").html((placesInRange != 1) ? (placesInRange + " Orte ") : (placesInRange + " Ort"));
		// Updatet den beschnittenen Abstand, so dass nur Marker im angegebenen Bereich angezeigt werden
		AR.context.scene.cullingDistance = Math.max(maxRangeMeters, 1);
		// Updatet ebenfalls die maximale Reichweite auf dem Radar
		PoiRadar.setMaxDistance(Math.max(maxRangeMeters, 1));
	},

	// Gibt die Anzahl der Marker mit gleichem oder niedrigerem Abstand als der angegebene Bereich zurueck
	getNumberOfVisiblePlacesInRange: function getNumberOfVisiblePlacesInRangeFn(maxRangeMeters) {
		// Sortiert die Marker der Entfernung nach
		World.markerList.sort(World.sortByDistanceSorting);
		// Fuehrt eine Schleife durch die Liste der Marker und bricht an dem Marker ab, der nicht mehr in Reichweite ist
		for (var i = 0; i < World.markerList.length; i++) {
			if (World.markerList[i].distanceToUser > maxRangeMeters) {
				return i;
			}
		};
		return World.markerList.length;
	},

	handlePanelMovements: function handlePanelMovementsFn() {

		$("#panel-distance").on("panelclose", function(event, ui) {
			$("#radarContainer").addClass("radarContainer_left");
			$("#radarContainer").removeClass("radarContainer_right");
			PoiRadar.updatePosition();
		});

		$("#panel-distance").on("panelopen", function(event, ui) {
			$("#radarContainer").removeClass("radarContainer_left");
			$("#radarContainer").addClass("radarContainer_right");
			PoiRadar.updatePosition();
		});
	},

	// Zeigt den Reichweiten-Slider
	showRange: function showRangeFn() {
		if (World.markerList.length > 0) {

			// Updatet die Label bei Veraenderung der Reichweite
			$('#panel-distance-range').change(function() {
				World.updateRangeValues();
			});

			World.updateRangeValues();
			World.handlePanelMovements();

			// Oeffnet das Reichweiten-Panel
			$("#panel-distance").trigger("updatelayout");
			$("#panel-distance").panel("open", 1234);
		} else {
			
		}
	},

	// Fragt POI-Daten ab
	requestDataFromServer: function requestDataFromServerFn(lat, lon) {
		
		// Setzt die Helfer-Variable, um eine Abfrage der Marker waehrend des Ladens zu verhindern
		World.isRequestingData = true;
		// Die Server-Url zum JSON Server
		var jqxhr = $.getJSON(POIURL, function(data) {
			World.loadPoisFromJsonData(data);
		})
			.error(function(err) {
				World.isRequestingData = false;
			})
			.complete(function() {
				World.isRequestingData = false;
			});
	},
	// Hilfsfunktion, um die Marker nach ihrer Entfernung zu sortieren
	sortByDistanceSorting: function(a, b) {
		return a.distanceToUser - b.distanceToUser;
	},
	// Hilfsfunktion, um die Marker absteigend nach ihrer Entfernung zu sortieren
	sortByDistanceSortingDescending: function(a, b) {
		return b.distanceToUser - a.distanceToUser;
	},
	worldLoaded: function worldLoadedFn() {
		//Transparentes Einblendungsfenster zum Start der Schwingbachtal-World
		var cssDivInstructions = " style='display: table-cell;vertical-align: middle; text-align: right; width: 80%; padding-top: 40%; padding-right: 45px;'";
		var cssDivTafel = " style='display: table-cell;vertical-align: middle; text-align: left; padding-right: 15px; padding-top: 40%; width: 38px'";
		var cssDivQR = " style='display: table-cell;vertical-align: middle; text-align: left; padding-top: 40%; padding-right: 15px;'";
		document.getElementById('loadingMessage').innerHTML =
			"<div" + cssDivInstructions + ">Suchen Sie einen blau markierten Wegpunkt auf und scannen Sie eine Schautafel oder einen QR-Code:</div>" +
			"<div" + cssDivTafel + "><img src='assets/schautafel_01_klein.jpg'></img></div>" +
			"<div" + cssDivQR + "><img src='assets/qrcode_01_klein.png'></img></div>";

		// Entfernt das transparente Einblendungsfenster 12 Sekunden nach Start der World
		setTimeout(function() {
			var e = document.getElementById('loadingMessage');
			e.parentElement.removeChild(e);
		}, 12000);
	},

};

World.init();
AR.context.onLocationChanged = World.locationChanged;
AR.context.onScreenClick = World.onScreenClick;
