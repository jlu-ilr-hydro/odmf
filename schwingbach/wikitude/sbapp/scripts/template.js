var ProjectConverter = function(SignalListener){

    this.arTracker = null;
    this.trackable2DObject = null;
    this.latestCamDrawables = [];
    this.projectInfo = null;
    this.lastTargetName = null;
    this.signal = new Signal();

    var _this = this;
    var DEFAULT_CLOUD_INTERVAL_MS = 3000;

    var SIGNAL_TYPES = {
        "LOADED": "LOADED",
        "CLICKED": "CLICKED",
        "DESTROYED": "DESTROYED",
        "ERROR": "ERROR",
        "PLAYED": "PLAYED",
        "PLAYED_FULLSCREEN": "PLAYED_FULLSCREEN",
        "RESUMED": "RESUMED",
        "PAUSED": "PAUSED",
        "CREATED": "CREATED",
        "TARGET_LOST": "TARGET_LOST",
        "TARGET_SCANNED": "TARGET_SCANNED",
        "TARGET_AUGMENTED": "TARGET_AUGMENTED"
    };

    var createSignal = function() {
        var signal = new Signal();
        signal.TYPE = SIGNAL_TYPES;
        if (SignalListener) {
            signal.add(SignalListener);
        };
        return signal;
    };

    /**
     * stops extended tracking by creating a new trackable of exact same type
     */
    this.stopExtendedTracking = function() {
        _this.createTrackable(true);
    };

    /**
     * show/hide the extended tracking control panel. By default this is just a button to reset the trackable
     * @param visible true means show, invisible otherwise
     */
    this.showExtendedTrackingControls = function(visible) {
        if (visible) {
            $("#disableExtendedTracking").show();
        } else {
            $("#disableExtendedTracking").hide();
        }
    };

    /**
     * creates trackable by using passed tracker and extendedTracking flag. Will destroy/reset existing trackables if they already exist
     * @param tracker the tracker this trackable should be attached to
     * @param enableExtendedTracking if true: extended tracking is enabled
     */
    this.createTrackable = function(enableExtendedTracking) {
        var tracker = _this.arTracker;
        _this.lastTargetName = null;
        $("#disableExtendedTracking").hide();

        tracker.enabled = false;

        if (_this.trackable2DObject) {
            _this.trackable2DObject.destroy();
        }

        _this.trackable2DObject = new AR.Trackable2DObject(tracker, "*", {
            drawables : {
                cam : []
            },
            enableExtendedTracking : enableExtendedTracking,
            onEnterFieldOfVision: onTargetRecognized,
            onExitFieldOfVision: onTargetLost
        });

        tracker.enabled = true;
    };

    /**
     * creates and launches project from given url
     * @param projectUrl path to Studio project in Client- or CloudTracker mode
     */
    this.convert = function(projectUrl) {

        var deferred = $.Deferred();

        _this.projectUrl = projectUrl;

        if(typeof AR === 'undefined') {
            deferred.reject(new Error("ARLibraryNotFound"));
            return deferred.promise();
        }

        if (!isSDKVersionSupported()) {
            deferred.reject(new Error("VersionConflict"));
            return deferred.promise();
        }

        if (!projectUrl && (typeof projectJSONOffline === 'undefined')) {
            deferred.reject(new Error("InvalidInput"));
            return deferred.promise();
        }

        $("#loading").show();

        _this.signal = createSignal();

        // kill all existing AR components
        AR.context.destroyAll();

        // disable sensors to save processing power
        AR.hardware.sensors.enabled = false;

        var initializeProjectJSON = function(projectJSON) {

            try {
                _this.projectInfo = projectJSON;
                _this.projectInfo.enableExtendedTracking = (projectJSON.studio && projectJSON.studio.extendedTracking);

                Logger.info('Project - File loaded.');

                if (!_this.projectInfo || _this.projectInfo.isCloud === undefined) {
                    Logger.error("Project - Invalid project file format");
                    deferred.reject(new Error("InvalidInput"));
                    return;
                }

                // 1) setup reporting
                setupReporting(_this.projectInfo, _this.signal);

                // 2) create a client/cloud- tracker
                try {
                    _this.arTracker = _this.projectInfo.isCloud ? createCloudTracker(_this.projectInfo, _this.onTrackerLoadedFn) : createClientTracker(_this.projectInfo, _this.onTrackerLoadedFn);
                } catch (err) {
                    Logger.error(err);
                    deferred.reject(new Error("ConnectionError"));
                    return;
                }

                // 3) Define trackable which is attached to the tracker
                _this.createTrackable(_this.projectInfo.enableExtendedTracking);

                // set document title to project name, if it exists
                document.title = _this.projectInfo.name ? _this.projectInfo.name : "Wikitude Studio";

                // 4) start the tracker
                _this.arTracker.start();

                deferred.resolve();
            } catch (err) {
                deferred.reject(err);
            }
        };

        if (typeof projectJSONOffline !== 'undefined') {
            initializeProjectJSON(projectJSONOffline);
        } else {
            // load project information from url
            loadJsonFromUrl(projectUrl).then(
                initializeProjectJSON,
                function(err) {
                    $("#loading").hide();
                    Logger.error('Project - JSON could not be loaded.');
                    Logger.error(err);
                    deferred.reject(new Error("ConnectionError"));
                });
        }

        return deferred.promise();
    };

    this.restartExperience = function() {
        if (_this.arTracker) {
            try {
                _this.arTracker.stop();
                _this.arTracker.destroy();
                Logger.info('RESTART EXPERIENCE: Existing tracker destroyed');
            } catch(err) {
                Logger.error("RESTART EXPERIENCE: Unexpected error occurred");
                Logger.error(err);
            }

        }
        _this.start(_this.projectUrl);
        Logger.info("RESTART EXPERIENCE - APPLIED");
    };

    this.start = function(projectUrl) {
        _this.convert(projectUrl).then(
            // success-callback
            function() {
                Logger.info("Tracker is active");
            },
            // error-callback
            function(err) {
                err = err || {};

                // function to execute in case
                var restartFn = function() { _this.start(projectUrl) };

                switch(err.message) {
                    case "InvalidInput" :
                        showError($.i18n._("invalid_input"), $.i18n._("invalid_input_descr"), restartFn );
                        break;

                    case "ConnectionError":
                        showError($.i18n._("connection_error"), $.i18n._("connection_error_descr"), restartFn );
                        break;

                    case "ARLibraryNotFound":
                        showError($.i18n._("invalid_environment"), $.i18n._("invalid_environment_descr"));
                        break;

                    case "VersionConflict":
                        showError($.i18n._("version_conflict"), $.i18n._("version_conflict_descr", AR.context.versionNumber ));
                        break;

                    default:
                        showError($.i18n._("unexpected_error"), $.i18n._("unexpected_error_descr"), restartFn);
                        break;
                }
            });
    };

    this.restartExperienceAndHideErrorDiv = function() {
        hideError();
        _this.restartExperience();
    };

    /**
     * called once Client- or CloudTracker was loaded successfully
     */
    this.onTrackerLoadedFn = function() {
        Logger.info('Tracker - loaded.');
        // hide loading div when tracker is available and active
        $("#loading").hide();
    };

    /**
     * call to update the Augmentation Loading indicator div style
     * @param finished
     */
    var updateAugmentationLoadingIndicatorVisibility = function(visible) {
        if (visible) {
            $('#loadingAugmentations').show();
        } else {
            $('#loadingAugmentations').hide();
        }
    };

    var updateAugmentationLoadingIndicatorValue = function(value) {
        if (!isNaN(value)) {
            $('#loadingDivProgressValue').html(value + '%');
            $('#loadingDivProgress').show();
        } else {
            $('#loadingDivProgressValue').html('');
            $('#loadingDivProgress').hide();
        }
    };

    /**
     * creates augmentations out of a list of augmentation-objects in predefined format (videoDrawable, 3dModel definitions etc.)
     * @param augmentationData metadata of the target the augmentations belong to.
     * @param augmentationsMeta metaData attached to the targets
     * @returns promise
     */
    var createAugmentations = function(augmentationData, augmentationsMeta) {
        var deferred = $.Deferred();

        // hold list of all created camDrawables
        var createdCamDrawables = [];

        // listener handling all load/error callbacks of the augmentations that should be created
        var listener = {
            "processedCounter": 0,
            "totalAugmentations" : augmentationData.length,
            "errorAugmentations": [],

            "checkIfallAugmentationsWereProcessed" : function() {
                this.progressCallback( Math.round( ( this.processedCounter / this.totalAugmentations) * 100 ));
                if (this.processedCounter>=this.totalAugmentations) {
                    // only resolve after all augmentations where created successfully (note: may cause issues when loading huge 3D models...)
                    if (!this.errorAugmentations.length) {
                        Logger.info('Augmentations - Successfully created');
                        deferred.resolve(createdCamDrawables, augmentationsMeta);
                    } else {
                        Logger.info('Augmentations - Created with errors ('+ this.errorAugmentations.length + ')');
                        deferred.reject(this.errorAugmentations, createdCamDrawables, augmentationsMeta);
                    }
                }
            },

            "progressCallback" : function(percentage) {
                // do not update UI in case the processed augmentations are already outdated
                if(_this.latestTrackedTargetName !== augmentationsMeta.targetName || _this.latestAugmentationsTimeStamp !== augmentationsMeta.latestAugmentationsTimeStamp) {
                    Logger.debug("Augmentations - Irrelevant progress info: " + percentage);
                } else {
                    Logger.info("Augmentations - loaded overall " + percentage);
                    updateAugmentationLoadingIndicatorValue(percentage);
                }
            },

            // an error occurred while creating / loading the augmentations
            "onError": function(augmentation) {
                Logger.info('ERROR\n' + JSON.stringify(augmentation));

                // 1) increase overall processed-counter
                this.processedCounter++;

                // 2) push the faulty augmentations to an error list
                this.errorAugmentations.push(augmentation);

                // 3) check if this augmentation was the last one
                this.checkIfallAugmentationsWereProcessed();
            },
            "onLoaded": function(augmentation) {

                // 1) increase overall processed-counter
                this.processedCounter++;

                // 2) check if this augmentation was the last one
                this.checkIfallAugmentationsWereProcessed();
            }
        };

        try {

            // the list of augmentations is at least not undefined or null
            if (augmentationData) {

                // loop through augmentationData and convert meta to real augmentations
                for (var i=0; i< augmentationData.length; i++) {

                    var augmentations = new AugmentationConverter().create(augmentationData[i], listener, _this.signal);

                    if (augmentations && augmentations.length) {
                        for (var j=0; j< augmentations.length; j++) {
                            var augmentation = augmentations[j];
                            createdCamDrawables.push(augmentation);
                        }
                        _this.signal.dispatch(_this.signal.TYPE.CREATED, augmentationData[i]);
                    } else {
                        Logger.error('AugmentationMeta - Unknown. No Drawables were created:\n' + JSON.stringify(augmentationData[i]));
                    }
                }

                // in case the list is empty -> no error: there are simply no augmentations defined for this target. resolve with empty array
                if (!augmentationData.length) {
                    deferred.resolve(createdCamDrawables, augmentationsMeta);
                }
            } else {

                Logger.info('AugmentationMeta - No augmentationdata available - Server response invalid?')
                // no augmentationData means no augmentations at all -> resolve with empty created camDrawables
                deferred.resolve(createdCamDrawables, augmentationsMeta);
            }

        } catch(err) {
            // an unexpected error occurred -> reject with empty 'causing augmentations' but list all targets that were created so far.
            Logger.info('AugmentationMeta - Unexpected error');
            Logger.info(err);
            deferred.reject([], createdCamDrawables, augmentationsMeta);
            return deferred.promise();
        }

        // return promise for asynchronous response handling
        return deferred.promise();
    };

    /**
     *
     * @param augmentationMeta
     * @returns {*}
     */
    var loadTargetJSON = function(augmentationMeta) {
        var deferred = $.Deferred();
        Logger.info('Augmentation JSON - Loading starts');

        if (augmentationMeta.augmentations) {
            Logger.info('Augmentation JSON - Bundled in metadata (for offline use)');
            deferred.resolve(augmentationMeta.augmentations, augmentationMeta);
        } else {
            loadJsonFromUrl(augmentationMeta.augmentationUri).then(
                // success case
                function(targetJSON) {
                    Logger.info('Augmentation JSON - Loaded');
                    deferred.resolve(targetJSON.augmentations, augmentationMeta);
                }
                // error case
                , function(error) {
                    Logger.info('Augmentation JSON - Error');
                    deferred.reject(error);
                }
            );
        }



        return deferred.promise();
    };



    /**
     * called when a target was lod / is no longer visible but was already visible
     * @param targetName name of lost target
     */
    var onTargetLost = function(targetName) {

        Logger.info('TARGET lost ' + targetName);

        _this.arTracker.isRecognized = false;
        _this.showExtendedTrackingControls(false);

        _this.signal.dispatch(_this.signal.TYPE.TARGET_LOST, targetName);

        // hide loading indicator
        updateAugmentationLoadingIndicatorVisibility(false);

        // loop through latest camDrawables and fire onExitFoV callback if set and disable the drawable too
        for (var i=_this.latestCamDrawables.length-1; i>=0; i-- ) {
            if (_this.latestCamDrawables[i].onExitFieldOfVision) {
                _this.latestCamDrawables[i].onExitFieldOfVision();
            }
            _this.latestCamDrawables[i].enabled = false;
        }

        // target was lost -> restart cloudTracker if set
        if (_this.arTracker.restart) {
            _this.arTracker.restart(DEFAULT_CLOUD_INTERVAL_MS);
        }
    };

    /**
     * called whenever a target was recognized
     * @param targetName
     */
    var onTargetRecognized = function(targetName) {
        Logger.info('TARGET recognized ' + targetName);

        _this.showExtendedTrackingControls(_this.trackable2DObject.enableExtendedTracking);
        _this.arTracker.isRecognized = true;

        _this.signal.dispatch(_this.signal.TYPE.TARGET_SCANNED, targetName);

        // a new target was recognized
        if (_this.lastTargetName !== targetName) {

            if (_this.latestCamDrawables) {
                for (var i=_this.latestCamDrawables.length-1; i>=0; i-- ) {
                    _this.latestCamDrawables[i].enabled = false;
                }
            }

            _this.lastTargetName = targetName;

            var augmentationsMeta;

            // CloudTracker
            if (_this.projectInfo.isCloud) {
                if (_this.projectInfo.cloudTargetInfo && _this.projectInfo.cloudTargetInfo.name == targetName) {
                    // update augmentationsMeta and stop tracking tracker now
                    augmentationsMeta = _this.projectInfo.cloudTargetInfo;
                    augmentationsMeta.targetName = _this.projectInfo.cloudTargetInfo.name;
                    _this.arTracker.stop();
                } else {
                    Logger.error('TARGET - No augmentations in the cloud: ' + targetName);
                    return;
                }
            }

            // ClientTracker
            else {
                if (!_this.projectInfo.targets) {
                    Logger.error('TARGET - No augmentations in projectJSON: ' + targetName);
                    return;
                }
                var foundAugmentations = $.grep(_this.projectInfo.targets, function(v) {
                    return v.name === targetName;
                });

                var augmentationUri = undefined;

                if (!foundAugmentations.length) {
                    Logger.error('TARGET - No augmentations defined for ' + targetName);
                    return;
                } else {
                    augmentationUri = foundAugmentations[0].path;
                }

                augmentationsMeta = { "targetName" : targetName, "augmentationUri" : augmentationUri, "augmentations": foundAugmentations[0].augmentations };
            }

            var latestAugmentationsTimeStamp = Date.now();
            augmentationsMeta.latestAugmentationsTimeStamp = latestAugmentationsTimeStamp;

            _this.latestAugmentationsTimeStamp = latestAugmentationsTimeStamp;
            _this.latestTrackedTargetName = targetName;

            if (!augmentationsMeta.augmentationUri && !augmentationsMeta.augmentations) {
                Logger.info('TARGET - No augmentations defined');
                return;
            }

            // show the 'target visible' indicator
            updateAugmentationLoadingIndicatorVisibility(true);

            // reset percentage value
            updateAugmentationLoadingIndicatorValue(2);

            loadTargetJSON(augmentationsMeta).then(

                // augmentations of this targets were created
                function(augmentationJSON, augmentationsMeta) {

                    // created targets tdo not match latest one -> kill created ones
                    if (_this.latestTrackedTargetName !== augmentationsMeta.targetName || _this.latestAugmentationsTimeStamp !== augmentationsMeta.latestAugmentationsTimeStamp) {
                        Logger.info('augmentations JSON response came too late, it is already outdated');
                        return;
                    }

                    var augmentationsListToUse = augmentationJSON || [];

                    createAugmentations(augmentationsListToUse, augmentationsMeta).then(

                        function(createdAugmentations, augmentationsMeta) {

                            updateAugmentationLoadingIndicatorVisibility(false);

                            // check if current target is not the one these augmentations belong to b'cause user moved away from the target already
                            if (_this.latestTrackedTargetName !== augmentationsMeta.targetName || _this.latestAugmentationsTimeStamp !== augmentationsMeta.latestAugmentationsTimeStamp) {
                                Logger.error('augmentation creation took too long, target already outdated. Killing ' + createdAugmentations.length + ' (invisible) augmentations');
                                for (var k=0; k<=createdAugmentations.length; k++ ) {
                                    if (createdAugmentations[k] && createdAugmentations[k].kill) {
                                        createdAugmentations[k].kill();
                                    } else {
                                        Logger.debug('CREATE AUGMENTATIONS - Missing kill method in ' + JSON.stringify(createdAugmentations[k]));
                                    }
                                }
                                return;
                            } else {
                                // loop through camDrawables and remove them from trackable's camDrawables
                                if (_this.latestCamDrawables.length) {
                                    // destroy augmentations of previous target's augmentations
                                    for (var i=_this.latestCamDrawables.length-1; i>=0; i-- ) {
                                        if (_this.latestCamDrawables[i].kill) {
                                            _this.latestCamDrawables[i].kill();
                                        } else {
                                            Logger.debug('CREATE AUGMENTATIONS - Missing kill method in ' + JSON.stringify(_this.latestCamDrawables[i]));
                                        }
                                        _this.trackable2DObject.drawables.removeCamDrawable(i);
                                    }
                                }

                                // push new augmantions to camDrawables and global variable for future direct access
                                var validAugmentations = [];
                                for (var i=0; i<createdAugmentations.length; i++) {
                                    if (createdAugmentations[i]) {
                                        _this.trackable2DObject.drawables.addCamDrawable(createdAugmentations[i]);
                                        validAugmentations.push(createdAugmentations[i]);
                                    }
                                }

                                _this.latestCamDrawables = validAugmentations;
                                _this.signal.dispatch(_this.signal.TYPE.TARGET_AUGMENTED, targetName, augmentationsMeta );
                            }
                        },

                        function(failedAugmentations, invalidCreatedAugmentations, augmentationsMeta) {
                            if (!invalidCreatedAugmentations || !invalidCreatedAugmentations.length) {
                                Logger.info('CREATE AUGMENTATIONS - Target has no augmentations');
                            } else{
                                if (failedAugmentations && failedAugmentations.length) {
                                    Logger.error('CREATE AUGMENTATIONS - At least one augmentation could not be loaded properly, namely ' + failedAugmentations.length);
                                    Logger.error(JSON.stringify(failedAugmentations));
                                } else {
                                    Logger.error('CREATE AUGMENTATIONS - Evil augmentations:\n' + JSON.stringify(augmentationsMeta));
                                }

                                showError($.i18n._("connection_error"),$.i18n._("connection_error_descr"), function() { _this.restartExperienceAndHideErrorDiv(); });
                            }
                            updateAugmentationLoadingIndicatorVisibility(false);
                        }

                    );

                },

                function (err) {
                    Logger.error('something strange happened! ' + err);
                    updateAugmentationLoadingIndicatorVisibility(false);
                    showError($.i18n._("unexpected_error"), $.i18n._("unexpected_error_descr"), function() { _this.restartExperienceAndHideErrorDiv(); });
                }
            );

        }
        // entering same target that went through exitFoV before -> reuse active camDrawables
        else {
            if (_this.latestCamDrawables.length) {
                for (var i=_this.latestCamDrawables.length-1; i>=0; i-- ) {
                    if (_this.latestCamDrawables[i].onEnterFieldOfVision) {
                        _this.latestCamDrawables[i].onEnterFieldOfVision();
                    }
                    _this.latestCamDrawables[i].enabled = true;
                }
            }
        }
    };
};

var AugmentationConverter = function() {

    var generateDrawable2DOptions = function (augmentation) {
        var object = {
            opacity: augmentation.properties.opacity,
            zOrder: augmentation.properties.zOrder
        };

        if(augmentation.properties.translate) {
            object.translate = {
                x: augmentation.properties.translate.x || 0.0,
                y: augmentation.properties.translate.y || 0.0,
                z: augmentation.properties.translate.z || 0.0
            };
        }

        if(augmentation.properties.scale) {
            object.scale = {
                x: augmentation.properties.scale.x || 1.0,
                y: augmentation.properties.scale.y || 1.0,
                z: augmentation.properties.scale.z || 1.0
            };
        }

        if(augmentation.properties.rotate) {
            object.rotate = {
                x: augmentation.properties.rotate.x || 0.0,
                y: augmentation.properties.rotate.y || 0.0,
                z: augmentation.properties.rotate.z || 0.0
            };
        }
        return object;
    };

    /**
     * converts a Studio Text into an ARchitect Label
     * @param text
     *            the Studio text that should be converted
     * @param listener
     *            {onError, onLoaded}, will fire onLoaded right after creation of the Label (error event interfaces not provided by the SDK)
     * @return the converted Label in an array.
     */
    var convertText = function (text, listener, signal) {
        // generate the default options that will be passed to the Label
        var options = generateDrawable2DOptions(text);

        if(text.properties && text.properties.style) {
            options.style = {
                backgroundColor: text.properties.style.backgroundColor ? convertRGBA(text.properties.style.backgroundColor) : '#FFFFFF00',
                textColor: text.properties.style.textColor ? convertRGBA(text.properties.style.textColor) : "#000000FF",
                fontStyle: (!text.properties.style.fontStyle || text.properties.style.fontStyle === '') ? 'normal' : text.properties.fontStyle
            };
        }
        if (text.properties.clickUrl !== '') {
            // set the click function
            var onClickFunction = function (text, listener, signal) {
                return function() {
                    signal.dispatch(signal.TYPE.CLICKED, text);
                    AR.context.openInBrowser(text.properties.clickUrl);
                }

            }(text, listener, signal);
            // in case the options already contain a click function, append the
            // new click function
            options.onClick = options.onClick ? (function (oldOnClick, newOnClick) {
                return function () {
                    oldOnClick();
                    newOnClick();
                };
            })(options.onClick, onClickFunction) : onClickFunction;
        }
        // create the final Label
        var label = new AR.Label(text.properties.text, text.height, options);

        label.kill = function (text, listener, signal) {
            return function() {
                signal.dispatch(signal.TYPE.DESTROYED, text);
                label.destroy();
            };
        }(text, listener, signal);

        if (listener && listener.onLoaded) {
            listener.onLoaded(text);
        }

        text.camDrawables = [label];
        return text.camDrawables;
    };

    /**
     * converts a Studio Private Video used as target augmentation into an ARchitect VideoDrawable
     *
     * @param video
     *            the Studio Video that should be converted
     * @return the converted VideoDrawable incl. its 'poster' ImageDrawable in an array of length 2.
     */
    var convertPrivateAugmentationVideo = function (video, signal) {
            // generate the default options that will be passed to the Label
            var options = generateDrawable2DOptions(video);
            options.isTransparent = video.properties.videoMode == "overlayAlpha";

            // create the final Label
            //var videoDrawable = new AR.VideoDrawable(video.uri, video.height / 100.0 / (options.isTransparent ? 2 : 1), options);
            var videoHeight = video.height;
            if(options.isTransparent) {
                videoHeight = video.height / 2;
            }

            var videoDrawable = new AR.VideoDrawable(video.uri, videoHeight, options);
            // videoDrawable.enabled = false;

            //when clicking on the video, pause/resume the video (depending on the state)
            var videoOnClickFunction = function (video, videoDrawable, signal) {
                return function() {
                    if (videoDrawable.state == "PLAYING") {
                        videoDrawable.state = "PAUSED";
                        videoDrawable.pause();
                        signal.dispatch(signal.TYPE.PAUSED, video);
                    }
                    else if (videoDrawable.state == "PAUSED") {
                        videoDrawable.state = "PLAYING";
                        videoDrawable.resume();
                        signal.dispatch(signal.TYPE.RESUMED, video);
                    }
                };
            }(video, videoDrawable, signal);

            // in case the options already contain a click function, append the
            // new click function
            videoDrawable.onClick = options.onClick ? (function (oldOnClick, newOnClick) {
                return function () {
                    oldOnClick();
                    newOnClick();
                };
            })(options.onClick, videoOnClickFunction) : videoOnClickFunction;

            //when the target enters the field of vision, the video is resumed
            videoDrawable.onEnterFieldOfVision = function (video, videoDrawable, signal) {
                return function() {
                    if (videoDrawable.autoResume && videoDrawable.state == "PAUSED") {
                        videoDrawable.state = "PLAYING";
                        videoDrawable.resume();
                        signal.dispatch(signal.TYPE.RESUMED, video);
                    }
                };
            }(video, videoDrawable, signal);

            //when the target exits the field of vision, the video is paused
            videoDrawable.onExitFieldOfVision = function (video, videoDrawable, signal) {
                return function() {
                    if (videoDrawable.state == "PLAYING") {
                        videoDrawable.state = "PAUSED";
                        videoDrawable.pause();
                        signal.dispatch(signal.TYPE.PAUSED, video);
                    }
                }
            }(video, videoDrawable, signal);

            //flag to indicate the status. This is used to determine if the loading indicator must be displayed
            videoDrawable.state = "LOADING";

            //since we have several onloaded functions, depending on the settings, we keep then in an array
            var onVideoLoadedFunctions = [];

            //for sure we set the loading status to true once the video is loaded. Add this to the onLoaded functions
            onVideoLoadedFunctions.push(function () {
                videoDrawable.state = "LOADED";
            });

            //function to play the video. Enables the video and plays it.
            var handlePlay = function (video, videoDrawable, signal) {
                return function() {
                    videoDrawable.state = "PLAYING";
                    videoDrawable.enabled = true;
                    signal.dispatch(signal.TYPE.PLAYED, video);
                    videoDrawable.play(video.properties.endlessLoop ? -1 : 1);
                }
            }(video, videoDrawable, signal);

            //handle the poster
            //create an ImageDrawable and show it
            var firstFrameUrl = "";
            if(options.isTransparent && video.firstFrameAlphaImgUrl) {
                firstFrameUrl = video.firstFrameAlphaImgUrl;
            } else if(!options.isTransparent && video.properties.firstFrameImgUrl) {
                firstFrameUrl = video.properties.firstFrameImgUrl;
            } else {
                // TODO STU-596
                firstFrameUrl = undefined;
            }

            var posterResource = new AR.ImageResource(firstFrameUrl);

            // ensure poster sits on top of the videoDrawable
            if (options.zOrder) {
                options.zOrder++;
            } else {
                options.zOrder = 1;
            }
            var poster = new AR.ImageDrawable(posterResource, videoHeight, options);
            //custom removal function (removes the poster and the underlying image drawable)
            poster.kill = function () {
                poster.imageResource.destroy();
                poster.destroy();
            };

            // add auto resume
            videoDrawable.autoResume = video.properties.autoResume;

            //automatically plays the video once the video has been loaded
            var addAutoplay = function () {
                //add a new onloaded function
                onVideoLoadedFunctions.push(function () {
                    //remove the poster
                    if (poster) {
                        poster.kill();
                    }
                    //play the video
                    handlePlay();
                });
            };

            //handle autoplay
            if (video.properties.autoPlay) {
                //play it automatically as soon as possible
                addAutoplay();
            } else {
                //when clicking on the poster, the video should start
                var onClickFunction = function () {
                    if (videoDrawable.state == "LOADED") {
                        //if the video is already loaded, immediately start it.
                        poster.kill();
                        handlePlay();
                    } else if (videoDrawable.state == "LOADING") {
                        //show loading indication and play as soon as the video is loaded
                        // TODO show loading animation while video is loading!
                        addAutoplay();
                    }
                    // consume click to not fire click of objects under the poster (like the video)
                    return true;
                };
                // in case the options already contain a click function, append the
                // new click function
                poster.onClick = options.onClick ? (function (oldOnClick, newOnClick) {
                    return function () {
                        oldOnClick();
                        newOnClick();
                    };
                })(options.onClick, onClickFunction) : onClickFunction;
            }

            //execute all onloaded functions
            videoDrawable.onLoaded = function () {
                for (var i = 0; i < onVideoLoadedFunctions.length; i++) {
                    onVideoLoadedFunctions[i]();
                }
            };

            //add the remove function
            videoDrawable.kill = function (video, videoDrawable, signal) {
                return function() {
                    signal.dispatch(signal.TYPE.DESTROYED, video);
                    videoDrawable.destroy();
                    if (poster && !poster.destroyed && poster.kill) {
                        poster.kill();
                    }
                };
            }(video, videoDrawable, signal);

            video.camDrawables = [videoDrawable, poster];
    };

    /**
     * converts a Studio Private Video into an ARchitect VideoDrawable
     *
     * @param project
     *            the studio project that contains the augmentation to be
     *            converted
     * @param target
     *            the Studio target that contains the augmentation to be
     *            converted
     * @param video
     *            the Studio Video that should be converted
     * @return the converted Video in case of static loading, a function to
     *         create the Video in case of dynamic loading.
     */
    var convertPrivateFullscreenVideo = function (video, signal) {
        var poster;

        if (video.properties.autoPlay) {
                //If we play the video automatically, this needs to happen once the target is scanned.
                //Since we don't know about the target yet in this context, we use a Circle as a placeholder.
                //However, the onEnterFieldOfVision trigger is set, which is fired as soon as the target becomes visible.
                //That ensures that the video starts playing immediately
                poster = new AR.Circle(1, {enabled: false});
                poster.onEnterFieldOfVision =
                    function (video, signal) {
                        return function() {
                            signal.dispatch(signal.TYPE.PLAYED, video);
                            AR.context.startVideoPlayer(video.uri);
                        }
                    }(video, signal)
            } else {
                var options = generateDrawable2DOptions(project, target, video);
                //handle the poster
                //create an ImageDrawable and show it

                // TODO STU-596
                var firstFrameUrl = video.properties.firstFrameImgUrl ? video.properties.firstFrameImgUrl: undefined;
                var posterResource = new AR.ImageResource(firstFrameUrl);
                poster = new AR.ImageDrawable(posterResource, video.height / 100.0, options);

                // set the click function to start the video player
                var onClickFunction =
                    function (video, signal) {
                        return function () {
                            signal.dispatch(signal.TYPE.PLAYED, video);
                            AR.context.startVideoPlayer(video.uri);
                        };
                    }(video, signal);

                // in case the options already contain a click function, append the
                // new click function
                poster.onClick = options.onClick ? (function (oldOnClick, newOnClick) {
                    return function () {
                        oldOnClick();
                        newOnClick();
                    };
                })(options.onClick, onClickFunction) : onClickFunction;
            }

            //add function to remove the poster
            poster.kill = function (video, poster, signal) {
                return function() {
                    if (poster.imageResource && !poster.imageResource.destroyed) {
                        poster.imageResource.destroy();
                    }
                    poster.destroy();
                    signal.dispatch(signal.TYPE.DESTROYED, video);
                };
            }(video, poster, signal);

            video.camDrawables = [poster];
    };

    var convertPanoramaSphere = function (model, listener, signal) {
        var drawable;
        var options = {
            scale: {
                x: model.scale,
                y: model.scale,
                z: model.scale
            }
        };
        options.onError = function(model, listener, signal) {
            return function () {
                if (listener && listener.onError) {
                    listener.onError(model);
                }
                signal.dispatch(signal.TYPE.ERROR, model);
            };
        }(model, listener, signal);

        options.onLoaded = function(model, listener, signal) {
            return function () {
                if (listener && listener.onLoaded) {
                    listener.onLoaded(model);
                }
                signal.dispatch(signal.TYPE.LOADED, model);
            };
        }(model, listener, signal);

        // create the drawable with options and return
        drawable = new AR.Model(model.uri, options );

        drawable.kill = function(model, drawable, signal) {
            return function() {
                drawable.destroy();
                signal.dispatch(signal.TYPE.DESTROYED, model);

            }
        }(model, drawable, signal);

        model.camDrawables = [drawable];
        return model.camDrawables;
    };

    var convertVideo = function (video, listener, signal) {
        var createdVideoAssets = [];
        if (video.properties.videoMode === 'fullscreen') {
            convertPrivateFullscreenVideo(video, signal);
        } else {
            convertPrivateAugmentationVideo(video, signal);
        }
        if (listener && listener.onLoaded) {
            // there is no video loading happening on video creation -> no idea if video is valid or accessible at t0
            listener.onLoaded(video);
        }

        return video.camDrawables;
    };

    var convertModel = function (model, listener, signal) {

        var onErrorFn = function(listener, model, signal) {
            return function() {
                if (listener && listener.onError) {
                    listener.onError(model);
                }
                signal.dispatch(signal.TYPE.ERROR, model);
            }
        }(listener, model, signal);

        var onLoadedFn = function(listener, model, signal) {
            return function() {
                if (listener && listener.onLoaded) {
                    listener.onLoaded(model);
                }
                signal.dispatch(signal.TYPE.LOADED, model);
            }
        }(listener, model, signal);

        var drawable = new AR.Model(model.uri, {
            onLoaded: onLoadedFn,
            onError: onErrorFn,
            scale: {
                x: model.properties.scale.x || 1.0,
                y: model.properties.scale.y || 1.0,
                z: model.properties.scale.z || 1.0
            },
            rotate: {
                x: model.properties.rotate.x || 0.0,
                y: -model.properties.rotate.y || 0.0,
                z: -model.properties.rotate.z || 0.0
            },
            translate: {
                x: model.properties.translate.x || 0.0,
                y: model.properties.translate.y || 0.0,
                z: model.properties.translate.z || 0.0
            }
        });

        drawable.kill = function (drawable, model, signal) {
            return function() {
                drawable.destroy();
                signal.dispatch(signal.TYPE.DESTROYED, model);
            }

        }(drawable, model, signal);

        drawable.augmentationType = model.type;
        model.camDrawables = [drawable];
        return model.camDrawables;
    };

    var convertImage = function (image, listener, signal) {

        // generate the ARchitect ImageResource
        var imageResOptions = {};

        var onErrorFn = function(image, listener, signal) {
            return function() {
                if (listener && listener.onError) {
                    listener.onError(image);
                }
                signal.dispatch(signal.TYPE.ERROR, image);
            }
        }(image, listener, signal);

        var onLoadedFn = function(image, listener, signal) {
            return function() {
                if (listener && listener.onLoaded) {
                    listener.onLoaded(image);
                }
                signal.dispatch(signal.TYPE.LOADED, image);
            }
        }(image, listener, signal);

        imageResOptions.onLoaded = onLoadedFn;
        imageResOptions.onError = onErrorFn;

        var imageResource = new AR.ImageResource(image.uri, imageResOptions);
        // generate the default options that will be passed to the ImageDrawable
        var options = generateDrawable2DOptions(image);
        if (image.properties.clickUrl && image.properties.clickUrl !== "") {
            // set the click function
            var onClickFunction = function (signal, image) {
                return function() {
                    signal.dispatch(signal.TYPE.CLICKED, image);
                    AR.context.openInBrowser(image.properties.clickUrl, image.properties.forceNativeBrowser == "true" ? true : false);
                }
            }(signal, image);
            // in case the options already contain a click function, append the
            // new click function
            options.onClick = options.onClick ? (function (oldOnClick, newOnClick, signal, image) {
                return function () {
                    signal.dispatch(signal.TYPE.CLICKED, image);
                    oldOnClick();
                    newOnClick();
                };
            })(options.onClick, onClickFunction, signal, image) : onClickFunction;
        }
        // create the final image drawable

        var imageDrawable = new AR.ImageDrawable(imageResource, image.height, options);

        imageDrawable.kill = function (imageResource, imageDrawable, signal, image) {
            return function() {
                imageResource.destroy();
                imageDrawable.destroy();
                signal.dispatch(signal.TYPE.DESTROYED, image);
            }
        }(imageResource, imageDrawable, signal, image );

        imageDrawable.augmentationType = image.type;

        image.camDrawables = [imageDrawable];
        return image.camDrawables;
    };

    this.create = function(augmentation, listener, signal) {
        var augmentationsToReturn = [];
        if (augmentation) {
            switch (augmentation.type) {
                case "Button":
                case "ImageDrawable":
                    augmentationsToReturn = convertImage(augmentation, listener, signal);
                    break;
                case "Label":
                    augmentationsToReturn = convertText(augmentation, listener, signal);
                    break;
                case "Model3D":
                    augmentationsToReturn = convertModel(augmentation, listener, signal);
                    break;
                case "PanoramaSphere":
                    augmentationsToReturn = convertPanoramaSphere(augmentation, listener, signal);
                    break;
                case "VideoDrawable":
                    augmentationsToReturn = convertVideo(augmentation, listener, signal);
                    break;
                default:
                    // 'unsupported augmentation
                    break;
            }
        }
        return augmentationsToReturn;
    };
};

var POIURL="http://fb09-pasig.umwelt.uni-giessen.de/sbapp/app/Poidata.json";

// implementation of AR-Experience (aka "World")
var World = {
    isRequestingData: false,
    init: function(projectUrl) {
        this.projectUrl = projectUrl;
        this.projectConverter = new ProjectConverter();
        this.projectConverter.start(projectUrl);
        //this.createOverlays();
    },
    // you may request new data from server periodically, however: in this sample data is only requested once

    restart: function() {
        World.projectConverter.restartExperienceAndHideErrorDiv();
    },


    //WWW-Button wird durch Hilfsfunktion erstellt
    createWwwLinkButton: function createWwwLinkButtonFn(url, size, options) {
        this.imgButton = new AR.ImageResource("assets/wwwLink.png");
        options.onClick = function() {
            AR.context.openInBrowser(url);
        };
        return new AR.ImageDrawable(this.imgButton, size, options);
    },
    createOverlays: function()
    {
        // Initialisiert den Tracker - die WTC-Datei bzw. Target-Datei -
        // beinhaltet Dateinamen und Erkennungsalgorithemen der Tracking-Objekte - die einzeln aufgerufen werden
        // wtc - Datei wird von online Serive bei Wikitude aus Bilddatei erstellt.
        // Der Tracker enth�lt alle trackable vorlagen, von QR-Code bis Brennessel
        this.targetCollectionResource = new AR.TargetCollectionResource("assets/tracker_LEGO.wtc", {

        });

        this.tracker = new AR.ImageTracker(this.targetCollectionResource, {
            onTargetsLoaded: this.worldLoaded
        });

        var video = new AR.VideoDrawable("assets/Steinkauz_Tembrock_Guenther_1322.mp4", 0.40, {
            translate: {
                y: -0.3
            }
        });

        var pageOne = new AR.ImageTrackable(this.tracker, "*", {
            drawables: {
                cam: [video]
            },
            onEnterFieldOfVision: function onEnterFieldOfVisionFn() {
                if (this.hasVideoStarted) {
                    video.resume();
                }
                else {
                    this.hasVideoStarted = true;
                    video.play(-1);
                }
            },
            onExitFieldOfVision: function onExitFieldOfVisionFn() {
                video.pause();
            }
        });
    },

    // true once data was fetched
    initiallyLoadedData: false,

    // different POI-Marker assets
    markerDrawable_idle: null,
    markerDrawable_selected: null,
    markerDrawable_directionIndicator: null,

    // list of AR.GeoObjects that are currently shown in the scene / World
    markerList: [],

    // The last selected marker
    currentMarker: null,

    // called to inject new POI data
    loadPoisFromJsonData: function loadPoisFromJsonDataFn(poiData) {
        // empty list of visible markers
        World.markerList = [];
        World.markerContentList = [];
        PoiRadar.show();
        $('#radarContainer').unbind('click');
        $("#radarContainer").click(PoiRadar.clickedRadar);
        // start loading marker assets
        World.markerDrawable_idle = new AR.ImageResource("assets/marker_idle.png");
        World.markerDrawable_selected = new AR.ImageResource("assets/marker_selected.png");
        // Create an AR.ImageResource referencing the image that should be displayed for a direction indicator.
        World.markerDrawable_directionIndicator = new AR.ImageResource("assets/indi.png");

        // loop through POI-information and create an AR.GeoObject (=Marker) per POI
        for (var currentPlaceNr = 0; currentPlaceNr < poiData.length; currentPlaceNr++) {

            var singlePoi = {
                "id": poiData[currentPlaceNr].id,
                "latitude": parseFloat(poiData[currentPlaceNr].latitude),
                "longitude": parseFloat(poiData[currentPlaceNr].longitude),
                "altitude": parseFloat(poiData[currentPlaceNr].altitude),
                "title": poiData[currentPlaceNr].name,
                "description": poiData[currentPlaceNr].description,

            };

            /*
             To be able to deselect a marker while the user taps on the empty screen,
             the World object holds an array that contains each marker.
             */
            World.markerList.push(new Marker(singlePoi));
            World.markerContentList.push(singlePoi);
        }

        World.updateStatusMessage(currentPlaceNr + ' places loaded');
    },

    // updates status message shon in small "i"-button aligned bottom center
    updateStatusMessage: function updateStatusMessageFn(message, isWarning) {

        var themeToUse = isWarning ? "e" : "c";
        var iconToUse = isWarning ? "alert" : "info";

        $("#status-message").html(message);
        $("#popupInfoButton").buttonMarkup({
            theme: themeToUse
        });
        $("#popupInfoButton").buttonMarkup({
            icon: iconToUse
        });
    },

    // location updates, fired every time you call architectView.setLocation() in native environment
    locationChanged: function locationChangedFn(lat, lon, alt, acc) {

        /*
         The custom function World.onLocationChanged checks with the flag World.initiallyLoadedData if the function was already called. With the first call of World.onLocationChanged an object that contains geo information will be created which will be later used to create a marker using the World.loadPoisFromJsonData function.
         */
        if (!World.initiallyLoadedData) {
            /*
             requestDataFromLocal with the geo information as parameters (latitude, longitude) creates different poi data to a random location in the user's vicinity.
             */
            World.requestDataFromLocal(lat, lon);
            World.initiallyLoadedData = true;
        }
    },

    // fired when user pressed maker in cam
    onMarkerSelected: function onMarkerSelectedFn(marker) {

        // deselect previous marker
        if (World.currentMarker) {
            if (World.currentMarker.poiData.id == marker.poiData.id) {
                return;
            }
            World.currentMarker.setDeselected(World.currentMarker);
        }

        // highlight current one
        marker.setSelected(marker);

        for(var index in World.markerList)
        {
            if(World.markerContentList[index]["id"] == marker.poiData.id)
            {
                swal({
                    html:World.markerContentList[index]["description"]
                });
                break;
            }
        }
        World.currentMarker = marker;
    },

    // screen was clicked but no geo-object was hit
    onScreenClick: function onScreenClickFn() {
        if (World.currentMarker) {
            World.currentMarker.setDeselected(World.currentMarker);
        }
    },

    // request POI data
    requestDataFromLocal: function requestDataFromLocalFn(centerPointLatitude, centerPointLongitude) {
        //var poisToCreate = 20;
        alert("Je nach Internetgeschwindigkeit kann es etwas dauern bis die umliegenden Positionen gelanden werden.");

        $.ajax({
            dataType: "json",
            url: "http://evolution.uni-giessen.de/sbapp/Poidata.json",
            success: function (data) {
                var poiData = [];
                for(var i in data)
                {
                    //alert(data[i]["id"]);
                    poiData.push({
                        "id": data[i]["id"],
                        "longitude": data[i]["lon"],
                        "latitude": data[i]["lat"],
                        "description": data[i]["comment"],
                        "altitude": AR.CONST.UNKNOWN_ALTITUDE,
                        "name": data[i]["name"]
                    });
                }
                World.loadPoisFromJsonData(poiData);
            },
            error: function (e) {
                alert("Your Internet connection is gone");

            }
        });

        /*for (var i = 0; i < poisToCreate; i++) {
         poiData.push({
         "id": (i + 1),
         "longitude": (centerPointLongitude + (Math.random() / 5 - 0.1)),
         "latitude": (centerPointLatitude + (Math.random() / 5 - 0.1)),
         "description": ("This is the description of POI#" + (i + 1)),
         "altitude": "100.0",
         "name": ("POI#" + (i + 1))
         });
         }*/



    }

};



function stopExtendedTracking() {
    if (World.projectConverter && World.projectConverter.stopExtendedTracking) {
        World.projectConverter.stopExtendedTracking();
    } else {
        alert("Unexpected execution of stopExtendedTracking");
    }

}

$(document).ready(function(){
    var projectUrl = getUrlParameter("j");
    World.init(projectUrl);

    AR.context.onLocationChanged = World.locationChanged;

    /*
     To detect clicks where no drawable was hit set a custom function on AR.context.onScreenClick where the currently selected marker is deselected.
     */
    AR.context.onScreenClick = World.onScreenClick;

});
