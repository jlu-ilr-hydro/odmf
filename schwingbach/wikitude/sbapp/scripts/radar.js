	var PoiRadar = {

		hide: function hideFn() {
			AR.radar.enabled = false;
		},

		show: function initFn() {

			// Hier wird der Radarcontainer definiert. Aufgerufen wird der Radarcontainer in der html-Datei
			AR.radar.container = document.getElementById("radarContainer");

			// Definiert das Hintergrund Bild vom Radar
			AR.radar.background = new AR.ImageResource("assets/radar_bg.png");

			// Definiert den Nord-Indikator vom Radar
			AR.radar.northIndicator.image = new AR.ImageResource("assets/radar_north.png");

			// Zentriert Nord-Indikator und Punkte im Radar, Mitte des Radars ist in genau in der Mitte des Hintergrundes (50% X und 50% Y Achse -> 0.5 centerX/centerY)
			AR.radar.centerX = 0.5;
			AR.radar.centerY = 0.5;

			AR.radar.radius = 0.3;
			AR.radar.northIndicator.radius = 0.0;

			AR.radar.enabled = true;
		},

		updatePosition: function updatePositionFn() {
			if (AR.radar.enabled) {
				AR.radar.notifyUpdateRadarPosition();
			}
		},

		clickedRadar: function clickedRadarFn(){
			AR.context.openInBrowser('http://fb09-pasig.umwelt.uni-giessen.de/sbapp/app/assets/Karte/index.html');
		},

		setMaxDistance: function setMaxDistanceFn(maxDistanceMeters) {
			AR.radar.maxDistance = maxDistanceMeters;
		}
	};