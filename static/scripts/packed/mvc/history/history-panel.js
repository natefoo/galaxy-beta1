define(["mvc/list/list-panel","mvc/history/history-model","mvc/history/history-contents","mvc/history/hda-li","mvc/history/hdca-li","mvc/collection/collection-panel","mvc/user/user-model","mvc/base-mvc","utils/localization"],function(d,f,l,b,a,m,g,o,e){var j=o.SessionStorageModel.extend({defaults:{expandedIds:{},show_deleted:false,show_hidden:false},addExpanded:function(p){var q="expandedIds";this.save(q,_.extend(this.get(q),_.object([p.id],[p.get("id")])))},removeExpanded:function(p){var q="expandedIds";this.save(q,_.omit(this.get(q),p.id))},toString:function(){return"HistoryPrefs("+this.id+")"}});j.storageKeyPrefix="history:";j.historyStorageKey=function h(p){if(!p){throw new Error("HistoryPrefs.historyStorageKey needs valid id: "+p)}return(j.storageKeyPrefix+p)};j.get=function c(p){return new j({id:j.historyStorageKey(p)})};j.clearAll=function i(q){for(var p in sessionStorage){if(p.indexOf(j.storageKeyPrefix)===0){sessionStorage.removeItem(p)}}};var n=d.ModelListPanel;var k=n.extend({HDAViewClass:b.HDAListItemView,HDCAViewClass:a.HDCAListItemView,collectionClass:l.HistoryContents,modelCollectionKey:"contents",tagName:"div",className:n.prototype.className+" history-panel",emptyMsg:e("This history is empty"),noneFoundMsg:e("No matching datasets found"),searchPlaceholder:e("search datasets"),initialize:function(p){n.prototype.initialize.call(this,p);this.linkTarget=p.linkTarget||"_blank"},freeModel:function(){n.prototype.freeModel.call(this);if(this.model){this.model.clearUpdateTimeout()}return this},_setUpListeners:function(){n.prototype._setUpListeners.call(this);this.on("error",function(q,t,p,s,r){this.errorHandler(q,t,p,s,r)});this.on("loading-done",function(){if(!this.views.length){this.trigger("empty-history",this)}})},loadHistoryWithDetails:function(s,r,q,t){this.info("loadHistoryWithDetails:",s,r,q,t);var p=function(u){return _.values(j.get(u.id).get("expandedIds"))};return this.loadHistory(s,r,q,t,p)},loadHistory:function(t,s,r,u,p){this.info("loadHistory:",t,s,r,u,p);var q=this;s=s||{};q.trigger("loading",q);var v=f.History.getHistoryData(t,{historyFn:r,contentsFn:u,detailIdsFn:s.initiallyExpanded||p});return q._loadHistoryFromXHR(v,s).fail(function(y,w,x){q.trigger("error",q,y,s,e("An error was encountered while "+w),{historyId:t,history:x||{}})}).always(function(){q.trigger("loading-done",q)})},_loadHistoryFromXHR:function(r,q){var p=this;r.then(function(s,t){p.JSONToModel(s,t,q);p.render()});r.fail(function(t,s){p.render()});return r},refreshContents:function(q,p){if(this.model){return this.model.refresh(q,p)}return $.when()},JSONToModel:function(s,p,q){this.log("JSONToModel:",s,p,q);q=q||{};var r=new f.History(s,p,q);this.setModel(r);return r},setModel:function(q,p){p=p||{};n.prototype.setModel.call(this,q,p);if(this.model){this._setUpWebStorage(p.initiallyExpanded,p.show_deleted,p.show_hidden)}},_setUpWebStorage:function(q,p,r){if(this.storage){this.stopListening(this.storage)}this.storage=new j({id:j.historyStorageKey(this.model.get("id"))});if(_.isObject(q)){this.storage.set("expandedIds",q)}if(_.isBoolean(p)){this.storage.set("show_deleted",p)}if(_.isBoolean(r)){this.storage.set("show_hidden",r)}this.trigger("new-storage",this.storage,this);this.log(this+" (init'd) storage:",this.storage.get());this.listenTo(this.storage,{"change:show_deleted":function(s,t){this.showDeleted=t},"change:show_hidden":function(s,t){this.showHidden=t}},this);this.showDeleted=(p!==undefined)?p:this.storage.get("show_deleted");this.showHidden=(r!==undefined)?r:this.storage.get("show_hidden");return this},_buildNewRender:function(){var p=n.prototype._buildNewRender.call(this);if(this.multiselectActions.length){p.find(".controls .actions").prepend(this._renderSelectButton())}return p},_renderSelectButton:function(p){return faIconButton({title:e("Operations on multiple datasets"),classes:"show-selectors-btn",faIcon:"fa-check-square-o"})},_getItemViewClass:function(p){var q=p.get("history_content_type");switch(q){case"dataset":return this.HDAViewClass;case"dataset_collection":return this.HDCAViewClass}throw new TypeError("Unknown history_content_type: "+q)},_filterItem:function(q){var p=this;return(n.prototype._filterItem.call(p,q)&&(!q.hidden()||p.showHidden)&&(!q.isDeletedOrPurged()||p.showDeleted))},_getItemViewOptions:function(q){var p=n.prototype._getItemViewOptions.call(this,q);return _.extend(p,{linkTarget:this.linkTarget,expanded:!!this.storage.get("expandedIds")[q.id],hasUser:this.model.ownedByCurrUser()})},_setUpItemViewListeners:function(q){var p=this;n.prototype._setUpItemViewListeners.call(p,q);q.on("expanded",function(r){p.storage.addExpanded(r.model)});q.on("collapsed",function(r){p.storage.removeExpanded(r.model)});return this},getSelectedModels:function(){var p=n.prototype.getSelectedModels.call(this);p.historyId=this.collection.historyId;return p},events:_.extend(_.clone(n.prototype.events),{"click .show-selectors-btn":"toggleSelectors"}),toggleShowDeleted:function(p,q){p=(p!==undefined)?(p):(!this.showDeleted);q=(q!==undefined)?(q):(true);this.showDeleted=p;if(q){this.storage.set("show_deleted",p)}this.renderItems();return this.showDeleted},toggleShowHidden:function(p,q){p=(p!==undefined)?(p):(!this.showHidden);q=(q!==undefined)?(q):(true);this.showHidden=p;if(q){this.storage.set("show_hidden",p)}this.renderItems();return this.showHidden},_firstSearch:function(p){var q=this,r=".history-search-input";this.log("onFirstSearch",p);if(q.model.contents.haveDetails()){q.searchItems(p);return}q.$el.find(r).searchInput("toggle-loading");q.model.contents.fetchAllDetails({silent:true}).always(function(){q.$el.find(r).searchInput("toggle-loading")}).done(function(){q.searchItems(p)})},errorHandler:function(r,u,q,t,s){this.error(r,u,q,t,s);if(u&&u.status===0&&u.readyState===0){}else{if(u&&u.status===502){}else{var p=this._parseErrorMessage(r,u,q,t,s);if(!this.$messages().is(":visible")){this.once("rendered",function(){this.displayMessage("error",p.message,p.details)})}else{this.displayMessage("error",p.message,p.details)}}}},_parseErrorMessage:function(t,w,x,r,p,u){var s=Galaxy.currUser,v={message:this._bePolite(r),details:{message:r,raven:(window.Raven&&_.isFunction(Raven.lastEventId))?(Raven.lastEventId()):(undefined),agent:navigator.userAgent,url:(window.Galaxy)?(Galaxy.lastAjax.url):(undefined),data:(window.Galaxy)?(Galaxy.lastAjax.data):(undefined),options:(w)?(_.omit(x,"xhr")):(x),xhr:w,source:(_.isFunction(t.toJSON))?(t.toJSON()):(t+""),user:(s instanceof g.User)?(s.toJSON()):(s+"")}};_.extend(v.details,p||{});if(w&&_.isFunction(w.getAllResponseHeaders)){var q=w.getAllResponseHeaders();q=_.compact(q.split("\n"));q=_.map(q,function(y){return y.split(": ")});v.details.xhr.responseHeaders=_.object(q)}return v},_bePolite:function(p){p=p||e("An error occurred while getting updates from the server");return p+". "+e("Please contact a Galaxy administrator if the problem persists")+"."},displayMessage:function(u,v,t){var r=this;this.scrollToTop();var s=this.$messages(),p=$("<div/>").addClass(u+"message").html(v);if(!_.isEmpty(t)){var q=$('<a href="javascript:void(0)">Details</a>').click(function(){Galaxy.modal.show(r._messageToModalOptions(u,v,t));return false});p.append(" ",q)}return s.html(p)},_messageToModalOptions:function(s,v,r){var p=this,q={title:"Details"};if(_.isObject(r)){r=_.omit(r,_.functions(r));var u=JSON.stringify(r,null,"  "),t=$("<pre/>").text(u);q.body=$("<div/>").append(t)}else{q.body=$("<div/>").html(r)}q.buttons={Ok:function(){Galaxy.modal.hide();p.clearMessages()}};return q},clearMessages:function(p){$(p.currentTarget).fadeOut(this.fxSpeed,function(){$(this).remove()});return this},scrollToHid:function(p){return this.scrollToItem(_.first(this.viewsWhereModel({hid:p})))},toString:function(){return"HistoryPanel("+((this.model)?(this.model.get("name")):(""))+")"}});k.prototype.templates=(function(){var p=o.wrapTemplate(['<div class="controls">','<div class="title">','<div class="name"><%= history.name %></div>',"</div>",'<div class="subtitle">',"</div>",'<div class="history-size"><%= history.nice_size %></div>','<div class="actions"></div>','<div class="messages">',"<% if( history.deleted ){ %>",'<div class="deleted-msg warningmessagesmall">',e("This history has been deleted"),"</div>","<% } %>","<% if( history.message ){ %>",'<div class="<%= history.message.level || "info" %>messagesmall">',"<%= history.message.text %>","</div>","<% } %>","</div>",'<div class="tags-display"></div>','<div class="annotation-display"></div>','<div class="search">','<div class="search-input"></div>',"</div>",'<div class="list-actions">','<div class="btn-group">','<button class="select-all btn btn-default"','data-mode="select">',e("All"),"</button>",'<button class="deselect-all btn btn-default"','data-mode="select">',e("None"),"</button>","</div>",'<button class="list-action-popup-btn btn btn-default">',e("For all selected"),"...</button>","</div>","</div>"],"history");return _.extend(_.clone(n.prototype.templates),{controls:p})}());return{HistoryPanel:k}});