
/**
 * creates function ready to use as signal-listener
 * @param gaReportingInfo the tracker information
 * @param projectInfo overall studio projectJSON
 * @param signalTypes list of signalTypes that are fired
 * @returns {Function}
 */
var createGoogleAnalyticsSignalListener = function(trackerId, projectInfo, signalTypes, ga) {

    if (!trackerId || trackerId.length<5) {
        throw "GOOGLE ANALYTICS - Invalid reporting info passed (Mandatory to extract googleAnalytics tracker infos like trackerId)";
    }

    if (!projectInfo || !projectInfo.tcId) {
        throw "GOOGLE ANALYTICS - Invalid projectInfo passed (Mandatory to read tcId etc.)";
    }

    if (!signalTypes) {
        throw "GOOGLE ANALYTICS - Invalid signalTypes passed (Mandatory to distinguish action types)";
    }

    if (typeof ga === 'undefined') {
        throw "GOOGLE ANALYTICS - 'ga' is not available > missing Google Analytics library?";
    }

    // the project's tcId, used as event category
    var tcId = projectInfo.tcId;

    // need to have a unique id to be able to report to multiple trackers > Use positive String hash as a quick approach
    var trackerName = "tracker"+ Math.abs(trackerId.hashCode());

    // ensure to also mention trackerName whenever a page or event track command is executed
    var trackerSendCommand = trackerName + ".send";

    ga('create', trackerId, 'auto', trackerName);
    ga('set', 'checkProtocolTask', null); // Disables file protocol checking.
    ga(trackerSendCommand, 'pageview');

    return function (signalType, component, param) {

        if (!signalType || !component) {
            // Invalid component passed over
            return;
        }

        switch(signalType) {
            case signalTypes.TARGET_SCANNED:
            case signalTypes.TARGET_LOST:
                // component = targetName, param = undefined
                // Event not tracked yet
                break;

            case signalTypes.TARGET_AUGMENTED:
                // component = targetName, param = augmentationList
                // Event not tracked yet
                break;

            case signalTypes.LOADED:
            case signalTypes.CLICKED:
            case signalTypes.DESTROYED:
            case signalTypes.ERROR:
            case signalTypes.PLAYED:
            case signalTypes.PLAYED_FULLSCREEN:
            case signalTypes.RESUMED:
            case signalTypes.PAUSED:
            case signalTypes.CREATED:
                if (!component.targetId || !component.id || !tcId) {
                    // Missing 'tcId', 'targetId' or 'id' attribute in component.
                    break;
                }

                // Track it like : trackEvent ( {tcId} _ {targetId} - {augmentationId} - CLICKED - 1)
                var category = tcId + '_' + component.targetId;
                var action = component.id;
                var label =  signalType;
                var value = 1;

                ga(trackerSendCommand, 'event', category, action, label, value);
                break;

            default:
                // unknown signal type
                break;
        }
    };
};

/* fast way to display system in console */
var Logger = {
    enabled : false,
    debug: function(value) {
        if (this.enabled) { console.debug(value); }
    },
    error: function(value) {
        if (this.enabled) { console.error(value); }
    },
    info: function(value) {
        if (this.enabled) { console.info(value); }
    },
    warn: function(value) {
        if (this.enabled) { console.warn(value); }
    }
};

function killFirefoxSafaryCache() {
    try {
        if (window.unload) {
            window.unload(function(){});
        }
    }catch(err) {
        Logger.error('not able to kill firefox/safari no-store trick');
    }
}

String.prototype.hashCode = function() {
    var hash = 0, i, chr, len;
    if (this.length === 0) return hash;
    for (i = 0, len = this.length; i < len; i++) {
        chr   = this.charCodeAt(i);
        hash  = ((hash << 5) - hash) + chr;
        hash |= 0; // Convert to 32bit integer
    }
    return hash;
};

function showError(title, message, onClickFn) {

    $('#errorTitle').html(title);
    $('#errorMsg').html(message);

    $("#loading").hide();
    $("#error").show();

    if (!onClickFn) {
        $("#errorbtns").hide();
    } else {
        $("#errorBtn").unbind( "click" );
        $("#errorBtn").click(onClickFn);
        $("#errorbtns").show();
    }
};

function hideError() {
    $("#error").hide();
};

/**
 *
 * @returns {boolean} true if currentSDK version is at least 5.1.4
 */
function isSDKVersionSupported() {
    var currentSDKVersion = parseVersionString(AR.context.versionNumber);
    var minSDKVersion = parseVersionString("6.1.0");

    return minSDKVersion.major < currentSDKVersion.major ||
        minSDKVersion.major == currentSDKVersion.major && minSDKVersion.minor < currentSDKVersion.minor ||
        minSDKVersion.major == currentSDKVersion.major && minSDKVersion.minor == currentSDKVersion.minor && minSDKVersion.patch <= currentSDKVersion.patch;
}

function getUrlParameter(sParam) {
    var sPageURL = decodeURIComponent(window.location.search.substring(1)),
        sURLVariables = sPageURL.split('&'),
        sParameterName,
        i;

    for (i = 0; i < sURLVariables.length; i++) {
        sParameterName = sURLVariables[i].split('=');

        if (sParameterName[0] === sParam) {
            return sParameterName[1] === undefined ? true : sParameterName[1];
        }
    }
}

// helper method to get the maj/min/pat version out of given string
function parseVersionString (str) {
    if (typeof(str) != 'string') { return false; }
    var x = str.split('.');
    // parse from string or default to 0 if can't parse
    var maj = parseInt(x[0]) || 0;
    var min = parseInt(x[1]) || 0;
    var pat = parseInt(x[2]) || 0;
    return {
        major: maj,
        minor: min,
        patch: pat
    }
}

function loadJsonFromUrl(url) {
    var deferred = $.Deferred();

    try {
        var xobj = new XMLHttpRequest();
        xobj.overrideMimeType("application/json");
        xobj.open('GET', url, true);
        xobj.onreadystatechange = function () {
            if (xobj.readyState == 4) {
                if (xobj.status == "200") {
                    try {
                        deferred.resolve(JSON.parse(xobj.responseText));
                    } catch(err) {
                        deferred.reject();
                    }
                } else {
                    deferred.reject();
                }
            }
        };
        xobj.send(null);
    } catch (err) {
        deferred.reject();
    }

    return deferred.promise();
}

/**
 * converts an rgba() string to an ARchitect-understandable color code
 *
 * @param color
 *            the input rgba() string
 * @return the ARchitect # color string
 */
var convertRGBA = function (rgbaString) {
    var indexLeft = rgbaString.indexOf('(') + 1;
    var indexRight = rgbaString.indexOf(')');

    var colorArray = rgbaString.substring(indexLeft, indexRight).replace(/ /g, '').split(',');
    var color = {
        r: parseInt(colorArray[0]),
        g: parseInt(colorArray[1]),
        b: parseInt(colorArray[2]),
        a: parseFloat(colorArray[3])
    };

    var hash = "#";
    hash += convertTo2DigitHex(color.r);
    hash += convertTo2DigitHex(color.g);
    hash += convertTo2DigitHex(color.b);
    hash += convertTo2DigitHex(Math.floor(color.a * 255));
    return hash;
};

/**
 * converts a color into an ARchitect-understandable color code.
 *
 * @param color
 *            the input color, as an object with properties r, g, b and
 *            a
 * @return the ARchitect # color string
 */
var convertColor = function (color) {
    var hash = "#";
    hash += convertTo2DigitHex(color.r);
    hash += convertTo2DigitHex(color.g);
    hash += convertTo2DigitHex(color.b);
    hash += convertTo2DigitHex(Math.floor(color.a * 255));
    return hash;
};

/**
 * converts a color into a browser-understandable rgba(x,y,z,w) value. This is used in Labels and HTMLDrawables.
 *
 * @param color
 *            the input color, as an object with properties r, g, b and
 *            a
 * @return the RGBA color string
 */
var convertToRgbaColor = function (color) {
    var rgba = "rgba(";
    rgba += color.r + ",";
    rgba += color.g + ",";
    rgba += color.b + ",";
    rgba += color.a + ")";
    return rgba;
};

/**
 * converts a single decimal value to a hex value with guaranteed 2
 * digits. If the hex value would only be 1 digit long, "0" is added to
 * the front
 *
 * @param value
 *            the decimal value to be converted
 * @return the HEX-string
 */
var convertTo2DigitHex = function (value) {
    var result = value.toString(16);
    return result.length == 2 ? result : "0" + result;
};

var getBestMatchingWtcFile = function(wtcFiles) {

    wtcFiles = wtcFiles || [];

    var version = parseVersionString(AR.context.versionNumber);
    var wtcVersionToUse = [];

    // list 'wtcVersionToUse' in preferred order, e.g. ["5.0", "4.1"] means: use version 5.0 if present, but 4.1 is also fine
    switch (version.major) {
        case 6:
            wtcVersionToUse = ["6.0", "5.3", "5.2", "5.1"];
            break;
        case 5:
            wtcVersionToUse = ["5.3", "5.2", "5.1"];
            break;
        case 4:
            return null;

        default:
            wtcVersionToUse = ["7.0", "6.3", "6.2", "6.1"];
            break;
    }

    // sort by version, descending (e.g. "5.0", "4.1", "4.0")
    wtcFiles.sort(function(a, b) {
      if (a.version>b.version) {
          return -1
      }
      if (b.version>a.version) {
          return 1;
      }
      return 0;
    });

    var matchingWtcFiles = $.grep( wtcFiles, function( n, i ) {
        return wtcVersionToUse.indexOf(n.version) > -1;
    });
    if (matchingWtcFiles.length < 1) {
        return null;
    } else {
        return matchingWtcFiles[0];
    }
};

var Signal = signals.Signal;

/**
 * sets up Analytics so that one can track any kind of signal fired
 * @param list of tracker-configurations
 */
var setupReporting = function(projectInfo, signal) {

    if (!projectInfo || !signal || !signal.TYPE) {
        throw "ANALYTICS - signal and projectInfo must be undefined";
    }

    if (!projectInfo.settings || !projectInfo.settings.tracker) {
        Logger.debug("ANALYTICS - No analytics providers listed");
        return;
    }

    var reportingConfigs = projectInfo.settings.tracker;

    if (reportingConfigs && reportingConfigs["GoogleAnalytics"]) {
        try {
            signal.add(createGoogleAnalyticsSignalListener(reportingConfigs["GoogleAnalytics"], projectInfo, signal.TYPE, ga));
            Logger.info('REPORTING - Added GOOGLE ANALYTICS');
        } catch (err) {
            Logger.error(err);
            Logger.error('REPORTING - ERROR while setting up GOOGLE ANALYTICS environment');
        }
    } else {
        Logger.debug('REPORTING - Not defined');
    }
};


/**
 * Creates an AR.ClientTracker out of passed projectInfo. Note that the created ClientTracker has enabled flag set to FALSE. Set enabled to true (or call arTracker.start() ) to activate it
 * @param projectInfo
 * @returns {undefined}
 */
var createClientTracker = function(projectInfo, onTrackerLoadedFn) {

    if (!projectInfo) {
        throw "ClientTracker - Missing mandatory field projectInfo";
    }

    if (!projectInfo.wtcFiles || !projectInfo.wtcFiles.length) {
        throw "ClientTracker - No WTC files listed in projectInfo";
    }

    var arTracker = undefined;
    // grep best matching WTC file for currently used SDK from projectInfo
    var wtcFile = getBestMatchingWtcFile(projectInfo.wtcFiles);

    if (!wtcFile) {
        throw "ClientTracker - required wtc NOT delivered, was searching for version but only found ' + projectInfo.wtcFiles";
    } else {
        var tcResource = new AR.TargetCollectionResource(wtcFile.url);
        arTracker = new AR.ImageTracker(tcResource, { "onTargetsLoaded": onTrackerLoadedFn, "enabled": false });
        arTracker.onError = function(err) {
            Logger.error('ClientTracker - ERROR occurred: ' + err);
            World.projectConverter.arTracker = null;
            showError($.i18n._("connection_error"), $.i18n._("connection_error_descr"), World.restart );
            Logger.error('Check availability of file ' + wtcFile.url);
        };
        arTracker.isCloud = false;
    }
    arTracker.start = function() {
        this.enabled = true;
    };
    arTracker.restart = function() {
        this.enabled = true;
    };
    arTracker.stop = function() {
        this.enabled = false;
    };

    return arTracker;
};

var createCloudTracker = function(projectInfo, onTrackerLoadedFn) {

    if (!projectInfo) {
        throw "missing mandatory field 'projectInfo'";
    }

    if (!projectInfo.clientToken || !projectInfo.tcId) {
        throw "missing mandatory field 'clientToken' or 'tcId'";
    }

    var cloudRecognitionService = new AR.CloudRecognitionService(projectInfo.clientToken, projectInfo.tcId, { "onLoaded": onTrackerLoadedFn });
    new AR.CloudTracker(cloudRecognitionService);
    cloudRecognitionService.isCloud = true;
    cloudRecognitionService.recoCounter = 0;

    // start coudTracker
    cloudRecognitionService.start = function(recoDelay) {

        recoDelay = recoDelay || 2000;

        Logger.info('Tracker - run serverside reco');
        cloudRecognitionService.isTracking = true;
        cloudRecognitionService.sendServerRequest = function() { if(cloudRecognitionService.isTracking && !cloudRecognitionService.isRecognized) cloudRecognitionService.recognize(cloudRecognitionService.onServerResponseArrives, cloudRecognitionService.onServerErrorOccurs); };

        cloudRecognitionService.onServerResponseArrives = function(recognized, response) {
            this.recoCounter++;

            if (recognized) {
                Logger.info('CLOUDTRACKER (scan #' + this.recoCounter + ' - POSITIVE '  + response.targetInfo.name);
                projectInfo.cloudTargetInfo = response.targetInfo;
                if (!response.studio) {
                    Logger.error('CLOUDTRACKER (scan #' + this.recoCounter + ') - No studio object passed');
                    /* if (response.metadata.augmentationUri) {
                        projectInfo.cloudTargetInfo.augmentationUri = response.metadata.augmentationUri;
                    }*/
                } else {
                    projectInfo.cloudTargetInfo.augmentationUri = response.studio.uri;
                }
            } else {
                Logger.info('CLOUDTRACKER (scan #' + this.recoCounter + ') - NEGATIVE');
                this.start(recoDelay);
            }
        };

        cloudRecognitionService.onServerErrorOccurs = function(code, errorObject) {
            Logger.error('CLOUDTRACKER (scan #' + this.recoCounter + ') - ERROR code #'+code);
            // give it another try, but increase delay to 5s so server can have a break
            this.restart(5000);
        };

        setTimeout(cloudRecognitionService.sendServerRequest , recoDelay);
    };

    // stop cloudTracker
    cloudRecognitionService.stop = function() {
        Logger.info('Tracker - stopped (cloud)');
        clearTimeout(cloudRecognitionService.sendServerRequest);
        cloudRecognitionService.isTracking = false;
    };

    // restart cloudTracker
    cloudRecognitionService.restart = function(recoDelay) {
        cloudRecognitionService.stop();
        cloudRecognitionService.start(recoDelay);
    };

    return cloudRecognitionService;
};

// kill cache
killFirefoxSafaryCache();



$(document).ready(function(){
    var currentDictionary = {};
    var browserLanguage = window.navigator.userLanguage || window.navigator.language;
    var currentLanguage = browserLanguage.substring(0, 2).toLowerCase(); // en-gb =>  en
    var fallBackLanguage = "en";

    _.forEach(_dictionary, function(value, key) {
        currentDictionary[key] = value[currentLanguage] || value[fallBackLanguage];
    });

    $.i18n.load(currentDictionary);

    $('#errorTitle')._t('error');
    $('#errorBtn')._t('retry');
    $('#loadingLabel')._t('loading');
    $('#disableExtendedTrackingBtn')._t('disable_extended_tracking');

});
