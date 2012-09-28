define(["libs/underscore","mvc/data","viz/trackster/util"],function(q,h,j){var i=function(s){return("isResolved" in s)};var e=function(s){this.default_font=s!==undefined?s:"9px Monaco, Lucida Console, monospace";this.dummy_canvas=this.new_canvas();this.dummy_context=this.dummy_canvas.getContext("2d");this.dummy_context.font=this.default_font;this.char_width_px=this.dummy_context.measureText("A").width;this.patterns={};this.load_pattern("right_strand","/visualization/strand_right.png");this.load_pattern("left_strand","/visualization/strand_left.png");this.load_pattern("right_strand_inv","/visualization/strand_right_inv.png");this.load_pattern("left_strand_inv","/visualization/strand_left_inv.png")};q.extend(e.prototype,{load_pattern:function(s,w){var t=this.patterns,u=this.dummy_context,v=new Image();v.src=galaxy_paths.attributes.image_path+w;v.onload=function(){t[s]=u.createPattern(v,"repeat")}},get_pattern:function(s){return this.patterns[s]},new_canvas:function(){var s=$("<canvas/>")[0];if(window.G_vmlCanvasManager){G_vmlCanvasManager.initElement(s)}s.manager=this;return s}});var o=Backbone.Model.extend({defaults:{num_elements:20,obj_cache:null,key_ary:null},initialize:function(s){this.clear()},get_elt:function(t){var u=this.attributes.obj_cache,v=this.attributes.key_ary,s=v.indexOf(t);if(s!==-1){if(u[t].stale){v.splice(s,1);delete u[t]}else{this.move_key_to_end(t,s)}}return u[t]},set_elt:function(t,v){var w=this.attributes.obj_cache,x=this.attributes.key_ary,u=this.attributes.num_elements;if(!w[t]){if(x.length>=u){var s=x.shift();delete w[s]}x.push(t)}w[t]=v;return v},move_key_to_end:function(t,s){this.attributes.key_ary.splice(s,1);this.attributes.key_ary.push(t)},clear:function(){this.attributes.obj_cache={};this.attributes.key_ary=[]},size:function(){return this.attributes.key_ary.length}});var c=o.extend({defaults:q.extend({},o.prototype.defaults,{dataset:null,filters_manager:null,data_type:"data",data_mode_compatible:function(s,t){return true},can_subset:function(s){return false}}),data_is_ready:function(){var u=this.get("dataset"),t=$.Deferred(),s=new j.ServerStateDeferred({ajax_settings:{url:this.get("dataset").url(),data:{hda_ldda:u.get("hda_ldda"),data_type:"state"},dataType:"json"},interval:5000,success_fn:function(v){return v!=="pending"}});$.when(s.go()).then(function(v){t.resolve(v==="ok"||v==="data")});return t},search_features:function(s){var t=this.get("dataset"),u={query:s,hda_ldda:t.get("hda_ldda"),data_type:"features"};return $.getJSON(t.url(),u)},load_data:function(A,z,t,y){var w=this.get("dataset"),v={data_type:this.get("data_type"),chrom:A.get("chrom"),low:A.get("start"),high:A.get("end"),mode:z,resolution:t,hda_ldda:w.get("hda_ldda")};$.extend(v,y);var C=this.get("filters_manager");if(C){var D=[];var s=C.filters;for(var x=0;x<s.length;x++){D.push(s[x].name)}v.filter_cols=JSON.stringify(D)}var u=this,B=$.getJSON(w.url(),v,function(E){u.set_data(A,E)});this.set_data(A,B);return B},get_data:function(y,x,u,w){var z=this.get_elt(y);if(z&&(i(z)||this.get("data_mode_compatible")(z,x))){return z}var A=this.get("key_ary"),t=this.get("obj_cache"),B,s;for(var v=0;v<A.length;v++){B=A[v];s=new f({from_str:B});if(s.contains(y)){z=t[B];if(i(z)||(this.get("data_mode_compatible")(z,x)&&this.get("can_subset")(z))){this.move_key_to_end(B,v);return z}}}return this.load_data(y,x,u,w)},set_data:function(t,s){this.set_elt(t,s)},DEEP_DATA_REQ:"deep",BROAD_DATA_REQ:"breadth",get_more_data:function(A,z,v,y,w){var C=this._mark_stale(A);if(!(C&&this.get("data_mode_compatible")(C,z))){console.log("ERROR: problem with getting more data: current data is not compatible");return}var u=A.get("start");if(w===this.DEEP_DATA_REQ){$.extend(y,{start_val:C.data.length+1})}else{if(w===this.BROAD_DATA_REQ){u=(C.max_high?C.max_high:C.data[C.data.length-1][2])+1}}var B=A.copy().set("start",u);var t=this,x=this.load_data(B,z,v,y),s=$.Deferred();this.set_data(A,s);$.when(x).then(function(D){if(D.data){D.data=C.data.concat(D.data);if(D.max_low){D.max_low=C.max_low}if(D.message){D.message=D.message.replace(/[0-9]+/,D.data.length)}}t.set_data(A,D);s.resolve(D)});return s},get_more_detailed_data:function(v,x,t,w,u){var s=this._mark_stale(v);if(!s){console.log("ERROR getting more detailed data: no current data");return}if(!u){u={}}var x;if(s.dataset_type==="bigwig"){u.num_samples=s.data.length*w}else{if(s.dataset_type==="summary_tree"){u.level=s.level+1}}return this.load_data(v,x,t,u)},_mark_stale:function(t){var s=this.get_elt(t);if(!s){console.log("ERROR: no data to mark as stale: ",this.get("dataset"),t.toString())}s.stale=true;return s},get_elt:function(s){return o.prototype.get_elt.call(this,s.toString())},set_elt:function(t,s){return o.prototype.set_elt.call(this,t.toString(),s)}});var m=c.extend({initialize:function(s){var t=new Backbone.Model();t.urlRoot=s.data_url;this.set("dataset",t)},load_data:function(u,v,s,t){console.log(u,v,s);if(s>1){return{data:null}}return c.prototype.load_data.call(this,u,v,s,t)}});var b=Backbone.Model.extend({defaults:{name:null,key:null,chroms_info:null},initialize:function(s){this.id=s.dbkey},get_chroms_info:function(){return this.attributes.chroms_info.chrom_info},get_chrom_region:function(s){var t=q.find(this.get_chroms_info(),function(u){return u.chrom==s});return new f({chrom:t.chrom,end:t.len})}});var f=Backbone.RelationalModel.extend({defaults:{chrom:null,start:0,end:0,DIF_CHROMS:1000,BEFORE:1001,CONTAINS:1002,OVERLAP_START:1003,OVERLAP_END:1004,CONTAINED_BY:1005,AFTER:1006},initialize:function(t){if(t.from_str){var v=t.from_str.split(":"),u=v[0],s=v[1].split("-");this.set({chrom:u,start:parseInt(s[0],10),end:parseInt(s[1],10)})}},copy:function(){return new f({chrom:this.get("chrom"),start:this.get("start"),end:this.get("end")})},length:function(){return this.get("end")-this.get("start")},toString:function(){return this.get("chrom")+":"+this.get("start")+"-"+this.get("end")},toJSON:function(){return{chrom:this.get("chrom"),start:this.get("start"),end:this.get("end")}},compute_overlap:function(z){var t=this.get("chrom"),y=z.get("chrom"),x=this.get("start"),v=z.get("start"),w=this.get("end"),u=z.get("end"),s;if(t&&y&&t!==y){return this.get("DIF_CHROMS")}if(x<v){if(w<v){s=this.get("BEFORE")}else{if(w<=u){s=this.get("OVERLAP_START")}else{s=this.get("CONTAINS")}}}else{if(x>u){s=this.get("AFTER")}else{if(w<=u){s=this.get("CONTAINED_BY")}else{s=this.get("OVERLAP_END")}}}return s},contains:function(s){return this.compute_overlap(s)===this.get("CONTAINS")},overlaps:function(s){return q.intersection([this.compute_overlap(s)],[this.get("DIF_CHROMS"),this.get("BEFORE"),this.get("AFTER")]).length===0}});var l=Backbone.Collection.extend({model:f});var d=Backbone.RelationalModel.extend({defaults:{region:null,note:""},relations:[{type:Backbone.HasOne,key:"region",relatedModel:f}]});var p=Backbone.Collection.extend({model:d});var r=h.Dataset.extend({initialize:function(s){this.set("id",s.dataset_id);var t=new c({dataset:this});this.set("data_manager",t);var u=this.get("preloaded_data");if(u){t.set("num_elements",u.data.length);q.each(u.data,function(v){t.set_data(v.region,v)})}},get_genome_wide_data:function(s){var t=this.get("data_manager");return q.map(s.get("chroms_info").chrom_info,function(u){return t.get_elt(new f({chrom:u.chrom,start:0,end:u.len}))})}});var n=Backbone.RelationalModel.extend({defaults:{id:"",title:"",type:"",dbkey:"",tracks:null},relations:[{type:Backbone.HasMany,key:"tracks",relatedModel:r}],url:function(){return galaxy_paths.get("visualization_url")},save:function(){return $.ajax({url:this.url(),type:"POST",dataType:"json",data:{vis_json:JSON.stringify(this)}})}});var k=n.extend({defaults:q.extend({},n.prototype.defaults,{bookmarks:null,viewport:null})});var a=Backbone.Model.extend({});var g=Backbone.Router.extend({initialize:function(t){this.view=t.view;this.route(/([\w]+)$/,"change_location");this.route(/([\w]+\:[\d,]+-[\d,]+)$/,"change_location");var s=this;s.view.on("navigate",function(u){s.navigate(u)})},change_location:function(s){this.view.go_to(s)}});return{BrowserBookmark:d,BrowserBookmarkCollection:p,Cache:o,CanvasManager:e,Genome:b,GenomeDataManager:c,GenomeRegion:f,GenomeRegionCollection:l,GenomeVisualization:k,ReferenceTrackDataManager:m,TrackBrowserRouter:g,TrackConfig:a,Visualization:n}});