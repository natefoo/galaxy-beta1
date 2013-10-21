define(["mvc/history/history-model","mvc/dataset/hda-base","mvc/dataset/hda-edit"],function(d,b,a){var c=Backbone.View.extend(LoggableMixin).extend({HDAView:a.HDAEditView,tagName:"div",className:"history-panel",fxSpeed:300,events:{"click #history-tag":"loadAndDisplayTags","click #message-container":"clearMessages"},initialize:function(e){e=e||{};if(e.logger){this.logger=e.logger}this.log(this+".initialize:",e);this._setUpListeners();this.hdaViews={};this.urls={};this.indicator=new LoadingIndicator(this.$el);if(this.model){this._setUpWebStorage(e.initiallyExpanded,e.show_deleted,e.show_hidden);this._setUpModelEventHandlers()}if(e.onready){e.onready.call(this)}},_setUpListeners:function(){this.on("error",function(f,i,e,h,g){this.errorHandler(f,i,e,h,g)});this.on("loading-history",function(){this.showLoadingIndicator()});this.on("loading-done",function(){this.hideLoadingIndicator()});this.once("rendered",function(){this.trigger("rendered:initial",this);return false});this.on("switched-history current-history new-history",function(){if(_.isEmpty(this.hdaViews)){this.trigger("empty-history",this)}});if(this.logger){this.on("all",function(e){this.log(this+"",arguments)},this)}},errorHandler:function(g,j,f,i,h){var e=this._parseErrorMessage(g,j,f,i,h);if(j&&j.status===502){}else{if(!this.$el.find("#message-container").is(":visible")){this.once("rendered",function(){this.displayMessage("error",e.message,e.details)})}else{this.displayMessage("error",e.message,e.details)}}},_parseErrorMessage:function(h,l,g,k,j){var f=Galaxy.currUser,e={message:this._bePolite(k),details:{user:(f instanceof User)?(f.toJSON()):(f+""),source:(h instanceof Backbone.Model)?(h.toJSON()):(h+""),xhr:l,options:(l)?(_.omit(g,"xhr")):(g)}};_.extend(e.details,j||{});if(l&&_.isFunction(l.getAllResponseHeaders)){var i=l.getAllResponseHeaders();i=_.compact(i.split("\n"));i=_.map(i,function(m){return m.split(": ")});e.details.xhr.responseHeaders=_.object(i)}return e},_bePolite:function(e){e=e||_l("An error occurred while getting updates from the server");return e+". "+_l("Please contact a Galaxy administrator if the problem persists.")},_loadHistoryFromXHR:function(g,f){var e=this;g.then(function(h,i){e.setModel(h,i,f)});g.fail(function(i,h){e.render()});return g},setModel:function(g,e,f){f=f||{};if(this.model){this.model.clearUpdateTimeout();this.stopListening(this.model);this.stopListening(this.model.hdas)}this.hdaViews={};if(Galaxy&&Galaxy.currUser){g.user=Galaxy.currUser.toJSON()}this.model=new d.History(g,e,f);this._setUpWebStorage(f.initiallyExpanded,f.show_deleted,f.show_hidden);this._setUpModelEventHandlers();this.trigger("new-model",this);this.render();return this},loadHistory:function(h,g,f,k,i){this.trigger("loading-history",this);g=g||{};var e=this;var j=d.History.getHistoryData(h,{historyFn:f,hdaFn:k,hdaDetailIds:g.initiallyExpanded||i});return this._loadHistoryFromXHR(j,g).fail(function(n,l,m){e.trigger("error",e,n,g,_l("An error was encountered while "+l),{historyId:h,history:m||{}})}).always(function(){e.trigger("loading-done",e)})},loadHistoryWithHDADetails:function(h,g,f,j){var e=this,i=function(k){return e.getExpandedHdaIds(k.id)};return this.loadHistory(h,g,f,j,i)},switchToHistory:function(h,g){var e=this,f=function(){return jQuery.post("/api/histories/"+h+"/set_as_current")};return this.loadHistoryWithHDADetails(h,g,f).then(function(j,i){e.trigger("switched-history",e)})},loadCurrentHistory:function(f){var e=this;return this.loadHistoryWithHDADetails("current",f).then(function(h,g){e.trigger("current-history",e)})},createNewHistory:function(g){var e=this,f=function(){return jQuery.post("/api/histories",{current:true})};return this.loadHistory(undefined,g,f).then(function(i,h){e.trigger("new-history",e)})},refreshHdas:function(f,e){if(this.model){return this.model.refresh(f,e)}return $.when()},_getStorageKey:function(e){if(!e){throw new Error("_getStorageKey needs valid id: "+e)}return("history:"+e)},_setUpWebStorage:function(f,e,g){this.storage=new PersistentStorage(this._getStorageKey(this.model.get("id")),{expandedHdas:{},show_deleted:false,show_hidden:false});this.log(this+" (prev) storage:",JSON.stringify(this.storage.get(),null,2));if(f){this.storage.set("exandedHdas",f)}if((e===true)||(e===false)){this.storage.set("show_deleted",e)}if((g===true)||(g===false)){this.storage.set("show_hidden",g)}this.show_deleted=this.storage.get("show_deleted");this.show_hidden=this.storage.get("show_hidden");this.trigger("new-storage",this.storage,this);this.log(this+" (init'd) storage:",this.storage.get())},clearWebStorage:function(){for(var e in sessionStorage){if(e.indexOf("HistoryView.")===0){sessionStorage.removeItem(e)}}},getStoredOptions:function(f){if(!f||f==="current"){return(this.storage)?(this.storage.get()):({})}var e=sessionStorage.getItem(this._getStorageKey(f));return(e===null)?({}):(JSON.parse(e))},getExpandedHdaIds:function(e){var f=this.getStoredOptions(e).expandedHdas;return((_.isEmpty(f))?([]):(_.keys(f)))},_setUpModelEventHandlers:function(){this.model.on("error error:hdas",function(f,h,e,g){this.errorHandler(f,h,e,g)},this);this.model.on("change:nice_size",this.updateHistoryDiskSize,this);if(Galaxy&&Galaxy.quotaMeter){this.listenTo(this.model,"change:nice_size",function(){Galaxy.quotaMeter.update()})}this.model.hdas.on("add",this.addHdaView,this);this.model.hdas.on("change:deleted",this.handleHdaDeletionChange,this);this.model.hdas.on("change:visible",this.handleHdaVisibleChange,this);this.model.hdas.on("change:purged",function(e){this.model.fetch()},this);this.model.hdas.on("state:ready",function(f,g,e){if((!f.get("visible"))&&(!this.storage.get("show_hidden"))){this.removeHdaView(f.get("id"))}},this)},addHdaView:function(h){this.log("add."+this,h);var f=this;if(!h.isVisible(this.storage.get("show_deleted"),this.storage.get("show_hidden"))){return}$({}).queue([function g(j){var i=f.$el.find("#emptyHistoryMessage");if(i.is(":visible")){i.fadeOut(f.fxSpeed,j)}else{j()}},function e(j){f.scrollToTop();var i=f.$el.find("#"+f.model.get("id")+"-datasets");f.createHdaView(h).$el.hide().prependTo(i).slideDown(f.fxSpeed)}])},createHdaView:function(g){var f=g.get("id"),e=this.storage.get("expandedHdas").get(f),h=new this.HDAView({model:g,expanded:e,hasUser:this.model.hasUser(),logger:this.logger});this._setUpHdaListeners(h);this.hdaViews[f]=h;return h.render()},handleHdaDeletionChange:function(e){if(e.get("deleted")&&!this.storage.get("show_deleted")){this.removeHdaView(e.get("id"))}},handleHdaVisibleChange:function(e){if(e.hidden()&&!this.storage.get("show_hidden")){this.removeHdaView(e.get("id"))}},removeHdaView:function(g){var e=this,f=this.hdaViews[g];if(!f){return}f.$el.fadeOut(e.fxSpeed,function(){f.remove();delete e.hdaViews[g];if(_.isEmpty(e.hdaViews)){e.$el.find("#emptyHistoryMessage").fadeIn(e.fxSpeed)}})},render:function(g){var e=this,f;if(this.model){f=this.renderModel()}else{f=this.renderWithoutModel()}$(e).queue("fx",[function(h){if(e.$el.is(":visible")){e.$el.fadeOut(e.fxSpeed,h)}else{h()}},function(h){e.$el.empty();if(f){e.$el.append(f.children())}e.$el.fadeIn(e.fxSpeed,h)},function(h){e._setUpBehaviours();if(g){g.call(this)}}]);return this},renderModel:function(){var e=$("<div/>");e.append(c.templates.historyPanel(this.model.toJSON()));e.find("[title]").tooltip({placement:"bottom"});if(!this.model.hdas.length||!this.renderItems(e.find("#"+this.model.get("id")+"-datasets"))){e.find("#emptyHistoryMessage").show()}return e},renderWithoutModel:function(){var e=$("<div/>"),f=$("<div/>").attr("id","message-container").css({"margin-left":"4px","margin-right":"4px"});return e.append(f)},renderItems:function(f){this.hdaViews={};var e=this,g=this.model.hdas.getVisible(this.storage.get("show_deleted"),this.storage.get("show_hidden"));_.each(g,function(j){var i=j.get("id"),h=e.storage.get("expandedHdas").get(i);e.hdaViews[i]=new e.HDAView({model:j,expanded:h,hasUser:e.model.hasUser(),logger:e.logger});e._setUpHdaListeners(e.hdaViews[i]);f.prepend(e.hdaViews[i].render().$el)});return g.length},_setUpHdaListeners:function(f){var e=this;f.on("body-expanded",function(g){e.storage.get("expandedHdas").set(g,true)});f.on("body-collapsed",function(g){e.storage.get("expandedHdas").deleteKey(g)});f.on("error",function(h,j,g,i){e.errorHandler(h,j,g,i)})},_setUpBehaviours:function(){if(!this.model||!(this.model.get("user")&&this.model.get("user").email)){return}var e=this,f=this.$("#history-annotation-area");this.$("#history-annotate").click(function(){if(f.is(":hidden")){f.slideDown(e.fxSpeed)}else{f.slideUp(e.fxSpeed)}return false});async_save_text("history-name-container","history-name",this.model.renameUrl(),"new_name",18);async_save_text("history-annotation-container","history-annotation",this.model.annotateUrl(),"new_annotation",18,true,4)},updateHistoryDiskSize:function(){this.$el.find("#history-size").text(this.model.get("nice_size"))},collapseAllHdaBodies:function(){_.each(this.hdaViews,function(e){e.toggleBodyVisibility(null,false)});this.storage.set("expandedHdas",{})},toggleShowDeleted:function(){this.storage.set("show_deleted",!this.storage.get("show_deleted"));this.render();return this.storage.get("show_deleted")},toggleShowHidden:function(){this.storage.set("show_hidden",!this.storage.get("show_hidden"));this.render();return this.storage.get("show_hidden")},loadAndDisplayTags:function(g){this.log(this+".loadAndDisplayTags",g);var e=this,h=this.$el.find("#history-tag-area"),f=h.find(".tag-elt");this.log("\t tagArea",h," tagElt",f);if(h.is(":hidden")){if(!jQuery.trim(f.html())){$.ajax({url:e.model.tagUrl(),error:function(k,j,i){e.log("Error loading tag area html",k,j,i);e.trigger("error",e,k,null,_l("Error loading tags"))},success:function(i){f.html(i);f.find("[title]").tooltip();h.slideDown(e.fxSpeed)}})}else{h.slideDown(e.fxSpeed)}}else{h.slideUp(e.fxSpeed)}return false},showLoadingIndicator:function(f,e,g){e=(e!==undefined)?(e):(this.fxSpeed);if(!this.indicator){this.indicator=new LoadingIndicator(this.$el,this.$el.parent())}if(!this.$el.is(":visible")){this.indicator.show(0,g)}else{this.$el.fadeOut(e);this.indicator.show(e,g)}},hideLoadingIndicator:function(e,f){e=(e!==undefined)?(e):(this.fxSpeed);if(this.indicator){this.indicator.hide(e,f)}},displayMessage:function(j,k,i){var g=this;this.scrollToTop();var h=this.$el.find("#message-container"),e=$("<div/>").addClass(j+"message").html(k);if(!_.isEmpty(i)){var f=$('<a href="javascript:void(0)">Details</a>').click(function(){Galaxy.modal.show(g.messageToModalOptions(j,k,i));return false});e.append(" ",f)}return h.html(e)},messageToModalOptions:function(i,k,h){var e=this,j=$("<div/>"),g={title:"Details"};function f(l){l=_.omit(l,_.functions(l));return["<table>",_.map(l,function(n,m){n=(_.isObject(n))?(f(n)):(n);return'<tr><td style="vertical-align: top; color: grey">'+m+'</td><td style="padding-left: 8px">'+n+"</td></tr>"}).join(""),"</table>"].join("")}if(_.isObject(h)){g.body=j.append(f(h))}else{g.body=j.html(h)}g.buttons={Ok:function(){Galaxy.modal.hide();e.clearMessages()}};return g},clearMessages:function(){var e=this.$el.find("#message-container");e.empty()},scrollPosition:function(){return this.$el.parent().scrollTop()},scrollTo:function(e){this.$el.parent().scrollTop(e)},scrollToTop:function(){this.$el.parent().scrollTop(0);return this},scrollIntoView:function(f,g){if(!g){this.$el.parent().parent().scrollTop(f);return this}var e=window,h=this.$el.parent().parent(),j=$(e).innerHeight(),i=(j/2)-(g/2);$(h).scrollTop(f-i);return this},scrollToId:function(f){if((!f)||(!this.hdaViews[f])){return this}var e=this.hdaViews[f].$el;this.scrollIntoView(e.offset().top,e.outerHeight());return this},scrollToHid:function(e){var f=this.model.hdas.getByHid(e);if(!f){return this}return this.scrollToId(f.id)},connectToQuotaMeter:function(e){if(!e){return this}this.listenTo(e,"quota:over",this.showQuotaMessage);this.listenTo(e,"quota:under",this.hideQuotaMessage);this.on("rendered rendered:initial",function(){if(e&&e.isOverQuota()){this.showQuotaMessage()}});return this},showQuotaMessage:function(){var e=this.$el.find("#quota-message-container");if(e.is(":hidden")){e.slideDown(this.fxSpeed)}},hideQuotaMessage:function(){var e=this.$el.find("#quota-message-container");if(!e.is(":hidden")){e.slideUp(this.fxSpeed)}},connectToOptionsMenu:function(e){if(!e){return this}this.on("new-storage",function(g,f){if(e&&g){e.findItemByHtml(_l("Include Deleted Datasets")).checked=g.get("show_deleted");e.findItemByHtml(_l("Include Hidden Datasets")).checked=g.get("show_hidden")}});return this},toString:function(){return"HistoryPanel("+((this.model)?(this.model.get("name")):(""))+")"}});c.templates={historyPanel:Handlebars.templates["template-history-historyPanel"]};return{HistoryPanel:c}});